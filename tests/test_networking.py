from skyrecon import (
    ForwardingBuffer,
    LinkReport,
    MeshMessage,
    MeshTopology,
    NetworkCondition,
    RelayPositionAdvisor,
    Vector3,
)


def link(source: str, destination: str, *, loss: float = 0.02, signal: float = -60) -> LinkReport:
    return LinkReport(source, destination, signal, latency_ms=20, loss_ratio=loss, capacity_kbps=512, observed_at=100)


def test_mesh_uses_relay_when_direct_link_is_poor() -> None:
    topology = MeshTopology()
    topology.update(link("command", "field", loss=0.8, signal=-95))
    topology.update(link("command", "relay"))
    topology.update(link("relay", "field"))
    assert topology.path("command", "field", now=100) == ["command", "relay", "field"]


def test_stale_links_produce_isolated_condition() -> None:
    topology = MeshTopology(stale_after=5)
    topology.update(link("robot-a", "robot-b"))
    assert topology.condition("robot-a", now=100) is NetworkCondition.HEALTHY
    assert topology.condition("robot-a", now=106) is NetworkCondition.ISOLATED


def test_buffer_prioritizes_emergency_traffic() -> None:
    buffer = ForwardingBuffer(capacity=2)
    routine = MeshMessage("a", "base", b"status", priority=2, created_at=100)
    urgent = MeshMessage("b", "base", b"medical request", priority=10, created_at=101)
    buffer.accept(routine, now=102)
    buffer.accept(urgent, now=102)
    assert [item.message_id for item in buffer.pending(now=102)] == [urgent.message_id, routine.message_id]


def test_buffer_rejects_expired_message() -> None:
    buffer = ForwardingBuffer()
    expired = MeshMessage("a", "b", b"old", lifetime_seconds=5, created_at=10)
    assert not buffer.accept(expired, now=20)


def test_relay_advisor_returns_midpoint_at_safe_height() -> None:
    target = RelayPositionAdvisor.between(Vector3(0, 10, -2), Vector3(20, 30, -4), altitude=15)
    assert target == Vector3(10, 20, -15)
