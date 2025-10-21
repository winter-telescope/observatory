# camera_command_decorators.py

import functools
import logging
from typing import Callable, Optional, Union

from wsp.camera.state import CameraState


def async_camera_command(
    timeout: Union[float, Callable] = 30.0,
    completion_state: CameraState = CameraState.READY,
    initial_state: Optional[CameraState] = CameraState.SETTING_PARAMETERS,
    pending_completion: bool = False,
):
    """
    Decorator for async camera commands.

    Args:
        timeout: Either a float or a callable that returns a float
        completion_state: State to set on successful completion
        initial_state: State to set immediately when command starts
        pending_completion: If True, stay in initial_state until completion conditions are met
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            # Set initial state immediately
            if initial_state:
                self.update_camera_state(initial_state)

            # Calculate timeout
            if callable(timeout):
                self.command_timeout = timeout(self, *args, **kwargs)
            else:
                self.command_timeout = timeout

            # Store metadata for completion handling
            command_completion_state = completion_state
            command_pending = pending_completion
            command_initial_state = initial_state

            # Create the blocking operation
            def blocking_operation():
                try:
                    # Call the actual decorated method
                    result = func(self, *args, **kwargs)

                    # Check if stopped
                    if (
                        hasattr(self, "command_worker")
                        and self.command_worker.stop_requested
                    ):
                        self.log(
                            f"{func.__name__} was interrupted", level=logging.WARNING
                        )
                        return False

                    # Handle completion based on pending flag
                    if command_pending and result:
                        # Command succeeded but needs completion checking
                        # Store info for polling to check
                        self.pending_command_completion = {
                            "command": func.__name__,
                            "completion_state": command_completion_state,
                            "initial_state": command_initial_state,
                            "start_time": self.command_sent_timestamp,
                        }
                        # Don't change state - stay in initial_state
                    elif result:
                        # Normal completion - set completion state immediately
                        self.pending_completion_state = command_completion_state

                    return result

                except Exception as e:
                    self.log(f"Error in {func.__name__}: {e}", level=logging.ERROR)
                    raise e

            # Execute asynchronously
            return self.execute_async_command(blocking_operation, func.__name__)

        # Store metadata
        wrapper.is_async_command = True
        wrapper.timeout = timeout
        wrapper.completion_state = completion_state
        wrapper.initial_state = initial_state
        wrapper.pending_completion = pending_completion

        return wrapper

    return decorator
