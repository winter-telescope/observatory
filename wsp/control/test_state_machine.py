"""
Test harness for the Multi-Camera State Machine

This allows testing the state machine logic without any hardware connections
or the full RoboOperator infrastructure.
"""

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

import yaml

# Import the state machine components
from camera_config import (
    CalibrationTask,
    CameraConfigManager,
    CameraInfo,
    CameraPort,
    CameraState,
    CameraStatus,
    ObservationRequest,
)
from multi_camera_state_machine import MultiCameraStateMachine, ObservatoryState

from wsp.utils.paths import CONFIG_PATH


class MockTimer:
    """Mock QTimer for testing"""

    def __init__(self):
        self.callback = None
        self.started = False

    def start(self):
        self.started = True
        print("  [Timer] Started check timer")

    def stop(self):
        self.started = False

    def timeout_connect(self, callback):
        self.callback = callback


class MockDome:
    """Mock dome for testing"""

    def __init__(self):
        self.Shutter_Status = "CLOSED"
        self.Control_Status = "REMOTE"
        self.Home_Status = "READY"

    def set_shutter(self, status):
        print(f"  [Dome] Setting shutter to {status}")
        self.Shutter_Status = status


class MockCamera:
    """Mock camera daemon"""

    def __init__(self, name):
        self.name = name
        self.state = {
            "autoStartRequested": False,
            "autoStartComplete": False,
            "autoShutdownRequested": False,
            "autoShutdownComplete": False,
            "exptime": 30.0,
        }

    def request_startup(self):
        print(f"  [Camera-{self.name}] Startup requested")
        self.state["autoStartRequested"] = True

    def complete_startup(self):
        print(f"  [Camera-{self.name}] Startup completed")
        self.state["autoStartComplete"] = True

    def request_shutdown(self):
        print(f"  [Camera-{self.name}] Shutdown requested")
        self.state["autoShutdownRequested"] = True
        self.state["autoStartRequested"] = False
        self.state["autoStartComplete"] = False


class MockSchedule:
    """Mock schedule for testing"""

    def __init__(self):
        self.currentObs = None
        self.end_of_schedule = False
        self.observations = []
        self.current_index = 0

    def add_observation(self, obs):
        self.observations.append(obs)

    def get_next_observation(self):
        if self.current_index < len(self.observations):
            self.currentObs = self.observations[self.current_index]
            self.current_index += 1
            return self.currentObs
        else:
            self.currentObs = None
            self.end_of_schedule = True
            return None

    def log_observation(self):
        if self.currentObs:
            print(
                f"  [Schedule] Logged observation: {self.currentObs.get('targName', 'Unknown')}"
            )


class MockEphem:
    """Mock ephemeris for testing"""

    def __init__(self):
        self.state = {"mjd": 60000.0}
        self.site = None  # Mock site location


