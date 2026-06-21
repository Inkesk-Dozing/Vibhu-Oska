# 06 — Specialized Cores

The four execution engines that handle non-LLM task categories. OrchestratorCore routes to these before falling through to HybridCore/CognitionCore.

## Pre-Cognition Routing Logic

```python
# In OrchestratorCore._route_to_specialized_core()
if any(trigger in prompt_lower for trigger in _image_triggers): → ImageGenerationCore
if any(trigger in prompt_lower for trigger in _design_triggers): → DesignCore
if any(trigger in prompt_lower for trigger in _os_triggers): → AutomationCore
return None  # → HybridCore default path
```

## AutomationCore

```
File: Backend/Core/SpecializedCore/AutomationCore/AutomationCore.py
Size: 25.2KB  (fully implemented — Stage 2/3 complete)
```

The AI-OS hardware-native executive. Treats the host OS as a programmable substrate.

**9 supported actions:**

| Action | What It Does |
|---|---|
| `get_system_info` | CPU %, physical cores, MHz; RAM used/total/%; Disk free/total; GPU VRAM (torch query) |
| `list_directory` | Returns list of `{name, type, size_bytes}` dicts for a path |
| `read_file` | Reads file text (with 1MB size guard) |
| `write_file` | Writes content to a path (with directory creation) |
| `run_command` | Sandboxed subprocess execution with 30s timeout + blacklist guard |
| `list_processes` | psutil snapshot: `[{pid, name, cpu_percent, mem_mb}]` |
| `kill_process` | `psutil.Process(pid).terminate()` |
| `watch_filesystem` | Async file system watcher on a directory path |
| `open_application` | `subprocess.Popen([app_name])` + Windows `start` fallback |

**Safety blacklist** (any match blocks `run_command`):
```python
{"format", "rm -rf", "del /f /s /q", "shutdown", "reboot", "mkfs", "dd if=", ":(){ :|:& };:"}
```

**OrchestratorCore routing intelligence** (Step 5):
The orchestrator not only dispatches to AutomationCore — it parses the result and formats a human-readable response:
- `get_system_info` → formatted telemetry table (CPU/RAM/Disk/GPU)
- `list_directory` → directory tree with emoji icons (📁/📄)
- Generic → JSON dump of raw result

---

## DesignCore

```
File: Backend/Core/SpecializedCore/DesignCore/DesignCore.py
Status: Fully implemented — Stage 2/3 complete
```

Generates dark-mode HTML/CSS from natural language descriptions using a Jinja2-style template library.

**4 supported actions:**

| Action | Description |
|---|---|
| `generate_layout` | Full page with header, sidebar, content area, footer |
| `generate_component` | Single component by type |
| `generate_dashboard` | Full dashboard shell with sidebar + stats cards |
| `list_templates` | Returns list of available component type names |

**8 component templates:**

| Component | HTML Output |
|---|---|
| `card` | Info card with title, body text, optional footer |
| `modal` | Fixed-position dialog overlay |
| `table` | `<table>` with thead + tbody |
| `nav_item` | `<li>` with icon + label |
| `stat_card` | KPI card with big number, label, trend |
| `chat` | Message bubble styled for user/assistant |
| `sidebar` | `<nav>` with item list |
| `dashboard` | Full shell (sidebar + main content) |

**Design system tokens (CSS variables):**
```css
--bg-primary: #0d0d0d;
--bg-secondary: #1a1a2e;
--accent-violet: #7c3aed;
--accent-cyan: #06b6d4;
--text-primary: #f8fafc;
--font-family: 'Inter', system-ui, sans-serif;
```

---

## ImageGenerationCore

```
File: Backend/Core/SpecializedCore/ImageGenerationCore/ImageGenerationCore.py
Status: VRAM guard + graceful fallback implemented. Diffusion weights NOT yet populated.
```

Local latent diffusion pipeline. Currently returns ASCII art descriptors when model weights are absent — full SDXL integration is Stage 4 work.

**VRAM Guard logic:**
```python
if available_vram >= 4GB: → full diffusion generation
elif available_vram >= 2GB: → reduced resolution / fewer steps
else: → ASCII art fallback (CPU-only, always works)
```

**Output format:**
```json
{
  "status": "success" | "fallback_ascii",
  "image_base64": "iVBORw0KGgo...",   // or null on fallback
  "ascii_descriptor": "...",          // always present on fallback
  "generation_time_ms": 4200
}
```

---

## DistributionCore

```
File: Backend/Core/SpecializedCore/DistributionCore/DistributionCore.py
Size: ~280 lines (fully implemented in Session 3)
```

**4 supported actions:**

| Action | Description |
|---|---|
| `compile_bundle` | Copy whitelisted files → strip markers → write manifest + SHA256 |
| `verify_bundle` | Scan bundle for private path patterns → pass/fail + violations list |
| `ingest_telemetry` | Queue anonymized telemetry packet (PII blocklist enforced) |
| `flush_telemetry` | Write queued packets to `Data/training/telemetry/telemetry.jsonl` |

**Whitelist** (what goes into a Stubvi public bundle):
README.md, LICENCE.md, CONTRIBUTING.md, pyproject.toml, requirements.txt, Shared models, Backend Gateway files.

**Private patterns** (abort bundle if detected in output):
Model checkpoint paths, `.env`, config YAML, training data paths, internal email addresses.
