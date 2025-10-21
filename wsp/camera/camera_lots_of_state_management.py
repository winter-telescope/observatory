#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
integrated_camera.py

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
from datetime import datetime
from enum import Enum, auto
from typing import Any, Dict, Optional

import astropy.io.fits as fits
import Pyro5.core
import Pyro5.errors
import Pyro5.server
from PyQt5 import QtCore

from wsp.camera.state import CameraState


class BaseCamera(QtCore.QObject, ABC):
    """
    Enhanced BaseCamera with integrated state management.

    This class now:
    1. Expects the Interface Daemon to report standardized states
    2. Provides state transition validation
    3. Emits state change signals for the state machine
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

        # State management - enhanced
        self.state = dict()
        self.hk_state = dict()
        self.remote_state = dict()
        self.connected = False
        self.hk_connected = False

        # Camera state tracking
        self._camera_state = CameraState.OFF
        self._previous_state = CameraState.OFF
        self._state_transition_time = datetime.utcnow()

        # Default value handling
        self.default = self.config.get("default_value", -999)

        # Image parameters
        self.imdir = ""
        self.imname = ""
        self.imstarttime = ""
        self.mode = None
        self.imtype = None

        # Connect signals and slots
        self.newCommand.connect(self.doCommand)

        # Initialize connections
        self.init_remote_object()
        self.update_state()
        self.init_hk_state_object()
        self.update_hk_state()

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
            self.log(f"State changed: {old_state.value} -> {new_state.value}")

    def is_state_valid_transition(
        self, from_state: CameraState, to_state: CameraState
    ) -> bool:
        """
        Check if a state transition is valid.
        Override in subclasses for camera-specific rules.
        """
        # Define valid state transitions
        valid_transitions = {
            CameraState.OFF: [CameraState.STARTUP_REQUESTED, CameraState.ERROR],
            CameraState.STARTUP_REQUESTED: [
                CameraState.STARTUP_COMPLETE,
                CameraState.ERROR,
                CameraState.OFF,
            ],
            CameraState.STARTUP_COMPLETE: [
                CameraState.SETTING_PARAMETERS,
                CameraState.READY,
                CameraState.ERROR,
            ],
            CameraState.SETTING_PARAMETERS: [CameraState.READY, CameraState.ERROR],
            CameraState.READY: [
                CameraState.EXPOSING,
                CameraState.SETTING_PARAMETERS,
                CameraState.SHUTDOWN_REQUESTED,
                CameraState.ERROR,
            ],
            CameraState.EXPOSING: [CameraState.READING, CameraState.ERROR],
            CameraState.READING: [CameraState.READY, CameraState.ERROR],
            CameraState.SHUTDOWN_REQUESTED: [
                CameraState.SHUTDOWN_COMPLETE,
                CameraState.ERROR,
            ],
            CameraState.SHUTDOWN_COMPLETE: [CameraState.OFF],
            CameraState.ERROR: [
                CameraState.OFF,
                CameraState.STARTUP_REQUESTED,
                CameraState.SHUTDOWN_REQUESTED,
            ],
        }

        return to_state in valid_transitions.get(from_state, [])

    def is_valid_state(self, state: CameraState) -> bool:
        """
        Check if the given state is a valid CameraState.
        This is useful for validating states received from remote daemons.
        """
        return isinstance(state, CameraState) and state in CameraState

    def update_state(self):
        """Enhanced update_state that also updates camera state"""
        if not self.connected:
            if self.verbose:
                self.log(
                    f"self.connected = {self.connected}: try to init_remote_object again"
                )
            self.init_remote_object()

        if not self.hk_connected:
            self.init_hk_state_object()

        if self.connected:
            try:
                self.remote_state = self.remote_object.getStatus()
                self.parse_state()

                # Update camera state from remote
                remote_camera_state = self.remote_state.get("camera_state", "OFF")
                try:
                    new_state = CameraState(remote_camera_state)
                    # Validate state transition
                    if self.is_valid_state(new_state):
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

            except Exception as e:
                if self.verbose:
                    self.log(f"camera: could not update/parse remote state: {e}")
                self.connected = False
                self.camera_state = CameraState.ERROR

    def parse_state(self):
        """
        Parse state must now include camera_state in self.state
        """
        # Base implementation - subclasses should call super().parse_state()
        self.state.update(
            {
                "camname": self.camname,
                "is_connected": self.connected,
                "camera_state": self.camera_state.value,
                "state_duration": self.get_state_duration(),
                "imdir": self.imdir,
                "imname": self.imname,
                "imstarttime": self.imstarttime,
                "imtype": self.imtype,
                "immode": self.mode,
            }
        )

    # Enhanced API methods that respect state

    def can_expose(self) -> bool:
        """Check if camera is in a state where it can start an exposure"""
        return self.camera_state == CameraState.READY

    def can_change_settings(self) -> bool:
        """Check if camera is in a state where settings can be changed"""
        return self.camera_state in [CameraState.READY, CameraState.STARTUP_COMPLETE]

    def doExposure(self, imdir=None, imname=None, imtype=None, mode=None, addrs=None):
        """Enhanced doExposure that checks state"""
        if not self.can_expose():
            self.log(
                f"Cannot start exposure in state {self.camera_state.value}",
                level=logging.WARNING,
            )
            return False

        # Update state to EXPOSING
        self.camera_state = CameraState.EXPOSING

        # Continue with original implementation
        super().doExposure(imdir, imname, imtype, mode, addrs)

        return True

    def setExposure(self, exptime, addrs=None):
        """Enhanced setExposure that checks state"""
        if not self.can_change_settings():
            self.log(
                f"Cannot change settings in state {self.camera_state.value}",
                level=logging.WARNING,
            )
            return False

        self.camera_state = CameraState.SETTING_PARAMETERS
        try:
            self.remote_object.setExposure(exptime, addrs=addrs)
            # State will be updated to READY by next update_state() call
            return True
        except Exception as e:
            self.camera_state = CameraState.ERROR
            raise

    def autoStartupCamera(self):
        """Enhanced startup that manages state transitions"""
        if self.camera_state not in [CameraState.OFF, CameraState.ERROR]:
            self.log(
                f"Cannot start camera from state {self.camera_state.value}",
                level=logging.WARNING,
            )
            return False

        self.camera_state = CameraState.STARTUP_REQUESTED
        try:
            self.remote_object.autoStartup()
            return True
        except Exception as e:
            self.camera_state = CameraState.ERROR
            raise

    def autoShutdownCamera(self):
        """Enhanced shutdown that manages state transitions"""
        if self.camera_state == CameraState.OFF:
            self.log("Camera already off", level=logging.INFO)
            return True

        if self.camera_state == CameraState.EXPOSING:
            self.log("Cannot shutdown while exposing", level=logging.WARNING)
            return False

        self.camera_state = CameraState.SHUTDOWN_REQUESTED
        try:
            self.remote_object.autoShutdown()
            return True
        except Exception as e:
            self.camera_state = CameraState.ERROR
            raise

    def get


    def log(self, msg, level=logging.INFO):
        msg = f"{self.daemonname}_local: {msg}"
        if self.logger is None:
            print(msg)
        else:
            self.logger.log(level=level, msg=msg)


class CameraDaemonInterface(ABC):
    """
    Abstract base class for Interface Daemons.

    This standardizes what the Interface Daemon must provide to BaseCamera.
    Each camera's Interface Daemon should inherit from this and implement
    the abstract methods.
    """

    def __init__(self):
        self._state = CameraState.OFF
        self._error_message = None

    @property
    def state(self) -> CameraState:
        return self._state

    @state.setter
    def state(self, value: CameraState):
        self._state = value

    def getStatus(self) -> Dict[str, Any]:
        """
        Return standardized status dictionary.
        MUST include 'camera_state' key with CameraState value.
        """
        status = {
            "camera_state": self._state.value,
            "error_message": self._error_message,
            "timestamp": datetime.utcnow().isoformat(),
        }
        # Add camera-specific status
        status.update(self._get_camera_specific_status())
        return status

    @abstractmethod
    def _get_camera_specific_status(self) -> Dict[str, Any]:
        """Get camera-specific status information"""
        pass

    @abstractmethod
    def setExposure(self, exptime: float, addrs=None):
        """Set exposure time"""
        pass

    @abstractmethod
    def doExposure(
        self,
        imdir: str,
        imname: str,
        imtype: str,
        mode: str,
        metadata: list,
        addrs=None,
    ):
        """Execute exposure"""
        pass

    @abstractmethod
    def autoStartup(self):
        """Automatic startup sequence"""
        pass

    @abstractmethod
    def autoShutdown(self):
        """Automatic shutdown sequence"""
        pass

    # ... other required methods ...


class WINTERCameraDaemonInterface(CameraDaemonInterface):
    """
    Example implementation of Interface Daemon for WINTER camera.

    This daemon translates between the standardized API and the
    WINTER-specific hardware daemon.
    """

    def __init__(self, hardware_daemon_uri):
        super().__init__()
        self.hardware_daemon = Pyro5.client.Proxy(hardware_daemon_uri)

    def _get_camera_specific_status(self) -> Dict[str, Any]:
        """Get WINTER-specific status"""
        try:
            hw_status = self.hardware_daemon.get_detailed_status()
            return {
                "sensor_temps": hw_status.get("temperatures", {}),
                "tec_status": hw_status.get("tec_status", {}),
                # ... other WINTER-specific fields ...
            }
        except Exception as e:
            return {"hardware_error": str(e)}

    def autoStartup(self):
        """WINTER startup sequence"""
        try:
            self.state = CameraState.STARTUP_REQUESTED

            # Power on sequence
            self.hardware_daemon.power_on()
            time.sleep(5)

            # Initialize sensors
            self.hardware_daemon.init_sensors()

            # Start TEC
            self.hardware_daemon.start_tec_control()

            # Wait for temperature stabilization
            self.state = CameraState.STARTUP_COMPLETE

            # Configure default parameters
            self.state = CameraState.SETTING_PARAMETERS
            self.hardware_daemon.set_default_params()

            self.state = CameraState.READY

        except Exception as e:
            self._error_message = str(e)
            self.state = CameraState.ERROR
            raise

    def doExposure(
        self,
        imdir: str,
        imname: str,
        imtype: str,
        mode: str,
        metadata: list,
        addrs=None,
    ):
        """Execute WINTER exposure"""
        try:
            self.state = CameraState.EXPOSING

            # Start exposure
            self.hardware_daemon.start_exposure(winter_mode)

            # Wait for readout
            self.state = CameraState.READING
            data = self.hardware_daemon.read_data()

            # Save with metadata
            self._save_fits(data, imdir, imname, metadata)

            self.state = CameraState.READY

        except Exception as e:
            self._error_message = str(e)
            self.state = CameraState.ERROR
            raise
