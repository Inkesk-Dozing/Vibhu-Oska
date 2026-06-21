"""
Vibhu-Oska AI-OS — API Gateway
FastAPI application serving as the central nervous system ingress.

All incoming requests — from web dashboards, Unity clients, CLI tools,
and external integrations — flow through this gateway.

Endpoints:
    GET  /health              → System health check
    GET  /status              → Detailed system status
    POST /api/v1/chat         → Submit a chat/task request
    POST /api/v1/events       → Submit raw events to the bus
    GET  /api/v1/plugins      → List registered plugins
    WS   /ws                  → Real-time WebSocket stream
"""

from __future__ import annotations

import sys
from pathlib import Path
import asyncio
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import time
import uuid
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from Backend.Core.EventBus.EventBus import EventBus
from Backend.Core.EventBus.Events import Event, EventFactory
from Backend.Core.EventBus.Topics import Topics
from Backend.Core.Watchdog.Watchdog import Watchdog
from Backend.Core.ContextManager.ContextManager import ContextManager
from Backend.Plugins.ConfigLoader.ConfigLoader import ConfigLoader
from Backend.Plugins.Logger.Logger import Logger
from Backend.Plugins.ToolRegistry.Registry import ToolRegistry
from Backend.Plugins.DatabaseConnector.DatabaseConnector import DatabaseConnector
from Backend.Plugins.CacheManager.CacheManager import CacheManager
from Backend.Core.MainCore.CognitionCore.cognition import CognitionCore
from Backend.Core.MainCore.OrchestratorCore.OrchestratorCore import OrchestratorCore
from Backend.Core.SpecializedCore.DataCore.datacore import DataCore
from Backend.Plugins.SearchEngine.SearchEngine import SearchEngine
from Backend.Plugins.FeedbackCollector.FeedbackCollector import FeedbackCollector
from Backend.Plugins.TestingFramework.TestingFramework import TestingFramework
from Backend.Plugins.CodeAnalyzer.CodeAnalyzer import CodeAnalyzer
from Backend.Plugins.ReplayLogger.ReplayLogger import ReplayLogger
from Backend.Plugins.Scheduler.Scheduler import Scheduler
from Backend.Plugins.ThermalMonitor.ThermalMonitor import ThermalMonitor
from Backend.Plugins.AuthenticationManager.AuthenticationManager import AuthenticationManager
from Backend.Plugins.SelfUpdater.SelfUpdater import SelfUpdater


# ══════════════════════════════════════════════════════════════════════════════
# Application State (shared across routes)
# ══════════════════════════════════════════════════════════════════════════════

class AppState:
    """Global application state container."""
    config: ConfigLoader
    event_bus: EventBus
    registry: ToolRegistry
    orchestrator: OrchestratorCore
    watchdog: Watchdog | None = None
    context_manager: ContextManager | None = None
    start_time: float = 0.0
    ws_clients: set[WebSocket] = set()
    training_in_progress: bool = False


state = AppState()


# ══════════════════════════════════════════════════════════════════════════════
# Request/Response Models
# ══════════════════════════════════════════════════════════════════════════════

class ChatRequest(BaseModel):
    prompt: str
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = "operator"
    model_id: str = ""
    temperature: float = 0.7
    max_tokens: int = 2048
    stream: bool = False
    parameters: dict[str, str] = Field(default_factory=dict)


class ChatResponse(BaseModel):
    request_id: str
    content: str = ""
    status: str = "pending"
    processing_time_ms: int = 0


class EventRequest(BaseModel):
    topic: str
    source: str = "external"
    payload: dict[str, Any] = Field(default_factory=dict)
    priority: int = 1


class HealthResponse(BaseModel):
    status: str
    uptime_seconds: float
    version: str
    environment: str
    event_bus_running: bool
    registered_plugins: int


class StatusResponse(BaseModel):
    system: dict[str, Any]
    plugins: list[dict[str, Any]]
    event_bus: dict[str, Any]


