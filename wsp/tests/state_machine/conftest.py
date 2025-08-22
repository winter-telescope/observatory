# tests/conftest.py
import os
import time
import types
from pathlib import Path

import pytest

from wsp.control.camera_config import CameraInfo
from wsp.control.multi_camera_state_machine import (
    CameraState,
    MultiCameraStateMachine,
    ObservatoryState,
)
from wsp.control.sm_diagram import GraphRecorder


class _NoOpTimer:
    """Mimics a Qt single-shot timer interface used by the SM."""

    def __init__(self):
        self.started = False

    def start(self, *args, **kwargs):
        self.started = True


class FakeCamera:
    """Minimal camera stub with the state shape the SM expects."""

    def __init__(self, name):
        # the SM probes camera.state.get("state", {}).get("autoStartComplete")
        self.name = name
        self.state = {"state": {"autoStartComplete": False}}


class FakeDome:
    def __init__(self):
        self.Shutter_Status = "OPEN"


class FakeSchedule:
    def __init__(self):
        self.currentObs = None
        self.end_of_schedule = False
        self.log = []

    def log_observation(self):
        self.log.append(("log_observation", time.time()))


class FakeRobo:
    """Just enough surface area to run the state machine."""

    def __init__(self):
        self.running = True
        self.checktimer = _NoOpTimer()
        self.autostart_override = True  # let cameras instantly READY
        self.camdict = {}
        self.commands = []  # record doTry commands
        self.state = {"sun_alt": -12.0}
        self.config = {"max_sun_alt_for_observing": -8.0}
        self.dometest = True  # skip dome-opening logic
        self.dome = FakeDome()
        self.schedule = FakeSchedule()
        self.ephem = types.SimpleNamespace(state={"mjd": 60000.0})
        self.camname = None
        self.observations_done = []

    # --- logging/announcements ---
    def log(self, msg):  # keep quiet during tests; could print if debugging
        pass

    def announce(self, msg):
        pass

    # --- environment/conditions ---
    def get_camera_should_be_running_status(self):
        return True

    def get_dome_status(self):
        return True

    def get_sun_status(self):
        return True

    def get_observatory_ready_status(self):
        return True

    # --- actions ---
    def doTry(self, cmd: str):
        self.commands.append(cmd)

    def do_startup(self):
        self.commands.append("startup")

    def switchCamera(self, name: str):
        self.camname = name

    def rotator_stop_and_reset(self):
        self.commands.append("rotator_reset")

    def do_currentObs(self, currentObs):
        # pretend we took an exposure
        self.observations_done.append(currentObs)

    def safe_park(self):
        self.commands.append("safe_park")

    # --- scheduling ---
    def load_best_observing_target(self, obstime_mjd):
        # Provide a simple, always-valid target
        self.schedule.currentObs = {
            "targName": "TestTarget",
            "raDeg": 150.0,
            "decDeg": 2.0,
            "filter": "r",
            "visitExpTime": 10.0,
            "ditherNumber": 1,
            # no explicit 'camera' → SM chooses based on filters/port
        }


@pytest.fixture
def fake_robo():
    return FakeRobo()


@pytest.fixture
def camera_infos():
    # Two cameras, different ports, both have 'r' filter
    return [
        CameraInfo(
            name="CamA",
            port=1,
            filters=["g", "r"],
            cal_interval_hours=999,  # avoid cals during tests
        ),
        CameraInfo(
            name="CamB",
            port=2,
            filters=["r"],
            cal_interval_hours=999,
        ),
    ]


@pytest.fixture
def state_machine(fake_robo, camera_infos, request):
    # Attach fake cameras to the robo dict
    for ci in camera_infos:
        fake_robo.camdict[ci.name] = FakeCamera(ci.name)

    sm = MultiCameraStateMachine(fake_robo, camera_infos)

    # Make camera states OFF initially
    for name, st in sm.camera_status.items():
        st.state = CameraState.OFF

    # The SM defines CHECKING_FOCUS but you haven't implemented a handler.
    # For tests, route CHECKING_FOCUS → SELECTING_TARGET using the existing state.
    from wsp.control.multi_camera_state_machine import (
        ObservatoryState,
        SelectingTargetState,
    )

    sm.states[ObservatoryState.CHECKING_FOCUS] = SelectingTargetState()

    # Optionally record the state machine diagram
    rec = GraphRecorder(sm)
    sm.on_transition = rec.record  # attach hook
    request.config._sm_recorders.append(rec)
    return sm


def pytest_configure(config):
    config._sm_recorders = []


@pytest.fixture
def run_ticks():
    """Return a helper that advances the state machine n ticks."""

    def _run(sm, n=1):
        for _ in range(n):
            sm.execute()

    return _run


def pytest_sessionfinish(session, exitstatus):
    """On test session end, export diagrams (optional: only when env flag set)."""
    recs = getattr(session.config, "_sm_recorders", [])
    if not recs:
        return

    # Merge all edges into the first recorder (in case multiple SMs were built)
    primary = recs[0]
    for r in recs[1:]:
        primary.edges |= r.edges
        primary.seen_states |= r.seen_states

    # Only generate files when explicitly asked (so normal 'pytest' stays clean)
    gen = os.getenv("GENERATE_SM_DIAGRAMS", "0") == "1"
    if not gen:
        return

    diagrams_dir = Path("diagrams")
    diagrams_dir.mkdir(parents=True, exist_ok=True)
    docs_dir = Path("docs")
    docs_dir.mkdir(parents=True, exist_ok=True)

    dot_path = diagrams_dir / "multicamera_sm.dot"
    mmd_path = diagrams_dir / "multicamera_sm.mmd"
    md_path = docs_dir / "StateMachine.md"

    primary.export_dot(str(dot_path))
    primary.export_mermaid(str(mmd_path))
    primary.inject_mermaid_into_markdown(str(md_path))
