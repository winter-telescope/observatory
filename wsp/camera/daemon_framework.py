#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
camera_daemon_framework.py

Framework for camera-specific daemon implementations.
Each camera type will have its own daemon that inherits from this framework.
"""

import getopt
import logging
import os
import signal
import subprocess
import sys
from abc import abstractmethod
from datetime import datetime

import Pyro5.server  # type: ignore
import pytz
import yaml
from PyQt5 import QtCore

from wsp.alerts.alert_handler import AlertHandler
from wsp.camera.camera_command_decorators import daemon_command
from wsp.camera.state import CameraState
from wsp.daemon.daemon_utils import PyroDaemon
from wsp.utils.logging_setup import setup_logger
from wsp.utils.paths import CONFIG_PATH, CREDENTIALS_DIR, WSP_PATH


class ExposureConfig:
    """Container for exposure configuration"""

    def __init__(self, imdir, imname, imtype, exposure_time, mode, metadata):
        self.imdir = imdir
        self.imname = imname
        self.imtype = imtype
        self.exposure_time = exposure_time
        self.mode = mode
        self.metadata = metadata


class BaseCameraInterface(QtCore.QObject):
    """
    Base interface for camera hardware communication.
    Camera-specific implementations should inherit from this.
    """

    newStatus = QtCore.pyqtSignal(object)
    stateChanged = QtCore.pyqtSignal(str)  # Emit state changes

    # Signals for tracking if a command has been sent, passed, timed out, or is active
    resetCommandPassSignal = QtCore.pyqtSignal(int)
    resetCommandTimeoutSignal = QtCore.pyqtSignal(float)
    resetCommandActiveSignal = QtCore.pyqtSignal(int)

    def __init__(
        self,
        name,
        config,
        logger=None,
        verbose=False,
        post_images_to_slack=False,
        alertHandler=None,
    ):
        super().__init__()

        self.name = name
        self.config = config
        self.logger = logger
        self.verbose = verbose
        self.post_images_to_slack = post_images_to_slack
        self.alertHandler = alertHandler

        # Signals for managing command tracking/timeouts

        # Command tracking attributes
        self.command_active = 0
        self.command_pass = 0
        self.command_timeout = 0.0
        self.command_sent_timestamp = 0.0
        self.command_elapsed_dt = 0.0

        # Connect signals to slots
        # connect state changed to update the camera state

        # Timeout check timer
        self.timeout_timer = QtCore.QTimer()
        self.timeout_timer.timeout.connect(self.check_command_timeout)
        self.timeout_timer.start(100)  # Check every 100ms

        # State management
        self.state = {
            "camera_state": CameraState.OFF.value,
            "connected": False,
            "timestamp": datetime.utcnow().timestamp(),
        }

        # Hardware connection status
        self.connected = False

        # Local timezone for timestamps
        self.local_timezone = pytz.timezone("America/Los_Angeles")

        # Set up hardware connection
        self.log(f"Setting up connection to camera: {self.name}")
        self.setup_connection()

        # Start polling timer
        self.log(f"Starting polling for camera: {self.name}")
        self.setup_polling()

    @property
    def _camera_state(self):
        """Compatibility property for decorators"""
        return CameraState(self.state.get("camera_state", "OFF"))

    def check_command_timeout(self):
        """Check if active command has timed out"""
        if self.command_active:
            elapsed = datetime.utcnow().timestamp() - self.command_sent_timestamp
            self.command_elapsed_dt = elapsed

            if elapsed > self.command_timeout:
                self.log(f"Command timeout after {elapsed:.1f}s", level=logging.ERROR)
                self.command_active = 0
                self.command_pass = 0
                self.update_camera_state(CameraState.ERROR)
                self.state.update(
                    {
                        "command_active": 0,
                        "command_pass": 0,
                        "command_timeout_occurred": True,
                        "command_elapsed_dt": elapsed,
                    }
                )

    def resetCommandActive(self, val):
        # reset the command active value to val (0 or 1), and update state
        # self.log(f'running resetCommandActive: {val}')
        self.command_active = val
        self.state.update({"command_active": val})

    def resetCommandPass(self, val):
        # reset the command pass value to val (0 or 1), and update state
        # self.log(f'running resetCommandPass: {val}')
        self.command_pass = val
        self.state.update({"command_pass": val})

    def resetCommandTimeout(self, dt):
        # this resets the timestamp of the last image send, and the amount of time
        # that is allocated before triggering a command timeout
        self.log(f"running resetCommandTimeout: {dt}")
        self.command_timeout = dt
        self.command_sent_timestamp = datetime.now(datetime.timezone.utc).timestamp()
        self.command_elapsed_dt = 0.0
        self.state.update(
            {
                "command_timeout": self.command_timeout,
                "command_sent_timestamp": self.command_sent_timestamp,
                "command_elapsed_dt": self.command_elapsed_dt,
            }
        )

    def setup_polling(self):
        """Set up periodic status polling"""
        self.pollTimer = QtCore.QTimer()
        self.pollTimer.timeout.connect(self.pollStatus)
        self.pollTimer.start(1000)  # Poll every second

    def log(self, msg, level=logging.INFO):
        msg = f"{self.name}_interface: {msg}"
        if self.logger is None:
            print(msg)
        else:
            self.logger.log(level=level, msg=msg)

    def announce(self, msg, group=None):
        # Post to winter_observatory slack channel (if alert handler exits) and to log
        self.log(msg)
        if self.alertHandler is not None:
            self.alertHandler.slack_log(f":camera: {msg}", group=group)

    def alert_error(self, msg, group=None):
        """Send error alert"""
        self.log(msg, level=logging.ERROR)
        if self.alertHandler is not None:
            self.alertHandler.slack_log(
                f":warning: {self.name} ERROR: {msg}", group=group
            )

    def update_camera_state(self, new_state: CameraState):
        """Update camera state and emit signal"""
        if self.state["camera_state"] != new_state.value:
            self.state["camera_state"] = new_state.value
            self.stateChanged.emit(new_state.value)
            self.log(f"State changed to: {new_state.value}")

    @abstractmethod
    def setup_connection(self):
        """Set up the connection to the camera hardware"""
        pass

    @abstractmethod
    def pollCameraStatus(self):
        """Poll the camera hardware for status updates"""
        pass

    def pollStatus(self):
        """Poll camera status - must emit newStatus signal"""
        self.state["timestamp"] = datetime.utcnow().timestamp()
        self.state["connected"] = self.connected

        self.pollCameraStatus()

        # Required methods to be polled
        self.tec_setpoint = self.tecGetSetpoint()
        self.tec_temp = self.tecGetTemp()
        self.tec_enabled = self.tecGetEnabled()
        self.exposure_time = self.getExposureTime()
        self.tec_voltage = self.tecGetVoltage()
        self.tec_current = self.tecGetCurrent()
        self.tec_percentage = self.tecGetPercentage()

        if self.command_active:
            self.check_if_command_passed()

        # if startup is requested, see if it is complete
        # if self._camera_state == CameraState.STARTUP_REQUESTED:

        # Update state
        self.state.update(
            {
                # Basic connection parameters
                "timestamp": datetime.utcnow().timestamp(),
                "connected": self.connected,
                # Image parameters
                "exptime": self.exposure_time,
                # TEC parameters
                "tec_temp": self.tec_temp,
                "tec_enabled": self.tec_enabled,
                "tec_setpoint": self.tec_setpoint,
                "tec_voltage": self.tec_voltage,
                "tec_current": self.tec_current,
                "tec_percentage": self.tec_percentage,
            }
        )

        # Emit the new status
        self.newStatus.emit(self.state)

    # === Required API Methods ===

    @abstractmethod
    def autoStartup(self):
        """Auto startup sequence"""
        pass

    @abstractmethod
    def autoShutdown(self):
        """Auto shutdown sequence"""
        pass

    @abstractmethod
    def _check_if_startup_complete(self):
        """Check if startup sequence is complete"""
        pass

    @abstractmethod
    def _check_if_ready_to_shutdown(self):
        """Check if ready to shutdown"""
        pass

    @abstractmethod
    def _complete_shutdown(self):
        """Complete shutdown sequence"""
        pass

    @abstractmethod
    def setExposure(self, exptime, addrs=None):
        """Set exposure time"""
        pass

    def getDefaultImageDirectory(self) -> str:
        """Get default image directory"""
        return os.path.join(
            os.path.expanduser("~"), "data", "images", datetime.now().strftime("%Y%m%d")
        )

    def getImageFilename(self, imname) -> str:
        """Get default image filename
        Can be overridden by specific camera implementations"""
        if not imname:
            return f"{self.name}_{datetime.now(datetime.timezone.utc).strftime('%Y%m%d-%H%M%S-%f')[:-3]}"
        return imname

    def getFileExtension(self):
        """Get default file extension for images
        Can be overridden by specific camera implementations"""
        # Default to FITS format
        return ".fits"

    def makeImageFilepath(self, imdir, imname, imtype):
        """Construct image file path"""
        if not imname:
            imname = self.getImageFilename(imname)

        if not imtype:
            imtype = "TEST"

        if not imdir:
            imdir = self.getDefaultImageDirectory()

        if not os.path.exists(imdir):
            os.makedirs(imdir)

        return os.path.join(imdir, imname + self.getFileExtension())

    def getDefaultSymLinkPath(self):
        """Get default symbolic link path for the last image taken"""
        return os.path.join(os.path.expanduser("~"), "data", "last_image.lnk")

    def makeSymLink_lastImage(self, image_path):
        # make a symbolic link to the last image taken: self.lastfilename

        last_image_link_path = self.getDefaultSymLinkPath()

        try:
            os.symlink(image_path, last_image_link_path)
        except FileExistsError:
            self.log("deleting existing symbolic link to last image taken")
            os.remove(last_image_link_path)
            os.symlink(image_path, last_image_link_path)

    @abstractmethod
    def doExposure(self, imdir, imname, imtype, mode, metadata, addrs=None):
        """Execute exposure
        Call this method first with super().doExposure(...) to set up the exposure
        then call camera-specific methods to finalize the exposure setup"""
        self.state.update({"doing_exposure": True})
        self.update_camera_state(CameraState.EXPOSING)
        self.imdir = imdir
        self.imname = imname
        self.imtype = imtype
        self.mode = mode
        self.metadata = metadata
        self.addrs = addrs
        self.lastfilename = self.makeImageFilepath(imdir, imname, imtype)

        # This is where the camera-specific implementation should handle the exposure
        # For example, it might start a timer or initiate hardware communication

    # helper method for closing out exposure, making symbolic links, etc.
    def _exposure_complete(self, imdir, imname):
        """Finalize exposure by creating symbolic link to last image"""

        self.makeSymLink_lastImage(self.lastfilename)
        self.update_camera_state(CameraState.READY)
        self.log(f"Exposure complete: {imname} at {imdir}")

        # Post the image to slack if configured
        if self.post_images_to_slack and self.alertHandler:
            try:
                plotterpath = os.path.join(WSP_PATH, "plotLastImg.py")
                subprocess.Popen(args=["python", plotterpath])
                self.announce(f"New image: {imname}")
            except Exception as e:
                self.log(f"Failed to post image to Slack: {e}", level=logging.ERROR)

    @abstractmethod
    def tecSetSetpoint(self, temp, addrs=None):
        """Set TEC temperature setpoint"""
        pass

    @abstractmethod
    def tecStart(self, addrs=None):
        """Start TEC control"""
        pass

    @abstractmethod
    def tecStop(self, addrs=None):
        """Stop TEC control"""
        pass

    @abstractmethod
    def startupCamera(self, addrs=None):
        """Manual startup"""
        pass

    @abstractmethod
    def shutdownCamera(self, addrs=None):
        """Manual shutdown"""
        pass

    @abstractmethod
    def tecGetSetpoint(self) -> float:
        """Get current TEC setpoint"""
        return 0.0

    @abstractmethod
    def tecGetVoltage(self) -> float:
        """Get current TEC voltage"""
        return 0.0

    @abstractmethod
    def tecGetCurrent(self) -> float:
        """Get current TEC current"""
        return 0.0

    @abstractmethod
    def tecGetPercentage(self) -> float:
        """Get current TEC power percentage"""
        return 0.0

    @abstractmethod
    def tecGetTemp(self) -> float:
        """Get current TEC temperature"""
        return 0.0

    @abstractmethod
    def tecGetEnabled(self) -> bool:
        """Check if TEC is enabled"""
        return False

    @abstractmethod
    def getExposureTime(self) -> float:
        """Get current exposure time"""
        return 0.0


class CameraDaemonInterface:
    """
    Pyro daemon interface that wraps the camera interface.
    This is what gets exposed via Pyro5.
    """

    def __init__(self, camera_interface: BaseCameraInterface):
        self.camera = camera_interface
        self.logger = camera_interface.logger

        # Connect to camera signals
        self.camera.newStatus.connect(self._update_status)
        self._last_status = {}

    def _update_status(self, status):
        """Cache the latest status from the camera"""
        self._last_status = status.copy()

    def log(self, msg, level=logging.INFO):
        if self.logger:
            self.logger.log(level=level, msg=f"daemon_interface: {msg}")
        else:
            print(f"daemon_interface: {msg}")

    # === Pyro-exposed methods with immediate state changes ===

    @Pyro5.server.expose
    def getStatus(self):
        """Return current camera status"""
        return self._last_status

    @Pyro5.server.expose
    @daemon_command(initial_state=CameraState.STARTUP_REQUESTED)
    def autoStartup(self):
        """Auto startup sequence"""
        self.log("Starting auto startup")
        self.camera.autoStartup()

    @Pyro5.server.expose
    @daemon_command(initial_state=CameraState.SHUTDOWN_REQUESTED)
    def autoShutdown(self):
        """Auto shutdown sequence"""
        self.log("Starting auto shutdown")
        self.camera.autoShutdown()

    @Pyro5.server.expose
    @daemon_command(initial_state=CameraState.SETTING_PARAMETERS)
    def setExposure(self, exptime, addrs=None):
        """Set exposure time"""
        self.camera.setExposure(exptime, addrs)
        # After setting, return to READY
        self.camera.update_camera_state(CameraState.READY)

    @Pyro5.server.expose
    @daemon_command(initial_state=CameraState.EXPOSING)
    def doExposure(self, imdir, imname, imtype, mode, metadata, addrs=None):
        """Execute exposure with immediate state update"""
        self.log(f"Starting exposure: {imname}")
        self.camera.doExposure(imdir, imname, imtype, mode, metadata, addrs)

    @Pyro5.server.expose
    @daemon_command(initial_state=CameraState.SETTING_PARAMETERS)
    def tecSetSetpoint(self, temp, addrs=None):
        """Set TEC temperature"""
        self.camera.tecSetSetpoint(temp, addrs)
        # Return to READY after setting
        self.camera.update_camera_state(CameraState.READY)

    @Pyro5.server.expose
    @daemon_command(initial_state=CameraState.SETTING_PARAMETERS)
    def tecStart(self, addrs=None):
        """Start TEC"""
        self.camera.tecStart(addrs)
        # Return to READY after starting
        self.camera.update_camera_state(CameraState.READY)

    @Pyro5.server.expose
    @daemon_command(initial_state=CameraState.SETTING_PARAMETERS)
    def tecStop(self, addrs=None):
        """Stop TEC"""
        self.camera.tecStop(addrs)
        # Return to READY after stopping
        self.camera.update_camera_state(CameraState.READY)

    @Pyro5.server.expose
    @daemon_command(initial_state=CameraState.STARTUP_REQUESTED)
    def startupCamera(self, addrs=None):
        """Manual startup"""
        self.camera.startupCamera(addrs)

    @Pyro5.server.expose
    @daemon_command(initial_state=CameraState.SHUTDOWN_REQUESTED)
    def shutdownCamera(self, addrs=None):
        """Manual shutdown"""
        self.camera.shutdownCamera(addrs)

    @Pyro5.server.expose
    def getDefaultImageDirectory(self):
        """Get default image directory"""
        return self.camera.getDefaultImageDirectory()

    @Pyro5.server.expose
    def killCameraDaemon(self):
        """Kill the daemon"""
        self.log("Daemon kill requested")
        QtCore.QCoreApplication.quit()


class CameraDaemonApp(QtCore.QObject):
    """
    Main application class for camera daemons.
    Handles Qt event loop and Pyro daemon setup.
    """

    def __init__(
        self,
        camera_class,
        daemon_name,
        config,
        ns_host=None,
        logger=None,
        verbose=False,
        alertHandler=None,
        post_images_to_slack=False,
    ):
        super().__init__()

        self.daemon_name = daemon_name
        self.config = config
        self.ns_host = ns_host
        self.logger = logger
        self.verbose = verbose
        self.alertHandler = alertHandler
        self.post_images_to_slack = post_images_to_slack

        # Create camera interface instance
        self.camera_interface = camera_class(
            name=daemon_name,
            config=config,
            logger=logger,
            verbose=verbose,
            alertHandler=alertHandler,
            post_images_to_slack=post_images_to_slack,
        )

        # Create daemon interface wrapper
        self.daemon_interface = CameraDaemonInterface(self.camera_interface)

        # Set up Pyro daemon
        self.pyro_thread = PyroDaemon(
            obj=self.daemon_interface, name=daemon_name, ns_host=ns_host
        )
        self.pyro_thread.start()

        self.log(f"Started {daemon_name} daemon")

    def log(self, msg):
        if self.logger:
            self.logger.info(f"{self.daemon_name}: {msg}")
        else:
            print(f"{self.daemon_name}: {msg}")


def create_camera_daemon(camera_class, daemon_name):
    """
    Factory function to create camera daemon applications.

    Usage:
        # For fake camera:
        main = create_camera_daemon(FakeCameraInterface, "FakeCamera")

        # For WINTER camera:
        main = create_camera_daemon(WINTERCameraInterface, "WINTERCamera")
    """

    def sigint_handler(*args):
        """Handler for the SIGINT signal."""
        sys.stderr.write("\r")
        print("\nCaught SIGINT, shutting down...")

        # explicitly kill any threads
        try:
            print("No internal threads to kill.")
        except Exception as e:
            print(f"Error stopping camera thread: {e}")
        finally:
            print("Killing application")
            QtCore.QCoreApplication.quit()

    # Parse command line arguments
    argumentList = sys.argv[1:]
    verbose = False
    doLogging = True
    ns_host = "192.168.1.10"
    slack_alerts = True
    post_images_to_slack = False

    options = "vpn:"
    long_options = ["verbose", "print", "ns_host=", "post_images"]

    try:
        arguments, values = getopt.getopt(argumentList, options, long_options)
        for currentArgument, currentValue in arguments:
            if currentArgument in ("-v", "--verbose"):
                verbose = True
            elif currentArgument in ("-p", "--print"):
                doLogging = False
            elif currentArgument in ("-n", "--ns_host"):
                ns_host = currentValue
            elif currentArgument in ("-s", "--slack_alerts"):
                slack_alerts = True
            elif currentArgument in ("--post_images"):
                post_images_to_slack = True
    except getopt.error as err:
        print(str(err))
        sys.exit(1)

    # Load configuration
    config = yaml.load(open(CONFIG_PATH), Loader=yaml.FullLoader)

    # Set up Qt application
    app = QtCore.QCoreApplication(sys.argv)

    # Set up logging
    if doLogging:
        logger = setup_logger(os.path.expanduser("~"), config)
    else:
        logger = None

    if slack_alerts:
        auth_config_file = os.path.join(CREDENTIALS_DIR, "authentication.yaml")
        user_config_file = os.path.join(CREDENTIALS_DIR, "alert_list.yaml")
        alert_config_file = os.path.join(WSP_PATH, "config", "alert_config.yaml")
        try:
            auth_config = yaml.load(open(auth_config_file), Loader=yaml.FullLoader)
            user_config = yaml.load(open(user_config_file), Loader=yaml.FullLoader)
            alert_config = yaml.load(open(alert_config_file), Loader=yaml.FullLoader)

            alertHandler = AlertHandler(user_config, alert_config, auth_config)
        except Exception as e:
            print(f"Error loading Slack credentials: {e}")
            alertHandler = None
    else:
        alertHandler = None

    # test the alert handler
    if alertHandler is not None:
        alertHandler.slack_log(":camera: WINTER Camera Daemon Started")

    # Create daemon
    main = CameraDaemonApp(
        camera_class=camera_class,
        daemon_name=daemon_name,
        config=config,
        ns_host=ns_host,
        logger=logger,
        verbose=verbose,
        alertHandler=alertHandler,
        post_images_to_slack=post_images_to_slack,
    )

    # Set up signal handling
    signal.signal(signal.SIGINT, sigint_handler)

    # Timer to catch SIGINT
    timer = QtCore.QTimer()
    timer.start(500)
    timer.timeout.connect(lambda: None)

    # Run event loop
    sys.exit(app.exec_())
