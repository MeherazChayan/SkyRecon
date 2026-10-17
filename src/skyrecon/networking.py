"""Transport-neutral tools for resilient robot-to-robot communication.

This module models link quality and message forwarding. Radio drivers remain
separate so deployments can enforce local spectrum and security requirements.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from heapq import heappop, heappush
from time import monotonic
from uuid import uuid4

from .models import Vector3


class NetworkCondition(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    ISOLATED = "isolated"


@dataclass(frozen=True, slots=True)
class LinkReport:
    source: str
    destination: str
    signal_dbm: float
    latency_ms: float
    loss_ratio: float
    capacity_kbps: float
    observed_at: float = field(default_factory=monotonic)

    def __post_init__(self) -> None:
        if not 0.0 <= self.loss_ratio <= 1.0:
            raise ValueError("loss_ratio must be between zero and one")
        if self.latency_ms < 0 or self.capacity_kbps < 0:
            raise ValueError("latency and capacity cannot be negative")

    @property
    def route_cost(self) -> float:
        if self.capacity_kbps == 0 or self.loss_ratio >= 1.0:
            return float("inf")
        weak_signal_penalty = max(0.0, (-70.0 - self.signal_dbm) / 8.0)
        return 1.0 + self.latency_ms / 100.0 + self.loss_ratio * 12.0 + weak_signal_penalty


@dataclass(frozen=True, slots=True)
class MeshMessage:
    sender: str
    recipient: str
    payload: bytes
    priority: int = 5
    lifetime_seconds: float = 300.0
    message_id: str = field(default_factory=lambda: uuid4().hex)
    created_at: float = field(default_factory=monotonic)

    def expired(self, now: float | None = None) -> bool:
        return (monotonic() if now is None else now) > self.created_at + self.lifetime_seconds


class MeshTopology:
    """Maintains recent link reports and chooses the least-cost multi-hop path."""

    def __init__(self, stale_after: float = 8.0) -> None:
        self.stale_after = stale_after
        self._links: dict[tuple[str, str], LinkReport] = {}

    def update(self, report: LinkReport) -> None:
        self._links[(report.source, report.destination)] = report

    def neighbors(self, node: str, now: float | None = None) -> list[LinkReport]:
        current = monotonic() if now is None else now
        return [
            report for (source, _), report in self._links.items()
            if source == node and current - report.observed_at <= self.stale_after and report.route_cost != float("inf")
        ]

    def path(self, source: str, destination: str, now: float | None = None) -> list[str]:
        current = monotonic() if now is None else now
        frontier: list[tuple[float, str]] = [(0.0, source)]
        costs = {source: 0.0}
        parent: dict[str, str | None] = {source: None}
        while frontier:
            cost, node = heappop(frontier)
            if node == destination:
                break
            if cost != costs[node]:
                continue
            for link in self.neighbors(node, current):
                candidate = cost + link.route_cost
                if candidate < costs.get(link.destination, float("inf")):
                    costs[link.destination] = candidate
                    parent[link.destination] = node
                    heappush(frontier, (candidate, link.destination))
        if destination not in parent:
            return []
        route: list[str] = []
        cursor: str | None = destination
        while cursor is not None:
            route.append(cursor)
            cursor = parent[cursor]
        return list(reversed(route))

    def condition(self, node: str, now: float | None = None) -> NetworkCondition:
        links = self.neighbors(node, now)
        if not links:
            return NetworkCondition.ISOLATED
        best = min(link.route_cost for link in links)
        return NetworkCondition.HEALTHY if best < 5.0 else NetworkCondition.DEGRADED


class ForwardingBuffer:
    """Bounded priority buffer for delay-tolerant store-and-forward delivery."""

    def __init__(self, capacity: int = 1_000) -> None:
        if capacity < 1:
            raise ValueError("capacity must be positive")
        self.capacity = capacity
        self._messages: dict[str, MeshMessage] = {}

    def accept(self, message: MeshMessage, now: float | None = None) -> bool:
        if message.expired(now) or message.message_id in self._messages:
            return False
        self._messages[message.message_id] = message
        if len(self._messages) > self.capacity:
            lowest = min(self._messages.values(), key=lambda item: (item.priority, -item.created_at))
            del self._messages[lowest.message_id]
        return message.message_id in self._messages

    def pending(self, recipient: str | None = None, now: float | None = None) -> list[MeshMessage]:
        current = monotonic() if now is None else now
        self._messages = {key: item for key, item in self._messages.items() if not item.expired(current)}
        messages = [item for item in self._messages.values() if recipient is None or item.recipient == recipient]
        return sorted(messages, key=lambda item: (-item.priority, item.created_at))

    def acknowledge(self, message_id: str) -> None:
        self._messages.pop(message_id, None)


class RelayPositionAdvisor:
    """Suggests a neutral relay position between disconnected robot groups."""

    @staticmethod
    def between(first: Vector3, second: Vector3, altitude: float | None = None) -> Vector3:
        down = (first.down + second.down) / 2.0 if altitude is None else -abs(altitude)
        return Vector3((first.north + second.north) / 2.0, (first.east + second.east) / 2.0, down)
