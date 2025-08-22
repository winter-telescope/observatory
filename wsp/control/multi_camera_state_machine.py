# multicamera_state_machine_revised.py
"""
Revised Multi-Camera State Machine for Observatory Control

This module implements a hierarchical state machine for controlling
multiple cameras in an observatory, handling startup/shutdown sequences,
calibrations, and observations.
"""

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional

# Import camera configuration classes
from wsp.control.camera_config import (
    CalibrationTask,
    CameraInfo,
    CameraPort,
    CameraState,
    CameraStatus,
    ObservationRequest,
)


def _label(context, text: str) -> None:
    """Store transition label for diagram generation"""
    context.state_data["_transition_label"] = text


class ObservatoryState(Enum):
    """All possible states for the observatory"""

    # Top-level states
    OFF = auto()  # Robot not running
    IDLE = auto()  # Robot running, waiting for timer

    # Camera management states
    CHECKING_CAMERAS = auto()
    STARTING_CAMERAS = auto()
    WAITING_CAMERAS_READY = auto()
    SHUTTING_DOWN_CAMERAS = auto()

    # Observation preparation states
    CHECKING_CALS = auto()
    EXECUTING_CAL = auto()
    CHECKING_CONDITIONS = auto()
    OPENING_DOME = auto()
    CHECKING_FOCUS = auto()
    EXECUTING_FOCUS = auto()

    # Observing states
    SELECTING_TARGET = auto()
    SWITCHING_PORT = auto()
    PREPARING_OBSERVATION = auto()
    OBSERVING = auto()
    STOWING = auto()

    # End states
    END_OF_SCHEDULE = auto()
    ERROR = auto()


@dataclass
class StateContext:
    """Context object that holds all the data needed by states"""

    robo: Any  # Reference to main robo operator object
    current_state: ObservatoryState = ObservatoryState.OFF
    previous_state: Optional[ObservatoryState] = None
    state_data: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3

    def log(self, message: str):
        """Wrapper for logging"""
        self.robo.log(f"[{self.current_state.name}] {message}")

    def announce(self, message: str):
        """Wrapper for announcements"""
        self.robo.announce(message)


class State(ABC):
    """Abstract base class for all states"""

    @abstractmethod
    def enter(self, context: StateContext) -> None:
        """Called when entering this state"""
        pass

    @abstractmethod
    def execute(self, context: StateContext) -> Optional[ObservatoryState]:
        """
        Execute state logic and return next state.
        Return None to stay in current state.
        """
        pass

    def exit(self, context: StateContext) -> None:
        """Called when exiting this state"""
        pass


class OffState(State):
    """Robot not running - dormant state"""

    def enter(self, context: StateContext):
        context.log("State machine OFF - robot not running")

    def execute(self, context: StateContext) -> Optional[ObservatoryState]:
        # Check if robot has started running
        if context.robo.running:
            context.log("Robot started - transitioning to IDLE")
            _label(context, "robot started")
            return ObservatoryState.IDLE
        # Stay in OFF state
        return None


class IdleState(State):
    """Robot running but waiting between checks"""

    def enter(self, context: StateContext):
        context.log("Entering IDLE state - waiting for next check")

    def execute(self, context: StateContext) -> Optional[ObservatoryState]:
        # This state is called by timer ticks when robot is running
        if not context.robo.running:
            context.log("Robot stopped - going to OFF")
            _label(context, "robot stopped")
            return ObservatoryState.OFF

        # Check what needs to be done
        context.log("Timer triggered - checking what to do")
        _label(context, "check triggered")
        return ObservatoryState.CHECKING_CAMERAS


