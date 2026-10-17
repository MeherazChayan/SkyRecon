"""Core value objects used by Sky Recon."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from math import sqrt
from time import monotonic


@dataclass(frozen=True, slots=True)
class Vector3:
    north: float = 0.0
    east: float = 0.0
    down: float = 0.0

    def __add__(self, other: "Vector3") -> "Vector3":
        return Vector3(self.north + other.north, self.east + other.east, self.down + other.down)

    def __sub__(self, other: "Vector3") -> "Vector3":
        return Vector3(self.north - other.north, self.east - other.east, self.down - other.down)

    def scale(self, factor: float) -> "Vector3":
        return Vector3(self.north * factor, self.east * factor, self.down * factor)

    @property
    def length(self) -> float:
        return sqrt(self.north**2 + self.east**2 + self.down**2)

    def limited(self, maximum: float) -> "Vector3":
        magnitude = self.length
        return self if magnitude <= maximum or magnitude == 0 else self.scale(maximum / magnitude)


class VehicleMode(str, Enum):
    OFFLINE = "offline"
    READY = "ready"
    ACTIVE = "active"
    RETURNING = "returning"
    LANDED = "landed"


@dataclass(frozen=True, slots=True)
class Telemetry:
    vehicle_id: str
    position: Vector3
    velocity: Vector3 = Vector3()
    battery_percent: float = 100.0
    mode: VehicleMode = VehicleMode.READY
    observed_at: float = field(default_factory=monotonic)


@dataclass(frozen=True, slots=True)
class Mission:
    mission_id: str
    destination: Vector3
    cruise_speed: float = 4.0
    arrival_radius: float = 0.75

    def __post_init__(self) -> None:
        if self.cruise_speed <= 0 or self.arrival_radius <= 0:
            raise ValueError("mission speed and arrival radius must be positive")
