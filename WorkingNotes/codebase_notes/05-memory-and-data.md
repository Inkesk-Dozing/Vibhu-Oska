# 05 — Memory & Data (DataCore)

## What It Is

DataCore is the dual-memory system — it holds everything the AI knows about past conversations, domain knowledge, and entity relationships.

```
File: Backend/Core/SpecializedCore/DataCore/datacore.py
Size: 14.3KB
```

## Two Memory Systems

### 1. Semantic Memory (ChromaDB — Vector Store)

ChromaDB stores text chunks as high-dimensional embedding vectors. When a new prompt arrives, the system queries ChromaDB for the `top_k` most semantically similar chunks from past interactions.

```python
# Store a memory
await data_core.store_memory(content="Vibhu-Oska is...", source="chat", metadata={...})

# Retrieve relevant memories
results = await data_core.query_memory(prompt="What is Vibhu-Oska?", top_k=1)
# Returns: [{"content": "...", "source": "...", "score": 0.87}]
```

ChromaDB uses its default embedding model (sentence-transformers/all-MiniLM-L6-v2) unless overridden.

### 2. Relational Memory (SQLite)

SQLite stores structured, queryable state. All sessions, chat messages, and telemetry events live here.

**Schema:**
```sql
sessions (
    session_id TEXT PRIMARY KEY,
    user_id TEXT,
    created_at REAL,
    updated_at REAL
)

chat_messages (
    message_id TEXT PRIMARY KEY,
    session_id TEXT,
    role TEXT,             -- "user" | "assistant"
    content TEXT,
    timestamp REAL
)

telemetry_events (
    event_id TEXT PRIMARY KEY,
    topic TEXT,
    source TEXT,
    payload TEXT,          -- JSON
    timestamp REAL
)

kg_nodes (
    node_id TEXT PRIMARY KEY,
    entity TEXT,
    entity_type TEXT,
    description TEXT,
    metadata TEXT          -- JSON
)

kg_edges (
    edge_id TEXT PRIMARY KEY,
    source_node TEXT,
    target_node TEXT,
    relation TEXT,
    weight REAL
)
```

### 3. Knowledge Graph (GraphRAG / GRAG)

The `kg_nodes` and `kg_edges` tables form a local knowledge graph. DataCore's `query_knowledge_graph()` method performs:

1. **Entity matching**: Find nodes where `entity` text matches words in the prompt (LIKE query)
2. **1-hop traversal**: For each matched node, retrieve all directly connected nodes via `kg_edges`
3. **Context assembly**: Format the entity + relationships into a readable context string

```python
kg_context = await data_core.query_knowledge_graph("What does eOzka mean?")
# → "eOzka [concept]: The echo of OSKA. RELATES_TO → OSKA [system], OSKA [system]: ..."
```

The seed knowledge graph is populated at startup with Vibhu-Oska's own domain entities (inkesk, OSKA, Vibhu, the architectural cores, etc.).

## DataCore Methods Reference

| Method | Purpose |
|---|---|
| `initialize(registry)` | Connect to ChromaDB + SQLite, run migrations, seed KG |
| `create_session(session_id, user_id)` | Upsert session into SQLite |
| `save_chat_message(msg_id, session_id, role, content)` | Persist a turn |
| `get_session_history(session_id, limit)` | Return recent turns as list of dicts |
| `store_memory(content, source, metadata)` | Embed + store in ChromaDB |
| `query_memory(prompt, top_k)` | Vector similarity search |
| `query_knowledge_graph(prompt)` | GRAG entity matching + 1-hop traversal |
| `shutdown()` | Close ChromaDB + SQLite connections |

## Why Two Systems?

SQLite alone would require exact or pattern-matched queries — useless for semantic "find me something related to this prompt" retrieval. ChromaDB alone has no concept of structured sessions, timestamps, or relational queries. The combination gives Vibhu-Oska both:
- **Associative memory** (find related things you've seen before)
- **Episodic memory** (remember exactly what was said, when, in which session)

The GRAG layer adds **semantic structure** — not just "related content" but "known entities with defined relationships."
