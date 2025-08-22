# tools/sm_gen.py
import sys
import time
from pathlib import Path

# Adjust imports if your src lives elsewhere
from wsp.control.camera_config import CameraInfo, CameraState
from wsp.control.multi_camera_state_machine import (
    MultiCameraStateMachine,
    ObservatoryState,
)
from wsp.control.sm_diagram import GraphRecorder


# --- Minimal fakes (kept local to avoid pytest dependency) ---
class _NoOpTimer:
    def start(self, *a, **k):
        pass


class FakeDome:
    def __init__(self):
        self.Shutter_Status = "OPEN"


class FakeSchedule:
    def __init__(self):
        self.currentObs = None
        self.end_of_schedule = False

    def log_observation(self):
        pass


class FakeRobo:
    def __init__(self):
        self.running = True
        self.checktimer = _NoOpTimer()
        self.autostart_override = True
        self.camdict = {}
        self.state = {"sun_alt": -12.0}
        self.config = {"max_sun_alt_for_observing": -8.0}
        self.dometest = True
        self.dome = FakeDome()
        self.schedule = FakeSchedule()
        self.ephem = type("E", (), {"state": {"mjd": 60000.0}})()
        self.camname = None

    # plumbing
    def log(self, msg):
        pass

    def announce(self, msg):
        pass

    def get_camera_should_be_running_status(self):
        return True

    def get_dome_status(self):
        return True

    def get_sun_status(self):
        return True

    def get_observatory_ready_status(self):
        return True

    def doTry(self, cmd):
        pass

    def do_startup(self):
        pass

    def switchCamera(self, name):
        self.camname = name

    def rotator_stop_and_reset(self):
        pass

    def do_currentObs(self, currentObs):
        pass

    def load_best_observing_target(self, obstime_mjd):
        self.schedule.currentObs = {
            "targName": "DocDemo",
            "raDeg": 150.0,
            "decDeg": 2.0,
            "filter": "r",
            "visitExpTime": 1.0,
            "ditherNumber": 1,
        }


def drive_machine(sm: MultiCameraStateMachine, ticks=40):
    for _ in range(ticks):
        sm.execute()


def main():
    repo = Path(__file__).resolve().parents[1]
    diagrams_dir = repo / "diagrams"
    docs_dir = repo / "docs"
    diagrams_dir.mkdir(parents=True, exist_ok=True)
    docs_dir.mkdir(parents=True, exist_ok=True)

    robo = FakeRobo()
    # two cameras on different ports, both have r filter
    cams = [
        CameraInfo(name="CamA", port=1, filters=["g", "r"], cal_interval_hours=999),
        CameraInfo(name="CamB", port=2, filters=["r"], cal_interval_hours=999),
    ]

    sm = MultiCameraStateMachine(robo, cams)
    # mark cameras OFF initially
    for name, st in sm.camera_status.items():
        st.state = CameraState.OFF

    # attach recorder
    rec = GraphRecorder(sm)
    sm.on_transition = rec.record

    # exercise typical path to hit most transitions
    drive_machine(sm, ticks=50)

    # export artifacts
    dot_path = diagrams_dir / "multicamera_sm.dot"
    mmd_path = diagrams_dir / "multicamera_sm.mmd"
    rec.export_dot(str(dot_path))
    rec.export_mermaid(str(mmd_path))

    # inject Mermaid into docs/StateMachine.md
    md_path = docs_dir / "StateMachine.md"
    rec.inject_mermaid_into_markdown(str(md_path))

    # Optionally render PNG from DOT if graphviz 'dot' is available
    from shutil import which

    dot = which("dot")
    if dot:
        png_path = diagrams_dir / "multicamera_sm.png"
        try:
            import subprocess

            subprocess.run(
                [dot, "-Tpng", str(dot_path), "-o", str(png_path)], check=True
            )
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(main())
