# Sky Recon

Sky Recon is a transport-neutral Python toolkit for coordinating teams of autonomous vehicles. It provides mission dispatch, predictive collision avoidance, grid-based route planning, live telemetry snapshots, emergency landing, deterministic simulation, and an auditable SQLite event journal.

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

## Safety boundary

Sky Recon is research software. Simulation success does not establish airworthiness. Hardware integrations must add authenticated command transport, flight-controller failsafes, regulatory geofencing, independent emergency controls, and scenario-specific validation before real-world use.

## License and provenance

Sky Recon is distributed under the MIT License. This implementation was independently structured for the Sky Recon project. The license file retains the notice from the earlier MIT-licensed project lineage as required.
