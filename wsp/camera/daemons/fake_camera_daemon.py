#!/usr/bin/env python3
"""
fake_camera_daemon.py

Example fake camera implementation that demonstrates proper state management
with immediate state transitions handled by the daemon.
"""

import logging
import os
from datetime import datetime

import astropy.io.fits as fits
import numpy as np
from PyQt5 import QtCore

from wsp.camera.camera_command_decorators import camera_command
from wsp.camera.daemon_framework import BaseCameraInterface, create_camera_daemon
from wsp.camera.state import CameraState


class ExposureConfig:
    """Container for exposure configuration"""

    def __init__(self, imdir, imname, imtype, exposure_time, mode, metadata):
        self.imdir = imdir
        self.imname = imname
        self.imtype = imtype
        self.exposure_time = exposure_time
        self.mode = mode
        self.metadata = metadata


class TimerWorker(QtCore.QObject):
    """Worker object that runs in a separate QThread to handle timers"""

    # Signals that can be emitted from any thread
    startupTimerRequested = QtCore.pyqtSignal(int)
    shutdownTimerRequested = QtCore.pyqtSignal(int)
    exposureTimerRequested = QtCore.pyqtSignal(int, object)

    # Signals emitted when timers complete
    startupComplete = QtCore.pyqtSignal()
    shutdownComplete = QtCore.pyqtSignal()
    exposureComplete = QtCore.pyqtSignal(object)

    def __init__(self):
        super().__init__()

        # Connect incoming requests to timer creation methods
        self.startupTimerRequested.connect(self.create_startup_timer)
        self.shutdownTimerRequested.connect(self.create_shutdown_timer)
        self.exposureTimerRequested.connect(self.create_exposure_timer)

    @QtCore.pyqtSlot(int)
    def create_startup_timer(self, delay_ms):
        """Create startup timer in this thread"""
        QtCore.QTimer.singleShot(delay_ms, self.startupComplete.emit)

    @QtCore.pyqtSlot(int)
    def create_shutdown_timer(self, delay_ms):
        """Create shutdown timer in this thread"""
        QtCore.QTimer.singleShot(delay_ms, self.shutdownComplete.emit)

    @QtCore.pyqtSlot(int, object)
    def create_exposure_timer(self, delay_ms, exposure_config):
        """Create exposure timer in this thread"""
        QtCore.QTimer.singleShot(
            delay_ms, lambda: self.exposureComplete.emit(exposure_config)
        )


