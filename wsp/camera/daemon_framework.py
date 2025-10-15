# camera_daemon_framework.py
"""
Framework for camera-specific daemon implementations.
Each camera type will have its own daemon that inherits from this framework.
"""

import getopt
import logging
import os
import shutil
import signal
import subprocess
import sys
import traceback
from abc import abstractmethod
from datetime import datetime
from pathlib import Path

import Pyro5.server  # type: ignore
import pytz
import yaml
from PyQt5 import QtCore

from wsp.alerts.alert_handler import AlertHandler
from wsp.camera.camera_command_decorators import async_camera_command
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


class CameraCommandWorker(QtCore.QObject):
    """Worker that executes camera commands in a separate thread"""

    # Signals
    commandStarted = QtCore.pyqtSignal(str)  # command name
    commandCompleted = QtCore.pyqtSignal(bool, str)  # success, message
    commandError = QtCore.pyqtSignal(str, str)  # error message, traceback

    def __init__(self, logger=None):
        super().__init__()
        self.current_command = None
        self.current_args = None
        self.current_kwargs = None
        self.stop_requested = False
        self.command_name = None
        self.logger = logger

    def log(self, msg, level=logging.INFO):
        if self.logger:
            self.logger.log(level=level, msg=f"command_worker: {msg}")
        else:
            print(f"command_worker: {msg}")

    @QtCore.pyqtSlot(object, str, object, object)
    def execute_command(self, command_func, command_name, args, kwargs):
        """Execute a command - called via signal from main thread"""
        self.current_command = command_func
        self.current_args = args or ()
        self.current_kwargs = kwargs or {}
        self.command_name = command_name

        self.stop_requested = False

        self.commandStarted.emit(command_name)

        try:
            # Check for stop before starting
            if self.stop_requested:
                self.commandError.emit(
                    f"{command_name}: Stopped before execution",
                    "",  # No traceback for manual stop
                )
                return

            # Execute the command
            result = self.current_command(*self.current_args, **self.current_kwargs)

            # Check if stop was requested during execution
            if self.stop_requested:
                self.commandError.emit(
                    f"{command_name}: Stopped during execution",
                    "",  # No traceback for manual stop
                )
            elif result is False:
                self.commandError.emit(
                    f"{command_name}: Command returned False",
                    "",  # No traceback for False return
                )
            else:
                self.commandCompleted.emit(
                    True, f"{command_name}: Completed successfully"
                )

        except Exception as e:
            # Capture the full traceback
            tb_str = traceback.format_exc()
            self.commandError.emit(f"{command_name}: Exception - {str(e)}", tb_str)
        finally:
            self.current_command = None
            self.current_args = None
            self.current_kwargs = None
            self.command_name = None

    @QtCore.pyqtSlot()
    def stop_command(self):
        """Request to stop the current command"""
        self.stop_requested = True
        self.log(f"Stop requested for command: {self.command_name}")


