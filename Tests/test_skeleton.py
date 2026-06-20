"""
Vibhu-Oska AI-OS — Skeleton Smoke Test
Verifies that all Stage 1 components are functional.

Run: python -m pytest Tests/ -v
"""

from __future__ import annotations

import asyncio
import json
import pytest

from Backend.Core.EventBus.Events import Event, EventFactory
from Backend.Core.EventBus.Topics import Topics
from Backend.Plugins.ToolRegistry.BaseService import BaseService
from Backend.Plugins.ToolRegistry.Registry import ToolRegistry
from Shared.Models import (
    TaskRequest,
    TaskResponse,
    TaskType,
    EventEnvelope,
    EventType,
    StatusCode,
    Priority,
    PluginInfo,
    CoreStatus,
)


# ══════════════════════════════════════════════════════════════════════════════
# Test: Pydantic Data Models
# ══════════════════════════════════════════════════════════════════════════════


class TestModels:
    def test_task_request_defaults(self):
        req = TaskRequest(prompt="Hello Vibhu-Oska")
        assert req.prompt == "Hello Vibhu-Oska"
        assert req.type == TaskType.UNKNOWN
        assert req.metadata.request_id  # UUID generated
        assert req.metadata.priority == Priority.NORMAL

    def test_task_request_serialization(self):
        req = TaskRequest(
            type=TaskType.CODE_GENERATE,
            prompt="Write a Python function",
            parameters={"language": "python"},
        )
        data = req.model_dump()
        assert data["type"] == TaskType.CODE_GENERATE
        assert data["parameters"]["language"] == "python"

        # Round-trip
        restored = TaskRequest(**data)
        assert restored.prompt == req.prompt

    def test_task_response_with_artifacts(self):
        resp = TaskResponse(
            type=TaskType.CODE_GENERATE,
            content="def hello(): return 'world'",
        )
        assert resp.content == "def hello(): return 'world'"
        assert resp.token_usage.total_tokens == 0

    def test_event_envelope(self):
        env = EventEnvelope(
            type=EventType.USER_INPUT,
            topic="user.input",
            source="gateway",
            payload={"prompt": "test"},
        )
        assert env.type == EventType.USER_INPUT
        assert env.payload["prompt"] == "test"


# ══════════════════════════════════════════════════════════════════════════════
# Test: Event System
# ══════════════════════════════════════════════════════════════════════════════


class TestEvents:
    def test_event_serialization(self):
        event = Event(
            topic="task.created",
            source="orchestrator",
            payload={"task_id": "abc-123", "prompt": "Hello"},
        )
        serialized = event.serialize()
        parsed = json.loads(serialized)
        assert parsed["topic"] == "task.created"
        assert parsed["payload"]["task_id"] == "abc-123"

    def test_event_deserialization(self):
        event = Event(
            topic="test.topic",
            source="test",
            payload={"key": "value"},
        )
        serialized = event.serialize()
        restored = Event.deserialize(serialized)
        assert restored.topic == event.topic
        assert restored.payload["key"] == "value"

    def test_event_zmq_frames(self):
        event = Event(topic="task.completed", source="cognition", payload={})
        frames = event.to_zmq_frames()
        assert len(frames) == 2
        assert frames[0] == b"task.completed"

        restored = Event.from_zmq_frames(frames)
        assert restored.topic == "task.completed"

    def test_event_factory_user_input(self):
        event = EventFactory.user_input("Hello world", session_id="sess-1")
        assert event.topic == "user.input"
        assert event.source == "gateway"
        assert event.payload["prompt"] == "Hello world"
        assert event.payload["session_id"] == "sess-1"

    def test_event_factory_task_created(self):
        event = EventFactory.task_created("t-1", "chat", "Say hello")
        assert event.topic == "task.created"
        assert event.payload["task_type"] == "chat"

    def test_event_factory_tool_request(self):
        event = EventFactory.tool_request(
            "search_engine", "search", {"query": "AI-OS architecture"}
        )
        assert event.topic == "tool.request.search_engine"
        assert event.payload["action"] == "search"

    def test_event_factory_heartbeat(self):
        event = EventFactory.heartbeat("monitoring", uptime_seconds=3600)
        assert event.topic == "system.heartbeat"
        assert event.payload["uptime_seconds"] == 3600

    def test_event_factory_alert(self):
        event = EventFactory.alert("gpu", "VRAM Critical", "Usage > 95%", severity=3)
        assert event.topic == "system.alert"
        assert event.priority == 2  # severity >= 2 bumps priority


# ══════════════════════════════════════════════════════════════════════════════
# Test: Topics
# ══════════════════════════════════════════════════════════════════════════════


