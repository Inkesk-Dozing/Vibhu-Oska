"""
Vibhu-Oska AI-OS — Event Bus Topics
Canonical topic constants for the ZeroMQ PUB/SUB event bus.

Topic naming convention:
    {domain}.{action}[.{detail}]

Examples:
    task.created
    tool.request.search_engine
    system.health.gpu
"""


class Topics:
    """
    Centralized topic registry. All event bus subscriptions reference these constants
    to prevent typo-driven routing failures.
    """

    # ── Task Lifecycle ──
    TASK_CREATED = "task.created"
    TASK_STARTED = "task.started"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"
    TASK_CANCELLED = "task.cancelled"

    # ── User Events ──
    USER_INPUT = "user.input"
    USER_FEEDBACK = "user.feedback"

    # ── Tool / Plugin Events ──
    TOOL_REQUEST = "tool.request"
    TOOL_RESULT = "tool.result"

    # ── Cognition Events ──
    COGNITION_INFERENCE_START = "cognition.inference.start"
    COGNITION_INFERENCE_DONE = "cognition.inference.done"
    COGNITION_STREAM_TOKEN = "cognition.stream.token"

    # ── Memory Events ──
    MEMORY_QUERY = "memory.query"
    MEMORY_STORE = "memory.store"
    MEMORY_UPDATED = "memory.updated"

    # ── Routing Events ──
    ROUTE_DECISION = "route.decision"
    ROUTE_QUEUE = "route.queue"

    # ── System Health ──
    SYSTEM_HEALTH = "system.health"
    SYSTEM_HEARTBEAT = "system.heartbeat"
    SYSTEM_ALERT = "system.alert"
    SYSTEM_SHUTDOWN = "system.shutdown"

    # ── Model Management ──
    MODEL_LOADED = "model.loaded"
    MODEL_UNLOADED = "model.unloaded"
    MODEL_TRAINING_START = "model.training.start"
    MODEL_TRAINING_DONE = "model.training.done"

    # ── Self-Improvement ──
    SELF_REPAIR_TRIGGERED = "self.repair.triggered"
    SELF_REPAIR_COMPLETED = "self.repair.completed"

    # ── Schedule ──
    SCHEDULE_TRIGGERED = "schedule.triggered"

    # ==================================================================================================

    # # Internal Separation Division

    # =================─────────────────────────────────────────────────────────────────────────────────

    @classmethod
    def all_topics(cls) -> list[str]:
        """Return all registered topic strings."""
        return [
            value for name, value in vars(cls).items()
            if isinstance(value, str) and not name.startswith("_")
        ]

    @classmethod
    def tool_request_for(cls, tool_name: str) -> str:
        """Generate a tool-specific request topic."""
        return f"{cls.TOOL_REQUEST}.{tool_name}"

    @classmethod
    def tool_result_for(cls, tool_name: str) -> str:
        """Generate a tool-specific result topic."""
        return f"{cls.TOOL_RESULT}.{tool_name}"