class CheckingCamerasState(State):
    """Check camera states and decide next action"""

    def enter(self, context: StateContext):
        context.log("Checking camera states")

    def execute(self, context: StateContext) -> Optional[ObservatoryState]:
        state_machine = context.state_data.get("state_machine")

        # Determine if cameras should be running based on conditions
        cameras_should_run = self._should_cameras_be_running(context)

        if cameras_should_run:
            # Cameras should be on - check their states
            cameras_needing_startup = []
            cameras_ready = []

            for cam_name, status in state_machine.camera_status.items():
                if status.state == CameraState.READY:
                    cameras_ready.append(cam_name)
                elif status.state == CameraState.OFF:
                    cameras_needing_startup.append(cam_name)

            if cameras_needing_startup:
                context.log(f"Cameras needing startup: {cameras_needing_startup}")
                _label(context, "need startup")
                return ObservatoryState.STARTING_CAMERAS
            elif cameras_ready:
                context.log(f"Cameras ready: {cameras_ready}")
                _label(context, "cameras ready")
                return ObservatoryState.CHECKING_CALS
            else:
                # Cameras in intermediate states, wait
                _label(context, "cameras starting")
                return ObservatoryState.WAITING_CAMERAS_READY
        else:
            # Cameras should be off
            cameras_needing_shutdown = []

            for cam_name, status in state_machine.camera_status.items():
                if status.state not in [CameraState.OFF, CameraState.SHUTDOWN_COMPLETE]:
                    cameras_needing_shutdown.append(cam_name)

            if cameras_needing_shutdown:
                context.log(f"Cameras needing shutdown: {cameras_needing_shutdown}")
                _label(context, "need shutdown")
                return ObservatoryState.SHUTTING_DOWN_CAMERAS
            else:
                # All cameras off, go back to idle
                _label(context, "all off")
                context.robo.checktimer.start()
                return ObservatoryState.IDLE

    def _should_cameras_be_running(self, context: StateContext) -> bool:
        """Determine if cameras should be running based on conditions"""
        # Check various conditions - customize based on your needs

        # Basic time-based check
        sun_alt = context.robo.state.get("sun_alt", 90)
        max_sun_alt = context.robo.config.get("max_sun_alt_for_cameras", -10)

        # Cameras should run if:
        # 1. Sun is low enough
        # 2. No weather/safety issues
        # 3. Schedule has targets

        if sun_alt > max_sun_alt:
            context.log(f"Sun too high ({sun_alt:.1f}°) for cameras")
            return False

        # Add other checks as needed
        return True


class StartingCamerasState(State):
    """Start cameras sequentially"""

    def enter(self, context: StateContext):
        context.log("Starting camera startup sequence")

    def execute(self, context: StateContext) -> Optional[ObservatoryState]:
        state_machine = context.state_data.get("state_machine")

        for cam_name, status in state_machine.camera_status.items():
            if status.state == CameraState.OFF:
                # Start this camera
                context.log(f"Starting camera {cam_name}")
                _label(context, f"starting {cam_name}")

                # Call the actual startup method
                self._start_camera(context, cam_name)

                # Update status
                status.state = CameraState.STARTUP_REQUESTED
                status.startup_requested_time = time.time()

                # Start check timer and move to waiting
                context.robo.checktimer.start()
                return ObservatoryState.WAITING_CAMERAS_READY

        # All cameras already started
        context.robo.checktimer.start()
        return ObservatoryState.WAITING_CAMERAS_READY

    def _start_camera(self, context: StateContext, camera_name: str):
        """Execute camera startup sequence"""
        # This is where you'd integrate with actual camera startup
        context.log(f"Executing startup for {camera_name}")

        # Example: Call a command or method
        # context.robo.doTry(f"camera_startup {camera_name}")

        # Or set a flag that the camera thread will see
        cam = context.robo.camdict.get(camera_name)
        if cam and hasattr(cam, "startup"):
            cam.startup()


class WaitingCamerasReadyState(State):
    """Wait for cameras to complete startup"""

    def enter(self, context: StateContext):
        context.log("Waiting for cameras to be ready")

    def execute(self, context: StateContext) -> Optional[ObservatoryState]:
        state_machine = context.state_data.get("state_machine")
        all_ready = True
        any_ready = False
        any_error = False

        for cam_name, status in state_machine.camera_status.items():
            if status.state == CameraState.STARTUP_REQUESTED:
                # Check if camera is ready
                if self._is_camera_ready(context, cam_name):
                    context.log(f"Camera {cam_name} is ready")
                    status.state = CameraState.READY
                    status.ready = True
                    status.startup_requested_time = None
                    any_ready = True
                else:
                    all_ready = False

                    # Check for timeout
                    if status.startup_requested_time:
                        elapsed = time.time() - status.startup_requested_time
                        timeout = state_machine.cameras[cam_name].startup_timeout

                        if elapsed > timeout:
                            context.announce(f"Camera {cam_name} startup timeout!")
                            status.state = CameraState.ERROR
                            status.error = "Startup timeout"
                            any_error = True

            elif status.state == CameraState.READY:
                any_ready = True
            elif status.state == CameraState.ERROR:
                any_error = True
                all_ready = False
            else:
                all_ready = False

        if any_ready and not any_error:
            # At least one camera ready, can proceed
            context.log("Some cameras ready, proceeding")
            _label(context, "cameras ready")
            return ObservatoryState.CHECKING_CALS
        elif all_ready:
            # All cameras ready
            _label(context, "all ready")
            return ObservatoryState.CHECKING_CALS
        else:
            # Keep waiting
            context.robo.checktimer.start()
            return None

    def _is_camera_ready(self, context: StateContext, camera_name: str) -> bool:
        """Check if a camera has completed startup"""
        # This is where you check actual camera status

        # Example: Check camera object state
        cam = context.robo.camdict.get(camera_name)
        if not cam:
            return False

        # Check various ways camera might indicate ready
        if hasattr(cam, "is_ready"):
            return cam.is_ready()

        if hasattr(cam, "state"):
            state = cam.state
            if isinstance(state, dict):
                # Check for various ready indicators
                if state.get("ready", False):
                    return True
                if state.get("autoStartComplete", False):
                    return True
                if state.get("status") == "READY":
                    return True

        # For testing/override
        if getattr(context.robo, "camera_ready_override", False):
            return True

        return False


