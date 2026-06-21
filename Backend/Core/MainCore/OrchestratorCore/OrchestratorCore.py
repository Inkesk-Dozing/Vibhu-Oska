"""
Vibhu-Oska AI-OS — OrchestratorCore
Driven by the ZeroMQ Event Bus, orchestrating the request processing lifecycle.
"""

from __future__ import annotations

import json
import time
import uuid
from typing import Any

from Backend.Core.BackupCore.BackupCore import BackupCore
from Backend.Core.EventBus.EventBus import EventBus
from Backend.Core.EventBus.Events import Event, EventFactory
from Backend.Core.EventBus.Topics import Topics
from Backend.Core.MainCore.HybridCore.HybridCore import HybridCore
from Backend.Core.MainCore.CognitionCore.cognition import CognitionCore
from Backend.Core.MainCore.ValidationCore.validation import ValidationCore
from Backend.Core.MainCore.MonitoringCore.MonitoringCore import MonitoringCore
from Backend.Core.MainCore.OptimizationCore.OptimizationCore import OptimizationCore
from Backend.Core.SpecializedCore.DataCore.datacore import DataCore
from Backend.Core.SpecializedCore.AutomationCore.AutomationCore import AutomationCore
from Backend.Core.SpecializedCore.DesignCore.DesignCore import DesignCore
from Backend.Core.SpecializedCore.ImageGenerationCore.ImageGenerationCore import ImageGenerationCore
from Backend.Plugins.Logger.Logger import Logger
from Backend.Plugins.ToolRegistry.Registry import ToolRegistry
from Shared.Models import TaskResponse, StatusCode


