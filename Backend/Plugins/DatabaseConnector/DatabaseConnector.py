"""
Vibhu-Oska AI-OS — Database Connector Plugin
Provides thread-safe, non-blocking SQLite relational storage and migration capabilities.
"""

from __future__ import annotations

import asyncio
import os
import sqlite3
from pathlib import Path
from typing import Any

from Backend.Plugins.ConfigLoader.ConfigLoader import ConfigLoader
from Backend.Plugins.ToolRegistry.BaseService import BaseService
from Shared.Models import PluginInfo, CoreStatus, ExecutionTarget


class DatabaseConnector(BaseService):
    """
    SQLite Relational Database Connector Service.
    Wraps standard SQL operations with non-blocking executors and handles database migrations.
    """

    def __init__(self, db_path: str | None = None) -> None:
        self._db_path = db_path
        self._initialized = False

    def info(self) -> PluginInfo:
        return PluginInfo(
            name="database_connector",
            version="0.1.0",
            description="Manages relational SQLite memory & migrations for user profiles and chat/telemetry logs.",
            capabilities=["relational_db", "query_execution", "migrations"],
            status=CoreStatus.HEALTHY if self._initialized else CoreStatus.UNKNOWN,
            preferred_target=ExecutionTarget.CPU,
        )

    async def initialize(self) -> None:
        """Lifecycle hook: resolve configuration, create database file and run migrations."""
        if self._initialized:
            return

        # Resolve db_path if not explicitly provided
        if not self._db_path:
            config = ConfigLoader.load()
            db_rel_path = config.get("memory.relational.database_path", "Data/vibhu_oska.db")
            self._db_path = str(config.project_root / db_rel_path)

        # Ensure directory exists
        db_dir = Path(self._db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)

        # Run initial migrations in background thread
        await asyncio.to_thread(self._run_migrations)
        self._initialized = True

    async def shutdown(self) -> None:
        """Lifecycle hook: cleanup database resources."""
        # sqlite3 connections are opened per query/transaction in the executor,
        # so no persistent connection pool needs to be shut down.
        self._initialized = False

    def health_check(self) -> bool:
        """Check if database file exists and is writable."""
        if not self._db_path:
            return False
        try:
            conn = sqlite3.connect(self._db_path)
            conn.execute("SELECT 1")
            conn.close()
            return True
        except Exception:
            return False

    async def execute(self, action: str, **kwargs: Any) -> Any:
        """
        Execute SQL commands or migrations.

        Actions:
            - "query": Run SELECT query. Returns list of dictionaries.
              Args: query (str), params (tuple)
            - "execute": Run INSERT/UPDATE/DELETE. Returns lastrowid or rowcount.
              Args: query (str), params (tuple)
            - "migrate": Force runs migrations.
        """
        if not self._initialized:
            await self.initialize()

        if action == "query":
            query = kwargs.get("query")
            params = kwargs.get("params", ())
            if not query:
                raise ValueError("Argument 'query' is required for action 'query'.")
            return await asyncio.to_thread(self._run_query, query, params)

        elif action == "execute":
            query = kwargs.get("query")
            params = kwargs.get("params", ())
            if not query:
                raise ValueError("Argument 'query' is required for action 'execute'.")
            return await asyncio.to_thread(self._run_execute, query, params)

        elif action == "migrate":
            await asyncio.to_thread(self._run_migrations)
            return True

        else:
            raise ValueError(f"Action '{action}' is not supported by DatabaseConnector.")

    # ══════════════════════════════════════════════════════════════════════
    # Threaded Synchronous Workloads
    # ══════════════════════════════════════════════════════════════════════

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _run_query(self, query: str, params: tuple) -> list[dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def _run_execute(self, query: str, params: tuple) -> dict[str, Any]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return {
                "lastrowid": cursor.lastrowid,
                "rowcount": cursor.rowcount
            }

    def _run_migrations(self) -> None:
        """Runs the base migrations to prepare tables."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # 1. Users Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    username TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # 2. Sessions Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    title TEXT DEFAULT 'New Session',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(user_id) REFERENCES users(user_id)
                );
            """)

            # 3. Chats/Messages Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS chats (
                    message_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    token_count INTEGER DEFAULT 0,
                    metadata_json TEXT DEFAULT '{}',
                    FOREIGN KEY(session_id) REFERENCES sessions(session_id)
                );
            """)

            # 4. Telemetry/System Logs Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS telemetry_logs (
                    log_id TEXT PRIMARY KEY,
                    source TEXT NOT NULL,
                    level TEXT NOT NULL,
                    message TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    details_json TEXT DEFAULT '{}'
                );
            """)

            # Seed default system user if not exists
            cursor.execute("SELECT 1 FROM users WHERE user_id = 'system'")
            if not cursor.fetchone():
                cursor.execute("INSERT INTO users (user_id, username) VALUES ('system', 'System')")
                cursor.execute("INSERT INTO users (user_id, username) VALUES ('operator', 'Operator')")

            # 5. Knowledge Graph Nodes Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS kg_nodes (
                    entity TEXT PRIMARY KEY,
                    type TEXT NOT NULL,
                    description TEXT
                );
            """)

            # 6. Knowledge Graph Edges Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS kg_edges (
                    source TEXT NOT NULL,
                    target TEXT NOT NULL,
                    relation TEXT NOT NULL,
                    weight REAL DEFAULT 1.0,
                    PRIMARY KEY (source, target, relation),
                    FOREIGN KEY(source) REFERENCES kg_nodes(entity) ON DELETE CASCADE,
                    FOREIGN KEY(target) REFERENCES kg_nodes(entity) ON DELETE CASCADE
                );
            """)

            # Seed default knowledge graph entities if empty
            cursor.execute("SELECT COUNT(*) FROM kg_nodes")
            if cursor.fetchone()[0] == 0:
                # Seed nodes
                default_nodes = [
                    ("eOzka", "company", "Operational holding company built to construct enterprise-grade systems and extend human capability."),
                    ("Harsh Dev Jha", "person", "Founder, Chairperson, and prime architect of eOzka."),
                    ("Krishyangi Dixit", "person", "CEO of eOzka, driving operations and subsidiary velocity."),
                    ("Mrinal Prakash", "person", "CSO of eOzka, defining the multi-sector expansion roadmap."),
                    ("Aman Chapadiya", "person", "COO of eOzka, managing physical and digital machinery."),
                    ("Pratham Sharma", "person", "CTO of eOzka, spearheading product engineering and system scalability."),
                    ("Mahin", "person", "CPO of eOzka, translating complex user needs into beautiful products."),
                    ("Rishita", "person", "CDO of eOzka, maintaining institutional memory and precision documentation."),
                    ("Stress-Calculator", "product", "Biometric mobile health app developed in Flutter/Dart to assess psychological and physical stress."),
                    ("Entab-D", "product", "Browser extension for automatic category/workspace-based tab sorting and grouping."),
                    ("AIris-Security", "product", "Automated threat intelligence and vulnerability scanner for codebases."),
                    ("Paradigm-Shift", "product", "Centralized strategic orchestration system for decentralized eOzka APIs."),
                    ("MOCE", "subsidiary", "Mind of Core Engineering, the primary software development house of eOzka."),
                    ("MOCK", "subsidiary", "Research, exploration, and bio-engineering arm of eOzka.")
                ]
                cursor.executemany("INSERT OR IGNORE INTO kg_nodes (entity, type, description) VALUES (?, ?, ?)", default_nodes)

                # Seed edges
                default_edges = [
                    ("Harsh Dev Jha", "eOzka", "founded", 1.0),
                    ("Krishyangi Dixit", "eOzka", "leads_as_ceo", 1.0),
                    ("Mrinal Prakash", "eOzka", "aligns_strategy_as_cso", 1.0),
                    ("Aman Chapadiya", "eOzka", "manages_operations_as_coo", 1.0),
                    ("Pratham Sharma", "eOzka", "directs_technology_as_cto", 1.0),
                    ("Mahin", "eOzka", "designs_products_as_cpo", 1.0),
                    ("Rishita", "eOzka", "manages_docs_as_cdo", 1.0),
                    ("MOCE", "eOzka", "subsidiary_of", 1.0),
                    ("MOCK", "eOzka", "research_arm_of", 1.0),
                    ("Stress-Calculator", "MOCE", "developed_by", 1.0),
                    ("Entab-D", "MOCE", "developed_by", 1.0),
                    ("AIris-Security", "eOzka", "developed_by", 1.0),
                    ("Paradigm-Shift", "eOzka", "developed_by", 1.0)
                ]
                cursor.executemany("INSERT OR IGNORE INTO kg_edges (source, target, relation, weight) VALUES (?, ?, ?, ?)", default_edges)

            conn.commit()
