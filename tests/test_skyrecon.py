import asyncio

from skyrecon import AirspaceGrid, EventJournal, Mission, MissionCoordinator, SafetyPolicy, SeparationGuard, Telemetry, Vector3
from skyrecon.adapters import SimulatedVehicle


def test_route_avoids_obstacle() -> None:
    grid = AirspaceGrid(8, 8)
    grid.block_disc((3, 3), radius=1)
    route = grid.route((0, 3), (7, 3))
    assert route[0] == (0, 3)
    assert route[-1] == (7, 3)
    assert (3, 3) not in route


def test_separation_guard_changes_collision_command() -> None:
    guard = SeparationGuard(SafetyPolicy(minimum_separation=4, prediction_seconds=1))
    subject = Telemetry("north", Vector3(0, 0), observed_at=10)
    neighbor = Telemetry("south", Vector3(3, 0), observed_at=10)
    output = guard.constrain(subject, Vector3(2, 0), [neighbor], now=10)
    assert output.north < 2


def test_coordinator_completes_and_journals_mission(tmp_path) -> None:
    async def scenario() -> None:
        journal = EventJournal(tmp_path / "events.db")
        coordinator = MissionCoordinator(journal)
        coordinator.register(SimulatedVehicle("scout"))
        assert await coordinator.connect() == {"scout": True}
        final = await coordinator.fly("scout", Mission("survey-a", Vector3(4, 3), cruise_speed=5), tick_seconds=0.1)
        assert (Vector3(4, 3) - final.position).length <= 0.75
        assert any(event["kind"] == "mission.arrived" for event in journal.recent())

    asyncio.run(scenario())


def test_emergency_landing_applies_to_all(tmp_path) -> None:
    async def scenario() -> None:
        coordinator = MissionCoordinator(EventJournal(tmp_path / "events.db"))
        coordinator.register(SimulatedVehicle("a"))
        coordinator.register(SimulatedVehicle("b"))
        await coordinator.connect()
        await coordinator.land_everyone()
        assert {reading.mode.value for reading in coordinator.snapshot().values()} == {"landed"}

    asyncio.run(scenario())
