# Sky Recon

Sky Recon is a transport-neutral Python toolkit for coordinating teams of autonomous vehicles. It provides mission dispatch, predictive collision avoidance, grid-based route planning, live telemetry snapshots, emergency landing, deterministic simulation, and an auditable SQLite event journal.

<p align="center">
  <img src="docs/assets/swarm_formation_flight.jpeg" alt="Sky Recon vehicles maintaining a coordinated formation" width="720">
</p>

The codebase is designed around small adapters. A simulator, MAVLink connection, or another vehicle transport can implement the `VehicleAdapter` protocol without changing mission logic.

## Quick start

```bash
python -m pip install -e ".[test]"
pytest
```

```python
import asyncio

from skyrecon import EventJournal, Mission, MissionCoordinator, Vector3
from skyrecon.adapters import SimulatedVehicle


async def survey():
    control = MissionCoordinator(EventJournal("mission-events.db"))
    control.register(SimulatedVehicle("scout-1"))
    await control.connect()
    final = await control.fly(
        "scout-1",
        Mission("ridge-pass", Vector3(north=40, east=15, down=-12)),
    )
    print(final)


asyncio.run(survey())
```

## Architecture

- `models.py` defines immutable vectors, telemetry, modes, and missions.
- `coordinator.py` owns asynchronous vehicle registration and mission execution.
- `safety.py` predicts near-future separation and modifies unsafe velocity commands.
- `routing.py` provides obstacle-aware grid routing.
- `journal.py` records operational events in SQLite.
- `adapters/` contains transport implementations; the included simulator is deterministic.

## Operational views

These reference views illustrate the workflows Sky Recon is designed to support. Hardware-specific screens require an appropriate `VehicleAdapter`; the core package remains independent of any single ground-control station or flight controller.

### Ground-control mission overview

Monitor connected vehicles, active routes, and mission progress from a compatible ground-control interface.

![Sky Recon ground-control mission overview](docs/assets/mission_planner_gcs.jpg)

### Readiness and diagnostics

Review navigation quality, power state, communication health, and safety checks before dispatching a mission.

![Sky Recon readiness and diagnostics view](docs/assets/preflight_status_check.png)

### Coordinated formation

Assign independent destinations while the separation guard adjusts unsafe velocity commands across the team.

![Sky Recon coordinated formation](docs/assets/swarm_formation_flight.jpeg)

### Separation analysis

Use recorded telemetry to inspect inter-vehicle distance and validate configured safety margins.

![Sky Recon separation analysis](docs/assets/fleet_distance_metrics.jpg)

### Survey trajectory reconstruction

Mission journals and adapter telemetry can feed downstream mapping and three-dimensional trajectory analysis.

![Sky Recon survey trajectory reconstruction](docs/assets/drones-05-00033-g009-550.jpg)

## Safety boundary

Sky Recon is research software. Simulation success does not establish airworthiness. Hardware integrations must add authenticated command transport, flight-controller failsafes, regulatory geofencing, independent emergency controls, and scenario-specific validation before real-world use.

## License and provenance

Sky Recon is distributed under the MIT License. This implementation was independently structured for the Sky Recon project. The license file retains the notice from the earlier MIT-licensed project lineage as required.
