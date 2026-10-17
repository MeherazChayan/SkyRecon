"""Deterministic in-memory vehicle adapter."""

from __future__ import annotations

import asyncio
from time import monotonic

from ..models import Telemetry, Vector3, VehicleMode


class SimulatedVehicle:
    def __init__(self, vehicle_id: str, position: Vector3 = Vector3()) -> None:
        self.vehicle_id = vehicle_id
        self._position = position
        self._velocity = Vector3()
        self._mode = VehicleMode.OFFLINE

    async def connect(self) -> None:
        await asyncio.sleep(0)
        self._mode = VehicleMode.READY

    async def apply_velocity(self, velocity: Vector3, interval: float) -> None:
        if self._mode is VehicleMode.OFFLINE:
            raise RuntimeError(f"{self.vehicle_id} is not connected")
        self._mode = VehicleMode.ACTIVE
        self._velocity = velocity
        self._position = self._position + velocity.scale(interval)
        await asyncio.sleep(0)

    async def land(self) -> None:
        self._velocity = Vector3()
        self._mode = VehicleMode.LANDED
        await asyncio.sleep(0)

    def telemetry(self) -> Telemetry:
        return Telemetry(self.vehicle_id, self._position, self._velocity, mode=self._mode, observed_at=monotonic())
