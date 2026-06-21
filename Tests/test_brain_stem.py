"""
Vibhu-Oska AI-OS — Stage 2 Integration Tests
Verifies the database connector, cache manager, DataCore, ValidationCore,
BackupCore, HybridCore, and Orchestrator core event loops.

Run: python -m pytest Tests/test_brain_stem.py -v
"""

from __future__ import annotations

import asyncio
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any

import pytest

from Backend.Core.BackupCore.BackupCore import BackupCore
from Backend.Core.EventBus.EventBus import EventBus
from Backend.Core.EventBus.Events import Event, EventFactory
from Backend.Core.EventBus.Topics import Topics
from Backend.Core.MainCore.HybridCore.HybridCore import HybridCore
from Backend.Core.MainCore.CognitionCore.cognition import CognitionCore
from Backend.Core.MainCore.OrchestratorCore.OrchestratorCore import OrchestratorCore
from Backend.Core.MainCore.ValidationCore.validation import ValidationCore
from Backend.Core.SpecializedCore.DataCore.datacore import DataCore
from Backend.Plugins.CacheManager.CacheManager import CacheManager
from Backend.Plugins.DatabaseConnector.DatabaseConnector import DatabaseConnector
from Backend.Plugins.ToolRegistry.Registry import ToolRegistry
from Shared.Models import TaskRequest, TaskResponse, StatusCode, ExecutionTarget, CoreStatus


# ══════════════════════════════════════════════════════════════════════════════
# Fixtures
# ══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def temp_dir():
    path = tempfile.mkdtemp()
    yield Path(path)
    shutil.rmtree(path, ignore_errors=True)


@pytest.fixture
def db_path(temp_dir):
    return str(temp_dir / "test_oska.db")


@pytest.fixture
def chroma_dir(temp_dir):
    return str(temp_dir / "chroma")


# ══════════════════════════════════════════════════════════════════════════════
# Test: DatabaseConnector Plugin
# ══════════════════════════════════════════════════════════════════════════════

class TestDatabaseConnector:
    @pytest.mark.asyncio
    async def test_db_setup_and_migrations(self, db_path):
        db = DatabaseConnector(db_path=db_path)
        await db.initialize()
        
        assert db.health_check() is True
        
        # Verify default seeded users
        users = await db.execute("query", query="SELECT * FROM users")
        assert len(users) == 2
        user_ids = {u["user_id"] for u in users}
        assert "system" in user_ids
        assert "operator" in user_ids

        # Test simple insert and retrieve
        await db.execute("execute", query="INSERT INTO users (user_id, username) VALUES (?, ?)", params=("test_user", "Test"))
        res = await db.execute("query", query="SELECT username FROM users WHERE user_id = ?", params=("test_user",))
        assert len(res) == 1
        assert res[0]["username"] == "Test"
        
        await db.shutdown()


# ══════════════════════════════════════════════════════════════════════════════
# Test: CacheManager Plugin
# ══════════════════════════════════════════════════════════════════════════════

class TestCacheManager:
    @pytest.mark.asyncio
    async def test_cache_lru_and_ttl(self):
        cache = CacheManager(max_size=3, default_ttl=2)
        await cache.initialize()

        # Set and get
        await cache.execute("set", key="a", value="val_a")
        assert await cache.execute("get", key="a") == "val_a"

        # Cache eviction (LRU check)
        await cache.execute("set", key="b", value="val_b")
        await cache.execute("set", key="c", value="val_c")
        # Access 'a' to make it recently used
        await cache.execute("get", key="a")
        # Add 'd' to cause eviction of 'b' (since 'b' is least recently used now)
        await cache.execute("set", key="d", value="val_d")
        
        assert await cache.execute("get", key="b") is None
        assert await cache.execute("get", key="a") == "val_a"

        # TTL check
        await cache.execute("set", key="expired_key", value="123", ttl=0)
        await asyncio.sleep(0.01)
        assert await cache.execute("get", key="expired_key") is None
        
        await cache.shutdown()


# ══════════════════════════════════════════════════════════════════════════════
# Test: DataCore (Dual-Memory System)
# ══════════════════════════════════════════════════════════════════════════════

