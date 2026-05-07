"""
Vibhu-Oska AI-OS — DataCore (Memory & Storage)
Coordinates vector-semantic (ChromaDB) and relational (SQLite) dual-memory engines.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from pathlib import Path
from typing import Any

import chromadb

from Backend.Plugins.ConfigLoader.ConfigLoader import ConfigLoader
from Backend.Plugins.ToolRegistry.Registry import ToolRegistry


class DataCore:
    """
    Central specialized memory layer for Vibhu-Oska.
    Manages vector embeddings (long-term semantic memory) and SQLite records (short-term relational state).
    """

    def __init__(self) -> None:
        self._registry: ToolRegistry | None = None
        self._db: Any = None  # DatabaseConnector
        self._cache: Any = None  # CacheManager
        self._chroma_client: chromadb.PersistentClient | None = None
        self._default_collection_name = "vibhu_oska_memory"
        self._initialized = False

    async def initialize(self, registry: ToolRegistry) -> None:
        """Initialize connection to relational DB connector, cache manager, and vector DB."""
        if self._initialized:
            return

        self._registry = registry
        
        # Get relational DB and cache plugins
        self._db = registry.get("database_connector")
        self._cache = registry.get("cache_manager")

        # Resolve ChromaDB settings
        config = ConfigLoader.load()
        chroma_rel_path = config.get("memory.vector.persist_directory", "Data/chromadb")
        persist_dir = str(config.project_root / chroma_rel_path)
        self._default_collection_name = config.get("memory.vector.default_collection", "vibhu_oska_memory")

        # Initialize ChromaDB in thread pool
        await asyncio.to_thread(self._init_chroma, persist_dir)

        # Run warm cache preloading
        await self.warm_cache()
        self._initialized = True

    def _init_chroma(self, persist_dir: str) -> None:
        Path(persist_dir).mkdir(parents=True, exist_ok=True)
        self._chroma_client = chromadb.PersistentClient(path=persist_dir)

    async def shutdown(self) -> None:
        """Teardown DataCore."""
        self._chroma_client = None
        self._initialized = False

    # ══════════════════════════════════════════════════════════════════════
    # Relational Memory (SQLite via DatabaseConnector)
    # ══════════════════════════════════════════════════════════════════════

    async def create_session(self, session_id: str, user_id: str, title: str = "New Session") -> None:
        """Create a new chat session in the database."""
        query = """
            INSERT OR IGNORE INTO sessions (session_id, user_id, title, created_at, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """
        await self._db.execute("execute", query=query, params=(session_id, user_id, title))
        
        # Cache the session details
        await self._cache.execute("set", key=f"session:{session_id}", value={
            "session_id": session_id,
            "user_id": user_id,
            "title": title
        })

    async def save_chat_message(
        self,
        message_id: str,
        session_id: str,
        role: str,
        content: str,
        metadata: dict[str, Any] | None = None
    ) -> None:
        """Save a new chat message and update the session updated time."""
        meta_json = json.dumps(metadata or {})
        query = """
            INSERT INTO chats (message_id, session_id, role, content, timestamp, token_count, metadata_json)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, 0, ?)
        """
        await self._db.execute("execute", query=query, params=(message_id, session_id, role, content, meta_json))

        # Update session timestamp
        update_session_query = "UPDATE sessions SET updated_at = CURRENT_TIMESTAMP WHERE session_id = ?"
        await self._db.execute("execute", query=update_session_query, params=(session_id,))

        # Invalidate the cache for this session's history
        await self._cache.execute("delete", key=f"session_history:{session_id}")

    async def get_session_history(self, session_id: str, limit: int = 20) -> list[dict[str, Any]]:
        """Get recent chat message history for a session, checking cache first."""
        cache_key = f"session_history:{session_id}"
        cached = await self._cache.execute("get", key=cache_key)
        if cached is not None:
            return cached[:limit]

        query = """
            SELECT message_id, role, content, timestamp, metadata_json
            FROM chats
            WHERE session_id = ?
            ORDER BY timestamp DESC, rowid DESC
            LIMIT ?
        """
        rows = await self._db.execute("query", query=query, params=(session_id, limit))
        
        # Reverse to return in chronological order
        history = list(reversed(rows))
        
        # Parse metadata JSON
        for msg in history:
            try:
                msg["metadata"] = json.loads(msg["metadata_json"]) if msg.get("metadata_json") else {}
            except Exception:
                msg["metadata"] = {}
            if "metadata_json" in msg:
                del msg["metadata_json"]

        # Cache it
        await self._cache.execute("set", key=cache_key, value=history)
        return history

    async def get_user_profile(self, user_id: str) -> dict[str, Any] | None:
        """Fetch a user profile by ID, using cache if hit."""
        cache_key = f"user:{user_id}"
        cached = await self._cache.execute("get", key=cache_key)
        if cached is not None:
            return cached

        query = "SELECT user_id, username, created_at FROM users WHERE user_id = ?"
        rows = await self._db.execute("query", query=query, params=(user_id,))
        if not rows:
            return None

        profile = rows[0]
        await self._cache.execute("set", key=cache_key, value=profile)
        return profile

    # ==================================================================================================

    # # Internal Separation Division

    # =================─────────────────────────────────────────────────────────────────────────────────

    # ══════════════════════════════════════════════════════════════════════
    # Vector Semantic Memory (ChromaDB)
    # ══════════════════════════════════════════════════════════════════════

    async def store_memory(
        self,
        content: str,
        collection_name: str | None = None,
        tags: dict[str, str] | None = None,
        source: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Store a semantic text chunk in ChromaDB with metadata tags.

        Parameters:
            content: Text content to embed and store.
            collection_name: Target ChromaDB collection (default if None).
            tags: Flat string-keyed metadata dict for ChromaDB.
            source: Logical source label — merged into metadata if provided.
            metadata: Arbitrary metadata dict — merged with tags if provided.
        Returns: None
        Edge cases: All metadata values are coerced to strings for ChromaDB compatibility.
        """
        col_name = collection_name or self._default_collection_name
        doc_id = str(uuid.uuid4())

        # Merge all metadata sources — ChromaDB requires str values only
        meta: dict[str, str] = {}
        if tags:
            meta.update({k: str(v) for k, v in tags.items()})
        if metadata:
            meta.update({k: str(v) for k, v in metadata.items()})
        if source:
            meta["source"] = source

        await asyncio.to_thread(self._chroma_add, col_name, doc_id, content, meta)

    def _chroma_add(self, col_name: str, doc_id: str, content: str, meta: dict[str, str]) -> None:
        col = self._chroma_client.get_or_create_collection(name=col_name)
        col.add(
            documents=[content],
            metadatas=[meta],
            ids=[doc_id]
        )

    async def query_memory(
        self,
        query_text: str,
        collection_name: str | None = None,
        top_k: int = 5,
        min_relevance: float = 0.0
    ) -> list[dict[str, Any]]:
        """Query semantic memories matching query text."""
        col_name = collection_name or self._default_collection_name
        
        results = await asyncio.to_thread(self._chroma_query, col_name, query_text, top_k)
        if not results or not results.get("documents") or not results["documents"][0]:
            return []

        formatted = []
        docs = results["documents"][0]
        metadatas = results["metadatas"][0] if results.get("metadatas") else [{}] * len(docs)
        ids = results["ids"][0]
        
        # Calculate distances/scores if available
        distances = results.get("distances", [[0.0] * len(docs)])[0]

        for i in range(len(docs)):
            # Convert distance to relevance score (Chroma returns L2 distance by default, so lower is closer)
            # A simple metric: 1 / (1 + distance)
            score = round(1.0 / (1.0 + distances[i]), 4)
            if score < min_relevance:
                continue

            meta = metadatas[i] if metadatas[i] is not None else {}
            formatted.append({
                "source": meta.get("source", "chromadb"),
                "content": docs[i],
                "relevance_score": score,
                "metadata": meta,
                "id": ids[i]
            })

        return formatted

    def _chroma_query(self, col_name: str, query_text: str, top_k: int) -> dict[str, Any]:
        col = self._chroma_client.get_or_create_collection(name=col_name)
        return col.query(
            query_texts=[query_text],
            n_results=top_k
        )

    # ══════════════════════════════════════════════════════════════════════
    # Cache Warming & Preloading
    # ══════════════════════════════════════════════════════════════════════

    async def warm_cache(self) -> None:
        """Preload the most recent 10 active chat sessions and system user profiles on startup."""
        try:
            # 1. Warm User Profiles
            users_query = "SELECT user_id, username, created_at FROM users LIMIT 10"
            users = await self._db.execute("query", query=users_query)
            for user in users:
                await self._cache.execute("set", key=f"user:{user['user_id']}", value=user)

            # 2. Warm Recent Sessions
            sessions_query = "SELECT session_id, user_id, title FROM sessions ORDER BY updated_at DESC LIMIT 10"
            sessions = await self._db.execute("query", query=sessions_query)
            for sess in sessions:
                await self._cache.execute("set", key=f"session:{sess['session_id']}", value=sess)
                
                # Fetch and cache recent history for these active sessions
                await self.get_session_history(sess["session_id"], limit=20)
                
        except Exception:
            # Silently tolerate warm-cache issues during initial skeleton setups
            pass

    async def query_knowledge_graph(self, query_text: str) -> str:
        """
        Retrieves matching entities and their 1-hop relationships from the SQLite Knowledge Graph.
        """
        if not self._initialized:
            return ""

        try:
            # Get all nodes to match against
            nodes = await self._db.execute("query", query="SELECT entity, type, description FROM kg_nodes")
            if not nodes:
                return ""

            matched_entities = []
            query_lower = query_text.lower()
            for node in nodes:
                entity = node["entity"]
                # Case-insensitive substring match
                if entity.lower() in query_lower:
                    matched_entities.append(entity)
                else:
                    # Also check individual words for person names (e.g. "Harsh" matches "Harsh Dev Jha")
                    words = entity.split()
                    if len(words) > 1 and any(w.lower() in query_lower for w in words if len(w) > 3):
                        matched_entities.append(entity)

            if not matched_entities:
                return ""

            # Dedup matched entities
            matched_entities = list(set(matched_entities))

            # Retrieve nodes details
            placeholders = ",".join("?" for _ in matched_entities)
            nodes_query = f"SELECT entity, type, description FROM kg_nodes WHERE entity IN ({placeholders})"
            matched_nodes = await self._db.execute("query", query=nodes_query, params=tuple(matched_entities))

            # Retrieve 1-hop edges
            edges_query = f"""
                SELECT source, target, relation, weight 
                FROM kg_edges 
                WHERE source IN ({placeholders}) OR target IN ({placeholders})
            """
            params = tuple(matched_entities) + tuple(matched_entities)
            matched_edges = await self._db.execute("query", query=edges_query, params=params)

            # Format context
            lines = ["Knowledge Graph Context:"]
            lines.append("Entities:")
            for node in matched_nodes:
                lines.append(f"- {node['entity']} ({node['type']}): {node['description']}")
            
            if matched_edges:
                lines.append("Relationships:")
                for edge in matched_edges:
                    lines.append(f"- {edge['source']} --[{edge['relation']}]--> {edge['target']} (weight: {edge['weight']})")

            return "\n".join(lines)

        except Exception as e:
            # Log or handle exception gracefully
            return f"Error retrieving knowledge graph context: {str(e)}"