class BaseCameraInterface(QtCore.QObject):
    """
    Base interface for camera hardware communication with single-threaded async execution.
    """

    newStatus = QtCore.pyqtSignal(object)
    stateChanged = QtCore.pyqtSignal(str)

    # Signals for command execution
    executeCommand = QtCore.pyqtSignal(object, str, object, object)
    stopCommand = QtCore.pyqtSignal()

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

        # Command tracking attributes
        self.command_active = 0
        self.command_pass = 0
        self.command_timeout = 0.0
        self.command_sent_timestamp = 0.0
        self.command_elapsed_dt = 0.0

        # Set up persistent worker thread
        self.command_thread = QtCore.QThread()
        self.command_worker = CameraCommandWorker(logger=logger)
        self.command_worker.moveToThread(self.command_thread)

        # Connect signals
        self.executeCommand.connect(self.command_worker.execute_command)
        self.stopCommand.connect(self.command_worker.stop_command)
        self.command_worker.commandStarted.connect(self._on_command_started)
        self.command_worker.commandCompleted.connect(self._on_command_completed)
        self.command_worker.commandError.connect(self._on_command_error)

        # Start the worker thread
        self.command_thread.start()

        # Track command execution
        self.command_running = False
        self.current_command_name = None
        self.pending_completion_state = None
        self.pending_command_completion = None

        # State management
        self.state = {
            "camera_state": CameraState.OFF.value,
            "connected": False,
            "timestamp": datetime.utcnow().timestamp(),
            "command_running": False,
            "current_command": None,
        }

        # Hardware connection status
        self.connected = False

        # Local timezone
        self.local_timezone = pytz.timezone("America/Los_Angeles")

        # Timeout check timer
        self.timeout_timer = QtCore.QTimer()
        self.timeout_timer.timeout.connect(self.check_command_timeout)
        self.timeout_timer.start(100)  # Check every 100ms

        # Set up hardware connection
        self.log(f"Setting up connection to camera: {self.name}")
        self.setup_connection()

        # Start polling timer
        self.log(f"Starting polling for camera: {self.name}")
        self.setup_polling()

    def __del__(self):
        """Clean up the worker thread on deletion"""
        if hasattr(self, "command_thread"):
            self.command_thread.quit()
            if not self.command_thread.wait(5000):  # Wait up to 5 seconds
                self.log("Force terminating worker thread", level=logging.WARNING)
                self.command_thread.terminate()

    @property
    def _camera_state(self):
        """Compatibility property for decorators"""
        return CameraState(self.state.get("camera_state", "OFF"))

    def execute_async_command(self, command_func, command_name, *args, **kwargs):
        """
        Execute a command asynchronously in the worker thread.
        Returns False if another command is already running.
        """
        if self.command_running:
            self.log(
                f"Cannot execute {command_name}: {self.current_command_name} is already running",
                level=logging.WARNING,
            )
            return False

        # Set command tracking state
        self.command_running = True
        self.current_command_name = command_name
        self.command_active = 1
        self.command_sent_timestamp = datetime.utcnow().timestamp()
        self.command_elapsed_dt = 0.0

        # Update state
        self.state.update(
            {
                "command_running": True,
                "current_command": command_name,
                "command_active": 1,
                "command_sent_timestamp": self.command_sent_timestamp,
            }
        )

        # Emit signal to execute command in worker thread
        self.executeCommand.emit(command_func, command_name, args, kwargs)

        self.log(f"Queued async command: {command_name}")
        return True

    def stop_current_command(self):
        """Stop the currently executing command"""
        if self.command_running:
            self.log(f"Requesting stop for command: {self.current_command_name}")
            self.stopCommand.emit()
            return True
        else:
            self.log("No command currently running to stop")
            return False

    def _on_command_started(self, command_name):
        """Handle command start notification"""
        self.log(f"Command started: {command_name}")
        # State already set by decorator's initial_state

    def _on_command_completed(self, success, message):
        """Handle command completion"""
        self.log(f"Command completed: {message}")

        # Update tracking state
        self.command_running = False
        self.command_active = 0
        self.command_pass = 1 if success else 0
        command_name = self.current_command_name
        self.current_command_name = None

        # Update state dict
        self.state.update(
            {
                "command_running": False,
                "current_command": None,
                "command_active": 0,
                "command_pass": self.command_pass,
                "last_command": command_name,
                "last_command_success": success,
            }
        )

        # Check if this command has pending completion
        if success and self.pending_command_completion:
            # Command succeeded but needs completion monitoring
            # Stay in the current state (initial_state) until conditions are met
            self.log(f"Command {command_name} monitoring for completion conditions")
            # Don't change state here - let polling handle it
        elif success and self.pending_completion_state:
            # Normal completion - set state immediately
            self.update_camera_state(self.pending_completion_state)
            self.pending_completion_state = None
        elif success:
            # Default to READY
            self.update_camera_state(CameraState.READY)

    def _on_command_error(self, error_msg, traceback_str=""):
        """Handle command error with optional traceback"""
        self.log(f"Command error: {error_msg}", level=logging.ERROR)

        # Log the full traceback if available
        if traceback_str:
            self.log("Full traceback:", level=logging.ERROR)
            # Split and log each line of the traceback for better readability
            for line in traceback_str.split("\n"):
                if line.strip():  # Skip empty lines
                    self.log(line, level=logging.ERROR)

        # Update tracking state
        self.command_running = False
        self.command_active = 0
        self.command_pass = 0
        command_name = self.current_command_name
        self.current_command_name = None
        self.pending_completion_state = None

        # Update state dict - include traceback in state for debugging
        self.state.update(
            {
                "command_running": False,
                "current_command": None,
                "command_active": 0,
                "command_pass": 0,
                "last_command": command_name,
                "last_command_error": error_msg,
                "last_command_traceback": traceback_str,  # Store for debugging
            }
        )

        # Set error state
        self.update_camera_state(CameraState.ERROR)

    def check_command_timeout(self):
        """Check if active command has timed out"""
        if self.command_active and self.command_running:
            elapsed = datetime.utcnow().timestamp() - self.command_sent_timestamp
            self.command_elapsed_dt = elapsed

            if elapsed > self.command_timeout:
                self.log(
                    f"Command timeout after {elapsed:.1f}s (limit: {self.command_timeout}s)",
                    level=logging.ERROR,
                )

                # Request stop of the current command
                self.stop_current_command()

                # Force cleanup after a short delay
                QtCore.QTimer.singleShot(1000, self._force_timeout_cleanup)

    def _force_timeout_cleanup(self):
        """Force cleanup after timeout"""
        if self.command_running:
            self.log("Forcing timeout cleanup", level=logging.WARNING)

            # Reset command state
            self.command_running = False
            self.command_active = 0
            self.command_pass = 0
            command_name = self.current_command_name
            self.current_command_name = None
            self.pending_completion_state = None

            self.update_camera_state(CameraState.ERROR)
            self.state.update(
                {
                    "command_running": False,
                    "current_command": None,
                    "command_active": 0,
                    "command_pass": 0,
                    "command_timeout_occurred": True,
                    "command_elapsed_dt": self.command_elapsed_dt,
                    "last_command": command_name,
                    "last_command_error": "Timeout",
                }
            )

    def log(self, msg, level=logging.INFO):
        msg = f"{self.name}_interface: {msg}"
        if self.logger is None:
            print(msg)
        else:
            self.logger.log(level=level, msg=msg)

    def announce(self, msg, group=None):
        self.log(msg)
        if self.alertHandler is not None:
            self.alertHandler.slack_log(f":camera: {msg}", group=group)

    def alert_error(self, msg, group=None):
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

    def setup_polling(self):
        """Set up periodic status polling"""
        self.pollTimer = QtCore.QTimer()
        self.pollTimer.timeout.connect(self.pollStatus)
        self.pollTimer.start(1000)  # Poll every second

    def pollStatus(self):
        """Enhanced polling that checks completion conditions"""
        self.state["timestamp"] = datetime.utcnow().timestamp()
        self.state["connected"] = self.connected

        # Poll camera-specific status
        self.pollCameraStatus()

        # Poll required values
        self.tec_setpoint = self.tecGetSetpoint()
        self.tec_temp = self.tecGetTemp()
        self.tec_enabled = self.tecGetEnabled()
        self.exposure_time = self.getExposureTime()
        self.tec_voltage = self.tecGetVoltage()
        self.tec_current = self.tecGetCurrent()
        self.tec_percentage = self.tecGetPercentage()
        self.tec_steady = self.tecGetSteadyStatus()

        # Check pending command completion
        if self.pending_command_completion:
            self._check_pending_completion()

        # Update state
        self.state.update(
            {
                "timestamp": datetime.utcnow().timestamp(),
                "connected": self.connected,
                "exptime": self.exposure_time,
                "tec_temp": self.tec_temp,
                "tec_enabled": self.tec_enabled,
                "tec_setpoint": self.tec_setpoint,
                "tec_voltage": self.tec_voltage,
                "tec_current": self.tec_current,
                "tec_percentage": self.tec_percentage,
                "tec_steady": self.tec_steady,
                "command_elapsed_dt": (
                    self.command_elapsed_dt if self.command_running else 0
                ),
                "pending_completion": self.pending_command_completion is not None,
            }
        )

        self.update_camera_state_info()

        # Emit the new status
        self.newStatus.emit(self.state)

    def _check_pending_completion(self):
        """Check if pending command has completed its conditions"""
        if not self.pending_command_completion:
            return

        command = self.pending_command_completion["command"]

        # Dispatch to command-specific completion checkers
        completed = False

        if command == "autoStartup":
            completed = self._check_startup_complete()
        elif command == "autoShutdown":
            completed = self._check_shutdown_complete()
        elif command == "tecSetSetpoint":
            completed = self._check_tec_setpoint_complete()
        elif command == "doExposure":
            completed = self._check_exposure_complete()
        elif command == "set_exposure":
            completed = self._check_set_exposure_complete()
        # Add more completion checkers as n`eeded

        if completed:
            # Completion conditions met!
            completion_state = self.pending_command_completion["completion_state"]
            self.log(f"Command {command} completion conditions met")
            self.update_camera_state(completion_state)
            self.pending_command_completion = None
        else:
            # Check timeout
            elapsed = (
                datetime.utcnow().timestamp()
                - self.pending_command_completion["start_time"]
            )
            if elapsed > self.command_timeout:
                self.log(
                    f"Command {command} timed out waiting for completion",
                    level=logging.ERROR,
                )
                self.update_camera_state(CameraState.ERROR)
                self.pending_command_completion = None
            # else: stay in current state and keep checking

    # === Required Methods ===
    # Command-specific completion checkers (to be overridden in implementations)
    @abstractmethod
    def _check_startup_complete(self) -> bool:
        """Override this to check if startup is complete"""
        return False

    @abstractmethod
    def _check_shutdown_complete(self) -> bool:
        """Override this to check if shutdown is complete"""
        return False

    @abstractmethod
    def _check_tec_setpoint_complete(self) -> bool:
        """Override this to check if TEC has reached setpoint"""
        return False

    @abstractmethod
    def _check_exposure_complete(self) -> bool:
        """Override this to check if exposure is complete"""
        return False

    @abstractmethod
    def _check_set_exposure_complete(self) -> bool:
        """Override this to check if set exposure is complete"""
        return False

    @abstractmethod
    def setup_connection(self):
        """Set up the connection to the camera hardware"""
        pass

    @abstractmethod
    def pollCameraStatus(self):
        """Poll the camera hardware for status updates"""
        pass

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
        return os.path.join(os.path.expanduser("~"), "data", "last_image.fits")

    def makeSymLink_lastImage(self, image_path):
        """Create/update a pointer to the latest image.
        - On POSIX: symlink.
        - On Windows: try symlink; if not permitted, fallback to hard link, then copy.
        """
        last_image_link_path = Path(self.getDefaultSymLinkPath())

        # remove existing link/file if present
        try:
            if last_image_link_path.exists() or last_image_link_path.is_symlink():
                last_image_link_path.unlink()
        except FileNotFoundError:
            pass

        try:
            os.symlink(image_path, last_image_link_path)
            self.log(f"Created symlink: {last_image_link_path} -> {image_path}")
        except OSError as e:
            if sys.platform.startswith("win") and getattr(e, "winerror", None) == 1314:
                # No symlink privilege, try hard link
                try:
                    os.link(image_path, last_image_link_path)
                    self.log(f"Created hard link for {last_image_link_path}")
                except OSError:
                    shutil.copy2(image_path, last_image_link_path)
                    self.log(f"Copied file to {last_image_link_path} (fallback)")
            else:
                # Other error, try hard link then copy
                try:
                    os.link(image_path, last_image_link_path)
                    self.log(f"Created hard link for {last_image_link_path}")
                except OSError:
                    shutil.copy2(image_path, last_image_link_path)
                    self.log(f"Copied file to {last_image_link_path} (fallback)")

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
    def tecGetSteadyStatus(self) -> bool:
        """Check if TEC temperature is steady"""
        return False

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

    def update_camera_state_info(self):
        """Update any camera-specific status info in the state dict"""
        pass


