# spring_camera_daemon.py
"""
Daemon for the SPRING camera.
This daemon communicates with the remote SPRING camera gui using the
pirt-camera-control library.
"""

import logging
from datetime import datetime

import astropy.io.fits as fits
import numpy as np
from pirtcam.client import CameraClient
from PyQt5 import QtCore

from wsp.camera.camera_command_decorators import camera_command
from wsp.camera.daemon_framework import BaseCameraInterface, create_camera_daemon
from wsp.camera.state import CameraState

DEFAULT_STATUS_VALUE = -888
'''
CAMERA_IP_ADDR = "192.168.1.15"
CAMERA_IP_ADDR = "localhost"
 def setup_connections(self):
        """
        Set up connections specific to the SPRING camera.
        """
        # Implementation for setting up connections
        self.cam = CameraClient(host=CAMERA_IP_ADDR, port=5555)
        self.cam.connect()

        self.initialize_camera()

    def initialize_camera(self):
        """
        Initialize the SPRING camera with necessary settings.
        """
        # Implementation for initializing the camera
        self.cam.set_correction("GAIN", "OFF")
        self.cam.set_correction("OFFSET", "OFF")
        self.cam.set_correction("SUB", "OFF")
'''


class SpringCameraInterface(BaseCameraInterface):
    """
    Interface for the SPRING camera.
    This class extends BaseCameraInterface to provide specific functionality for the SPRING camera.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Additional initialization if needed

    def setup_connections(self):
        """
        Set up connections specific to the SPRING camera.
        """
        # Implementation for setting up connections

        # Initialize camera status dictionary which is populated when
        # self.cam.get_status() is called in self.pollCameraStatus()

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
        """
        Initialize the SPRING camera with necessary settings.
        """
        # Implementation for initializing the camera
        self.cam.set_correction("GAIN", "OFF")
        self.cam.set_correction("OFFSET", "OFF")
        self.cam.set_correction("SUB", "OFF")

    def pollCameraStatus(self):
        """Poll the camera status and update state
        Expects a dictionary:
        {
            "status": "success",
            "data": {
            "tec_locked": 1,
            "exposure": 1.0,
            "nframes": 1,
            "object": "SCICAM",
            "observer": "MDM",
            "save_path": "~/data",
            "tec_temp": -39.96138,
            "tec_setpoint": -39.994728,
            "soc": "30HZ_32MSEXP_-40C",
            "gain_corr": 1,
            "offset_corr": 1,
            "sub_corr": 1,
            "tec_lock": 1,
            "waiting_on_exposure_update": 0
            }
            }
        """
        if not self.connected:
            self.log("Camera not connected.")

        try:
            self.camera_status = self.cam.get_status()

        except Exception as e:
            self.log(f"Error polling camera status: {e}")
            self.connected = False
        finally:
            if not self.connected:
                # try to reconnect
                self.setup_connections()

    def check_if_command_passed(self):
        """Override to check if command completed"""
        # This is called during polling when command_active is True
        # For fake camera, we rely on timer callbacks to signal completion
        pass

    @camera_command(timeout=10.0, completion_state=CameraState.READY)
    def tecSetSetpoint(self, temp, addrs=None):
        """Set TEC setpoint"""
        self.tec_setpoint = temp
        self.log(f"Set TEC setpoint to {temp}C")
        reply = self.cam.set_tec_temperature(temp)
        if reply.get("status") == "success":
            return True
        else:
            self.log(f"Failed to set TEC setpoint: {reply}")
            return False

    @camera_command(timeout=5.0, completion_state=CameraState.READY)
    def tecStart(self, addrs=None):
        """Start TEC"""
        self.tec_enabled = True
        self.log("TEC started")
        reply = self.cam.set_tec_enabled(True)
        if reply.get("status") == "success":
            return True
        else:
            self.log(f"Failed to start TEC: {reply}")
            return False

    @camera_command(timeout=5.0, completion_state=CameraState.READY)
    def tecStop(self, addrs=None):
        """Stop TEC"""
        self.tec_enabled = False
        self.log("TEC stopped")
        reply = self.cam.set_tec_enabled(False)
        if reply.get("status") == "success":
            return True
        else:
            self.log(f"Failed to stop TEC: {reply}")
            return False

    @camera_command(timeout=1800.0, completion_state=CameraState.READY)
    def autoStartup(self):
        """Auto startup:
        1. connect to camera if not already
        2. set TEC setpoint to config value
        3. start TEC
        """
        self.update_camera_state(CameraState.STARTUP_REQUESTED)

        if not self.connected:
            self.setup_connections()
            if not self.connected:
                self.update_camera_state(CameraState.ERROR)
                return False

        # Set TEC setpoint
        self.tecSetSetpoint(-60.0)

        # Start TEC
        self.tecStart()

        return True

    @camera_command(timeout=1800.0, completion_state=CameraState.OFF)
    def autoShutdown(self):
        """Auto shutdown:
        1. connect to camera if not already
        2. set TEC setpoint to -40C
        """
        self.update_camera_state(CameraState.SHUTDOWN_REQUESTED)

        if not self.connected:
            self.setup_connections()
            if not self.connected:
                self.update_camera_state(CameraState.ERROR)
                return False

        # Stop TEC
        self.tecStop()

        return True

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
        return True

    def startupCamera(self, addrs=None):
        """Manual startup - delegates to autoStartup"""
        return self.autoStartup()

    def shutdownCamera(self, addrs=None):
        """Manual shutdown - delegates to autoShutdown"""
        return self.autoShutdown()

    # Polling Methods
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
        # this is approximate.
        # max power ~ 55 W at 9V
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
        # TEC percent is voltage/max voltage
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


if __name__ == "__main__":
    # Create and run the daemon
    create_camera_daemon(SpringCameraInterface, "SpringCamera")