class TestTopics:
    def test_all_topics_returns_list(self):
        topics = Topics.all_topics()
        assert isinstance(topics, list)
        assert len(topics) > 10

    def test_topic_constants(self):
        assert Topics.TASK_CREATED == "task.created"
        assert Topics.USER_INPUT == "user.input"
        assert Topics.SYSTEM_HEALTH == "system.health"

    def test_tool_request_for(self):
        assert Topics.tool_request_for("search") == "tool.request.search"

    def test_tool_result_for(self):
        assert Topics.tool_result_for("code_analyzer") == "tool.result.code_analyzer"


# ══════════════════════════════════════════════════════════════════════════════
# Test: Tool Registry
# ══════════════════════════════════════════════════════════════════════════════


class _MockPlugin(BaseService):
    """Minimal plugin for testing."""

    def __init__(self, name: str = "mock_plugin"):
        self._name = name
        self._healthy = True

    def info(self) -> PluginInfo:
        return PluginInfo(
            name=self._name,
            version="1.0.0",
            description="A test plugin",
            capabilities=["testing", "mock"],
            status=CoreStatus.HEALTHY,
        )

    async def execute(self, action: str, **kwargs) -> str:
        return f"Executed {action} with {kwargs}"

    def health_check(self) -> bool:
        return self._healthy


class TestToolRegistry:
    def test_register_and_get(self):
        registry = ToolRegistry()
        plugin = _MockPlugin("test_a")
        registry.register(plugin)
        assert registry.has("test_a")
        assert registry.get("test_a") is plugin

    def test_get_unknown_raises(self):
        registry = ToolRegistry()
        with pytest.raises(KeyError, match="not registered"):
            registry.get("nonexistent")

    def test_duplicate_registration_raises(self):
        registry = ToolRegistry()
        registry.register(_MockPlugin("dup"))
        with pytest.raises(ValueError, match="already registered"):
            registry.register(_MockPlugin("dup"))

    def test_unregister(self):
        registry = ToolRegistry()
        plugin = _MockPlugin("removable")
        registry.register(plugin)
        removed = registry.unregister("removable")
        assert removed is plugin
        assert not registry.has("removable")

    def test_list_plugins(self):
        registry = ToolRegistry()
        registry.register(_MockPlugin("p1"))
        registry.register(_MockPlugin("p2"))
        infos = registry.list_plugins()
        assert len(infos) == 2
        names = {i.name for i in infos}
        assert names == {"p1", "p2"}

    def test_find_by_capability(self):
        registry = ToolRegistry()
        registry.register(_MockPlugin("searcher"))
        results = registry.find_by_capability("testing")
        assert len(results) == 1
        assert results[0].name == "searcher"

    def test_find_by_capability_no_match(self):
        registry = ToolRegistry()
        registry.register(_MockPlugin("x"))
        results = registry.find_by_capability("quantum_computing")
        assert len(results) == 0

    def test_health_report(self):
        registry = ToolRegistry()
        plugin = _MockPlugin("healthy_one")
        registry.register(plugin)
        report = registry.health_report()
        assert report["healthy_one"]["healthy"] is True

    @pytest.mark.asyncio
    async def test_register_and_init(self):
        registry = ToolRegistry()
        plugin = _MockPlugin("initable")
        await registry.register_and_init(plugin)
        assert registry.has("initable")

    @pytest.mark.asyncio
    async def test_execute_plugin(self):
        registry = ToolRegistry()
        plugin = _MockPlugin("executor")
        registry.register(plugin)
        result = await registry.get("executor").execute("test_action", data="hello")
        assert "test_action" in result

    @pytest.mark.asyncio
    async def test_shutdown_all(self):
        registry = ToolRegistry()
        registry.register(_MockPlugin("s1"))
        registry.register(_MockPlugin("s2"))
        await registry.shutdown_all()  # Should not raise


# ══════════════════════════════════════════════════════════════════════════════
# Test: ConfigLoader
# ══════════════════════════════════════════════════════════════════════════════


class TestConfigLoader:
    def test_load_and_get(self):
        from Backend.Plugins.ConfigLoader.ConfigLoader import ConfigLoader
        # Force reload to pick up our config files
        config = ConfigLoader.reload()
        # Should load default.yaml
        assert config.get("system.name") == "Vibhu-Oska"
        assert config.get("system.version") == "0.2.0"

    def test_get_with_default(self):
        from Backend.Plugins.ConfigLoader.ConfigLoader import ConfigLoader
        config = ConfigLoader.load()
        assert config.get("nonexistent.key", "fallback") == "fallback"

    def test_get_section(self):
        from Backend.Plugins.ConfigLoader.ConfigLoader import ConfigLoader
        config = ConfigLoader.load()
        gateway = config.get_section("gateway")
        assert "port" in gateway
        assert isinstance(gateway["port"], int)