class CheckingConditionsState(State):
    """Check if conditions are suitable for observing"""

    def enter(self, context: StateContext):
        context.log("Checking observing conditions")

    def execute(self, context: StateContext) -> Optional[ObservatoryState]:
        # Check sun altitude
        sun_alt = context.robo.state.get("sun_alt", 90)
        max_sun_alt = context.robo.config.get("max_sun_alt_for_observing", -10)

        if sun_alt > max_sun_alt:
            context.log(f"Sun too high for observing ({sun_alt:.1f}°)")
            _label(context, "sun too high")
            context.robo.checktimer.start()
            return ObservatoryState.IDLE

        # Check weather/dome conditions
        if not self._check_dome_conditions(context):
            context.log("Dome conditions not suitable")
            _label(context, "bad conditions")
            context.robo.checktimer.start()
            return ObservatoryState.STOWING

        # Check if dome is open
        if not self._is_dome_open(context):
            context.log("Dome needs to be opened")
            _label(context, "dome closed")
            return ObservatoryState.OPENING_DOME

        # All good, proceed to observing
        _label(context, "conditions OK")
        return ObservatoryState.SELECTING_TARGET

    def _check_dome_conditions(self, context: StateContext) -> bool:
        """Check if dome/weather conditions are acceptable"""
        # Implement your dome/weather checks here

        # Example checks:
        # - Wind speed
        # - Humidity
        # - Rain sensor
        # - etc.

        # For now, return True unless explicitly set otherwise
        return context.robo.state.get("dome_conditions_ok", True)

    def _is_dome_open(self, context: StateContext) -> bool:
        """Check if dome is open"""
        if hasattr(context.robo, "dome"):
            return context.robo.dome.Shutter_Status == "OPEN"
        return context.robo.state.get("dome_open", False)


class SelectingTargetState(State):
    """Select next observation target"""

    def enter(self, context: StateContext):
        context.log("Selecting next target")

    def execute(self, context: StateContext) -> Optional[ObservatoryState]:
        state_machine = context.state_data.get("state_machine")

        # Get current time for scheduling
        obstime_mjd = context.robo.ephem.state.get(
            "mjd", time.time() / 86400.0 + 40587.0
        )

        # Load next target from schedule
        self._load_next_target(context, obstime_mjd)

        # Check if we have a valid observation
        if (
            not hasattr(context.robo.schedule, "currentObs")
            or context.robo.schedule.currentObs is None
        ):
            context.log("No valid observations available")

            # Check if schedule is complete
            if getattr(context.robo.schedule, "end_of_schedule", False):
                context.announce("End of schedule reached")
                _label(context, "schedule complete")
                return ObservatoryState.END_OF_SCHEDULE
            else:
                # Wait and try again
                _label(context, "no targets")
                context.robo.checktimer.start()
                return ObservatoryState.IDLE

        # Convert to our observation format
        obs = context.robo.schedule.currentObs
        camera_name = state_machine._select_camera_for_observation(obs)

        if not camera_name:
            context.log("No suitable camera for observation")
            context.robo.checktimer.start()
            return ObservatoryState.IDLE

        # Create observation request
        state_machine.current_observation = ObservationRequest(
            target_name=obs.get("targName", "Unknown"),
            ra=obs.get("raDeg", 0) / 15.0,  # Convert to hours
            dec=obs.get("decDeg", 0),
            camera_name=camera_name,
            filter_name=obs.get("filter", "r"),
            exposure_time=obs.get("visitExpTime", 30),
            num_exposures=obs.get("ditherNumber", 1),
        )

        context.log(f"Selected target: {state_machine.current_observation.target_name}")
        _label(context, "target selected")

        return ObservatoryState.SWITCHING_PORT

    def _load_next_target(self, context: StateContext, obstime_mjd: float):
        """Load next target from schedule"""
        # This integrates with your existing scheduling system

        if hasattr(context.robo, "scheduler"):
            # Use the actual scheduler
            context.robo.scheduler.loadNextObs(obstime_mjd)
        else:
            # Simplified version
            context.log("Loading next observation from schedule")
            # Set context.robo.schedule.currentObs