# ══════════════════════════════════════════════════════════════════════════════
# Application Lifecycle
# ══════════════════════════════════════════════════════════════════════════════

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle."""
    log = Logger.get("Gateway")

    # ── Startup ──
    state.start_time = time.time()
    state.config = ConfigLoader.load()
    state.registry = ToolRegistry()

    # Initialize logger from config
    log_config = state.config.get_section("logging")
    Logger.initialize(
        level=log_config.get("level", "DEBUG"),
        fmt=log_config.get("format", "console"),
        output_dir=log_config.get("output_dir", "Log"),
        file_enabled=log_config.get("file_enabled", True),
        console_enabled=log_config.get("console_enabled", True),
        project_root=state.config.project_root,
    )

    log.info(
        "Vibhu-Oska AI-OS booting",
        version=state.config.get("system.version"),
        environment=state.config.environment,
        codename=state.config.get("system.codename"),
    )

    # Register and initialize all plugins
    await state.registry.register_and_init(DatabaseConnector())
    await state.registry.register_and_init(CacheManager())
    await state.registry.register_and_init(CognitionCore())
    # DataCore exposed directly for Memory API endpoints
    data_core = DataCore()
    await data_core.initialize(state.registry)
    state.registry.register("data_core", data_core)

    # Stage 4-6 Plugins
    search_engine      = SearchEngine()
    feedback_collector = FeedbackCollector()
    testing_framework  = TestingFramework()
    code_analyzer      = CodeAnalyzer()
    replay_logger      = ReplayLogger()
    scheduler          = Scheduler()
    thermal_monitor    = ThermalMonitor()
    auth_manager       = AuthenticationManager()

    await state.registry.register_and_init(search_engine)
    await state.registry.register_and_init(feedback_collector)
    await state.registry.register_and_init(testing_framework)
    await state.registry.register_and_init(code_analyzer)
    await state.registry.register_and_init(replay_logger)
    await state.registry.register_and_init(scheduler)
    await state.registry.register_and_init(thermal_monitor)
    await state.registry.register_and_init(auth_manager)

    self_updater = SelfUpdater()
    self_updater.set_registry(state.registry)
    await state.registry.register_and_init(self_updater)

    # Start event bus
    bus_config = state.config.get_section("event_bus")
    state.event_bus = EventBus(
        pub_port=bus_config.get("publisher_port", 5555),
        sub_port=bus_config.get("subscriber_port", 5556),
        push_port=bus_config.get("push_port", 5557),
        pull_port=bus_config.get("pull_port", 5558),
    )
    await state.event_bus.start()
    log.info("Event bus started", topics=Topics.all_topics()[:5])

    # Inject event bus into plugins that need it
    scheduler.set_event_bus(state.event_bus)
    thermal_monitor.set_event_bus(state.event_bus)

    # Initialize ContextManager
    model_cfg = state.config.get_section("models.reasoning")
    state.context_manager = ContextManager(model_id=model_cfg.get("name", "default"))

    # Subscribe to broadcast events for WebSocket forwarding
    await state.event_bus.subscribe("task.", _broadcast_to_ws)
    await state.event_bus.subscribe("system.", _broadcast_to_ws)
    await state.event_bus.subscribe("feedback.", _broadcast_to_ws)

    # Start Orchestrator
    state.orchestrator = OrchestratorCore()
    await state.orchestrator.start(state.event_bus, state.registry)

    # Start Watchdog (monitors plugin health every 30s)
    state.watchdog = Watchdog(registry=state.registry, event_bus=state.event_bus)
    await state.watchdog.start()

    log.info(
        "Vibhu-Oska AI-OS ready",
        gateway_port=state.config.get("gateway.port"),
        plugins_registered=state.registry.plugin_count,
    )

    yield  # ── Application Running ──

    # ── Shutdown ──
    log.info("Vibhu-Oska AI-OS shutting down")
    if state.watchdog:
        await state.watchdog.stop()
    await state.orchestrator.shutdown()
    await state.registry.shutdown_all()
    await state.event_bus.stop()
    log.info("Shutdown complete")


# ══════════════════════════════════════════════════════════════════════════════
# FastAPI Application
# ══════════════════════════════════════════════════════════════════════════════

app = FastAPI(
    title="Vibhu-Oska AI-OS",
    description="Autonomous AI Operating Layer — Gateway API",
    version="0.2.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files and index template
project_root = Path(__file__).resolve().parent.parent.parent
static_dir = project_root / "Frontend" / "web_app" / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

@app.get("/", response_class=HTMLResponse, tags=["UI"])
async def read_index():
    index_path = project_root / "Frontend" / "web_app" / "templates" / "index.html"
    if index_path.exists():
        with open(index_path, "r", encoding="utf-8") as f:
            return f.read()
    return HTMLResponse("<h1>Vibhu-Oska AI-OS</h1><p>Frontend template not found.</p>")


# ══════════════════════════════════════════════════════════════════════════════
# Health & Status Routes
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """System health check — used by Docker, load balancers, and monitoring."""
    return HealthResponse(
        status="healthy",
        uptime_seconds=round(time.time() - state.start_time, 2),
        version=state.config.get("system.version", "unknown"),
        environment=state.config.environment,
        event_bus_running=state.event_bus.is_running,
        registered_plugins=state.registry.plugin_count,
    )


@app.get("/status", response_model=StatusResponse, tags=["System"])
async def system_status():
    """Detailed system status including all plugins and event bus state."""
    return StatusResponse(
        system={
            "name": state.config.get("system.name"),
            "version": state.config.get("system.version"),
            "codename": state.config.get("system.codename"),
            "environment": state.config.environment,
            "uptime_seconds": round(time.time() - state.start_time, 2),
            "tier": state.config.get("system.tier"),
        },
        plugins=[info.model_dump() for info in state.registry.list_plugins()],
        event_bus={
            "running": state.event_bus.is_running,
            "registered_topics": state.event_bus.registered_topics(),
            "ws_clients_connected": len(state.ws_clients),
        },
    )


# ══════════════════════════════════════════════════════════════════════════════
# Chat / Task Routes
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/api/v1/chat", response_model=ChatResponse, tags=["AI"])
async def submit_chat(request: ChatRequest):
    """Submit a chat or task request to the AI-OS."""
    log = Logger.get("Gateway")
    request_id = str(uuid.uuid4())
    start = time.time()

    Logger.bind_request(request_id)
    log.info("Chat request received", prompt_length=len(request.prompt))

    # Create and publish the event
    event = EventFactory.user_input(
        prompt=request.prompt,
        session_id=request.session_id,
        user_id=request.user_id,
        model_id=request.model_id,
    )
    event.event_id = request_id

    await state.event_bus.publish(event)

    elapsed_ms = int((time.time() - start) * 1000)
    Logger.clear_context()

    return ChatResponse(
        request_id=request_id,
        content="",  # Will be populated via WebSocket stream or polling
        status="accepted",
        processing_time_ms=elapsed_ms,
    )


# ══════════════════════════════════════════════════════════════════════════════
# Event Routes
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/api/v1/events", tags=["Events"])
async def submit_event(request: EventRequest):
    """Submit a raw event to the event bus."""
    event = Event(
        topic=request.topic,
        source=request.source,
        payload=request.payload,
        priority=request.priority,
    )
    await state.event_bus.publish(event)
    return {"status": "published", "event_id": event.event_id}


# ══════════════════════════════════════════════════════════════════════════════
# Plugin Routes
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/api/v1/plugins", tags=["Plugins"])
async def list_plugins():
    """List all registered plugins and their status."""
    plugins_raw = state.registry.list_plugins()
    plugins_data = []
    for info in plugins_raw:
        d = info.model_dump()
        # Add live health check
        svc = state.registry.get_safe(info.name)
        d["healthy"] = svc.health_check() if svc else False
        plugins_data.append(d)
    return {
        "plugins": plugins_data,
        "total":   state.registry.plugin_count,
    }


@app.get("/api/v1/plugins/{plugin_name}/health", tags=["Plugins"])
async def plugin_health(plugin_name: str):
    """Check health of a specific plugin."""
    plugin = state.registry.get_safe(plugin_name)
    if not plugin:
        raise HTTPException(status_code=404, detail=f"Plugin '{plugin_name}' not found")
    return {
        "name":    plugin_name,
        "healthy": plugin.health_check(),
        "info":    plugin.info().model_dump(),
    }


# ──────────────────────────────────────────────
# Feedback endpoint (RLHF training signal)
# ──────────────────────────────────────────────

class FeedbackRequest(BaseModel):
    request_id: str = ""
    prompt: str     = ""
    response: str   = ""
    approved: bool  = True
    annotation: str = ""


@app.post("/api/v1/feedback", tags=["AI"])
async def submit_feedback(req: FeedbackRequest):
    """Submit RLHF feedback signal — stored as training data."""
    feedback_plugin = state.registry.get_safe("feedback_collector")
    if not feedback_plugin:
        raise HTTPException(status_code=503, detail="FeedbackCollector plugin not available")
    result = await feedback_plugin.execute(
        "log_feedback",
        request_id=req.request_id,
        prompt=req.prompt,
        response=req.response,
        approved=req.approved,
        annotation=req.annotation,
    )
    return result


@app.get("/api/v1/feedback/stats", tags=["AI"])
async def feedback_stats():
    """Get RLHF feedback statistics."""
    plugin = state.registry.get_safe("feedback_collector")
    if not plugin:
        raise HTTPException(status_code=503, detail="FeedbackCollector plugin not available")
    return await plugin.execute("get_stats")


# ──────────────────────────────────────────────
# Search endpoint
# ──────────────────────────────────────────────

class SearchRequest(BaseModel):
    query: str
    num_results: int = 5
    deep: bool       = False


@app.post("/api/v1/search", tags=["AI"])
async def web_search(req: SearchRequest):
    """Search via self-hosted SearXNG."""
    plugin = state.registry.get_safe("search_engine")
    if not plugin:
        raise HTTPException(status_code=503, detail="SearchEngine plugin not available")
    action = "deep_research" if req.deep else "search"
    return await plugin.execute(action, query=req.query, num_results=req.num_results)


# ──────────────────────────────────────────────
# Telemetry endpoint (hardware)
# ──────────────────────────────────────────────


# ──────────────────────────────────────────────
# Memory endpoints (DataCore — Stage 4)
# ──────────────────────────────────────────────

class MemoryQueryRequest(BaseModel):
    query: str
    top_k: int = 5
    collection: str = "vibhu_oska_memory"


class MemoryStoreRequest(BaseModel):
    content: str
    source: str = "dashboard"
    collection: str = "vibhu_oska_memory"
    metadata: dict[str, Any] = Field(default_factory=dict)


@app.post("/api/v1/memory/query", tags=["Memory"])
async def query_vector_memory(req: MemoryQueryRequest):
    """Query ChromaDB semantic memory for relevant chunks."""
    dc = state.registry.get_safe("data_core")
    if not dc:
        raise HTTPException(status_code=503, detail="DataCore unavailable")
    results = await dc.query_memory(query_text=req.query, top_k=req.top_k)
    return {"query": req.query, "results": results, "count": len(results)}


@app.post("/api/v1/memory/store", tags=["Memory"])
async def store_vector_memory(req: MemoryStoreRequest):
    """Store a text chunk in ChromaDB semantic memory."""
    dc = state.registry.get_safe("data_core")
    if not dc:
        raise HTTPException(status_code=503, detail="DataCore unavailable")
    await dc.store_memory(
        content=req.content,
        source=req.source,
        metadata=req.metadata,
    )
    return {"status": "stored", "chars": len(req.content), "collection": req.collection}


@app.post("/api/v1/memory/kg", tags=["Memory"])
async def query_knowledge_graph(req: MemoryQueryRequest):
    """Query the GRAG knowledge graph for entity matches; always returns live node/edge counts."""
    dc = state.registry.get_safe("data_core")
    db = state.registry.get_safe("database_connector")
    if not dc:
        raise HTTPException(status_code=503, detail="DataCore unavailable")

    # Always fetch live counts for sidebar metrics
    node_count, edge_count = 0, 0
    if db:
        try:
            nc = await db.execute("query", query="SELECT COUNT(*) as cnt FROM kg_nodes")
            ec = await db.execute("query", query="SELECT COUNT(*) as cnt FROM kg_edges")
            node_count = nc[0]["cnt"] if nc else 0
            edge_count = ec[0]["cnt"] if ec else 0
        except Exception:
            pass

    # If sentinel query, only return counts
    if req.query.strip() == "__count__":
        return {
            "query": req.query,
            "context": f"{node_count} nodes · {edge_count} edges",
            "node_count": node_count,
            "edge_count": edge_count,
        }

    kg_context = await dc.query_knowledge_graph(req.query)
    return {
        "query": req.query,
        "context": kg_context,
        "node_count": node_count,
        "edge_count": edge_count,
    }



@app.get("/api/v1/memory/sessions", tags=["Memory"])
async def list_sessions(limit: int = 20):
    """List recent chat sessions from SQLite."""
    dc = state.registry.get_safe("data_core")
    if not dc:
        raise HTTPException(status_code=503, detail="DataCore unavailable")
    db = state.registry.get_safe("database_connector")
    if not db:
        raise HTTPException(status_code=503, detail="DatabaseConnector unavailable")
    async with db._get_connection() as conn:
        rows = await conn.execute_fetchall(
            "SELECT session_id, user_id, created_at FROM sessions ORDER BY created_at DESC LIMIT ?",
            (limit,),
        )
    return {"sessions": [{"session_id": r[0], "user_id": r[1], "created_at": r[2]} for r in (rows or [])]}


@app.get("/api/v1/memory/history/{session_id}", tags=["Memory"])
async def get_session_history(session_id: str, limit: int = 50):
    """Get chat history for a session."""
    dc = state.registry.get_safe("data_core")
    if not dc:
        raise HTTPException(status_code=503, detail="DataCore unavailable")
    history = await dc.get_session_history(session_id=session_id, limit=limit)
    return {"session_id": session_id, "messages": history, "count": len(history)}




@app.get("/api/v1/telemetry", tags=["System"])
async def get_telemetry():
    """Get real-time hardware telemetry from ThermalMonitor."""
    plugin = state.registry.get_safe("thermal_monitor")
    if not plugin:
        return {"available": False}
    reading = await plugin.execute("read")
    safety  = await plugin.execute("is_safe")
    return {"available": True, "thermal": reading, "safe_for_gpu": safety.get("safe")}


# ──────────────────────────────────────────────
# Scheduler endpoints
# ──────────────────────────────────────────────

@app.get("/api/v1/scheduler/tasks", tags=["System"])
async def list_scheduled_tasks():
    """List all scheduled maintenance tasks."""
    plugin = state.registry.get_safe("scheduler")
    if not plugin:
        return {"tasks": []}
    return {"tasks": await plugin.execute("list_tasks")}


# ──────────────────────────────────────────────
# Self-Updater endpoints
# ──────────────────────────────────────────────

@app.post("/api/v1/self-update", tags=["System"])
async def trigger_self_update(test_path: str = "Tests/test_brain_stem.py"):
    """Trigger the local self-healing/self-updation test-and-repair cycle."""
    plugin = state.registry.get_safe("self_updater")
    if not plugin:
        raise HTTPException(status_code=503, detail="SelfUpdater plugin not available")
    return await plugin.execute("run_self_update", test_path=test_path)


class ModelTrainRequest(BaseModel):
    learning_rate: str = "5e-4"
    layers: int = 4
    attention_heads: int = 4
    hidden_dimension: int = 128
    vocab_size: int = 2000
    epochs: int = 60
    batch_size: int = 4
    device: str = "auto"


# ──────────────────────────────────────────────
# Corpus management
# ──────────────────────────────────────────────

class CorpusAppendRequest(BaseModel):
    text: str
    format: str = "raw"  # "raw" or "qa" (Q&A pair format)


@app.post("/api/v1/corpus/append", tags=["AI"])
async def append_corpus(req: CorpusAppendRequest):
    """
    Append new text to the Sovereign GPT training corpus.
    If format=qa, wraps the text in Query/Response scaffold.
    Also automatically stores the text in ChromaDB semantic memory.
    """
    from pathlib import Path
    corpus_path = Path(state.config.project_root) / "Data" / "training" / "sovereign_gpt" / "corpus.txt"
    corpus_path.parent.mkdir(parents=True, exist_ok=True)

    text = req.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    if req.format == "qa":
        # Expect format: "Question | Answer"
        if "|" in text:
            parts = text.split("|", 1)
            appended = f"\nQuery: {parts[0].strip()}\nResponse: {parts[1].strip()}\n"
        else:
            appended = f"\n{text}\n"
    else:
        appended = f"\n{text}\n"

    with open(corpus_path, "a", encoding="utf-8") as f:
        f.write(appended)

    # Also ingest into ChromaDB for immediate semantic retrieval
    dc = state.registry.get_safe("data_core")
    if dc:
        await dc.store_memory(content=text, source="corpus_append", metadata={"format": req.format})

    word_count = len(appended.split())
    log = Logger.get("Gateway")
    log.info("Corpus appended", words=word_count, format=req.format)
    return {"status": "appended", "words_added": word_count, "corpus_path": str(corpus_path)}


# ──────────────────────────────────────────────
# Session listing for sidebar
# ──────────────────────────────────────────────

@app.get("/api/v1/sessions", tags=["Memory"])
async def list_sessions_sidebar(limit: int = 15):
    """List recent chat sessions ordered by last update — used by sidebar session history."""
    db = state.registry.get_safe("database_connector")
    if not db:
        return {"sessions": []}
    try:
        rows = await db.execute(
            "query",
            query="SELECT session_id, user_id, title, created_at, updated_at FROM sessions ORDER BY updated_at DESC LIMIT ?",
            params=(limit,)
        )
        return {"sessions": rows or []}
    except Exception as e:
        return {"sessions": [], "error": str(e)}


# ──────────────────────────────────────────────
# GRAG — Knowledge Graph population
# ──────────────────────────────────────────────

class KGIngestRequest(BaseModel):
    text: str
    source: str = "manual"


@app.post("/api/v1/memory/kg/ingest", tags=["Memory"])
async def ingest_into_kg(req: KGIngestRequest):
    """
    Extract named entities from text and populate the knowledge graph.
    Uses simple heuristic NER — upgrades to spaCy/stanza when installed.
    """
    import re
    db = state.registry.get_safe("database_connector")
    if not db:
        raise HTTPException(status_code=503, detail="DatabaseConnector unavailable")

    # Heuristic NER: capitalised tokens 2+ chars not at sentence start
    words = req.text.split()
    entities: list[str] = []
    for i, w in enumerate(words):
        clean = re.sub(r'[^a-zA-Z\-]', '', w)
        if len(clean) >= 3 and clean[0].isupper() and i > 0:
            entities.append(clean)

    # Deduplicate
    entities = list(set(entities))[:20]

    inserted = 0
    for entity in entities:
        try:
            await db.execute(
                "execute",
                query="INSERT OR IGNORE INTO kg_nodes (entity, type, description) VALUES (?, ?, ?)",
                params=(entity, "auto_extracted", f"Extracted from: {req.source}")
            )
            inserted += 1
        except Exception:
            pass

    # Store full text in semantic memory too
    dc = state.registry.get_safe("data_core")
    if dc:
        await dc.store_memory(content=req.text, source=req.source, metadata={"type": "kg_ingest"})

    return {"status": "ingested", "entities_extracted": inserted, "total_candidates": len(entities)}


@app.post("/api/v1/model/train", tags=["AI"])
async def trigger_model_training(req: ModelTrainRequest, background_tasks: BackgroundTasks):
    """Trigger BPE tokenizer and transformer model training from scratch in a background thread."""
    if getattr(state, "training_in_progress", False):
        raise HTTPException(status_code=400, detail="Training is already in progress.")

    state.training_in_progress = True
    main_loop = asyncio.get_running_loop()

    def run_training():
        from Models.sovereign_gpt.train import train as train_model
        from pathlib import Path

        def callback(msg: str):
            async def publish_log():
                event = Event(
                    topic="system.model_training_log",
                    source="trainer",
                    payload={"log": msg}
                )
                await state.event_bus.publish(event)
            try:
                main_loop.call_soon_threadsafe(
                    lambda: asyncio.create_task(publish_log())
                )
            except Exception as ex:
                print(f"Error publishing training log: {ex}")

        try:
            callback("Starting Vibhu-Oska Sovereign GPT training pipeline...")
            
            root = Path(__file__).resolve().parent.parent.parent
            corpus_file = root / "Data" / "training" / "sovereign_gpt" / "corpus.txt"
            checkpoints = root / "Models" / "sovereign_gpt" / "checkpoints"
            
            try:
                lr_val = float(req.learning_rate)
            except ValueError:
                lr_val = 5e-4
                
            train_model(
                corpus_path=corpus_file,
                output_dir=checkpoints,
                epochs=req.epochs,
                batch_size=req.batch_size,
                lr=lr_val,
                device=req.device,
                hidden_size=req.hidden_dimension,
                num_layers=req.layers,
                num_heads=req.attention_heads,
                vocab_size=req.vocab_size,
                progress_callback=callback
            )
            callback("[SUCCESS] Sovereign GPT training pipeline completed successfully!")
        except Exception as e:
            callback(f"[ERROR] Training failed: {str(e)}")
        finally:
            state.training_in_progress = False

    background_tasks.add_task(run_training)
    return {"status": "started", "message": "Training has been initiated in background."}


# ══════════════════════════════════════════════════════════════════════════════
# WebSocket — Real-time Event Stream
# ══════════════════════════════════════════════════════════════════════════════

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    Real-time WebSocket connection for streaming events to frontends.
    Clients receive all task and system events as they happen.
    """
    await websocket.accept()
    state.ws_clients.add(websocket)
    log = Logger.get("WebSocket")
    log.info("Client connected", total_clients=len(state.ws_clients))

    try:
        while True:
            # Listen for incoming messages from the client
            data = await websocket.receive_json()

            # Client can submit events via WebSocket too
            if "prompt" in data:
                event = EventFactory.user_input(
                    prompt=data["prompt"],
                    session_id=data.get("session_id", str(uuid.uuid4())),
                )
                await state.event_bus.publish(event)
                await websocket.send_json({
                    "type": "ack",
                    "event_id": event.event_id,
                })

    except WebSocketDisconnect:
        state.ws_clients.discard(websocket)
        log.info("Client disconnected", remaining_clients=len(state.ws_clients))
    except Exception as e:
        state.ws_clients.discard(websocket)
        log.error("WebSocket error", error=str(e))


async def _broadcast_to_ws(event: Event) -> None:
    """Forward events from the bus to all connected WebSocket clients."""
    if not state.ws_clients:
        return

    message = {
        "event_id": event.event_id,
        "type": event.topic,
        "source": event.source,
        "payload": event.payload,
        "timestamp": event.timestamp,
    }

    disconnected: set[WebSocket] = set()
    for ws in state.ws_clients:
        try:
            await ws.send_json(message)
        except Exception:
            disconnected.add(ws)

    state.ws_clients -= disconnected
