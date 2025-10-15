# spring_camera_daemon.py

import logging
import time
from datetime import datetime
from pathlib import Path

import astropy.io.fits as fits
import numpy as np
from pirtcam.client import CameraClient
from PyQt5 import QtCore

from wsp.camera.camera_command_decorators import async_camera_command
from wsp.camera.daemon_framework import BaseCameraInterface, create_camera_daemon
from wsp.camera.state import CameraState

DEFAULT_STATUS_VALUE = -888


class SpringCameraInterface(BaseCameraInterface):
    """
    Interface for the SPRING camera using the async decorator pattern.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Additional initialization if needed

    def setup_connection(self):
        """Set up connections specific to the SPRING camera."""
        self.log("Setting up connection to SPRING camera...")

        self.camera_status = {}

        try:
            self.cam = CameraClient(host="localhost", port=5555)
            self.cam.connect()

            self.initialize_camera()
            self.connected = True
            self.log("Connected to SPRING camera.")

        except Exception as e:
            self.log(f"Failed to connect to SPRING camera: {e}")
            self.connected = False

    def initialize_camera(self):
        """Initialize the SPRING camera with necessary settings."""
        self.cam.set_correction("GAIN", "OFF")
        self.cam.set_correction("OFFSET", "OFF")
        self.cam.set_correction("SUB", "OFF")

    def pollCameraStatus(self):
        """Poll the camera status"""
        if not self.connected:
            self.log("Camera not connected.")
            return

        try:
            self.camera_status = self.cam.get_status()
            if self.verbose:
                self.log(self.camera_status)

        except Exception as e:
            self.log(f"Error polling camera status: {e}")
            self.connected = False
        finally:
            if not self.connected:
                # Try to reconnect
                self.setup_connection()

    # === Update the Camera Status Dictionary ===
    def pollStatus(self):

        # Call the parent method to update common fields
        super().pollStatus()

        # Update camera-specific status fields
        self.state.update(
            {
                "case_temp": self.getCaseTemp(),
                "digpcb_temp": self.getDigPCBTemp(),
                "senspcb_temp": self.getPCBTemp(),
                "gain_corr": self.getGainCorr(),
                "offset_corr": self.getOffsetCorr(),
                "sub_corr": self.getSubCorr(),
                "gui_state": self.getGUIState(),
            }
        )

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

    @async_camera_command(timeout=10.0, completion_state=CameraState.READY)
    def setExposure(self, exptime, addrs=None):
        """Set exposure time"""
        self.log(f"Setting exposure time to {exptime}s")

        self.cam.set_exposure(exptime)

        if self.command_worker.stop_requested:
            return False

        self.exposure_time = exptime
        self.state.update({"exposure_time": exptime})
        return True

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
        timeout=120.0,  # 2 minutes
        completion_state=CameraState.READY,
        initial_state=CameraState.SETTING_PARAMETERS,
        pending_completion=True,  # Stay in SETTING_PARAMETERS until temp stable
    )
    def tecSetSetpoint(self, temp, addrs=None):
        """Set TEC setpoint - stays in SETTING_PARAMETERS until stable"""
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
        timeout=1800.0,  # 30 minutes
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
        self.startup_target_temp = self.config.get("tec_setpoint", -60.0)

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
        self.log("Shutdown initiated, waiting for camera to warm up...")
        return True

    def startupCamera(self, addrs=None):
        """Manual startup - delegates to autoStartup"""
        return self.autoStartup()

    def shutdownCamera(self, addrs=None):
        """Manual shutdown - delegates to autoShutdown"""
        return self.autoShutdown()

    # === Completion Condition Checkers ===

    def _check_startup_complete(self) -> bool:
        """Check if startup sequence is complete"""
        # Define your startup completion conditions
        conditions = [
            self.connected,
            self.tec_enabled,
            abs(self.tec_temp - self.startup_target_temp) < 0.5,  # Within 0.5C
            # Could add more conditions like:
            # self.camera_status.get("data", {}).get("tec_locked", False),
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
        """Check if shutdown is complete"""
        # For example, wait for TEC to warm up
        conditions = [
            not self.tec_enabled,
            self.tec_temp > -45.0,  # Warmed up enough
        ]
        return all(conditions)

    def _check_set_exposure_complete(self) -> bool:
        """Check if set exposure command is complete"""
        # make sure camera is READY and that the exposure timeout is 0 and
        # that the exposure time matches the requested time
        status_data = self.camera_status.get("data", {})

        return True

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

    # === Status Polling Methods (unchanged) ===

    def tecGetSetpoint(self):
        try:
            return self.camera_status.get("data", {}).get(
                "tec_setpoint", DEFAULT_STATUS_VALUE
            )
        except Exception as e:
            if self.verbose:
                self.log(f"Error getting TEC setpoint: {e}")
            return DEFAULT_STATUS_VALUE

    def tecGetTemp(self):
        try:
            return self.camera_status.get("data", {}).get(
                "tec_temp", DEFAULT_STATUS_VALUE
            )
        except Exception as e:
            if self.verbose:
                self.log(f"Error getting TEC temperature: {e}")
            return DEFAULT_STATUS_VALUE

    def tecGetVoltage(self):
        try:
            return self.camera_status.get("data", {}).get(
                "tec_voltage", DEFAULT_STATUS_VALUE
            )
        except Exception as e:
            if self.verbose:
                self.log(f"Error getting TEC voltage: {e}")
            return DEFAULT_STATUS_VALUE

    def tecGetCurrent(self):
        max_power = 55.0
        max_voltage = 9.0
        approx_impedance = max_voltage**2 / max_power
        try:
            current = self.tecGetVoltage() / approx_impedance
            return current
        except Exception as e:
            if self.verbose:
                self.log(f"Error getting TEC current: {e}")
            return DEFAULT_STATUS_VALUE

    def tecGetPercentage(self):
        try:
            voltage = self.camera_status.get("data", {}).get(
                "tec_voltage", DEFAULT_STATUS_VALUE
            )
            max_voltage = 9.0
            if voltage == DEFAULT_STATUS_VALUE:
                return DEFAULT_STATUS_VALUE
            return (voltage / max_voltage) * 100
        except Exception as e:
            if self.verbose:
                self.log(f"Error getting TEC percentage: {e}")
            return DEFAULT_STATUS_VALUE

    def tecGetSteadyStatus(self) -> bool:
        try:
            return self.camera_status.get("data", {}).get("tec_locked", False)
        except Exception as e:
            if self.verbose:
                self.log(f"Error getting TEC steady status: {e}")
            return False

    def tecGetEnabled(self):
        try:
            return self.camera_status.get("data", {}).get(
                "tec_enabled", DEFAULT_STATUS_VALUE
            )
        except Exception as e:
            if self.verbose:
                self.log(f"Error getting TEC enabled status: {e}")
            return DEFAULT_STATUS_VALUE

    def getExposureTime(self):
        try:
            return self.camera_status.get("data", {}).get(
                "exposure", DEFAULT_STATUS_VALUE
            )
        except Exception as e:
            if self.verbose:
                self.log(f"Error getting exposure time: {e}")
            return DEFAULT_STATUS_VALUE

    def getPCBTemp(self):
        try:
            return self.camera_status.get("data", {}).get(
                "senspcb_temp", DEFAULT_STATUS_VALUE
            )
        except Exception as e:
            if self.verbose:
                self.log(f"Error getting PCB temperature: {e}")
            return DEFAULT_STATUS_VALUE

    def getCaseTemp(self):
        try:
            return self.camera_status.get("data", {}).get(
                "case_temp", DEFAULT_STATUS_VALUE
            )
        except Exception as e:
            if self.verbose:
                self.log(f"Error getting case temperature: {e}")
            return DEFAULT_STATUS_VALUE

    def getDigPCBTemp(self):
        try:
            return self.camera_status.get("data", {}).get(
                "digpcb_temp", DEFAULT_STATUS_VALUE
            )
        except Exception as e:
            if self.verbose:
                self.log(f"Error getting digital PCB temperature: {e}")
            return DEFAULT_STATUS_VALUE

    def getGainCorr(self):
        try:
            return self.camera_status.get("data", {}).get(
                "gain_corr", DEFAULT_STATUS_VALUE
            )
        except Exception as e:
            if self.verbose:
                self.log(f"Error getting gain correction status: {e}")
            return DEFAULT_STATUS_VALUE

    def getOffsetCorr(self):
        try:
            return self.camera_status.get("data", {}).get(
                "offset_corr", DEFAULT_STATUS_VALUE
            )
        except Exception as e:
            if self.verbose:
                self.log(f"Error getting offset correction status: {e}")
            return DEFAULT_STATUS_VALUE

    def getSubCorr(self):
        try:
            return self.camera_status.get("data", {}).get(
                "sub_corr", DEFAULT_STATUS_VALUE
            )
        except Exception as e:
            if self.verbose:
                self.log(f"Error getting subframe correction status: {e}")
            return DEFAULT_STATUS_VALUE

    def getGUIState(self):
        try:
            return self.camera_status.get("data", {}).get("camera_state", "UNKNOWN")
        except Exception as e:
            if self.verbose:
                self.log(f"Error getting camera state: {e}")
            return DEFAULT_STATUS_VALUE

    '''
    def _check_if_startup_complete(self, state):
        """Check if startup is complete"""
        startup_conditions = [
            state["connected"],
            state["tec_enabled"],
            abs(state["tec_temp"] - state["tec_setpoint"]) < 0.1,
            state["tec_lock"],
        ]
        if all(startup_conditions):
            self.update_camera_state(CameraState.READY)
            return True
        return False

    def _check_if_ready_to_shutdown(self, state):
        """Check if camera is ready to shutdown"""
        shutdown_conditions = [
            state["connected"],
            state["tec_temp"] > -45.0,
        ]
        if all(shutdown_conditions):
            return True
        return False

    def _complete_shutdown(self):
        """Complete shutdown process"""
        self.tecStop()
        self.update_camera_state(CameraState.OFF)
        return True'''


if __name__ == "__main__":
    # Create and run the daemon
    create_camera_daemon(SpringCameraInterface, "SpringCamera")