class ObservingState(State):
    """Execute the observation"""

    def enter(self, context: StateContext):
        context.log("Starting observation")

    def execute(self, context: StateContext) -> Optional[ObservatoryState]:
        state_machine = context.state_data.get("state_machine")
        obs = state_machine.current_observation

        if not obs:
            context.log("No observation to execute")
            return ObservatoryState.SELECTING_TARGET

        # Execute the observation
        context.announce(f"Observing {obs.target_name} with {obs.camera_name}")

        # This is where you integrate with actual observation execution
        self._execute_observation(context, obs)

        # Clear current observation
        state_machine.current_observation = None

        # Go back to check for next target
        _label(context, "observation complete")
        return ObservatoryState.CHECKING_CONDITIONS

    def _execute_observation(self, context: StateContext, obs: ObservationRequest):
        """Execute the actual observation"""
        # Integration point with your observation system

        # Example:
        cmd = f"observe --camera {obs.camera_name} --filter {obs.filter_name} "
        cmd += f"--exptime {obs.exposure_time} --count {obs.num_exposures}"

        context.log(f"Executing: {cmd}")
        # context.robo.doTry(cmd)


# Additional states would be implemented similarly...


class MultiCameraStateMachine:
    """
    Single-threaded state machine for multi-camera observatory control.
    """

    def __init__(self, robo_operator, camera_configs: List[CameraInfo]):
        self.robo = robo_operator
        self.cameras = {cam.name: cam for cam in camera_configs}

        # Initialize camera status tracking
        self.camera_status = {cam_name: CameraStatus() for cam_name in self.cameras}

        # Current operations
        self.current_camera: Optional[str] = None
        self.current_port: Optional[int] = None
        self.pending_cal_tasks: List[CalibrationTask] = []
        self.current_cal_task: Optional[CalibrationTask] = None
        self.current_observation: Optional[ObservationRequest] = None

        # State context - start in OFF state
        self.context = StateContext(
            robo=robo_operator, current_state=ObservatoryState.OFF
        )
        self.context.state_data["state_machine"] = self

        # Initialize all states
        self.states = {
            ObservatoryState.OFF: OffState(),
            ObservatoryState.IDLE: IdleState(),
            ObservatoryState.CHECKING_CAMERAS: CheckingCamerasState(),
            ObservatoryState.STARTING_CAMERAS: StartingCamerasState(),
            ObservatoryState.WAITING_CAMERAS_READY: WaitingCamerasReadyState(),
            ObservatoryState.CHECKING_CONDITIONS: CheckingConditionsState(),
            ObservatoryState.SELECTING_TARGET: SelectingTargetState(),
            ObservatoryState.OBSERVING: ObservingState(),
            # Add other states as implemented...
        }

        self.current_state_obj = self.states[ObservatoryState.OFF]
        self.current_state_obj.enter(self.context)

        # Timing
        self.state_start_time = time.time()
        self._in_tick = False

        # For state diagram generation
        self.on_transition = None

    def checkWhatToDo(self):
        """Main entry point called by timer"""
        # Only execute if not already in a tick
        if self._in_tick:
            return

        self._in_tick = True
        try:
            self.execute()
        finally:
            self._in_tick = False

    def execute(self):
        """Execute one step of the state machine"""
        try:
            # Execute current state
            if self.current_state_obj:
                next_state = self.current_state_obj.execute(self.context)

                # Transition if needed
                if next_state is not None:
                    self.transition_to(next_state)
        except Exception as e:
            # Handle errors
            self.context.error_message = str(e)
            self.robo.log(f"State machine error: {e}")
            import traceback

            self.robo.log(traceback.format_exc())
            self.transition_to(ObservatoryState.ERROR)

    def transition_to(self, new_state: ObservatoryState):
        """Transition to a new state"""
        if new_state != self.context.current_state:
            # Record transition for diagramming
            if self.on_transition:
                label = self.context.state_data.pop("_transition_label", None)
                self.on_transition(self.context.current_state, new_state, label)

            # Exit current state
            self.current_state_obj.exit(self.context)

            # Update context
            self.context.previous_state = self.context.current_state
            self.context.current_state = new_state

            # Enter new state
            self.current_state_obj = self.states.get(new_state)
            if self.current_state_obj:
                self.current_state_obj.enter(self.context)
            else:
                self.robo.log(f"Warning: No handler for state {new_state}")

    def _select_camera_for_observation(self, obs: dict) -> Optional[str]:
        """Select best camera for observation"""
        required_filter = obs.get("filter")

        # Get ready cameras
        ready_cameras = [
            cam_name
            for cam_name, status in self.camera_status.items()
            if status.state == CameraState.READY
        ]

        if not ready_cameras:
            return None

        # Find cameras with required filter
        suitable_cameras = []
        for cam_name in ready_cameras:
            cam_info = self.cameras[cam_name]
            if required_filter in cam_info.filters:
                suitable_cameras.append(cam_name)

        if not suitable_cameras:
            return None

        # Return first suitable camera (could be smarter)
        return suitable_cameras[0]
