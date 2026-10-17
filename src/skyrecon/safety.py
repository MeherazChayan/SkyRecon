"""Predictive deconfliction for local velocity commands."""

from __future__ import annotations

from dataclasses import dataclass

from .models import Telemetry, Vector3


@dataclass(frozen=True, slots=True)
class SafetyPolicy:
    minimum_separation: float = 3.0
    prediction_seconds: float = 2.5
    maximum_speed: float = 8.0
    stale_after: float = 3.0


class SeparationGuard:
    def __init__(self, policy: SafetyPolicy | None = None) -> None:
        self.policy = policy or SafetyPolicy()

    def constrain(self, subject: Telemetry, desired: Vector3, neighbors: list[Telemetry], now: float) -> Vector3:
        command = desired.limited(self.policy.maximum_speed)
        predicted_subject = subject.position + command.scale(self.policy.prediction_seconds)
        correction = Vector3()
        for neighbor in neighbors:
            if neighbor.vehicle_id == subject.vehicle_id or now - neighbor.observed_at > self.policy.stale_after:
                continue
            predicted_neighbor = neighbor.position + neighbor.velocity.scale(self.policy.prediction_seconds)
            delta = predicted_subject - predicted_neighbor
            distance = delta.length
            if distance >= self.policy.minimum_separation:
                continue
            direction = delta.scale(1.0 / distance) if distance else Vector3(1.0, 0.0, 0.0)
            correction = correction + direction.scale((self.policy.minimum_separation - distance) / self.policy.prediction_seconds)
        return (command + correction).limited(self.policy.maximum_speed)
