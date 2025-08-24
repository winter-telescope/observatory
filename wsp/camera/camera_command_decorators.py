"""
camera_command_decorators.py

Enhanced decorators that handle state management for both
camera interface implementations and daemon wrapper methods.
"""

import functools
import logging
from datetime import datetime
from typing import Any, Callable, Optional

from PyQt5 import QtCore

from wsp.camera.state import CameraState


def daemon_command(
    initial_state: Optional[CameraState] = None,
    final_state: Optional[CameraState] = None,
    error_state: CameraState = CameraState.ERROR,
):
    """
    Decorator for daemon interface methods that manages immediate state transitions.
    This decorator is used on CameraDaemonInterface methods to set state immediately
    when commands are received from the client.

    Parameters
    ----------
    initial_state : CameraState, optional
        State to set immediately when command is received
    final_state : CameraState, optional
        State to set after successful completion (rarely used at daemon level)
    error_state : CameraState
        State to set on error
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            # Set initial state immediately when command is received
            if initial_state:
                self.log(f"Setting immediate state: {initial_state.value}")
                self.camera.update_camera_state(initial_state)

            try:
                result = func(self, *args, **kwargs)

                # Set final state if specified (usually not needed at daemon level)
                if final_state:
                    self.camera.update_camera_state(final_state)

                return result

            except Exception as e:
                self.log(f"Error in {func.__name__}: {e}", level=logging.ERROR)
                self.camera.update_camera_state(error_state)
                raise

        return wrapper

    return decorator


def camera_command(
    timeout: Optional[float] = 10.0,
    timeout_func: Optional[Callable] = None,
    required_state: Optional[CameraState] = None,
    target_state: Optional[CameraState] = None,
    completion_state: Optional[CameraState] = None,
    error_state: CameraState = CameraState.ERROR,
    check_addresses: bool = True,
):
    """
    Enhanced decorator for camera implementation commands.
    State validation is skipped since daemon handles state transitions.

    Parameters
    ----------
    timeout : float
        Command timeout in seconds
    timeout_func : callable, optional
        Function to calculate timeout dynamically
    required_state : CameraState, optional
        DEPRECATED - state validation now handled by daemon
    target_state : CameraState, optional
        DEPRECATED - state transitions handled by daemon
    completion_state : CameraState, optional
        State to set when command completes successfully
    error_state : CameraState
        State to set on error
    check_addresses : bool
        Whether to check/handle address parameters
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            # Skip state validation - daemon has already set the appropriate state
            # The daemon interface is responsible for checking if commands are allowed

            # Handle address parameters if needed
            if check_addresses and "addrs" in kwargs:
                addrs = kwargs.get("addrs")
                if addrs is None:
                    kwargs["addrs"] = getattr(self, "addrs", None)
                elif not isinstance(addrs, list):
                    kwargs["addrs"] = [addrs]

            # Calculate timeout dynamically if function provided
            if timeout_func:
                actual_timeout = timeout_func(self, *args, **kwargs)
            else:
                actual_timeout = timeout

            # Set up command tracking signals
            self.resetCommandPassSignal.emit(0)
            self.resetCommandActiveSignal.emit(1)
            self.resetCommandTimeoutSignal.emit(actual_timeout)

            try:
                # Execute the actual command
                result = func(self, *args, **kwargs)

                # If command completed successfully and immediately
                # (e.g., setExposure, tecSetSetpoint)
                if result is not False and completion_state:
                    self.update_camera_state(completion_state)
                    self.resetCommandPassSignal.emit(1)
                    self.resetCommandActiveSignal.emit(0)

                return result

            except Exception as e:
                self.log(f"Error in {func.__name__}: {e}", level=logging.ERROR)
                self.resetCommandPassSignal.emit(0)
                self.resetCommandActiveSignal.emit(0)
                self.update_camera_state(error_state)
                raise

        return wrapper

    return decorator


# That's it! Just two decorators: daemon_command and camera_command
# No need for exposure_command, startup_command, shutdown_command, etc.
