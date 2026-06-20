# 12 — Stage Roadmap (Stage 4 → 7)

> Stages 1–3 are complete. This document outlines what comes next.

---

## Stage 4: The Eyes & Hands 🔲

*Goal: Give Vibhu-Oska a rich visual interface and real-time research capability.*

### Web Dashboard (Next.js / Vite)

A full-featured dark-mode dashboard separate from the existing eOzka WebSocket connection:

- **Chat view**: Streaming responses from the WebSocket, session history sidebar
- **Task Manager**: Live queue of processing tasks with status indicators
- **Telemetry Panel**: CPU/GPU/Memory real-time graphs (fed from AutomationCore)
- **Model Panel**: Sovereign GPT training status, Router predictions, model selection
- **Research Viewer**: SearXNG search results rendered in a clean card grid
- **Config Editor**: Live-edit `config/default.yaml` values from the UI

### SearXNG Integration

1. Add SearXNG to `Docker/docker-compose.yml`
2. Configure `config/default.yaml` with `search_engine.host: "localhost:8888"`
3. Activate `SearchEngine` plugin in the ToolRegistry
4. Wire `search_query` intent to `OrchestratorCore._route_to_specialized_core()`

### Unity 3D Prototype (Optional)

A spatial 3D interface for Vibhu-Oska — voice commands trigger model queries, gesture engine maps spatial movements to OS commands. The WebSocket endpoint is already built; Unity just needs a client implementation.

---

## Stage 5: The Conscience 🔲

*Goal: Vibhu-Oska learns from its own outputs and improves continuously.*

### Self-Correction Loop

```
CognitionCore generates code
    ↓
TestingFramework runs the code in a sandbox
    ↓
If tests fail: failure transcript fed back to CognitionCore as context
    ↓
CognitionCore regenerates (up to N attempts)
    ↓
If still failing: escalate to human via SYSTEM_ALERT
```

### RLHF-Lite Feedback System

- Gateway adds a `/feedback` endpoint: `POST {"request_id": "...", "rating": 1, "comment": "..."}`
- FeedbackCollector writes approved entries to `Data/training/feedback/feedback_dataset.jsonl`
- Scheduler triggers QLoRA fine-tuning weekly using accumulated approved examples

### ReplayLogger Activation

- Every full pipeline execution (prompt → context → response → tools) is recorded
- Stored as structured JSONL in `Data/training/replays/`
- Training data generator can sample from replays for offline learning

### Autonomous Scheduler Jobs

```yaml
# In config/default.yaml:
scheduler:
  jobs:
    - name: nightly_retrain
      cron: "0 3 * * *"       # 3 AM daily
      action: train_sovereign_gpt
    - name: weekly_compaction
      cron: "0 2 * * 0"       # Sunday 2 AM
      action: compact_chromadb
    - name: telemetry_flush
      cron: "*/30 * * * *"    # Every 30 min
      action: flush_telemetry
```

---

## Stage 6: The Armor 🔲

*Goal: Harden the system for persistent operation.*

### JWT Auth Enforcement

- All Gateway endpoints except `/health` require `Authorization: Bearer <token>`
- `AuthenticationManager` issues tokens on a `/auth/login` endpoint
- WebSocket connections require a token query parameter

### Docker Sandboxing

- `TestingFramework.run_code()` executes inside a Docker container with no network access
- Resource limits: 512MB RAM, 1 CPU, 30s timeout
- Output captured and returned; container destroyed after each run

### Rate Limiting

- Per-user-id rate limiting on `/chat` (configurable: requests per minute)
- Per-IP rate limiting on auth endpoints (brute force protection)

### Production Hardening

- `gunicorn` + `uvicorn` workers (multi-process)
- Nginx reverse proxy with TLS termination
- Log rotation (daily, 7-day retention)
- Performance profiling: `py-spy` snapshots during inference

---

## Stage 7: The Offering 🔲

*Goal: Release the public Stubvi tier.*

### Model Distillation

- Train a compact student model from Sovereign GPT teacher (knowledge distillation)
- Target: <50MB, CPU-runnable, privacy-preserving
- This is the public Stubvi inference engine — no private weights exposed

### Public API

- OpenAPI spec for the Stubvi endpoint
- Rate-limited public API keys
- Differential privacy applied to all telemetry before storage

### DistributionCore Deployment Gate

```python
# Final deployment checklist:
await dist.compile_bundle(version="stubvi-0.3")
result = await dist.verify_bundle()
assert result["status"] == "pass", "DO NOT DEPLOY — private data leaked"
# deploy(bundle_path)
```

### Landing Page

- Marketing page for Stubvi public tier
- Download links for the compiled public bundle
- Feature comparison: Stubvi vs. private sovereign tier

---

## Quick Decision Reference

| Decision | Answer |
|---|---|
| Should I add a new plugin? | Only if it's core infra. Domain-specific plugins should be AI-generated via SelfUpdater (Stage 5) |
| Should I add more keywords to OrchestratorCore routing? | Prefer training the Router model to classify new task types |
| Can I store secrets in config YAML? | No — secrets go in `.env` only (gitignored) |
| Should I add inference logic to ValidationCore? | No — ValidationCore never processes, only validates |
| Can I put DB queries in CognitionCore? | No — DataCore only |
