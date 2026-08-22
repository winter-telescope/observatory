# summer_camera_daemon.py
"""
Interface daemon for the SUMMER camera (QHY42PRO behind the CMOS Control GUI).

Near-copy of spring_camera_daemon.py per docs/SummerCameraGuiHandoff.md and
the GUI-side handoff (WspSummerDaemonHandoff.md, GUI repo zwo-camera-control,
branch qhy42). The GUI server must be running first, e.g.:

    python -m cmos_camera_gui --headless --ws-port 5566 \
           --auto-connect qhy --instrument summer

SummerClient comes from the GUI package: `pip install -e` the GUI repo into
this environment, or vendor cmos_camera_gui/summer_client.py (it depends only
on `websockets`).

Deltas from spring (WspSummerDaemonHandoff §6): client import + config-driven
host/port, no init-time corrections, no TEC voltage telemetry (PWM percent
instead), no warm-up wait on shutdown, TEC setpoint clamped to -45..+20 C,
SUMMER status extras, summer image directory.
"""

import logging
import os
from datetime import datetime
from pathlib import Path

from cmos_camera_gui.summer_client import SummerClient

from wsp.camera.camera_command_decorators import async_camera_command
from wsp.camera.daemon_framework import BaseCameraInterface, create_camera_daemon
from wsp.camera.state import CameraState
from wsp.utils.utils import tonight_local

DEFAULT_STATUS_VALUE = -888

# QHY42PRO TEC setpoint clamp range (the GUI clamps silently; we clamp loudly)
TEC_SETPOINT_MIN = -45.0
TEC_SETPOINT_MAX = 20.0


