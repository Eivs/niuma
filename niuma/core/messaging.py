"""Messaging system for inter-agent communication."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Callable
from uuid import uuid4

if TYPE_CHECKING:
    from niuma.core.agent import Agent


class MessagePriority(Enum):
    """Message priority levels."""

    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


class MessageType(Enum):
    """Types of messages agents can exchange."""

    TASK = "task"  # Task assignment
    RESULT = "result"  # Task completion result
    QUERY = "query"  # Information request
    RESPONSE = "response"  # Response to query
    NOTIFY = "notify"  # Notification
    COORDINATE = "coordinate"  # Coordination message
    STATUS = "status"  # Status update


@dataclass
class Message:
    """Message for agent communication."""

    sender: str
    receiver: str | None  # None = broadcast
    content: Any
    msg_type: MessageType = MessageType.NOTIFY
    priority: MessagePriority = MessagePriority.NORMAL

    # Metadata
    id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)
    correlation_id: str | None = None  # For request/response correlation
    ttl: int = 300  # seconds, 0 = no expiry

    # Delivery tracking
    delivered: bool = False
    delivery_time: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "sender": self.sender,
            "receiver": self.receiver,
            "content": self.content,
            "type": self.msg_type.value,
            "priority": self.priority.value,
            "timestamp": self.timestamp.isoformat(),
            "correlation_id": self.correlation_id,
            "ttl": self.ttl,
            "delivered": self.delivered,
        }


MessageHandler = Callable[[Message], None]


class MessageBus:
    """Central message bus for agent communication."""

    def __init__(self, max_queue_size: int = 10000) -> None:
        """Initialize message bus.

        Args:
            max_queue_size: Maximum messages in queue.
        """
        self.max_queue_size = max_queue_size
        self._queues: dict[str, asyncio.Queue[Message]] = {}  # agent_id -> queue
        self._handlers: dict[str, list[MessageHandler]] = {}  # agent_id -> handlers
        self._broadcast_handlers: list[MessageHandler] = []
        self._message_history: list[Message] = []
        self._max_history = 1000
        self._running = False
        self._dispatcher_task: asyncio.Task | None = None

    async def start(self) -> None:
        """Start the message bus."""
        self._running = True
        self._dispatcher_task = asyncio.create_task(self._dispatcher())

    async def stop(self) -> None:
        """Stop the message bus."""
        self._running = False
        if self._dispatcher_task:
            self._dispatcher_task.cancel()
            try:
                await self._dispatcher_task
            except asyncio.CancelledError:
                pass

    def register_agent(self, agent_id: str) -> None:
        """Register an agent to receive messages.

        Args:
            agent_id: Agent identifier.
        """
        if agent_id not in self._queues:
            self._queues[agent_id] = asyncio.Queue(maxsize=self.max_queue_size)

    def unregister_agent(self, agent_id: str) -> None:
        """Unregister an agent.

        Args:
            agent_id: Agent identifier.
        """
        if agent_id in self._queues:
            del self._queues[agent_id]
        if agent_id in self._handlers:
            del self._handlers[agent_id]

    def subscribe(
        self,
        agent_id: str,
        handler: MessageHandler,
    ) -> None:
        """Subscribe an agent to receive messages.

        Args:
            agent_id: Agent identifier.
            handler: Message handler function.
        """
        if agent_id not in self._handlers:
            self._handlers[agent_id] = []
        self._handlers[agent_id].append(handler)

    def unsubscribe(
        self,
        agent_id: str,
        handler: MessageHandler,
    ) -> None:
        """Unsubscribe a handler.

        Args:
            agent_id: Agent identifier.
            handler: Handler to remove.
        """
        if agent_id in self._handlers:
            self._handlers[agent_id] = [
                h for h in self._handlers[agent_id] if h != handler
            ]

    def subscribe_broadcast(self, handler: MessageHandler) -> None:
        """Subscribe to broadcast messages.

        Args:
            handler: Message handler function.
        """
        self._broadcast_handlers.append(handler)

    async def send(self, message: Message) -> bool:
        """Send a message.

        Args:
            message: Message to send.

        Returns:
            True if queued successfully, False otherwise.
        """
        # Add to history
        self._message_history.append(message)
        if len(self._message_history) > self._max_history:
            self._message_history.pop(0)

        if message.receiver is None:
            # Broadcast
            for agent_id, queue in self._queues.items():
                if agent_id != message.sender:  # Don't send to self
                    try:
                        queue.put_nowait(message)
                    except asyncio.QueueFull:
                        pass  # Drop message if queue full

            # Notify broadcast handlers
            for handler in self._broadcast_handlers:
                try:
                    handler(message)
                except Exception:
                    pass

            return True

        else:
            # Direct message
            queue = self._queues.get(message.receiver)
            if queue is None:
                return False

            try:
                queue.put_nowait(message)
                return True
            except asyncio.QueueFull:
                return False

    async def send_immediate(
        self,
        sender: str,
        receiver: str,
        content: Any,
        msg_type: MessageType = MessageType.NOTIFY,
        priority: MessagePriority = MessagePriority.NORMAL,
    ) -> bool:
        """Send a message immediately.

        Args:
            sender: Sender agent ID.
            receiver: Receiver agent ID.
            content: Message content.
            msg_type: Type of message.
            priority: Message priority.

        Returns:
            True if sent successfully.
        """
        message = Message(
            sender=sender,
            receiver=receiver,
            content=content,
            msg_type=msg_type,
            priority=priority,
        )
        return await self.send(message)

    async def request_response(
        self,
        sender: str,
        receiver: str,
        content: Any,
        timeout: float = 30.0,
    ) -> Message | None:
        """Send a query and wait for response.

        Args:
            sender: Sender agent ID.
            receiver: Receiver agent ID.
            content: Query content.
            timeout: Maximum time to wait.

        Returns:
            Response message or None if timeout.
        """
        correlation_id = str(uuid4())

        # Create response waiter
        response_queue: asyncio.Queue[Message] = asyncio.Queue()

        def response_handler(msg: Message) -> None:
            if msg.correlation_id == correlation_id:
                try:
                    response_queue.put_nowait(msg)
                except asyncio.QueueFull:
                    pass

        # Subscribe temporarily
        self.subscribe(sender, response_handler)

        # Send query
        query = Message(
            sender=sender,
            receiver=receiver,
            content=content,
            msg_type=MessageType.QUERY,
            correlation_id=correlation_id,
            priority=MessagePriority.HIGH,
        )
        await self.send(query)

        # Wait for response
        try:
            response = await asyncio.wait_for(
                response_queue.get(),
                timeout=timeout,
            )
            return response
        except asyncio.TimeoutError:
            return None
        finally:
            # Unsubscribe
            self.unsubscribe(sender, response_handler)

    async def receive(
        self,
        agent_id: str,
        timeout: float | None = None,
    ) -> Message | None:
        """Receive a message for an agent.

        Args:
            agent_id: Agent identifier.
            timeout: Maximum time to wait.

        Returns:
            Message or None if timeout.
        """
        queue = self._queues.get(agent_id)
        if queue is None:
            return None

        try:
            message = await asyncio.wait_for(queue.get(), timeout=timeout)
            message.delivered = True
            message.delivery_time = datetime.now()
            return message
        except asyncio.TimeoutError:
            return None

    def get_history(
        self,
        sender: str | None = None,
        receiver: str | None = None,
        msg_type: MessageType | None = None,
        limit: int = 100,
    ) -> list[Message]:
        """Get message history.

        Args:
            sender: Filter by sender.
            receiver: Filter by receiver.
            msg_type: Filter by type.
            limit: Maximum messages to return.

        Returns:
            List of matching messages.
        """
        messages = self._message_history

        if sender:
            messages = [m for m in messages if m.sender == sender]

        if receiver:
            messages = [m for m in messages if m.receiver == receiver]

        if msg_type:
            messages = [m for m in messages if m.msg_type == msg_type]

        return messages[-limit:]

    async def _dispatcher(self) -> None:
        """Background task to dispatch messages to handlers."""
        while self._running:
            for agent_id, queue in list(self._queues.items()):
                try:
                    # Non-blocking check
                    message = queue.get_nowait()

                    # Deliver to handlers
                    handlers = self._handlers.get(agent_id, [])
                    for handler in handlers:
                        try:
                            handler(message)
                        except Exception:
                            pass  # Log error but continue

                except asyncio.QueueEmpty:
                    continue

            await asyncio.sleep(0.01)  # Small delay to prevent busy-waiting

    def get_stats(self) -> dict[str, Any]:
        """Get message bus statistics."""
        return {
            "registered_agents": len(self._queues),
            "queue_sizes": {
                agent_id: queue.qsize()
                for agent_id, queue in self._queues.items()
            },
            "total_messages": len(self._message_history),
            "running": self._running,
        }