class MockRoboOperator:
    """
    Mock RoboOperator that simulates all the hardware interfaces
    without actually connecting to anything.
    """

    def __init__(self, config):
        self.config = config
        self.running = True
        self.autostart_override = False
        self.dometest = False

        # Set up logging
        self.setup_logging()

        # Mock hardware components
        self.checktimer = MockTimer()
        self.dome = MockDome()
        self.camdict = {
            "winter": MockCamera("winter"),
            "summer": MockCamera("summer"),
            "winter-deep": MockCamera("winter-deep"),
        }
        self.schedule = MockSchedule()
        self.ephem = MockEphem()

        # State tracking
        self.state = {
            "sun_alt": -20.0,
            "sun_rising": False,
            "mount_is_connected": True,
            "mount_alt_is_enabled": True,
            "mount_az_is_enabled": True,
            "rotator_is_connected": True,
            "rotator_is_enabled": True,
            "rotator_wrap_check_enabled": True,
            "focuser_is_connected": True,
            "focuser_is_enabled": True,
            "Mirror_Cover_State": 0,
            "dome_tracking_status": False,
            "dome_az_deg": 40.0,
            "mount_az_deg": 220.0,
            "mount_alt_deg": 45.0,
            "rotator_mech_position": 65.5,
            "mount_is_tracking": False,
            "winter_fw_is_homed": 1,
            "summer_fw_is_homed": 1,
            "pdu1_1": 0,  # Cal lamp
        }

        # Simulation control flags
        self.simulate_camera_startup_delay = True
        self.simulate_dome_open_delay = True
        self.simulate_weather_ok = True
        self.simulate_sun_ok = True

        # Action log
        self.action_log = []

    def setup_logging(self):
        """Set up logging for the test"""
        logging.basicConfig(
            level=logging.INFO, format="%(asctime)s - %(message)s", datefmt="%H:%M:%S"
        )
        self.logger = logging.getLogger(__name__)

    def log(self, message):
        """Log a message"""
        self.logger.info(f"[ROBO] {message}")
        self.action_log.append(
            {"time": datetime.now(), "type": "log", "message": message}
        )

    def announce(self, message):
        """Simulate announcement"""
        print(f"\n*** ANNOUNCE: {message} ***\n")
        self.action_log.append(
            {"time": datetime.now(), "type": "announce", "message": message}
        )

    def doTry(self, command):
        """Simulate command execution"""
        print(f"  [CMD] {command}")
        self.action_log.append(
            {"time": datetime.now(), "type": "command", "command": command}
        )

        # Simulate effects of various commands
        if command.startswith("dome_open"):
            if self.simulate_dome_open_delay:
                print("  [Dome] Opening... (simulated delay)")
            self.dome.Shutter_Status = "OPEN"

        elif command.startswith("telescope_select_port"):
            port = int(command.split()[-1])
            print(f"  [Telescope] Switched to port {port}")

        elif command.startswith("cal_sequence"):
            print(f"  [Calibration] Executing: {command}")
            time.sleep(0.1)  # Simulate cal execution

    def get_camera_should_be_running_status(self) -> bool:
        """Decide if cameras should be on based on sun altitude"""
        sun_alt = self.state["sun_alt"]
        sun_rising = self.state["sun_rising"]

        # Turn on when sun is setting and below +10 deg
        if not sun_rising and sun_alt <= 10:
            return True

        # Turn off when sun is rising and above -5 deg
        if sun_rising and sun_alt >= -5:
            return False

        # Otherwise keep cameras on if sun is below -5
        return sun_alt < -5

    def get_dome_status(self):
        """Check if dome/weather is ok"""
        return self.simulate_weather_ok

    def get_sun_status(self):
        """Check if sun is low enough"""
        return self.simulate_sun_ok and self.state["sun_alt"] < -7

    def get_observatory_ready_status(self):
        """Check if observatory is ready"""
        return (
            self.state["mount_is_connected"]
            and self.state["mount_alt_is_enabled"]
            and self.state["mount_az_is_enabled"]
        )

    def do_camera_startup(self, camera_name):
        """Simulate camera startup"""
        self.log(f"Starting camera {camera_name}")
        if camera_name in self.camdict:
            self.camdict[camera_name].request_startup()

    def do_camera_shutdown(self, camera_name):
        """Simulate camera shutdown"""
        self.log(f"Shutting down camera {camera_name}")
        if camera_name in self.camdict:
            self.camdict[camera_name].request_shutdown()

    def do_startup(self):
        """Simulate observatory startup"""
        self.announce("Running observatory startup sequence")
        self.state["mount_is_connected"] = True
        self.state["mount_alt_is_enabled"] = True
        self.state["mount_az_is_enabled"] = True

    def switchCamera(self, camera_name):
        """Simulate camera switching"""
        self.log(f"Switched to camera: {camera_name}")

    def switch_telescope_port(self, port):
        """Simulate port switching"""
        self.doTry(f"telescope_select_port {port}")

    def load_best_observing_target(self, obstime_mjd):
        """Simulate loading next target"""
        self.log("Loading next observation target")
        self.schedule.get_next_observation()

    def rotator_stop_and_reset(self):
        """Simulate rotator reset"""
        self.log("Stopping and resetting rotator")

    def do_currentObs(self, obs):
        """Simulate observation execution"""
        self.announce(f"Executing observation: {obs.get('targName', 'Unknown')}")
        time.sleep(0.5)  # Simulate observation


