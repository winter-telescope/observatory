# spring_camera_daemon.py

import logging
import time
from datetime import datetime

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
        except Exception as e:
            self.log(f"Error polling camera status: {e}")
            self.connected = False
        finally:
            if not self.connected:
                # Try to reconnect
                self.setup_connection()

    # === Update the Camera Status Dictionary ===
    def pollStatus(self):
        # Update camera-specific status fields
        self.state.update(
            {
                "case_temp": self.getCaseTemp(),
                "digpcb_temp": self.getDigPCBTemp(),
                "senspcb_temp": self.getPCBTemp(),
                "gain_corr": self.getGainCorr(),
                "offset_corr": self.getOffsetCorr(),
                "sub_corr": self.getSubCorr(),
            }
        )

        # Call the parent method to update common fields
        super().pollStatus()

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
        timeout=lambda self, *args, **kwargs: self.exposure_time + 30.0,
        completion_state=CameraState.READY,
        initial_state=CameraState.EXPOSING,
    )
    def doExposure(self, imdir, imname, imtype, mode, metadata, addrs=None):
        """Execute exposure with interruptible checking"""
        # Set up exposure parameters (from parent class)
        self.imdir = imdir
        self.imname = imname
        self.imtype = imtype
        self.mode = mode
        self.metadata = metadata
        self.addrs = addrs
        self.lastfilename = self.makeImageFilepath(imdir, imname, imtype)

        self.log(f"Starting exposure: {self.lastfilename}")

        # If the camera API supports async/polling, make it interruptible:
        # Example of interruptible exposure if API supports it:
        """
        # Start exposure
        self.cam.start_exposure(self.lastfilename)
        
        # Poll for completion with interrupt checking
        poll_interval = 0.1  # seconds
        max_polls = int((self.exposure_time + 30) / poll_interval)
        
        for i in range(max_polls):
            if self.command_worker.stop_requested:
                self.cam.abort_exposure()
                self.log("Exposure aborted by user")
                return False
            
            if self.cam.is_exposure_complete():
                break
            
            time.sleep(poll_interval)
        """

        # For blocking API (current case):
        reply = self.cam.take_image(
            filename=self.lastfilename, nframes=1, object_name=imtype
        )

        if self.command_worker.stop_requested:
            self.log("Exposure command was interrupted")
            return False

        if reply.get("status") == "success":
            self._exposure_complete(imdir, imname)
            return True
        else:
            raise Exception(f"Exposure failed: {reply}")

    # === Commands with Pending Completion ===
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
