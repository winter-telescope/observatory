"""
camera.py

Integrated Camera System with standardized state management
Combines BaseCamera with CameraState for consistent state machine integration

Architecture:
1. Camera Hardware Daemon (vendor-specific)
2. Interface Daemon (standardizes communication, manages state)
3. BaseCamera Client (communicates with Interface Daemon)
4. State Machine (uses BaseCamera instances)
"""

import json
import logging
import os
import sys
import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from enum import Enum, auto
from typing import Any, Dict, Optional

import astropy.io.fits as fits
import Pyro5.core
import Pyro5.errors
import Pyro5.server
from PyQt5 import QtCore

from wsp.camera import fitsheader
from wsp.camera.state import CameraState


class BaseCamera(QtCore.QObject):
    """
    BaseCamera client that communicates with camera daemons.

    The daemon is now responsible for immediate state changes,
    so this class simply sends commands and polls for state updates.
    """

    # Qt signals
    newCommand = QtCore.pyqtSignal(object)
    imageSaved = QtCore.pyqtSignal()
    stateChanged = QtCore.pyqtSignal(str, str)  # old_state, new_state

    def __init__(
        self,
        base_directory,
        config,
        camname,
        daemon_pyro_name,
        ns_host=None,
        logger=None,
        verbose=False,
    ):
        """
        Initialize the base camera object.

        Parameters
        ----------
        base_directory : str
            Base directory path for the camera system
        config : dict
            Configuration dictionary
        camname : str
            Name identifier for this camera
        daemon_pyro_name : str
            Pyro daemon name for this camera
        ns_host : str, optional
            IP address of the Pyro name server
        logger : logging.Logger, optional
            Logger instance
        verbose : bool, optional
            Enable verbose logging
        """

        super(BaseCamera, self).__init__()

        # Core attributes
        self.base_directory = base_directory
        self.config = config
        self.camname = camname
        self.daemonname = daemon_pyro_name
        self.ns_host = ns_host
        self.logger = logger
        self.verbose = verbose

        # State management
        self.state = dict()
        self.hk_state = dict()
        self.remote_state = dict()
        self.connected = False
        self.hk_connected = False

        # Camera state tracking
        self._camera_state = CameraState.OFF
        self._previous_state = CameraState.OFF
        self._state_transition_time = datetime.utcnow()

        # Operation tracking for grace period
        self.active_operation_time = None
        self.state_sync_grace_period = 2.0  # seconds to wait for daemon state sync

        # Default value handling
        self.default = self.config.get("default_value", -999)

        # Image parameters
        self.imdir = ""
        self.imname = ""
        self.imstarttime = ""
        self.mode = None
        self.imtype = None
        self.exptime = 0.0

        # TEC parameters
        self.tec_temp = 0  # Current temperature of TEC
        self.tec_enabled = 0  # Is the TEC enabled?(0: OFF, 1: ON)
        self.tec_setpoint = 0.0  # Setpoint temperature for TEC
        self.tec_voltage = 0.0  # Voltage of TEC
        self.tec_current = 0.0  # Current of TEC
        self.tec_percentage = 0.0  # Percentage of TEC power

        # Backwards compatibility attributes
        self.timestamp = datetime.utcnow().timestamp()
        self.command_pass = False
        self.command_active = False
        self.doing_exposure = False
        self.is_connected = False
        self.command_timeout = 0.0
        self.command_sent_timestamp = 0.0
        self.command_elapsed_dt = 0.0
        self.autoShutdownRequested = False
        self.autoShutdownComplete = False
        self.autoStartupRequested = False
        self.autoStartupComplete = False

        # Connect signals and slots
        self.newCommand.connect(self.doCommand)

        # Initialize connections
        self.init_remote_object()
        self.update_state()

    def log(self, msg, level=logging.INFO):
        msg = f"{self.camname} local interface: {msg}"
        if self.logger is None:
            print(msg)
        else:
            self.logger.log(level=level, msg=msg)

    def doCommand(self, cmd_obj):
        """
        Execute command from signal.
        """
        cmd = cmd_obj.cmd
        args = cmd_obj.args
        kwargs = cmd_obj.kwargs

        try:
            getattr(self, cmd)(*args, **kwargs)
        except:
            pass

    @property
    def camera_state(self) -> CameraState:
        """Get current camera state"""
        return self._camera_state

    @camera_state.setter
    def camera_state(self, new_state: CameraState):
        """Set camera state and emit signal if changed"""
        if new_state != self._camera_state:
            old_state = self._camera_state
            self._previous_state = old_state
            self._camera_state = new_state
            self._state_transition_time = datetime.utcnow()
            self.stateChanged.emit(old_state.value, new_state.value)
            self.log(
                f"State changed: {self._state_transition_time}: {old_state.value} -> {new_state.value}"
            )
            # Update local state dict immediately
            self.state["camera_state"] = new_state.value

    def is_valid_state(self, state: CameraState) -> bool:
        """Check if the given state is a valid CameraState."""
        return isinstance(state, CameraState) and state in CameraState

    def _mark_operation_start(self):
        """Mark the start of an operation for grace period tracking"""
        self.active_operation_time = datetime.now(timezone.utc).timestamp()

    def init_remote_object(self):
        """Initialize connection to remote daemon"""
        try:
            if self.verbose:
                self.log(f"init_remote_object: trying to connect to {self.daemonname}")
            ns = Pyro5.core.locate_ns(host=self.ns_host)
            uri = ns.lookup(self.daemonname)
            self.remote_object = Pyro5.client.Proxy(uri)
            self.connected = True
            self.is_connected = True
        except Exception as e:
            self.connected = False
            self.is_connected = False
            if self.verbose:
                self.log(f"connection to remote object failed: {e}")

    def init_hk_state_object(self):
        """Initialize housekeeping state connection"""
        try:
            ns = Pyro5.core.locate_ns(host=self.ns_host)
            uri = ns.lookup("state")
            self.remote_hk_state_object = Pyro5.client.Proxy(uri)
            self.hk_connected = True
        except:
            self.hk_connected = False

    def update_hk_state(self):
        """Update housekeeping state"""
        if not self.hk_connected:
            self.init_hk_state_object()
        else:
            try:
                self.hk_state = self.remote_hk_state_object.GetStatus()
            except Exception as e:
                if self.verbose:
                    self.log(f"could not update remote housekeeping state: {e}")
                self.hk_connected = False

    def update_state(self):
        """Poll daemon for current state"""
        if not self.connected:
            if self.verbose:
                self.log(
                    f"self.connected = {self.connected}: try to init_remote_object again"
                )
            self.init_remote_object()

        if self.connected:
            try:
                self.remote_state = self.remote_object.getStatus()

                # Update camera state from remote BEFORE parsing
                remote_camera_state = self.remote_state.get("camera_state", "OFF")
                if self.verbose:
                    print(f"Remote camera state: {remote_camera_state}")

                try:
                    new_state = CameraState(remote_camera_state)
                    if self.is_valid_state(new_state):
                        # Check if we're within grace period
                        should_update = True

                        if self.active_operation_time:
                            time_since_operation = (
                                datetime.now(timezone.utc).timestamp()
                                - self.active_operation_time
                            )
                            if time_since_operation < self.state_sync_grace_period:
                                if self.verbose:
                                    self.log(
                                        f"Within grace period ({time_since_operation:.1f}s < "
                                        f"{self.state_sync_grace_period}s), not overwriting state"
                                    )
                                should_update = False
                            else:
                                # Grace period expired
                                self.active_operation_time = None

                        # Only update if we should
                        if should_update and new_state != self._camera_state:
                            self.camera_state = new_state

                    else:
                        self.log(
                            f"Invalid camera state received: {remote_camera_state}",
                            level=logging.ERROR,
                        )
                except ValueError:
                    self.log(
                        f"Unknown camera state from remote: {remote_camera_state}",
                        level=logging.ERROR,
                    )

                # Update backwards compatibility attributes from remote state
                self.timestamp = datetime.utcnow().timestamp()
                self.command_pass = self.remote_state.get("command_pass", False)
                self.command_active = self.remote_state.get("command_active", False)
                self.exptime = self.remote_state.get("exposure_time", 0.0)
                self.command_timeout = self.remote_state.get("command_timeout", 0.0)
                self.command_sent_timestamp = self.remote_state.get(
                    "command_sent_timestamp", 0.0
                )

                # Calculate elapsed time
                if self.command_sent_timestamp > 0:
                    self.command_elapsed_dt = (
                        self.timestamp - self.command_sent_timestamp
                    )
                else:
                    self.command_elapsed_dt = 0.0

                # Update exposure status based on camera state
                self.doing_exposure = self._camera_state in [
                    CameraState.EXPOSING,
                    CameraState.READING,
                ]

                # Update startup/shutdown flags based on state
                self.autoStartupRequested = (
                    self._camera_state == CameraState.STARTUP_REQUESTED
                )
                self.autoStartupComplete = (
                    self._previous_state == CameraState.STARTUP_REQUESTED
                    and self._camera_state == CameraState.READY
                )
                self.autoShutdownRequested = (
                    self._camera_state == CameraState.SHUTDOWN_REQUESTED
                )
                self.autoShutdownComplete = (
                    self._previous_state == CameraState.SHUTDOWN_REQUESTED
                    and self._camera_state == CameraState.OFF
                )

                # Now parse the rest of the state
                self.parse_state()

            except Exception as e:
                if self.verbose:
                    self.log(f"camera: could not update/parse remote state: {e}")
                self.connected = False
                self.is_connected = False
                self.camera_state = CameraState.ERROR

    def parse_state(self):
        """Parse state - must be implemented by subclasses"""
        # Base implementation with backwards compatibility attributes
        self.state.update(
            {
                "timestamp": self.timestamp,
                "camname": self.camname,
                "is_connected": self.is_connected,
                "camera_state": self.camera_state.value,
                "imdir": self.imdir,
                "imname": self.imname,
                "imstarttime": self.imstarttime,
                "imtype": self.imtype,
                "immode": self.mode,
                # TEC
                "tec_temp": self.tec_temp,
                "tec_enabled": self.tec_enabled,
                "tec_setpoint": self.tec_setpoint,
                "tec_voltage": self.tec_voltage,
                "tec_current": self.tec_current,
                "tec_percentage": self.tec_percentage,
                # Exposure
                "exptime": self.exptime,
                # Backwards compatibility entries
                # "command_pass": self.command_pass,
                # "command_active": self.command_active,
                # "doing_exposure": self.doing_exposure,
                # "command_timeout": self.command_timeout,
                # "command_sent_timestamp": self.command_sent_timestamp,
                # "command_elapsed_dt": self.command_elapsed_dt,
                # "autoShutdownRequested": self.autoShutdownRequested,
                # "autoShutdownComplete": self.autoShutdownComplete,
                # "autoStartupRequested": self.autoStartupRequested,
                # "autoStartupComplete": self.autoStartupComplete,
            }
        )

    def validate_mode(self, mode: Optional[str], **kwargs) -> str:
        """Validate readout mode - should be implemented by subclasses"""
        pass

    def getFITSheader(self):
        """Get FITS header"""
        try:
            header = fitsheader.GetHeader(
                self.config, self.hk_state, self.state, logger=self.logger
            )
        except Exception as e:
            self.log(f"could not build default header: {e}")
            header = []
        self.header = header
        return self.header

    def print_state(self):
        """Print current state for debugging"""
        self.update_state()
        print(json.dumps(self.state, indent=2))

    # === Simplified API Methods - daemon handles state changes ===

    def setExposure(self, exptime, **kwargs):
        """Set exposure time

        Parameters
        ----------
        exptime : float
            Exposure time in seconds
        **kwargs
            Additional camera-specific parameters
        """
        self._mark_operation_start()
        # Don't update local exposure time, let it come from the server because sometimes it is slow
        try:
            self.camera_state = CameraState.SETTING_PARAMETERS
            self.remote_object.setExposure(exptime, **kwargs)
            self.camera_state = CameraState.READY
        except Exception as e:
            self.active_operation_time = None
            self.camera_state = CameraState.ERROR
            print(f"Error setting exposure: {e}")
            raise

    def doExposure(self, imdir=None, imname=None, imtype=None, mode=None, **kwargs):
        """Execute exposure"""
        self.log(f"running doExposure")

        self.imstarttime = datetime.utcnow().strftime("%Y%m%d-%H%M%S-%f")[:-3]

        if imname is None:
            imname = f"{self.daemonname}_{self.imstarttime}"
        self.imname = imname

        if imdir is None:
            imdir = self.remote_object.getDefaultImageDirectory()
        self.imdir = imdir

        if imtype is None:
            imtype = "test"

        if mode is None:
            mode = "single"

        self.imtype = imtype
        self.mode = mode

        self._mark_operation_start()

        try:
            # Optimistically set state to EXPOSING
            self.camera_state = CameraState.EXPOSING
            self.doing_exposure = True  # Set exposure flag

            # Update state dictionaries
            self.log(f"updating state dictionaries")
            self.update_hk_state()
            self.update_state()

            self.log(f"making FITS header")
            header = self.getFITSheader()

            self.log(
                f"sending doExposure request to camera: imdir = {self.imdir}, imname = {self.imname}"
            )

            self.remote_object.doExposure(
                imdir=self.imdir,
                imname=self.imname,
                imtype=self.imtype,
                mode=self.mode,
                metadata=header,
                **kwargs,
            )

        except Exception as e:
            self.active_operation_time = None
            self.camera_state = CameraState.ERROR
            self.doing_exposure = False
            print(f"Error: {e}, PyroError: {Pyro5.errors.get_pyro_traceback()}")

    def tecSetSetpoint(self, temp, **kwargs):
        """Set TEC setpoint"""
        self._mark_operation_start()
        try:
            self.camera_state = CameraState.SETTING_PARAMETERS
            self.remote_object.tecSetSetpoint(temp, **kwargs)
            self.camera_state = CameraState.READY
        except Exception as e:
            self.active_operation_time = None
            self.camera_state = CameraState.ERROR
            print(f"Error setting TEC setpoint: {e}")
            raise

    def tecStart(self, **kwargs):
        """Start TEC"""
        self._mark_operation_start()
        try:
            self.camera_state = CameraState.SETTING_PARAMETERS
            self.remote_object.tecStart(**kwargs)
            self.camera_state = CameraState.READY
        except Exception as e:
            self.active_operation_time = None
            self.camera_state = CameraState.ERROR
            print(f"Error starting TEC: {e}")
            raise

    def tecStop(self, **kwargs):
        """Stop TEC"""
        self._mark_operation_start()
        try:
            self.camera_state = CameraState.SETTING_PARAMETERS
            self.remote_object.tecStop(**kwargs)
            self.camera_state = CameraState.READY
        except Exception as e:
            self.active_operation_time = None
            self.camera_state = CameraState.ERROR
            print(f"Error stopping TEC: {e}")
            raise

    def startupCamera(self, **kwargs):
        """Manual startup"""
        self._mark_operation_start()
        self.autoStartupRequested = True
        try:
            self.camera_state = CameraState.STARTUP_REQUESTED
            self.remote_object.startupCamera(**kwargs)
        except Exception as e:
            self.active_operation_time = None
            self.camera_state = CameraState.ERROR
            self.autoStartupRequested = False
            print(f"Error starting camera: {e}")
            raise

    def shutdownCamera(self, **kwargs):
        """Manual shutdown"""
        self._mark_operation_start()
        self.autoShutdownRequested = True
        try:
            self.camera_state = CameraState.SHUTDOWN_REQUESTED
            self.remote_object.shutdownCamera(**kwargs)
        except Exception as e:
            self.active_operation_time = None
            self.camera_state = CameraState.ERROR
            self.autoShutdownRequested = False
            print(f"Error shutting down camera: {e}")
            raise

    def autoStartupCamera(self, **kwargs):
        """Auto startup"""
        self._mark_operation_start()
        self.autoStartupRequested = True
        try:
            self.camera_state = CameraState.STARTUP_REQUESTED
            self.remote_object.autoStartup(**kwargs)
        except Exception as e:
            self.active_operation_time = None
            self.camera_state = CameraState.ERROR
            self.autoStartupRequested = False
            print(f"Error during auto startup: {e}")
            raise

    def autoShutdownCamera(self, **kwargs):
        """Auto shutdown"""
        self._mark_operation_start()
        self.autoShutdownRequested = True
        try:
            self.camera_state = CameraState.SHUTDOWN_REQUESTED
            self.remote_object.autoShutdown(**kwargs)
        except Exception as e:
            self.active_operation_time = None
            self.camera_state = CameraState.ERROR
            self.autoShutdownRequested = False
            print(f"Error during auto shutdown: {e}")
            raise

    def restartSensorDaemon(self, **kwargs):
        """Restart sensor daemon"""
        self.remote_object.restartSensorDaemon(**kwargs)

    def updateStartupValidation(self, startupValidation, **kwargs):
        """Update startup validation"""
        self.remote_object.updateStartupValidation(
            startupValidation=startupValidation, **kwargs
        )

    def checkCamera(self, **kwargs):
        """Check camera status"""
        self.remote_object.checkCamera(**kwargs)

    def killCameraDaemon(self, **kwargs):
        """Kill camera daemon"""
        self.remote_object.killCameraDaemon(**kwargs)