class CameraDaemonInterface:
    """
    Pyro daemon interface that wraps the camera interface.
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

    # === Pyro-exposed methods ===

    @Pyro5.server.expose
    def getStatus(self):
        """Return current camera status"""
        return self._last_status

    @Pyro5.server.expose
    def stopCurrentCommand(self):
        """Stop the currently executing command"""
        self.log("Stop command requested")
        return self.camera.stop_current_command()

    @Pyro5.server.expose
    def getCurrentCommand(self):
        """Get the name of the currently running command"""
        return self.camera.current_command_name

    @Pyro5.server.expose
    def isCommandRunning(self):
        """Check if a command is currently running"""
        return self.camera.command_running

    @Pyro5.server.expose
    def autoStartup(self):
        """Auto startup sequence"""
        self.log("Starting auto startup")
        return self.camera.autoStartup()

    @Pyro5.server.expose
    def autoShutdown(self):
        """Auto shutdown sequence"""
        self.log("Starting auto shutdown")
        return self.camera.autoShutdown()

    @Pyro5.server.expose
    def setExposure(self, exptime, addrs=None):
        """Set exposure time"""
        return self.camera.setExposure(exptime, addrs)

    @Pyro5.server.expose
    def doExposure(self, imdir, imname, imtype, mode, metadata, addrs=None):
        """Execute exposure"""
        self.log(f"Starting exposure: {imname}")
        return self.camera.doExposure(imdir, imname, imtype, mode, metadata, addrs)

    @Pyro5.server.expose
    def tecSetSetpoint(self, temp, addrs=None):
        """Set TEC temperature"""
        return self.camera.tecSetSetpoint(temp, addrs)

    @Pyro5.server.expose
    def tecStart(self, addrs=None):
        """Start TEC"""
        return self.camera.tecStart(addrs)

    @Pyro5.server.expose
    def tecStop(self, addrs=None):
        """Stop TEC"""
        return self.camera.tecStop(addrs)

    @Pyro5.server.expose
    def startupCamera(self, addrs=None):
        """Manual startup"""
        return self.camera.startupCamera(addrs)

    @Pyro5.server.expose
    def shutdownCamera(self, addrs=None):
        """Manual shutdown"""
        return self.camera.shutdownCamera(addrs)

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