class SummerCameraInterface(BaseCameraInterface):
    """
    Interface for the SUMMER camera using the async decorator pattern.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Additional initialization if needed

    def setup_connection(self):
        """Set up connections specific to the SUMMER camera GUI server."""
        self.log("Setting up connection to SUMMER camera...")

        self.camera_status = {}

        gui_conf = self.config.get("summer_camera", {})
        host = gui_conf.get("gui_host", "localhost")
        port = gui_conf.get("gui_port", 5566)

        # drop any stale connection before making a new one
        if hasattr(self, "cam") and self.cam is not None:
            try:
                self.cam.close()
            except Exception:
                pass

        try:
            self.cam = SummerClient(host=host, port=port)
            self.cam.connect()

            self.initialize_camera()
            self.connected = True
            self.log(f"Connected to SUMMER camera GUI at {host}:{port}.")

        except Exception as e:
            self.log(f"Failed to connect to SUMMER camera: {e}")
            self.connected = False

    def initialize_camera(self):
        """Initialize the SUMMER camera with necessary settings.

        No-op: unlike SPRING there are no correction toggles to push, and the
        GUI's --auto-connect handles camera bring-up. Keeping this trivially
        idempotent makes the reconnect loop safe.
        """
        pass

    def pollCameraStatus(self):
        """Poll the camera status"""
        if not self.connected:
            self.log("Camera not connected.")
            return

        try:
            self.camera_status = self.cam.get_status()
            # if self.verbose:
            #    self.log(self.camera_status)

        except Exception as e:
            self.log(f"Error polling camera status: {e}")
            self.connected = False
        finally:
            if not self.connected:
                # Try to reconnect
                self.setup_connection()

    # === Update the Camera Status Dictionary ===
    def update_camera_state_info(self):
        """Update any camera-specific status info in the state dict"""

        # Update camera-specific status fields
        self.state.update(
            {
                # kept for shape compatibility with spring (always -888 on QHY42)
                "case_temp": self.getCaseTemp(),
                "digpcb_temp": self.getDigPCBTemp(),
                "senspcb_temp": self.getPCBTemp(),
                # SUMMER extras
                "tec_power_pct": self.tecGetPowerPct(),
                "gain": self._status_get("gain"),
                "offset": self._status_get("offset"),
                "usbtraffic": self._status_get("usbtraffic"),
                "gps_locked": self._status_get("gps_locked"),
                "gps_seq": self._status_get("gps_seq"),
                "vendor": self._status_get("vendor", "unknown"),
                "idle_mode": self._status_get("idle_mode", False),
                "gui_state": self.getGUIState(),
            }
        )

        if self.verbose:
            self.log(f"Updated camera state: {self.state}")

    # === Image Path Overrides ===
    def getDefaultImageDirectory(self) -> str:
        """Get default image directory"""
        return os.path.join("~", "data", "images", tonight_local(), "summer")

    # === Async Command Methods with Decorators ===

    @async_camera_command(timeout=10.0, completion_state=CameraState.READY)
    def tecStart(self, addrs=None):
        """Start TEC"""
        self.log("Starting TEC")

        reply = self.cam.set_tec_enabled(True)

        if self.command_worker.stop_requested:
            return False

        if reply.get("status") == "success":
            self.tec_enabled = True
            return True
        else:
            raise Exception(f"Failed to start TEC: {reply}")

    @async_camera_command(timeout=10.0, completion_state=CameraState.READY)
    def tecStop(self, addrs=None):
        """Stop TEC"""
        self.log("Stopping TEC")

        reply = self.cam.set_tec_enabled(False)

        if self.command_worker.stop_requested:
            return False

        if reply.get("status") == "success":
            self.tec_enabled = False
            return True
        else:
            raise Exception(f"Failed to stop TEC: {reply}")

    @async_camera_command(
        timeout=lambda self, *args, **kwargs: 3 * kwargs.get("exptime", args[0]) + 30.0,
        completion_state=CameraState.READY,
        initial_state=CameraState.SETTING_PARAMETERS,
        pending_completion=True,
    )
    def setExposure(self, exptime, addrs=None):
        """Set exposure time"""
        self.log(f"Setting exposure time to {exptime}s")
        self.requested_exposure_time = exptime

        reply = self.cam.set_exposure(exptime)

        if reply.get("status") == "success":
            self.log(
                "Exposure time requested successfully, waiting for camera to complete..."
            )
            return True
        else:
            raise Exception(f"Failed to set exposure time: {reply}")

    @async_camera_command(
        timeout=lambda self, *args, **kwargs: 2 * self.exposure_time + 30.0,
        completion_state=CameraState.READY,
        initial_state=CameraState.EXPOSING,
        pending_completion=True,  # Stay in EXPOSING until exposure completes
    )
    def doExposure(self, imdir, imname, imtype, mode, metadata, addrs=None):
        """Execute exposure with interruptible checking.

        metadata:
            - Dict: {'KEYWORD': value} or {'KEYWORD': (value, 'comment')}
            - List of tuples: [('KEYWORD', value), ('KEYWORD', value, 'comment')]
        Anything else (e.g., astropy.io.fits.Card) is rejected.
        """
        # Set up exposure parameters (from parent class)
        self.imdir = imdir
        self.imname = imname
        self.imtype = imtype
        self.mode = mode
        self.metadata = metadata
        self.addrs = addrs
        self.lastfilename = self.makeImageFilepath(imdir, imname, imtype)

        self.log(f"Starting exposure: {self.lastfilename}")

        # Set the directory
        self.cam.set_save_path(imdir)

        def _extract_value(v):
            # If dict value is a (value, comment) tuple, return value
            if isinstance(v, tuple) and len(v) >= 1:
                return v[0]
            return v

        object_name = None
        observer_name = "unknown"  # default if not provided
        cleaned_metadata = None

        if metadata is None:
            cleaned_metadata = None

        elif isinstance(metadata, dict):
            # Copy so we don't mutate caller's dict
            md = dict(metadata)

            # Case-insensitive lookups for OBJECT/OBSERVER
            key_obj = next(
                (k for k in md.keys() if isinstance(k, str) and k.lower() == "object"),
                None,
            )
            key_obs = next(
                (
                    k
                    for k in md.keys()
                    if isinstance(k, str) and k.lower() == "observer"
                ),
                None,
            )

            if key_obj is not None:
                object_name = _extract_value(md.pop(key_obj))
            if key_obs is not None:
                observer_name = _extract_value(md.pop(key_obs))

            cleaned_metadata = md

        elif isinstance(metadata, list):
            # Must be list of (key, value[, comment]) tuples
            if not all(
                isinstance(item, tuple) and len(item) in (2, 3) for item in metadata
            ):
                # Explicitly call out Card objects or bad shapes
                bad = next(
                    (
                        type(item).__name__
                        for item in metadata
                        if not (isinstance(item, tuple) and len(item) in (2, 3))
                    ),
                    None,
                )
                raise TypeError(
                    f"metadata must be a list of 2- or 3-tuples; unsupported item type/shape: {bad or 'unknown'}"
                )

            new_tuples = []
            for t in metadata:
                key = t[0]
                if not isinstance(key, str):
                    raise TypeError("metadata tuple key must be a string")

                key_lower = key.lower()
                if key_lower == "object":
                    if object_name is None:
                        object_name = t[1]
                    continue
                if key_lower == "observer":
                    if observer_name == "unknown":
                        observer_name = t[1]
                    continue

                new_tuples.append(t)

            cleaned_metadata = new_tuples

        else:
            raise TypeError(
                "metadata must be a dict or a list of (key, value[, comment]) tuples; "
                f"got {type(metadata).__name__}"
            )

        # filename should have no extension and no path
        self.log(f"imname: {imname}")
        self.log(f"imdir: {imdir}")
        self.log(f"imtype: {imtype}")
        self.log(f"lastfilename: {self.lastfilename}")

        # strip off any file extension and leading path
        filename_stem = Path(self.lastfilename.replace("\\", "/")).expanduser().stem

        reply = self.cam.capture_frames(
            filename=filename_stem,
            nframes=1,
            object=object_name,
            observer=observer_name,
            headers=cleaned_metadata,
            wait_for_completion=False,  # Don't wait in client
            debug=False,
        )

        if self.command_worker.stop_requested:
            self.log("Exposure command was interrupted")
            return False

        # Check the ACK response
        if reply is None:
            raise Exception("No response from GUI - communication error")

        if isinstance(reply, dict):
            if reply.get("status") == "success":
                self.log("Capture command accepted, exposure started")
                # Return True - state stays EXPOSING until _check_exposure_complete() returns True
                return True
            else:
                raise Exception(
                    f"Capture failed to start: {reply.get('message', 'Unknown error')}"
                )

        # Unexpected reply type
        raise Exception(f"Unexpected reply type: {type(reply).__name__}: {reply}")

    @async_camera_command(
        timeout=600.0,  # 10 minutes: QHY42 cooldown measured ~2 min from warm
        completion_state=CameraState.READY,
        initial_state=CameraState.SETTING_PARAMETERS,
        pending_completion=True,  # Stay in SETTING_PARAMETERS until temp stable
    )
    def tecSetSetpoint(self, temp, addrs=None):
        """Set TEC setpoint - stays in SETTING_PARAMETERS until stable"""
        temp = self._clamp_tec_setpoint(temp)
        self.log(f"Setting TEC setpoint to {temp}C")

        # Store target for completion checking
        self.tec_target_temp = temp

        reply = self.cam.set_tec_temperature(temp)

        if reply.get("status") == "success":
            self.tec_setpoint = temp
            self.log("Setpoint changed, waiting for temperature to stabilize...")
            return True
        else:
            raise Exception(f"Failed to set TEC setpoint: {reply}")

    @async_camera_command(
        timeout=1800.0,  # 30 minutes (huge margin: measured ~126 s to locked 0C)
        completion_state=CameraState.READY,
        initial_state=CameraState.STARTUP_REQUESTED,
        pending_completion=True,  # Stay in STARTUP_REQUESTED until complete
    )
    def autoStartup(self):
        """Start startup sequence - stays in STARTUP_REQUESTED until conditions met"""
        self.log("Initiating startup sequence")

        if not self.connected:
            self.setup_connection()
            if not self.connected:
                raise Exception("Failed to connect to camera")

        # Get target from config
        self.startup_target_temp = self._clamp_tec_setpoint(
            self.config.get("summer_camera", {}).get("tec_setpoint", 0.0)
        )

        # Set TEC setpoint
        self.log(f"Setting TEC setpoint to {self.startup_target_temp}C")
        reply = self.cam.set_tec_temperature(self.startup_target_temp)
        if reply.get("status") != "success":
            raise Exception(f"Failed to set TEC setpoint: {reply}")

        # Start TEC
        self.log("Enabling TEC")
        reply = self.cam.set_tec_enabled(True)
        if reply.get("status") != "success":
            raise Exception(f"Failed to start TEC: {reply}")

        # Return success - state stays STARTUP_REQUESTED
        self.log("Startup initiated, monitoring temperature...")
        return True

    @async_camera_command(
        timeout=600.0,  # 10 minutes
        completion_state=CameraState.OFF,
        initial_state=CameraState.SHUTDOWN_REQUESTED,
        pending_completion=True,  # Stay in SHUTDOWN_REQUESTED until complete
    )
    def autoShutdown(self):
        """Start shutdown - stays in SHUTDOWN_REQUESTED until conditions met"""
        self.log("Initiating shutdown sequence")

        if not self.connected:
            self.setup_connection()
            if not self.connected:
                raise Exception("Failed to connect to camera")

        # Stop TEC
        self.log("Disabling TEC")
        reply = self.cam.set_tec_enabled(False)
        if reply.get("status") != "success":
            raise Exception(f"Failed to stop TEC: {reply}")

        # Return success - state stays SHUTDOWN_REQUESTED
        self.log("Shutdown initiated...")
        return True

    def startupCamera(self, addrs=None):
        """Manual startup - delegates to autoStartup"""
        return self.autoStartup()

    def shutdownCamera(self, addrs=None):
        """Manual shutdown - delegates to autoShutdown"""
        return self.autoShutdown()

    # === Helpers ===

    def _clamp_tec_setpoint(self, temp):
        """Clamp a requested TEC setpoint to the camera's allowed range.

        The GUI clamps silently (WspSummerDaemonHandoff §6.5); clamp here too
        so the startup/setpoint completion checks compare against the value
        the camera will actually regulate to.
        """
        clamped = max(TEC_SETPOINT_MIN, min(TEC_SETPOINT_MAX, float(temp)))
        if clamped != temp:
            self.log(
                f"Requested TEC setpoint {temp}C outside allowed range "
                f"[{TEC_SETPOINT_MIN}, {TEC_SETPOINT_MAX}], clamping to {clamped}C",
                level=logging.WARNING,
            )
        return clamped

    def _status_get(self, key, default=DEFAULT_STATUS_VALUE):
        """Fetch a key from the cached GUI status data dict."""
        try:
            return self.camera_status.get("data", {}).get(key, default)
        except Exception as e:
            if self.verbose:
                self.log(f"Error getting {key}: {e}")
            return default

    # === Completion Condition Checkers ===

    def _check_startup_complete(self) -> bool:
        """Check if startup sequence is complete"""
        # Define your startup completion conditions
        conditions = [
            self.connected,
            self.tec_enabled,
            abs(self.tec_temp - self.startup_target_temp) < 0.5,  # Within 0.5C
        ]

        if all(conditions):
            self.log(f"Startup complete: TEC at {self.tec_temp:.1f}C")
            return True
        else:
            # Optional: log progress
            if (
                hasattr(self, "_last_startup_log")
                and (datetime.utcnow().timestamp() - self._last_startup_log) > 10
            ):
                self.log(
                    f"Startup progress: Temp={self.tec_temp:.1f}C, "
                    f"Target={self.startup_target_temp}C"
                )
                self._last_startup_log = datetime.utcnow().timestamp()
            elif not hasattr(self, "_last_startup_log"):
                self._last_startup_log = datetime.utcnow().timestamp()

        return False

    def _check_tec_setpoint_complete(self) -> bool:
        """Check if TEC has stabilized at new setpoint"""
        if hasattr(self, "tec_target_temp"):
            temp_stable = abs(self.tec_temp - self.tec_target_temp) < 0.5
            if temp_stable:
                self.log(f"TEC stabilized at {self.tec_temp:.1f}C")
                del self.tec_target_temp  # Clean up
                return True
        return False

    def _check_shutdown_complete(self) -> bool:
        """Check if shutdown is complete.

        Unlike spring there is no warm-up wait: the QHY TEC shuts off
        instantly with no ramp needed (decision per WspSummerDaemonHandoff
        §6.4), so shutdown is complete as soon as the TEC reports disabled.
        """
        return not self.tec_enabled

    def _check_set_exposure_complete(self) -> bool:
        """Check if set exposure command is complete"""
        # make sure the GUI is READY and the exposure time echoes the
        # requested time (exact float echo per the GUI contract)
        conditions = [
            self.state.get("gui_state", "") == "READY",
            self.state.get("exptime", -1) == self.requested_exposure_time,
        ]
        if self.verbose:
            self.log(
                f"Set exposure check conditions: gui_state={self.state.get('gui_state','')}, "
                f"exptime={self.state.get('exptime',-1)}, "
                f"requested_exposure_time={self.requested_exposure_time}"
            )
        return all(conditions)

    def _check_exposure_complete(self) -> bool:
        """Check if exposure has completed by polling camera status"""
        try:
            # Poll the GUI for current status
            status_data = self.camera_status.get("data", {})

            # Check if camera is still capturing
            is_capturing = status_data.get("is_capturing", False)

            if not is_capturing:
                # Exposure complete!
                self.log("Exposure completed")

                # Call the exposure completion handler
                self._exposure_complete(self.imdir, self.imname)

                return True

            # Still exposing - log progress occasionally
            if (
                not hasattr(self, "_last_exposure_log")
                or (datetime.utcnow().timestamp() - self._last_exposure_log) > 5
            ):
                current_frame = status_data.get("current_frame", 0)
                total_frames = status_data.get("total_frames", 1)
                time_remaining = status_data.get("capture_time_remaining", 0)
                self.log(
                    f"Exposing: frame {current_frame}/{total_frames}, "
                    f"{time_remaining:.1f}s remaining"
                )
                self._last_exposure_log = datetime.utcnow().timestamp()

            return False

        except Exception as e:
            self.log(f"Error checking exposure completion: {e}", level=logging.ERROR)
            # On error, assume exposure failed
            return True

    # === Status Polling Methods ===

    def tecGetSetpoint(self):
        return self._status_get("tec_setpoint")

    def tecGetTemp(self):
        return self._status_get("tec_temp")

    def tecGetVoltage(self):
        # QHY exposes cooler PWM percent, not voltage (see tecGetPowerPct)
        return DEFAULT_STATUS_VALUE

    def tecGetCurrent(self):
        # not derivable without voltage; see tecGetPowerPct
        return DEFAULT_STATUS_VALUE

    def tecGetPercentage(self):
        return self.tecGetPowerPct()

    def tecGetPowerPct(self):
        return self._status_get("tec_power_pct")

    def tecGetSteadyStatus(self) -> bool:
        try:
            return self.camera_status.get("data", {}).get("tec_locked", False)
        except Exception as e:
            if self.verbose:
                self.log(f"Error getting TEC steady status: {e}")
            return False

    def tecGetEnabled(self):
        return self._status_get("tec_enabled")

    def getExposureTime(self):
        return self._status_get("exposure")

    def getPCBTemp(self):
        return self._status_get("senspcb_temp")

    def getCaseTemp(self):
        return self._status_get("case_temp")

    def getDigPCBTemp(self):
        return self._status_get("digpcb_temp")

    def getGUIState(self):
        try:
            return self.camera_status.get("data", {}).get("camera_state", "UNKNOWN")
        except Exception as e:
            if self.verbose:
                self.log(f"Error getting camera state: {e}")
            return DEFAULT_STATUS_VALUE


if __name__ == "__main__":
    # Create and run the daemon

    create_camera_daemon(SummerCameraInterface, "SUMMERCamera")