class TestDataCore:
    @pytest.mark.asyncio
    async def test_dual_memory(self, db_path, chroma_dir):
        # Setup registry
        registry = ToolRegistry()
        db = DatabaseConnector(db_path=db_path)
        cache = CacheManager()
        await registry.register_and_init(db)
        await registry.register_and_init(cache)

        # Environment mock settings for Chroma
        os.environ["VIBHU_OSKA__memory__vector__persist_directory"] = chroma_dir
        os.environ["VIBHU_OSKA__memory__vector__default_collection"] = "test_collection"

        datacore = DataCore()
        await datacore.initialize(registry)

        # 1. Relational chats
        session_id = "session_x"
        await datacore.create_session(session_id, "operator", "Test Session")
        await datacore.save_chat_message("m1", session_id, "user", "Hello Oska")
        await datacore.save_chat_message("m2", session_id, "assistant", "Hello! How can I help?")

        history = await datacore.get_session_history(session_id)
        assert len(history) == 2
        assert history[0]["role"] == "user"
        assert history[0]["content"] == "Hello Oska"
        assert history[1]["role"] == "assistant"
        assert history[1]["content"] == "Hello! How can I help?"

        # 2. Vector Semantic memory
        await datacore.store_memory("Paris is the capital of France.", tags={"source": "geography"})
        await datacore.store_memory("Water boils at 100 degrees Celsius.", tags={"source": "science"})

        memories = await datacore.query_memory("What is the capital of France?", top_k=1)
        assert len(memories) == 1
        assert "Paris" in memories[0]["content"]
        assert memories[0]["metadata"]["source"] == "geography"

        await datacore.shutdown()
        await registry.shutdown_all()


# ══════════════════════════════════════════════════════════════════════════════
# Test: ValidationCore Safety Checks
# ══════════════════════════════════════════════════════════════════════════════

class TestValidationCore:
    def test_validation_bounds_and_safety(self):
        val = ValidationCore()
        val.initialize()

        # Valid input package
        valid_pkg = {
            "prompt": "Tell me a story",
            "type": 1,
            "metadata": {
                "request_id": "req-1",
                "session_id": "sess-1",
                "user_id": "operator"
            }
        }
        is_ok, reason = val.validate_input_package(valid_pkg)
        assert is_ok is True

        # SQL Injection safety test
        sql_inj = valid_pkg.copy()
        sql_inj["prompt"] = "DROP TABLE users;"
        is_ok, reason = val.validate_input_package(sql_inj)
        assert is_ok is False
        assert "Security violation" in reason

        # HTML script safety test
        html_inj = valid_pkg.copy()
        html_inj["prompt"] = "Hello <script>alert(1)</script>"
        is_ok, reason = val.validate_input_package(html_inj)
        assert is_ok is False

        # Output compliance test
        valid_response = TaskResponse(content="Success response")
        is_ok, reason = val.validate_ai_output(valid_response)
        assert is_ok is True

        invalid_response = {"content": ""}
        is_ok, reason = val.validate_ai_output(invalid_response)
        assert is_ok is False


# ══════════════════════════════════════════════════════════════════════════════
# Test: BackupCore & HybridCore routing
# ══════════════════════════════════════════════════════════════════════════════

class TestCoreFailover:
    @pytest.mark.asyncio
    async def test_backup_core_rules(self):
        backup = BackupCore()
        
        # Test rules triggers
        resp_help = await backup.generate("Show me help info")
        assert "supports: system status checks" in resp_help.content
        assert resp_help.metadata.status.code == StatusCode.COMPLETED

        # Test queue trigger (not matched by static rules)
        resp_queue = await backup.generate("Compute 5 + 5")
        assert "queued for execution" in resp_queue.content
        assert resp_queue.metadata.status.code == StatusCode.PENDING
        assert backup.queue_size == 1

        queued = backup.flush_queue()
        assert len(queued) == 1
        assert queued[0]["prompt"] == "Compute 5 + 5"
        assert backup.queue_size == 0

    @pytest.mark.asyncio
    async def test_hybrid_core_failover(self):
        class BrokenCognition(CognitionCore):
            async def generate(self, *args, **kwargs):
                raise RuntimeError("Primary model inference offline")

        primary = BrokenCognition()
        backup = BackupCore()
        hybrid = HybridCore(primary_cognition=primary, backup_core=backup)
        await hybrid.initialize()

        # Primary is down, should route to backup core automatically
        resp = await hybrid.process_request("hello")
        assert resp.metadata.executed_on == ExecutionTarget.CPU
        assert "running in Backup Core mode" in resp.content
        assert hybrid.status == CoreStatus.DEGRADED


# ══════════════════════════════════════════════════════════════════════════════
# Test: Orchestrator Loop Integration
# ══════════════════════════════════════════════════════════════════════════════