class StateMachineTestHarness:
    """
    Test harness for running state machine scenarios
    """

    def __init__(self, config_file=CONFIG_PATH):
        """Initialize the test harness"""
        # Load config
        with open(config_file, "r") as f:
            self.config = yaml.safe_load(f)

        # Create mock robo operator
        self.robo = MockRoboOperator(self.config)

        # Create camera config manager
        self.camera_config_manager = CameraConfigManager(self.config)
        camera_infos = self.camera_config_manager.get_all_camera_info()

        # Create state machine
        self.state_machine = MultiCameraStateMachine(self.robo, camera_infos)

        print(
            f"Test harness initialized with cameras: {[c.name for c in camera_infos]}"
        )

    def run_cycles(self, num_cycles=10):
        """Run the state machine for a number of cycles"""
        print(f"\n{'='*60}")
        print(f"Running {num_cycles} state machine cycles")
        print(f"{'='*60}\n")

        for i in range(num_cycles):
            print(f"\n--- Cycle {i+1} ---")
            print(f"Current state: {self.state_machine.context.current_state.name}")

            # Execute one cycle
            self.state_machine.checkWhatToDo()

            # Simulate timer callback if timer was started
            if self.robo.checktimer.started:
                print("  [Timer] Timer would fire, continuing...")
                self.robo.checktimer.started = False

            time.sleep(0.1)  # Small delay for readability

    def simulate_camera_ready(self, camera_name):
        """Simulate a camera becoming ready"""
        print(f"\n[SIMULATION] Making {camera_name} ready")
        if camera_name in self.robo.camdict:
            self.robo.camdict[camera_name].complete_startup()

    def simulate_schedule_with_observations(self):
        """Add some test observations to the schedule"""
        print("\n[SIMULATION] Adding test observations to schedule")

        test_obs = [
            {
                "obsHistID": 1,
                "targName": "Test Star 1",
                "raDeg": 150.0,
                "decDeg": 30.0,
                "filter": "r",
                "visitExpTime": 300.0,
                "priority": 1,
                "camera": "winter",  # Explicit camera selection
            },
            {
                "obsHistID": 2,
                "targName": "Test Galaxy",
                "raDeg": 200.0,
                "decDeg": -20.0,
                "filter": "g",
                "visitExpTime": 600.0,
                "priority": 2,
                # No camera specified - should auto-select
            },
            {
                "obsHistID": 3,
                "targName": "Test Nebula",
                "raDeg": 180.0,
                "decDeg": 0.0,
                "filter": "u",  # Only available on summer
                "visitExpTime": 900.0,
                "priority": 3,
            },
        ]

        for obs in test_obs:
            self.robo.schedule.add_observation(obs)

    def simulate_dome_open(self):
        """Simulate dome opening"""
        print("\n[SIMULATION] Dome is now open")
        self.robo.dome.Shutter_Status = "OPEN"

    def simulate_weather_change(self, ok=True):
        """Simulate weather change"""
        self.robo.simulate_weather_ok = ok
        status = "GOOD" if ok else "BAD"
        print(f"\n[SIMULATION] Weather is now {status}")

    def simulate_sun_position(self, altitude, rising=False):
        """Simulate sun position change"""
        self.robo.state["sun_alt"] = altitude
        self.robo.state["sun_rising"] = rising
        direction = "RISING" if rising else "SETTING"
        print(f"\n[SIMULATION] Sun at {altitude}° and {direction}")

    def print_summary(self):
        """Print summary of actions taken"""
        print(f"\n{'='*60}")
        print("ACTION SUMMARY")
        print(f"{'='*60}")

        command_counts = {}
        for action in self.robo.action_log:
            if action["type"] == "command":
                cmd = action["command"].split()[0]
                command_counts[cmd] = command_counts.get(cmd, 0) + 1

        print("\nCommands executed:")
        for cmd, count in sorted(command_counts.items()):
            print(f"  {cmd}: {count}")

        print(f"\nTotal actions: {len(self.robo.action_log)}")
        print(f"Final state: {self.state_machine.context.current_state.name}")


