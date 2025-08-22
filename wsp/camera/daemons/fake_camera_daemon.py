# fake_camera_daemon.py
import logging
import os
from datetime import datetime

import astropy.io.fits as fits
import numpy as np
from PyQt5 import QtCore

from wsp.camera.camera_command_decorators import (
    camera_command,
    exposure_command,
    shutdown_command,
    startup_command,
)
from wsp.camera.daemon_framework import BaseCameraInterface, create_camera_daemon
from wsp.camera.state import CameraState


class ExposureConfig:
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
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.exposure_time = 1.0
        self.tec_setpoint = -20.0
        self.tec_temp = 20.0
        self.tec_enabled = False

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
                "thing": "value",  # Example status item
            }
        )

    @startup_command(timeout=300.0)
    def autoStartup(self):
        """Fake startup sequence"""
        self.log("Starting fake camera startup")

        # Request timer creation in worker thread
        self.timer_worker.startupTimerRequested.emit(2000)

    def _startup_complete(self):
        """Complete startup - called by signal from worker thread"""
        self.update_camera_state(CameraState.READY)
        self.log("Fake camera startup complete")
        # Signal command completion
        self.resetCommandPassSignal.emit(1)
        self.resetCommandActiveSignal.emit(0)

    @shutdown_command(timeout=300.0)
    def autoShutdown(self):
        """Fake shutdown sequence"""
        self.log("Starting fake camera shutdown")

        # Request timer in worker thread
        self.timer_worker.shutdownTimerRequested.emit(1000)

    def _shutdown_complete(self):
        """Complete shutdown - called by signal from worker thread"""
        self.update_camera_state(CameraState.OFF)
        self.log("Fake camera shutdown complete")
        # Signal command completion
        self.resetCommandPassSignal.emit(1)
        self.resetCommandActiveSignal.emit(0)

    @camera_command(
        timeout_func=lambda self, *args, **kwargs: (
            4 * args[0] + 5 if args else 10
        ),  # args[0] is exposure time
        completion_state=CameraState.READY,
    )
    def setExposure(self, exptime, addrs=None, **kwargs):  # Add **kwargs here
        """Set exposure time"""
        self.exposure_time = exptime
        self.log(f"Set exposure time to {exptime}s")
        return True

    @exposure_command(
        timeout_func=lambda self, *args, **kwargs: 5 * self.exposure_time + 5
    )
    def doExposure(self, imdir, imname, imtype, mode, metadata, addrs=None, **kwargs):
        """Fake exposure"""
        # Call parent to set up basic exposure parameters
        super().doExposure(imdir, imname, imtype, mode, metadata, addrs)

        self.log(f"Starting fake exposure: {self.imname}")

        # Initialize fake exposure parameters
        if not os.path.exists(self.imdir):
            os.makedirs(self.imdir)

        # Create a unique filename if needed
        if not self.imname:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            self.imname = f"fake_{timestamp}"

        self.log(f"Fake exposure initialized: {self.imname}")

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
        self.log(f"Completing exposure: {exposure_config.imname}")

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

        # Add exposure time
        hdr["EXPTIME"] = exposure_config.exposure_time

        # Ensure full filepath
        if not self.lastfilename.endswith(".fits"):
            self.lastfilename = f"{self.lastfilename}.fits"

        # Write the image
        try:
            self.log(f"Writing FITS file to: {self.lastfilename}")
            hdu.writeto(self.lastfilename, overwrite=True)
            self.log(f"FITS file written successfully: {self.lastfilename}")
        except Exception as e:
            self.log(f"Error writing FITS file: {e}", level=logging.ERROR)
            raise

        # Signal command completion
        self.resetCommandPassSignal.emit(1)
        self.resetCommandActiveSignal.emit(0)

        # Call parent's exposure complete method
        super()._exposure_complete(exposure_config.imdir, exposure_config.imname)

    @camera_command(timeout=10.0)
    def tecSetSetpoint(self, temp, addrs=None, **kwargs):
        """Set TEC setpoint"""
        self.tec_setpoint = temp
        self.log(f"Set TEC setpoint to {temp}C")
        return True

    @camera_command(timeout=5.0)
    def tecStart(self, addrs=None, **kwargs):
        """Start TEC"""
        self.tec_enabled = True
        self.log("TEC started")
        return True

    @camera_command(timeout=5.0)
    def tecStop(self, addrs=None, **kwargs):
        """Stop TEC"""
        self.tec_enabled = False
        self.log("TEC stopped")
        return True

    def startupCamera(self, addrs=None, **kwargs):
        """Manual startup"""
        return self.autoStartup()

    def shutdownCamera(self, addrs=None, **kwargs):
        """Manual shutdown"""
        return self.autoShutdown()

    # Required abstract methods
    def tecGetSetpoint(self) -> float:
        """Get current TEC setpoint"""
        return self.tec_setpoint

    def tecGetTemp(self) -> float:
        """Get current TEC temperature"""
        return self.tec_temp

    def tecGetEnabled(self) -> bool:
        """Check if TEC is enabled"""
        return self.tec_enabled

    def getExposureTime(self) -> float:
        """Get current exposure time"""
        return self.exposure_time


if __name__ == "__main__":
    create_camera_daemon(FakeCameraInterface, "FakeCamera")
