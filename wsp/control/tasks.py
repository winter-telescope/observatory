"""
control/tasks.py
Task definitions for the WSP control system.
These tasks are used to manage camera operations,
including calibration and observation requests.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class CalibrationTask:
    """A calibration task to execute"""

    camera_name: str
    filter_name: str
    cal_type: str = "bias"  # bias, dark, flat, etc.


@dataclass
class ObservationRequest:
    """An observation request with camera selection"""

    target_name: str
    ra: float
    dec: float
    camera_name: str
    filter_name: str
    exposure_time: float
    num_exposures: int = 1
    priority: int = 0
    constraints: Dict[str, Any] = field(default_factory=dict)
