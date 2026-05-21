"""
Vibhu-Oska AI-OS — ZeroMQ Event Bus
The central nervous system of the Multi-Core Plugin Mesh.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine
from typing import Any

import zmq
import zmq.asyncio

from Backend.Core.EventBus.Events import Event
from Backend.Core.EventBus.Topics import Topics


# Type alias for event handler callbacks
EventHandler = Callable[[Event], Coroutine[Any, Any, None]]


class EventBus:
    """
    ZeroMQ-based event bus for inter-core messaging.

    Usage:
        bus = EventBus()
        await bus.start()

        # Subscribe to events
        await bus.subscribe("task.created", my_handler)
        await bus.subscribe("system.*", my_wildcard_handler)

        # Publish events
        await bus.publish(EventFactory.task_created(...))

        # Push tasks to workers
        await bus.push_task(EventFactory.user_input("Hello"))

        await bus.stop()
    """

    def __init__(
        self,
        pub_port: int = 5555,
        sub_port: int = 5556,
        push_port: int = 5557,
        pull_port: int = 5558,
    ):
        self._pub_port = pub_port
        self._sub_port = sub_port
        self._push_port = push_port
        self._pull_port = pull_port

        self._context: zmq.asyncio.Context | None = None
        self._pub_socket: zmq.asyncio.Socket | None = None
        self._sub_socket: zmq.asyncio.Socket | None = None
        self._push_socket: zmq.asyncio.Socket | None = None
        self._pull_socket: zmq.asyncio.Socket | None = None

        # Handler registry: topic_prefix → list of async handlers
        self._handlers: dict[str, list[EventHandler]] = {}
        self._running: bool = False
        self._listener_task: asyncio.Task | None = None
        self._worker_task: asyncio.Task | None = None

    # ══════════════════════════════════════════════════════════════════════
    # Lifecycle
    # ══════════════════════════════════════════════════════════════════════

    async def start(self) -> None:
        """Initialize ZeroMQ sockets and start the listener loops."""
        if self._running:
            return

        self._context = zmq.asyncio.Context()

        # PUB socket: binds and broadcasts events
        self._pub_socket = self._context.socket(zmq.PUB)
        self._pub_socket.bind(f"tcp://127.0.0.1:{self._pub_port}")

        # SUB socket: connects and receives events
        self._sub_socket = self._context.socket(zmq.SUB)
        self._sub_socket.connect(f"tcp://127.0.0.1:{self._pub_port}")

        # PUSH socket: binds for task distribution
        self._push_socket = self._context.socket(zmq.PUSH)
        self._push_socket.bind(f"tcp://127.0.0.1:{self._push_port}")

        # PULL socket: connects for task consumption
        self._pull_socket = self._context.socket(zmq.PULL)
        self._pull_socket.connect(f"tcp://127.0.0.1:{self._push_port}")

        self._running = True

        # Start background listener tasks
        self._listener_task = asyncio.create_task(self._sub_listener_loop())
        self._worker_task = asyncio.create_task(self._pull_worker_loop())

        # Small delay to let ZeroMQ sockets settle
        await asyncio.sleep(0.1)

    async def stop(self) -> None:
        """Gracefully shut down all sockets and listener tasks."""
        self._running = False

        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass

        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass

        for sock in [self._pub_socket, self._sub_socket, self._push_socket, self._pull_socket]:
            if sock:
                sock.close(linger=0)

        if self._context:
            self._context.term()

        self._context = None
        self._running = False

    @property
    def is_running(self) -> bool:
        return self._running

    # ==================================================================================================

    # # Internal Separation Division

    # =================─────────────────────────────────────────────────────────────────────────────────

    # ══════════════════════════════════════════════════════════════════════
    # PUB/SUB — Broadcast Events
    # ══════════════════════════════════════════════════════════════════════

    async def publish(self, event: Event) -> None:
        """
        Publish an event to all subscribers matching the topic.

        Args:
            event: The event to broadcast
        """
        if not self._pub_socket:
            raise RuntimeError("EventBus not started. Call await bus.start() first.")

        frames = event.to_zmq_frames()
        await self._pub_socket.send_multipart(frames)

    async def subscribe(self, topic_prefix: str, handler: EventHandler) -> None:
        """
        Subscribe to events matching a topic prefix.

        Args:
            topic_prefix: Topic to subscribe to (e.g., "task.created" or "task." for all task events)
            handler: Async function called with the Event when a matching event arrives
        """
        if not self._sub_socket:
            raise RuntimeError("EventBus not started. Call await bus.start() first.")

        # Register the handler
        if topic_prefix not in self._handlers:
            self._handlers[topic_prefix] = []
            # Tell ZeroMQ to forward messages with this prefix
            self._sub_socket.subscribe(topic_prefix.encode("utf-8"))

        self._handlers[topic_prefix].append(handler)

    async def unsubscribe(self, topic_prefix: str) -> None:
        """Remove all handlers for a topic prefix."""
        if topic_prefix in self._handlers:
            del self._handlers[topic_prefix]
            if self._sub_socket:
                self._sub_socket.unsubscribe(topic_prefix.encode("utf-8"))

    # ══════════════════════════════════════════════════════════════════════
    # PUSH/PULL — Task Distribution
    # ══════════════════════════════════════════════════════════════════════

    async def push_task(self, event: Event) -> None:
        """
        Push a task to the work queue for a single worker to consume.
        Unlike publish, this ensures exactly one worker processes the task.
        """
        if not self._push_socket:
            raise RuntimeError("EventBus not started.")

        data = event.serialize().encode("utf-8")
        await self._push_socket.send(data)

    # ══════════════════════════════════════════════════════════════════════
    # Background Listener Loops
    # ══════════════════════════════════════════════════════════════════════

    async def _sub_listener_loop(self) -> None:
        """Continuously receive PUB/SUB messages and dispatch to handlers."""
        while self._running and self._sub_socket:
            try:
                frames = await self._sub_socket.recv_multipart()
                event = Event.from_zmq_frames(frames)
                await self._dispatch(event)
            except zmq.ZMQError:
                if self._running:
                    await asyncio.sleep(0.1)
            except asyncio.CancelledError:
                break
            except Exception:
                # Log but don't crash the listener
                await asyncio.sleep(0.01)

    async def _pull_worker_loop(self) -> None:
        """Continuously receive PUSH/PULL tasks and dispatch to handlers."""
        while self._running and self._pull_socket:
            try:
                data = await self._pull_socket.recv()
                event = Event.deserialize(data.decode("utf-8"))
                await self._dispatch(event)
            except zmq.ZMQError:
                if self._running:
                    await asyncio.sleep(0.1)
            except asyncio.CancelledError:
                break
            except Exception:
                await asyncio.sleep(0.01)

    async def _dispatch(self, event: Event) -> None:
        """Find and invoke all handlers whose topic prefix matches the event."""
        for prefix, handlers in self._handlers.items():
            if event.topic.startswith(prefix):
                for handler in handlers:
                    try:
                        await handler(event)
                    except Exception:
                        # Individual handler failures don't kill the bus
                        pass

    # ══════════════════════════════════════════════════════════════════════
    # Utility
    # ══════════════════════════════════════════════════════════════════════

    def registered_topics(self) -> list[str]:
        """Return all topic prefixes with registered handlers."""
        return list(self._handlers.keys())

    def handler_count(self, topic_prefix: str) -> int:
        """Return the number of handlers registered for a topic prefix."""
        return len(self._handlers.get(topic_prefix, []))
