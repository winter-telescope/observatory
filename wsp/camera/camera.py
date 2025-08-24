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
from datetime import datetime
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

        # State verification tracking
        self._expected_state = None
        self._expected_state_timeout = 2.0
        self._expected_state_set_time = None

        # Initialize connections
        self.init_remote_object()
        self.update_state()

    def _set_expected_state(self, expected_state: CameraState, timeout: float = 2.0):
        """Set the expected state and start tracking for verification"""
        self._expected_state = expected_state
        self._expected_state_timeout = timeout
        self._expected_state_set_time = datetime.utcnow()

    def _check_expected_state(self):
        """Check if expected state matches actual state (called during update_state)"""
        if self._expected_state is None or self._expected_state_set_time is None:
            return

        # Calculate elapsed time
        elapsed = (datetime.utcnow() - self._expected_state_set_time).total_seconds()

        # If we've exceeded the timeout, check if states match
        if elapsed > self._expected_state_timeout:
            if self._camera_state != self._expected_state:
                self.log(
                    f"State verification timeout! Expected {self._expected_state.value} "
                    f"but daemon reports {self._camera_state.value} after {elapsed:.1f}s",
                    level=logging.WARNING,
                )
            # Clear the expected state tracking
            self._expected_state = None
            self._expected_state_set_time = None

    def _start_local_override(
        self,
        expected: CameraState,
        min_hold: float = 0.4,  # keep local state at least this long after it’s first confirmed
        max_wait: float = 2.0,  # give daemon up to this long to report the expected state
    ) -> None:
        self._local_override = {
            "expected": expected,
            "t0": datetime.utcnow(),
            "min_hold": min_hold,
            "max_wait": max_wait,
            "seen_expected": False,  # flips True once daemon reports expected at least once
        }

    def _maybe_gate_remote(self, remote_state: CameraState) -> CameraState:
        """Return the state we should apply *now* (possibly the current local state to ignore a regression)."""
        gate = getattr(self, "_local_override", None)
        if not gate:
            return remote_state

        now = datetime.utcnow()
        elapsed = (now - gate["t0"]).total_seconds()
        expected = gate["expected"]

        # If daemon reports the expected state, mark confirmed
        if remote_state == expected:
            gate["seen_expected"] = True
            # fall-through: allow updating to expected

        # If we haven't yet seen expected and we're within max_wait, ignore regressions like READY
        if not gate["seen_expected"] and elapsed < gate["max_wait"]:
            if remote_state in (
                CameraState.READY,
                CameraState.SETTING_PARAMETERS,
                CameraState.OFF,
            ):
                # keep local optimistic state for now
                return self._camera_state

        # If we have seen expected, enforce a brief min_hold before allowing a drop back
        if gate["seen_expected"] and elapsed < gate["min_hold"]:
            if remote_state != expected and remote_state != CameraState.ERROR:
                return self._camera_state

        # Clear the gate once we either time out or leave the expected state after min_hold
        if elapsed >= gate["max_wait"] or (
            gate["seen_expected"] and remote_state != expected
        ):
            self._local_override = None

        return remote_state

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

    def init_remote_object(self):
        """Initialize connection to remote daemon"""
        try:
            if self.verbose:
                self.log(f"init_remote_object: trying to connect to {self.daemonname}")
            ns = Pyro5.core.locate_ns(host=self.ns_host)
            uri = ns.lookup(self.daemonname)
            self.remote_object = Pyro5.client.Proxy(uri)
            self.connected = True
        except Exception as e:
            self.connected = False
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
                # This ensures remote state is set before parse_state is called
                remote_camera_state = self.remote_state.get("camera_state", "OFF")
                if self.verbose:
                    print(f"Remote camera state: {remote_camera_state}")

                try:
                    new_state = CameraState(remote_camera_state)
                    if self.is_valid_state(new_state):
                        # GATE HERE:
                        gated_state = self._maybe_gate_remote(new_state)

                        if gated_state != self._camera_state:
                            self.camera_state = gated_state
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

                # Now parse the rest of the state
                self.parse_state()

                # Check if expected state matches actual state
                self._check_expected_state()

            except Exception as e:
                if self.verbose:
                    self.log(f"camera: could not update/parse remote state: {e}")
                self.connected = False
                self.camera_state = CameraState.ERROR

    def parse_state(self):
        """Parse state - must be implemented by subclasses"""
        # Base implementation
        self.state.update(
            {
                "camname": self.camname,
                "is_connected": self.connected,
                "camera_state": self.camera_state.value,
                "imdir": self.imdir,
                "imname": self.imname,
                "imstarttime": self.imstarttime,
                "imtype": self.imtype,
                "immode": self.mode,
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

    def setExposure(self, exptime, timeout=5.0, **kwargs):
        """Set exposure time

        Parameters
        ----------
        exptime : float
            Exposure time in seconds
        timeout : float
            Time to wait for state verification (default 5.0s)
            For cameras with slow exposure changes, set this higher
        **kwargs
            Additional camera-specific parameters
        """
        try:
            # Optimistically set state
            self.camera_state = CameraState.SETTING_PARAMETERS

            self.remote_object.setExposure(exptime, **kwargs)

            # Optimistically return to READY
            self.camera_state = CameraState.READY

            # Track expected state
            self._set_expected_state(CameraState.READY, timeout=timeout)
        except Exception as e:
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

        # NOTE: Moved state updates AFTER we set the EXPOSING state
        # to avoid overwriting our optimistic state change

        try:
            # Optimistically set state to EXPOSING FIRST
            self.camera_state = CameraState.EXPOSING

            # Start local override so we don't accept READY for a moment
            self._start_local_override(CameraState.EXPOSING, min_hold=2.0, max_wait=5.0)

            # THEN update state dictionaries (but this won't overwrite camera_state)
            self.log(f"updating state dictionaries")
            # Don't call update_state() here as it will overwrite our optimistic state!
            # Just update housekeeping state
            self.update_hk_state()

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

            # Track expected state - we expect to stay in EXPOSING
            self._set_expected_state(CameraState.EXPOSING, timeout=2.0)

        except Exception as e:
            # Revert state on error
            self.camera_state = CameraState.ERROR
            print(f"Error: {e}, PyroError: {Pyro5.errors.get_pyro_traceback()}")

    def tecSetSetpoint(self, temp, timeout=1.0, **kwargs):
        """Set TEC setpoint"""
        try:
            self.camera_state = CameraState.SETTING_PARAMETERS
            self.remote_object.tecSetSetpoint(temp, **kwargs)
            self.camera_state = CameraState.READY
            self._set_expected_state(CameraState.READY, timeout=timeout)
        except Exception as e:
            self.camera_state = CameraState.ERROR
            print(f"Error setting TEC setpoint: {e}")
            raise

    def tecStart(self, **kwargs):
        """Start TEC"""
        try:
            self.camera_state = CameraState.SETTING_PARAMETERS
            self.remote_object.tecStart(**kwargs)
            self.camera_state = CameraState.READY
            self._set_expected_state(CameraState.READY, timeout=1.0)
        except Exception as e:
            self.camera_state = CameraState.ERROR
            print(f"Error starting TEC: {e}")
            raise

    def tecStop(self, **kwargs):
        """Stop TEC"""
        try:
            self.camera_state = CameraState.SETTING_PARAMETERS
            self.remote_object.tecStop(**kwargs)
            self.camera_state = CameraState.READY
            self._set_expected_state(CameraState.READY, timeout=1.0)
        except Exception as e:
            self.camera_state = CameraState.ERROR
            print(f"Error stopping TEC: {e}")
            raise

    def startupCamera(self, **kwargs):
        """Manual startup"""
        try:
            self.camera_state = CameraState.STARTUP_REQUESTED
            self.remote_object.startupCamera(**kwargs)
            self._set_expected_state(CameraState.STARTUP_REQUESTED, timeout=2.0)
        except Exception as e:
            self.camera_state = CameraState.ERROR
            print(f"Error starting camera: {e}")
            raise

    def shutdownCamera(self, **kwargs):
        """Manual shutdown"""
        try:
            self.camera_state = CameraState.SHUTDOWN_REQUESTED
            self.remote_object.shutdownCamera(**kwargs)
            self._set_expected_state(CameraState.SHUTDOWN_REQUESTED, timeout=2.0)
        except Exception as e:
            self.camera_state = CameraState.ERROR
            print(f"Error shutting down camera: {e}")
            raise

    def autoStartupCamera(self, **kwargs):
        """Auto startup"""
        try:
            self.camera_state = CameraState.STARTUP_REQUESTED
            self.remote_object.autoStartup(**kwargs)
            self._set_expected_state(CameraState.STARTUP_REQUESTED, timeout=2.0)
        except Exception as e:
            self.camera_state = CameraState.ERROR
            print(f"Error during auto startup: {e}")
            raise

    def autoShutdownCamera(self, **kwargs):
        """Auto shutdown"""
        try:
            self.camera_state = CameraState.SHUTDOWN_REQUESTED
            self.remote_object.autoShutdown(**kwargs)
            self._set_expected_state(CameraState.SHUTDOWN_REQUESTED, timeout=2.0)
        except Exception as e:
            self.camera_state = CameraState.ERROR
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
