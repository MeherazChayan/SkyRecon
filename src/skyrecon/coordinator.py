"""Mission orchestration independent of any flight-controller transport."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from time import monotonic
from typing import Protocol

from .journal import EventJournal
from .models import Mission, Telemetry, Vector3
from .safety import SeparationGuard


class VehicleAdapter(Protocol):
    vehicle_id: str

    async def connect(self) -> None: ...
    async def apply_velocity(self, velocity: Vector3, interval: float) -> None: ...
    async def land(self) -> None: ...
    def telemetry(self) -> Telemetry: ...


class MissionCoordinator:
    def __init__(self, journal: EventJournal, guard: SeparationGuard | None = None) -> None:
        self.journal = journal
        self.guard = guard or SeparationGuard()
        self._vehicles: dict[str, VehicleAdapter] = {}
        self._listeners: list[Callable[[Telemetry], None]] = []

    def register(self, vehicle: VehicleAdapter) -> None:
        if vehicle.vehicle_id in self._vehicles:
            raise ValueError(f"duplicate vehicle id: {vehicle.vehicle_id}")
        self._vehicles[vehicle.vehicle_id] = vehicle
        self.journal.record("vehicle.registered", vehicle.vehicle_id)

    def subscribe(self, listener: Callable[[Telemetry], None]) -> None:
        self._listeners.append(listener)

    async def connect(self) -> dict[str, bool]:
        results = await asyncio.gather(*(self._connect_one(vehicle) for vehicle in self._vehicles.values()))
        return dict(results)

    async def _connect_one(self, vehicle: VehicleAdapter) -> tuple[str, bool]:
        try:
            await vehicle.connect()
            self.journal.record("vehicle.connected", vehicle.vehicle_id)
            return vehicle.vehicle_id, True
        except Exception as error:
            self.journal.record("vehicle.connection_failed", vehicle.vehicle_id, error=str(error))
            return vehicle.vehicle_id, False

    def snapshot(self) -> dict[str, Telemetry]:
        readings = {key: vehicle.telemetry() for key, vehicle in self._vehicles.items()}
        for reading in readings.values():
            for listener in self._listeners:
                listener(reading)
        return readings

    async def fly(self, vehicle_id: str, mission: Mission, tick_seconds: float = 0.1, timeout: float = 120.0) -> Telemetry:
        vehicle = self._vehicles[vehicle_id]
        started = monotonic()
        self.journal.record("mission.started", vehicle_id, mission_id=mission.mission_id)
        while monotonic() - started < timeout:
            fleet = self.snapshot()
            current = fleet[vehicle_id]
            error = mission.destination - current.position
            if error.length <= mission.arrival_radius:
                self.journal.record("mission.arrived", vehicle_id, mission_id=mission.mission_id)
                return current
            desired = error.scale(mission.cruise_speed / error.length)
            safe = self.guard.constrain(current, desired, list(fleet.values()), monotonic())
            await vehicle.apply_velocity(safe, tick_seconds)
        self.journal.record("mission.timed_out", vehicle_id, mission_id=mission.mission_id)
        raise TimeoutError(f"mission {mission.mission_id} exceeded {timeout} seconds")

    async def fly_all(self, assignments: dict[str, Mission], **options: float) -> dict[str, Telemetry]:
        completed = await asyncio.gather(*(self.fly(vehicle_id, mission, **options) for vehicle_id, mission in assignments.items()))
        return dict(zip(assignments, completed))

    async def land_everyone(self) -> None:
        await asyncio.gather(*(vehicle.land() for vehicle in self._vehicles.values()))
        for vehicle_id in self._vehicles:
            self.journal.record("vehicle.landed", vehicle_id)