class FakeCameraInterface(BaseCameraInterface):
    """
    Example fake camera implementation for testing.
    Demonstrates proper state management with decorators.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Camera parameters
        self.exposure_time = 1.0
        self.tec_setpoint = -20.0
        self.tec_temp = 20.0
        self.tec_enabled = False

        # Track exposure
        self._exposure_start_time = datetime.utcnow()
        self._exposure_complete_time = datetime.utcnow()

        # Create worker thread for timers
        self.timer_thread = QtCore.QThread()
        self.timer_worker = TimerWorker()
        self.timer_worker.moveToThread(self.timer_thread)

        # Connect worker signals to our methods
        self.timer_worker.startupComplete.connect(self._startup_complete)
        self.timer_worker.shutdownComplete.connect(self._shutdown_complete)
        self.timer_worker.exposureComplete.connect(self._exposure_complete)

        # Start the worker thread
        self.timer_thread.start()

        # Initial state
        self.update_camera_state(CameraState.OFF)

    def __del__(self):
        """Clean up the worker thread"""
        if hasattr(self, "timer_thread"):
            self.timer_thread.quit()
            self.timer_thread.wait()

    def setup_connection(self):
        """Fake camera always connected"""
        self.connected = True
        self.log("Fake camera connected")

    def pollCameraStatus(self):
        """Poll fake camera status: called automatically by the daemon"""
        # Simulate temperature control
        if self.tec_enabled:
            # Slowly approach setpoint
            self.tec_temp += (self.tec_setpoint - self.tec_temp) * 0.1

        # Add camera specific items to the status
        self.state.update(
            {
                "fake_camera_status": "operational",
                "simulation_mode": True,
            }
        )

    def check_if_command_passed(self):
        """Override to check if command completed"""
        # This is called during polling when command_active is True
        # For fake camera, we rely on timer callbacks to signal completion
        pass

    @camera_command(timeout=3600.0)  # 1 hour timeout for long startups
    def autoStartup(self):
        """Fake startup sequence"""
        self.log("Starting fake camera startup")
        self.update_camera_state(CameraState.STARTUP_REQUESTED)

        # Simulate startup delay
        self.timer_worker.startupTimerRequested.emit(2000)
        return True

    def _startup_complete(self):
        """Complete startup - called by signal from worker thread"""
        self.update_camera_state(CameraState.READY)
        self.log("Fake camera startup complete")
        # Signal command completion
        self.resetCommandPassSignal.emit(1)
        self.resetCommandActiveSignal.emit(0)

    @camera_command(timeout=300.0)  # 5 minute timeout for shutdown
    def autoShutdown(self):
        """Fake shutdown sequence"""
        self.log("Starting fake camera shutdown")
        self.update_camera_state(CameraState.SHUTDOWN_REQUESTED)

        # Simulate shutdown delay
        self.timer_worker.shutdownTimerRequested.emit(1000)
        return True

    def _shutdown_complete(self):
        """Complete shutdown - called by signal from worker thread"""
        self.update_camera_state(CameraState.OFF)
        self.log("Fake camera shutdown complete")
        # Signal command completion
        self.resetCommandPassSignal.emit(1)
        self.resetCommandActiveSignal.emit(0)

    @camera_command(
        timeout_func=lambda self, *args, **kwargs: 10.0,
        completion_state=CameraState.READY,
    )
    def setExposure(self, exptime, addrs=None):
        """Set exposure time"""
        self.exposure_time = exptime
        self.log(f"Set exposure time to {exptime}s")
        self.state.update({"exposure_time": exptime})
        return True

    @camera_command(
        timeout_func=lambda self, *args, **kwargs: max(
            5 * self.exposure_time + 10, 60.0
        )
    )
    def doExposure(self, imdir, imname, imtype, mode, metadata, addrs=None):
        """Execute fake exposure - state already set to EXPOSING by daemon decorator"""
        # Call parent to set up basic exposure parameters
        super().doExposure(imdir, imname, imtype, mode, metadata, addrs)
        self._exposure_start_time = datetime.utcnow()
        self.log(
            f"Starting fake exposure: {self.imname}, starttime = {self._exposure_start_time.isoformat()}"
        )

        # Create a unique filename if needed
        if not self.imname:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            self.imname = f"fake_{timestamp}"

        # Update lastfilename with full path
        self.lastfilename = self.makeImageFilepath(self.imdir, self.imname, self.imtype)

        self.log(f"Fake exposure initialized: {self.imname}")
        self.log(f"Will save to: {self.lastfilename}")

        exposure_config = ExposureConfig(
            imdir=self.imdir,
            imname=self.imname,
            imtype=self.imtype,
            exposure_time=self.exposure_time,
            mode=self.mode,
            metadata=metadata,
        )

        # Request timer in worker thread
        delay_ms = int(self.exposure_time * 1000)
        self.timer_worker.exposureTimerRequested.emit(delay_ms, exposure_config)

        return True

    def _exposure_complete(self, exposure_config):
        """Complete the fake exposure - called by signal from worker thread"""
        self._exposure_complete_time = datetime.utcnow()
        self.log(
            f"Completing exposure: {exposure_config.imname}, endtime = {self._exposure_complete_time.isoformat()}, dt = {self._exposure_complete_time - self._exposure_start_time} s"
        )

        # Transition to READING state
        self.update_camera_state(CameraState.READING)

        # Make a fake FITS image
        img_data = np.random.randint(0, 65535, (1024, 1280), dtype=np.uint16)
        hdu = fits.PrimaryHDU(img_data)
        hdr = hdu.header

        # Add metadata
        if isinstance(exposure_config.metadata, list):
            for cardtuple in exposure_config.metadata:
                try:
                    card = fits.Card(*cardtuple)
                    hdr.append(card)
                except Exception as e:
                    self.log(f"Could not add {cardtuple[0]} to header: {e}")
        elif isinstance(exposure_config.metadata, dict):
            for key, value in exposure_config.metadata.items():
                try:
                    hdr[key] = value
                except Exception as e:
                    self.log(f"Could not add {key} to header: {e}")

        # Add standard headers
        hdr["EXPTIME"] = exposure_config.exposure_time
        hdr["IMAGETYP"] = exposure_config.imtype
        hdr["DATE-OBS"] = datetime.utcnow().isoformat()

        # Write the image
        try:
            self.log(f"Writing FITS file to: {self.lastfilename}")
            hdu.writeto(self.lastfilename, overwrite=True)
            self.log(f"FITS file written successfully: {self.lastfilename}")
        except Exception as e:
            self.log(f"Error writing FITS file: {e}", level=logging.ERROR)
            self.update_camera_state(CameraState.ERROR)
            self.resetCommandPassSignal.emit(0)
            self.resetCommandActiveSignal.emit(0)
            return

        # Signal command completion
        self.resetCommandPassSignal.emit(1)
        self.resetCommandActiveSignal.emit(0)

        # Update state to show exposure complete
        self.state.update(
            {
                "last_image": self.lastfilename,
                "last_exposure_time": exposure_config.exposure_time,
            }
        )

        # Call parent's exposure complete method
        super()._exposure_complete(exposure_config.imdir, exposure_config.imname)

    @camera_command(timeout=10.0, completion_state=CameraState.READY)
    def tecSetSetpoint(self, temp, addrs=None):
        """Set TEC setpoint"""
        self.tec_setpoint = temp
        self.log(f"Set TEC setpoint to {temp}C")
        self.state.update({"tec_setpoint": temp})
        return True

    @camera_command(timeout=5.0, completion_state=CameraState.READY)
    def tecStart(self, addrs=None):
        """Start TEC"""
        self.tec_enabled = True
        self.log("TEC started")
        self.state.update({"tec_enabled": True})
        return True

    @camera_command(timeout=5.0, completion_state=CameraState.READY)
    def tecStop(self, addrs=None):
        """Stop TEC"""
        self.tec_enabled = False
        self.log("TEC stopped")
        self.state.update({"tec_enabled": False})
        return True

    def startupCamera(self, addrs=None):
        """Manual startup - delegates to autoStartup"""
        return self.autoStartup()

    def shutdownCamera(self, addrs=None):
        """Manual shutdown - delegates to autoShutdown"""
        return self.autoShutdown()

    # Required abstract methods
    def tecGetSetpoint(self) -> float:
        """Get current TEC setpoint"""
        return self.tec_setpoint

    def tecGetTemp(self) -> float:
        """Get current TEC temperature"""
        return self.tec_temp
        return self.tec_setpoint

    def tecGetVoltage(self) -> float:
        """Get current TEC voltage"""
        if self.tec_enabled:
            # base voltage + some noise
            self.tec_voltage = 7.5 + np.random.uniform(-0.5, 0.5)
        else:
            self.tec_voltage = 0.0
        return self.tec_voltage

    def tecGetCurrent(self) -> float:
        """Get current TEC current"""
        approx_tec_impedence = 4.0  # ohms
        if self.tec_enabled:
            # Simulate current based on voltage
            self.tec_current = self.tec_voltage / approx_tec_impedence
        else:
            self.tec_current = 0.0
        return self.tec_current

    def tecGetPercentage(self):
        """Get current TEC power percentage"""
        max_tec_voltage = 8.0
        approx_tec_impedence = 4.0  # ohms
        max_power = max_tec_voltage**2 / approx_tec_impedence
        power = self.tec_voltage**2 / approx_tec_impedence
        self.tec_percentage = min(100.0, power / max_power * 100.0)
        return self.tec_percentage

    def tecGetEnabled(self) -> bool:
        """Check if TEC is enabled"""
        return self.tec_enabled

    def getExposureTime(self) -> float:
        """Get current exposure time"""
        return self.exposure_time


if __name__ == "__main__":
    # Create and run the daemon
    create_camera_daemon(FakeCameraInterface, "FakeCamera")