class TestOrchestratorEventLoop:
    @pytest.mark.asyncio
    async def test_orchestrator_flow(self, db_path, chroma_dir):
        # 1. Setup bus
        bus = EventBus(pub_port=5591, sub_port=5592, push_port=5593, pull_port=5594)
        await bus.start()

        # 2. Setup registry
        registry = ToolRegistry()
        db = DatabaseConnector(db_path=db_path)
        cache = CacheManager()
        
        # Mock class for Cognition to bypass actual HTTP requests
        class MockCognition(CognitionCore):
            async def initialize(self):
                pass
            async def generate(self, prompt, **kwargs):
                from Shared.Models import ResponseMetadata, Status, StatusCode
                return TaskResponse(
                    content=f"Echo: {prompt}",
                    metadata=ResponseMetadata(
                        status=Status(code=StatusCode.COMPLETED, message="Success")
                    )
                )

        await registry.register_and_init(db)
        await registry.register_and_init(cache)
        await registry.register_and_init(MockCognition())

        # Mock settings for Chroma inside tests
        os.environ["VIBHU_OSKA__memory__vector__persist_directory"] = chroma_dir
        os.environ["VIBHU_OSKA__memory__vector__default_collection"] = "test_collection"

        # 3. Setup Orchestrator
        orch = OrchestratorCore()
        await orch.start(bus, registry)

        # 4. Listen for results
        completions = []
        async def on_completed(event):
            completions.append(event)

        await bus.subscribe(Topics.TASK_COMPLETED, on_completed)

        # Give ZeroMQ subscriptions time to propagate
        await asyncio.sleep(0.2)

        # 5. Fire user input
        input_event = EventFactory.user_input("hello computer", session_id="sess_test", user_id="operator")
        await bus.publish(input_event)

        # 6. Wait for event loop processing
        for _ in range(50):
            if completions:
                break
            await asyncio.sleep(0.05)

        assert len(completions) == 1
        payload = completions[0].payload
        assert payload["content"] == "Echo: hello computer"
        assert payload["metadata"]["status"]["code"] == StatusCode.COMPLETED

        # Cleanup
        await orch.shutdown()
        await registry.shutdown_all()
        await bus.stop()


# ══════════════════════════════════════════════════════════════════════════════
# Test: GraphRAG, MonitoringCore, OptimizationCore
# ══════════════════════════════════════════════════════════════════════════════

class TestGraphRAGAndSubCores:
    @pytest.mark.asyncio
    async def test_knowledge_graph_seeding_and_retrieval(self, db_path, chroma_dir):
        registry = ToolRegistry()
        db = DatabaseConnector(db_path=db_path)
        cache = CacheManager()
        await registry.register_and_init(db)
        await registry.register_and_init(cache)

        os.environ["VIBHU_OSKA__memory__vector__persist_directory"] = chroma_dir
        datacore = DataCore()
        await datacore.initialize(registry)

        # Verify seeded entities
        res_nodes = await db.execute("query", query="SELECT * FROM kg_nodes")
        assert len(res_nodes) >= 10
        entities = {n["entity"] for n in res_nodes}
        assert "Harsh Dev Jha" in entities
        assert "eOzka" in entities
        assert "Krishyangi Dixit" in entities

        # Test GraphRAG query lookup
        kg_context = await datacore.query_knowledge_graph("Who is Harsh Jha and what did he build?")
        assert "Harsh Dev Jha" in kg_context
        assert "founded" in kg_context

        # Test Optimization core context compression
        from Backend.Core.MainCore.OptimizationCore.OptimizationCore import OptimizationCore
        opt = OptimizationCore()
        await opt.initialize(registry)
        
        chunks = [
            {"source": "test_src1", "content": "Short text", "relevance_score": 0.9},
            {"source": "test_src2", "content": "A very long sentence " * 50, "relevance_score": 0.5}
        ]
        compressed = await opt.optimize_prompt_context(chunks, max_chars=100)
        assert len(compressed) == 2
        assert "[Truncated...]" in compressed[1]["content"]

        # Test Monitoring core system event logging
        from Backend.Core.MainCore.MonitoringCore.MonitoringCore import MonitoringCore
        bus = EventBus(pub_port=5601, sub_port=5602, push_port=5603, pull_port=5604)
        await bus.start()
        
        mon = MonitoringCore()
        await mon.initialize(registry, bus)
        
        # Dispatch health check system event
        alert_event = Event(
            topic=Topics.SYSTEM_ALERT,
            source="test_runner",
            payload={"severity": 2, "message": "Disk space critical"}
        )
        await mon.log_system_event(alert_event)
        
        reports = await mon.generate_report()
        assert len(reports) >= 1
        assert reports[0]["level"] == "ERROR"
        assert "Disk space critical" in reports[0]["message"]

        # Cleanup
        await datacore.shutdown()
        await registry.shutdown_all()
        await bus.stop()

    @pytest.mark.asyncio
    async def test_sovereign_gpt_generation(self):
        cognition = CognitionCore()
        await cognition.initialize()
        resp = await cognition.generate(prompt="Vibhu-Oska", model_id="sovereign-gpt")
        assert resp.content
        assert "Inference completed successfully via Sovereign GPT" in resp.metadata.status.message
