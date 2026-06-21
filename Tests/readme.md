# Tests

Integration test suite for Vibhu-Oska. **65 tests passing** across three test files covering the skeleton, brain stem, and all specialized cores.

## Running Tests

```bash
# From project root with .venv activated
python -m pytest Tests/ -v

# Single file
python -m pytest Tests/test_brain_stem.py -v

# With output capture disabled (see print statements)
python -m pytest Tests/ -v -s

# Coverage report
python -m pytest Tests/ --cov=Backend --cov=Models --cov=Shared --cov-report=term-missing
```

## Test Files

### `test_skeleton.py`
Tests the foundational infrastructure layer (Stage 1):
- EventBus pub/sub messaging
- Logger initialization and structured output
- ConfigLoader YAML loading + env overrides
- FastAPI Gateway health endpoint
- Protobuf schema compilation
- Editable install import paths

### `test_brain_stem.py`
Tests the core intelligence pipeline (Stage 2):
- OrchestratorCore full pipeline (input → validation → memory → cognition → output)
- ValidationCore input and output guard logic
- DataCore session creation, chat persistence, semantic memory query
- DataCore knowledge graph (GRAG) entity matching and 1-hop traversal
- HybridCore routing (primary → backup fallback)
- CognitionCore inference (Sovereign GPT path + BackupCore fallback)
- OptimizationCore cache hit/miss behavior
- MonitoringCore event subscription and telemetry write

### `test_specialized_cores.py`
Tests the specialized execution cores (Stage 2 completion / Stage 3):
- AutomationCore: get_system_info, list_directory, read_file, run_command (safe commands)
- AutomationCore: blacklist enforcement (blocked commands rejected)
- DesignCore: layout generation, component generation for all 6 component types
- ImageGenerationCore: VRAM guard behavior, fallback ASCII art generation
- DistributionCore: bundle compilation, bundle integrity verification, telemetry ingestion/flush
- OrchestratorCore pre-cognition routing (keyword dispatch to correct specialized core)

## conftest.py

Provides shared pytest fixtures:
- `event_loop` — configured for Windows compatibility (`WindowsSelectorEventLoopPolicy`)
- `registry` — pre-built ToolRegistry with all plugins registered
- `event_bus` — initialized EventBus instance

## Adding New Tests

1. Create `Tests/test_your_feature.py`
2. Import `conftest` fixtures via `pytest` dependency injection
3. Use `@pytest.mark.asyncio` for async tests
4. Follow the pattern: arrange → act → assert, one clear scenario per test function