class OrchestratorCore:
    """
    OrchestratorCore manages the lifecycle of chat & task execution.
    Driven by event subscriptions, coordinating double-validation, memory, and cognition.
    """

    def __init__(self) -> None:
        self._event_bus: EventBus | None = None
        self._registry: ToolRegistry | None = None
        self._data_core = DataCore()
        self._validation = ValidationCore()
        self._monitoring = MonitoringCore()
        self._optimization = OptimizationCore()
        self._hybrid_core: HybridCore | None = None
        self._automation_core = AutomationCore()
        self._design_core = DesignCore()
        self._image_core = ImageGenerationCore()
        self._log = Logger.get("Orchestrator")
        self._initialized = False

    async def start(self, event_bus: EventBus, registry: ToolRegistry) -> None:
        """Boot the orchestrator and subscribe to central user input events."""
        if self._initialized:
            return

        self._event_bus = event_bus
        self._registry = registry
        
        # Initialize sub-cores
        await self._data_core.initialize(registry)
        self._validation.initialize()
        await self._monitoring.initialize(registry, event_bus)
        await self._optimization.initialize(registry)
        await self._automation_core.initialize()
        await self._design_core.initialize()
        await self._image_core.initialize()
        
        # Instantiate Hybrid routing core
        primary_cog = registry.get_safe("cognition")
        if primary_cog and isinstance(primary_cog, CognitionCore):
            self._hybrid_core = HybridCore(primary_cognition=primary_cog)
        else:
            self._hybrid_core = HybridCore()
        
        await self._hybrid_core.initialize()

        # Subscribe to user inputs
        await self._event_bus.subscribe(Topics.USER_INPUT, self.handle_user_input)
        self._log.info("Orchestrator registered on EventBus", topics=[Topics.USER_INPUT])
        self._initialized = True

    async def shutdown(self) -> None:
        """Teardown orchestrator components."""
        await self._data_core.shutdown()
        if self._hybrid_core:
            # Shutdown backup client if needed
            pass
        self._initialized = False

    # ==================================================================================================

    # # Internal Separation Division

    # =================─────────────────────────────────────────────────────────────────────────────────

    async def handle_user_input(self, event: Event) -> None:
        """
        Orchestration pipeline triggered by incoming user inputs.
        Flow: input → validate → memory context → cognition → tool execution → validate → publish.
        """
        if not self._initialized:
            return

        prompt = event.payload.get("prompt", "")
        session_id = event.payload.get("session_id", "")
        user_id = event.payload.get("user_id", "operator")
        model_id = event.payload.get("model_id", "")
        request_id = event.event_id

        # Bind tracing ID for diagnostics
        Logger.bind_request(request_id)
        self._log.info("Processing user input event", session_id=session_id, user_id=user_id)
        start_time = time.time()

        try:
            # 1. VALIDATION CORE (Input Gate)
            input_pkg = {
                "prompt": prompt,
                "type": 1,  # CHAT
                "metadata": {
                    "request_id": request_id,
                    "session_id": session_id,
                    "user_id": user_id
                }
            }
            
            is_valid, reason = self._validation.validate_input_package(input_pkg)
            if not is_valid:
                self._log.warning("Input failed validation check", reason=reason)
                # Publish task failure
                fail_event = Event(
                    topic=Topics.TASK_FAILED,
                    source="orchestrator",
                    payload={"request_id": request_id, "error": f"Input validation failed: {reason}"}
                )
                await self._event_bus.publish(fail_event)
                
                # Trigger system alert
                alert_event = EventFactory.alert(
                    source="validation",
                    title="Input Validation Failure",
                    description=f"Request {request_id} rejected: {reason}",
                    severity=1  # Warning
                )
                await self._event_bus.publish(alert_event)
                return

            # 1.5 OPTIMIZATION CORE (Cache Check)
            cached_reply = await self._optimization.check_query_cache(prompt)
            if cached_reply:
                self._log.info("Cache hit! Serving response directly", prompt=prompt)
                
                # Persist session and log chat
                await self._data_core.create_session(session_id, user_id)
                user_msg_id = str(uuid.uuid4())
                ai_msg_id = str(uuid.uuid4())
                await self._data_core.save_chat_message(user_msg_id, session_id, "user", prompt)
                await self._data_core.save_chat_message(ai_msg_id, session_id, "assistant", cached_reply)

                # Send task completed event
                completed_payload = {
                    "content": cached_reply,
                    "request_id": request_id,
                    "metadata": {
                        "status": {"code": 5, "message": "Inference completed successfully (cache hit)"},
                        "processing_time_ms": int((time.time() - start_time) * 1000)
                    }
                }
                completed_event = Event(
                    topic=Topics.TASK_COMPLETED,
                    source="orchestrator",
                    payload=completed_payload
                )
                await self._event_bus.publish(completed_event)
                return

            # 2. CREATE TASK & PERSIST SESSION
            await self._data_core.create_session(session_id, user_id)
            
            created_event = EventFactory.task_created(
                task_id=request_id,
                task_type="chat",
                prompt=prompt
            )
            await self._event_bus.publish(created_event)

            # 3. DATA CORE (Context Retrieval)
            # Retrieve recent relational chat history (limit to 2 turns for the 1.14M model)
            history = await self._data_core.get_session_history(session_id, limit=2)
            
            # Query semantic memories matching prompt (limit to top_k=1)
            semantic_context = await self._data_core.query_memory(prompt, top_k=1)

            # Query knowledge graph (GraphRAG / GRAG) matching prompt
            kg_context_str = await self._data_core.query_knowledge_graph(prompt)

            # Combine histories & semantic findings into list of context chunks
            context = []
            for msg in history:
                context.append({
                    "source": f"chat_history:{msg['role']}",
                    "content": msg["content"]
                })
            context.extend(semantic_context)
            if kg_context_str:
                context.append({
                    "source": "knowledge_graph",
                    "content": kg_context_str
                })

            # Optimize and prune context using OptimizationCore
            context = await self._optimization.optimize_prompt_context(context)

            # 4. SPECIALIZED CORE ROUTING (Pre-Cognition Task Dispatcher)
            # Detect if prompt targets a specialized core before routing to HybridCore
            specialized_response = await self._route_to_specialized_core(prompt, context)
            if specialized_response is not None:
                # Wrap specialized result in a TaskResponse-compatible structure
                response = specialized_response
            else:
                # 4b. HYBRID CORE (Cognition execution target — default path)
                system_prompt = (
                    "You are Vibhu-Oska AI-OS. Respond concisely and professionally. "
                    "Ensure your response is valid and answers the prompt directly."
                )
                response = await self._hybrid_core.process_request(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    context=context,
                    model_id=model_id
                )

            # 5. DYNAMIC TOOL REGISTRY (Tool Execution)
            if response.tool_calls:
                for tool in response.tool_calls:
                    self._log.info("Executing tool call", tool=tool.tool_name, action=tool.action)
                    tool_req = EventFactory.tool_request(
                        tool_name=tool.tool_name,
                        action=tool.action,
                        arguments=json.loads(tool.arguments_json)
                    )
                    await self._event_bus.publish(tool_req)
                    
                    try:
                        plugin = self._registry.get(tool.tool_name)
                        result = await plugin.execute(tool.action, **json.loads(tool.arguments_json))
                        
                        tool_res = Event(
                            topic=Topics.tool_result_for(tool.tool_name),
                            source="orchestrator",
                            payload={"status": "success", "result": result}
                        )
                        await self._event_bus.publish(tool_res)
                    except Exception as err:
                        self._log.error("Tool execution failed", tool=tool.tool_name, error=str(err))
                        tool_res = Event(
                            topic=Topics.tool_result_for(tool.tool_name),
                            source="orchestrator",
                            payload={"status": "error", "error": str(err)}
                        )
                        await self._event_bus.publish(tool_res)

            # 6. VALIDATION CORE (Output Gate)
            is_output_valid, out_reason = self._validation.validate_ai_output(response)
            if not is_output_valid:
                self._log.error("AI output failed validation check", reason=out_reason)
                fail_event = Event(
                    topic=Topics.TASK_FAILED,
                    source="orchestrator",
                    payload={"request_id": request_id, "error": f"Output validation failed: {out_reason}"}
                )
                await self._event_bus.publish(fail_event)
                return

            # 7. DATA CORE (Save chat interaction)
            user_msg_id = str(uuid.uuid4())
            ai_msg_id = str(uuid.uuid4())
            await self._data_core.save_chat_message(user_msg_id, session_id, "user", prompt)
            await self._data_core.save_chat_message(ai_msg_id, session_id, "assistant", response.content)

            # Save to response cache in OptimizationCore
            await self._optimization.save_response_cache(prompt, response.content)

            # 8. PUBLISH RESULT
            elapsed_ms = int((time.time() - start_time) * 1000)
            response.metadata.processing_time_ms = elapsed_ms
            
            completed_payload = response.model_dump()
            completed_payload["request_id"] = request_id
            
            completed_event = Event(
                topic=Topics.TASK_COMPLETED,
                source="orchestrator",
                payload=completed_payload
            )
            await self._event_bus.publish(completed_event)
            self._log.info("Request completed successfully", elapsed_ms=elapsed_ms)

        except Exception as e:
            elapsed_ms = int((time.time() - start_time) * 1000)
            self._log.exception("Unhandled error during request orchestration")
            
            fail_event = Event(
                topic=Topics.TASK_FAILED,
                source="orchestrator",
                payload={"request_id": request_id, "error": f"Internal exception: {str(e)}"}
            )
            await self._event_bus.publish(fail_event)

        finally:
            Logger.clear_context()

    # ==================================================================================================

    # # Internal Separation Division

    # =================─────────────────────────────────────────────────────────────────────────────────

    async def _route_to_specialized_core(
        self, prompt: str, context: list[dict[str, Any]]
    ) -> TaskResponse | None:
        """
        Pre-cognition specialized core router.

        Classifies the prompt via keyword matching and dispatches to the
        appropriate SpecializedCore (AutomationCore, DesignCore, ImageGenerationCore).
        Returns None if no specialized core matches — allowing the normal HybridCore path.

        Parameters:
            prompt: User input string
            context: Retrieved context chunks from DataCore
        Returns: TaskResponse if a specialized core handled the request, else None
        Edge cases: Any specialized core exception is caught and None is returned,
                    falling back to HybridCore gracefully
        """
        from Shared.Models import TaskResponse, TokenUsage, ResponseMetadata, Status, StatusCode
        import json as _json

        prompt_lower = prompt.lower()

        # ── IMAGE GENERATION ─────────────────────────────────────────────
        _image_triggers = {
            "generate image", "draw", "render image", "create image",
            "picture of", "show me an image", "make an image", "paint",
        }
        if any(trigger in prompt_lower for trigger in _image_triggers):
            try:
                self._log.info("Routing to ImageGenerationCore", prompt_fragment=prompt[:60])
                result = await self._image_core.execute(
                    "generate_image", prompt=prompt
                )
                content = (
                    result.get("message") or
                    result.get("descriptor", {}).get("message") or
                    f"Image generation: {result.get('status', 'unknown')}"
                )
                if result.get("status") == "success" and result.get("image_base64"):
                    content = f"[IMAGE_GENERATED] base64:{result['image_base64'][:64]}..."
                return TaskResponse(
                    content=content,
                    token_usage=TokenUsage(prompt_tokens=0, completion_tokens=0, total_tokens=0),
                    metadata=ResponseMetadata(
                        status=Status(code=StatusCode.COMPLETED, message="Handled by ImageGenerationCore"),
                    ),
                )
            except Exception as e:
                self._log.warning("ImageGenerationCore routing failed, falling back", error=str(e))

        # ── DESIGN / UI GENERATION ────────────────────────────────────────
        _design_triggers = {
            "design", "layout", "ui component", "generate component",
            "create a dashboard", "build a ui", "html", "css layout",
            "interface", "webpage", "make a page",
        }
        if any(trigger in prompt_lower for trigger in _design_triggers):
            try:
                self._log.info("Routing to DesignCore", prompt_fragment=prompt[:60])
                # Detect whether this is a component or full layout request
                if any(k in prompt_lower for k in ["card", "modal", "table", "nav", "button", "stat"]):
                    comp = next(
                        (c for c in ["card", "modal", "table", "nav_item", "stat_card", "chat"]
                         if c.replace("_", " ") in prompt_lower or c in prompt_lower), "card"
                    )
                    result = await self._design_core.execute(
                        "generate_component",
                        component_type=comp,
                        props={"title": "Generated Component", "body": prompt},
                    )
                    content = f"[COMPONENT_HTML]\n{result.get('html', '')}"
                else:
                    result = await self._design_core.execute(
                        "generate_layout",
                        description=prompt,
                        page_title="Vibhu-Oska Generated",
                    )
                    content = f"[LAYOUT_HTML]\n{result.get('html', '')[:1024]}"

                return TaskResponse(
                    content=content,
                    token_usage=TokenUsage(prompt_tokens=0, completion_tokens=0, total_tokens=0),
                    metadata=ResponseMetadata(
                        status=Status(code=StatusCode.COMPLETED, message="Handled by DesignCore"),
                    ),
                )
            except Exception as e:
                self._log.warning("DesignCore routing failed, falling back", error=str(e))

        # ── OS / AUTOMATION ───────────────────────────────────────────────
        _os_triggers = {
            "list files", "list directory", "list folder", "show files",
            "run command", "execute", "open app", "launch", "open application",
            "cpu usage", "memory usage", "system info", "disk space",
            "what processes", "kill process", "terminate", "check process",
            "read file", "write file", "what is my ram", "gpu info",
            "system status", "hardware",
        }
        if any(trigger in prompt_lower for trigger in _os_triggers):
            try:
                self._log.info("Routing to AutomationCore", prompt_fragment=prompt[:60])

                # Determine specific action
                if any(k in prompt_lower for k in ["cpu", "memory", "ram", "disk", "gpu", "system info", "hardware", "system status"]):
                    result = await self._automation_core.execute("get_system_info")
                    data = result.get("data", {})
                    cpu = data.get("cpu", {})
                    mem = data.get("memory", {})
                    disk = data.get("disk", {})
                    gpu = data.get("gpu", {})
                    content = (
                        f"**System Telemetry**\n"
                        f"CPU: {cpu.get('usage_percent', '?')}% ({cpu.get('physical_cores', '?')} cores @ {cpu.get('frequency_mhz', '?')}MHz)\n"
                        f"Memory: {mem.get('used_gb', '?')}GB used / {mem.get('total_gb', '?')}GB total ({mem.get('usage_percent', '?')}%)\n"
                        f"Disk: {disk.get('free_gb', '?')}GB free / {disk.get('total_gb', '?')}GB total\n"
                        f"GPU: {gpu.get('name', 'N/A')} — {gpu.get('vram_allocated_mb', 'N/A')}MB allocated"
                    )

                elif any(k in prompt_lower for k in ["list files", "list directory", "list folder", "show files"]):
                    # Extract path from prompt — simple heuristic
                    import re as _re
                    path_match = _re.search(r'[A-Za-z]:[\\\\./\w\s-]+|/[\w./\s-]+', prompt)
                    target_path = path_match.group(0).strip() if path_match else "."
                    result = await self._automation_core.execute("list_directory", path=target_path)
                    entries = result.get("entries", [])
                    lines = [f"**Directory: {result.get('path', target_path)}**"]
                    for e in entries[:30]:
                        icon = "📁" if e["type"] == "directory" else "📄"
                        size = f" ({e['size_bytes']}B)" if e.get("size_bytes") is not None else ""
                        lines.append(f"{icon} {e['name']}{size}")
                    if len(entries) > 30:
                        lines.append(f"... and {len(entries) - 30} more")
                    content = "\n".join(lines)

                else:
                    # Generic: return system info as fallback
                    result = await self._automation_core.execute("get_system_info")
                    content = f"AutomationCore result: {_json.dumps(result.get('data', result), indent=2)[:800]}"

                return TaskResponse(
                    content=content,
                    token_usage=TokenUsage(prompt_tokens=0, completion_tokens=0, total_tokens=0),
                    metadata=ResponseMetadata(
                        status=Status(code=StatusCode.COMPLETED, message="Handled by AutomationCore"),
                    ),
                )
            except Exception as e:
                self._log.warning("AutomationCore routing failed, falling back", error=str(e))

        # No specialized core matched — return None to trigger HybridCore path
        return None

    def process_request(self, request: Any) -> Any:
        """Stub pass-through."""
        pass
