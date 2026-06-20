# 03 — Orchestration Pipeline (Double-Validation Loop)

## What It Is

The spine of every request. Every prompt that enters Vibhu-Oska — regardless of source — flows through this exact 8-step pipeline inside `OrchestratorCore.handle_user_input()`.

```
File: Backend/Core/MainCore/OrchestratorCore/OrchestratorCore.py
Size: 474 lines, 23.4KB
```

## The 8-Step Pipeline (Annotated)

```
USER_INPUT event received on EventBus
          ↓
Step 1:  ValidationCore.validate_input_package(input_pkg)
         → Fail fast: empty prompts, dangerous content, missing metadata
         → On fail: publish TASK_FAILED + ALERT, return immediately

Step 1.5: OptimizationCore.check_query_cache(prompt)
         → If cache hit: save to DB, publish TASK_COMPLETED, return
         → This is the fast path — skips all inference for repeated prompts

Step 2:  DataCore.create_session(session_id, user_id)
         → Upsert session into SQLite sessions table
         → Publish TASK_CREATED event

Step 3:  DataCore.get_session_history(session_id, limit=2)
         DataCore.query_memory(prompt, top_k=1)
         DataCore.query_knowledge_graph(prompt)
         → Collect: recent chat turns + semantic memory + GRAG entity facts

Step 4:  OptimizationCore.optimize_prompt_context(context)
         → Prune context to fit within token budget

Step 5:  _route_to_specialized_core(prompt, context)
         → Keyword classification → dispatch to AutomationCore / DesignCore / ImageGenerationCore
         → Returns TaskResponse if matched, else returns None

Step 6:  HybridCore.process_request(prompt, context, model_id)
         → [Only if Step 5 returned None]
         → Speculative routing via Router model → assigns model_id
         → Primary: CognitionCore.generate() → Sovereign GPT or Qwen
         → Fallback: BackupCore.generate() on any exception

Step 7:  ValidationCore.validate_ai_output(response)
         → Schema check: content non-empty, status code valid, token counts non-negative
         → On fail: publish TASK_FAILED, return

Step 8:  DataCore.save_chat_message() × 2 (user + assistant)
         OptimizationCore.save_response_cache(prompt, content)
         → Persist interaction to SQLite
         → Update cache for future reuse
         → Publish TASK_COMPLETED with full TaskResponse payload
```

## Error Handling

Every step is wrapped in a try/except at the top level. Any unhandled exception publishes `TASK_FAILED` with the exception message. The `finally` block always calls `Logger.clear_context()` to prevent request ID bleed across requests.

## Specialized Core Router (Step 5 Detail)

The `_route_to_specialized_core()` method uses keyword sets to classify prompts:

```python
# Image triggers
_image_triggers = {"generate image", "draw", "render image", "create image", ...}

# Design triggers  
_design_triggers = {"design", "layout", "html", "interface", "webpage", ...}

# OS/Automation triggers
_os_triggers = {"list files", "run command", "cpu usage", "system info", ...}
```

Each match triggers a different specialized core execute call. The response is wrapped in a `TaskResponse` with the matching `StatusCode.COMPLETED` and a descriptive message identifying which core handled it. Any specialized core exception causes `None` to be returned — falling through gracefully to HybridCore.

## Request Tracing

Each request gets a `request_id` (UUID from `event.event_id`). It's bound to the logger context at the start of `handle_user_input` and cleared in `finally`. This means every log line during a request carries the same `request_id` for easy trace reconstruction.

## Tool Call Execution (Step 6 Extension)

If CognitionCore returns a `TaskResponse` with non-empty `tool_calls`:

```python
for tool in response.tool_calls:
    plugin = self._registry.get(tool.tool_name)
    result = await plugin.execute(tool.action, **json.loads(tool.arguments_json))
    # Publishes tool_request + tool_result events to EventBus
```

Tool results are not currently fed back into the model (no ReAct loop yet — Stage 5 work).
