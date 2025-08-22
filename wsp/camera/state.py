"""
camera/state.py

Shared camera state definitions used across the entire system.
This is the single source of truth for camera states.
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional


class CameraState(Enum):
    """
    Standard camera states for all camera types.
    Used by:
    - State machine (for decision making)
    - Interface daemons (for reporting)
    - BaseCamera (for state tracking)
    - Status tracking (for runtime monitoring)
    """

    OFF = "OFF"
    STARTUP_REQUESTED = "STARTUP_REQUESTED"
    STARTUP_TIMEOUT = "STARTUP_TIMEOUT"  # used for startup timeout handling
    SETTING_PARAMETERS = "SETTING_PARAMETERS"
    READY = "READY"
    EXPOSING = "EXPOSING"
    READING = "READING"
    SHUTDOWN_REQUESTED = "SHUTDOWN_REQUESTED"
    SHUTDOWN_TIMEOUT = "SHUTDOWN_TIMEOUT"  # used for shutdown timeout handling
    ERROR = "ERROR"

    @classmethod
    def is_operational(cls, state: "CameraState") -> bool:
        """Check if camera is in an operational state"""
        return state in [cls.READY, cls.EXPOSING, cls.READING, cls.SETTING_PARAMETERS]

    @classmethod
    def is_transitional(cls, state: "CameraState") -> bool:
        """Check if camera is in a transitional state"""
        return state in [cls.STARTUP_REQUESTED, cls.SHUTDOWN_REQUESTED]

    @classmethod
    def can_expose(cls, state: "CameraState") -> bool:
        """Check if camera can start an exposure in this state"""
        return state == cls.READY

    @classmethod
    def can_shutdown(cls, state: "CameraState") -> bool:
        """Check if camera can be shutdown from this state"""
        return state not in [
            cls.EXPOSING,
            cls.READING,
            cls.SHUTDOWN_REQUESTED,
            cls.OFF,
        ]


@dataclass
class CameraStatus:
    """Runtime status of a camera"""

    state: CameraState = CameraState.OFF
    startup_requested_time: Optional[float] = None
    ready: bool = False
    last_cal_time: Dict[str, float] = field(default_factory=dict)  # filter -> timestamp
    last_focus_time: Dict[str, float] = field(
        default_factory=dict
    )  # filter -> timestamp
    error: Optional[str] = None