def run_basic_test():
    """Run a basic test scenario"""
    print("\n" + "=" * 80)
    print("BASIC STATE MACHINE TEST")
    print("=" * 80)

    # Create test harness
    harness = StateMachineTestHarness()

    # Scenario 1: Sun is high, cameras should be off
    print("\n\nSCENARIO 1: Daytime - Cameras Off")
    print("-" * 40)
    harness.simulate_sun_position(20, rising=False)
    harness.run_cycles(5)

    # Scenario 2: Sun setting, cameras should start
    print("\n\nSCENARIO 2: Evening - Starting Cameras")
    print("-" * 40)
    harness.simulate_sun_position(5, rising=False)
    harness.run_cycles(5)

    # Make cameras ready
    harness.simulate_camera_ready("winter")
    harness.simulate_camera_ready("summer")
    harness.run_cycles(5)

    # Scenario 3: Sun low, dome closed - should open
    print("\n\nSCENARIO 3: Ready to Observe - Opening Dome")
    print("-" * 40)
    harness.simulate_sun_position(-10, rising=False)
    harness.run_cycles(5)

    # Open dome
    harness.simulate_dome_open()
    harness.run_cycles(3)

    # Scenario 4: Add observations and observe
    print("\n\nSCENARIO 4: Observing")
    print("-" * 40)
    harness.simulate_schedule_with_observations()
    harness.run_cycles(10)

    # Print summary
    harness.print_summary()


def run_weather_interruption_test():
    """Test weather interruption scenario"""
    print("\n" + "=" * 80)
    print("WEATHER INTERRUPTION TEST")
    print("=" * 80)

    harness = StateMachineTestHarness()

    # Set up for observing
    harness.simulate_sun_position(-15, rising=False)
    harness.simulate_camera_ready("winter")
    harness.simulate_dome_open()
    harness.simulate_schedule_with_observations()

    # Start observing
    harness.run_cycles(5)

    # Weather goes bad
    harness.simulate_weather_change(ok=False)
    harness.run_cycles(5)

    # Weather improves
    harness.simulate_weather_change(ok=True)
    harness.run_cycles(5)

    harness.print_summary()


if __name__ == "__main__":
    # Run tests
    run_basic_test()
    # run_weather_interruption_test()

    # Interactive mode
    print("\n\nEntering interactive mode. Commands:")
    print("  cycles N     - Run N cycles")
    print("  ready CAM    - Make camera CAM ready")
    print("  sun ALT      - Set sun altitude")
    print("  weather OK   - Set weather (OK = good/bad)")
    print("  dome open    - Open dome")
    print("  add obs      - Add test observations")
    print("  summary      - Print summary")
    print("  quit         - Exit")

    harness = StateMachineTestHarness()

    while True:
        try:
            cmd = input("\n> ").strip().split()
            if not cmd:
                continue

            if cmd[0] == "quit":
                break
            elif cmd[0] == "cycles":
                harness.run_cycles(int(cmd[1]))
            elif cmd[0] == "ready":
                harness.simulate_camera_ready(cmd[1])
            elif cmd[0] == "sun":
                harness.simulate_sun_position(float(cmd[1]))
            elif cmd[0] == "weather":
                harness.simulate_weather_change(cmd[1].lower() == "good")
            elif cmd[0] == "dome" and cmd[1] == "open":
                harness.simulate_dome_open()
            elif cmd[0] == "add" and cmd[1] == "obs":
                harness.simulate_schedule_with_observations()
            elif cmd[0] == "summary":
                harness.print_summary()
            else:
                print("Unknown command")

        except Exception as e:
            print(f"Error: {e}")
