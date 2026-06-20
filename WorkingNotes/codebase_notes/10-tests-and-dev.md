# 10 — Tests & Development

## Current Test Status

**65 tests — all passing** across three test files.

```
Tests/
├── conftest.py                ← Shared fixtures (event_loop, registry, event_bus)
├── test_skeleton.py           ← Stage 1 infrastructure tests
├── test_brain_stem.py         ← Stage 2 core pipeline tests
└── test_specialized_cores.py  ← Stage 2/3 specialized core tests
```

---

## Running Tests

```bash
# Full suite
python -m pytest Tests/ -v

# Single file
python -m pytest Tests/test_brain_stem.py -v

# Specific test
python -m pytest Tests/test_brain_stem.py::test_validation_rejects_empty_prompt -v

# With output capture off (see log lines)
python -m pytest Tests/ -v -s

# With coverage
python -m pytest Tests/ --cov=Backend --cov=Shared --cov=Models --cov-report=term-missing
```

---

## conftest.py (Shared Fixtures)

```python
@pytest.fixture(scope="session")
def event_loop():
    # Windows: WindowsSelectorEventLoopPolicy required for asyncio on pytest
    policy = asyncio.WindowsSelectorEventLoopPolicy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
async def registry():
    reg = ToolRegistry()
    # Registers Logger, ConfigLoader, DatabaseConnector, CacheManager, ...
    return reg

@pytest.fixture
async def event_bus():
    bus = EventBus()
    await bus.start()
    yield bus
    await bus.stop()
```

---

## test_skeleton.py — What It Tests

| Test | What It Verifies |
|---|---|
| test_event_bus_pubsub | publish → subscriber receives event within 1s |
| test_logger_initialization | Logger.get() returns a valid logger |
| test_config_loader_yaml | Loads default.yaml, reads system.version |
| test_gateway_health_endpoint | GET /health returns 200 + JSON |
| test_protobuf_imports | brain_pb2, router_pb2, telemetry_pb2 importable |
| test_editable_install_imports | `from Backend.Core import ...` works without sys.path hacks |

---

## test_brain_stem.py — What It Tests

| Test | What It Verifies |
|---|---|
| test_orchestrator_full_pipeline | End-to-end: prompt → TASK_COMPLETED event published |
| test_validation_rejects_empty_prompt | Empty string → validation fail |
| test_validation_rejects_dangerous | Blocked keyword → validation fail |
| test_datacore_session_creation | create_session → SQLite row exists |
| test_datacore_chat_persistence | save + retrieve chat messages |
| test_datacore_semantic_memory | store + query_memory returns results |
| test_datacore_knowledge_graph | GRAG entity matching returns context string |
| test_optimization_cache_hit | Same prompt twice → second call hits cache |
| test_hybrid_core_fallback | CognitionCore mock failure → BackupCore response |
| test_monitoring_core_logging | TASK_COMPLETED event → telemetry_events table row |
| ... (total ~30 tests) | |

---

## test_specialized_cores.py — What It Tests

| Test | What It Verifies |
|---|---|
| test_automation_get_system_info | Returns dict with cpu, memory, disk keys |
| test_automation_list_directory | Returns entries for a valid path |
| test_automation_blacklist_enforcement | `rm -rf` command → rejected |
| test_automation_read_file | Reads file content correctly |
| test_design_generate_layout | Returns HTML string with `<html>` |
| test_design_generate_component_card | Returns HTML with card CSS class |
| test_design_generate_component_modal | Returns HTML with modal CSS class |
| test_design_generate_component_table | Returns HTML `<table>` element |
| test_imagegen_vram_guard | Low VRAM → fallback ASCII descriptor |
| test_distribution_compile_bundle | Produces output dir with BUNDLE_MANIFEST.json |
| test_distribution_verify_bundle_pass | Clean bundle → pass status |
| test_distribution_telemetry_ingest | PII field → rejected; clean packet → queued |
| test_distribution_telemetry_flush | flush → JSONL file written |
| test_orchestrator_routes_to_automation | "system info" prompt → AutomationCore response |
| test_orchestrator_routes_to_design | "generate html" prompt → DesignCore response |
| test_orchestrator_routes_to_image | "draw a cat" prompt → ImageGenerationCore response |
| ... (total ~26 tests) | |

---

## Development Workflow

### Adding a New Feature

1. Write the feature code in the appropriate module
2. Write tests in `Tests/test_your_feature.py`
3. Run `python -m pytest Tests/ -v` — must remain 100% green
4. Update the relevant `readme.md` in the module folder
5. Update `WorkingNotes/codebase_notes/` relevant file
6. Update `AGENT_STATE_CACHE.md` session log

### Linting

```bash
# Ruff linter (fast, configured in pyproject.toml)
ruff check Backend/ Models/ Shared/

# Type checking
mypy Backend/ --ignore-missing-imports
```

### Code Style

- Line length: 100 chars
- All functions must have docstrings (purpose, parameters, returns, edge cases)
- All constants named at module scope — no magic numbers
- `CamelCase` for all folders and Python files
- `lowercase-kebab.md` for all markdown files
