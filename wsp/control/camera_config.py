# camera_config.py
"""
Camera Configuration Management for Multi-Camera Observatory System

This module handles camera configuration, info extraction from distributed
config files, and camera/port management.
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional


class CameraState(Enum):
    """Individual camera states"""

    OFF = auto()
    STARTUP_REQUESTED = auto()
    STARTUP_COMPLETE = auto()
    SETTING_PARAMETERS = auto()
    READY = auto()
    SHUTDOWN_REQUESTED = auto()
    SHUTDOWN_COMPLETE = auto()
    ERROR = auto()


class CameraPort(Enum):
    """Telescope camera ports"""

    PORT_1 = 1
    PORT_2 = 2


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


@dataclass
class CameraInfo:
    """
    Camera configuration information extracted from distributed config.
    This class consolidates camera-related settings from various config sections.
    """

    name: str
    port: int
    filters: List[str]
    cal_interval_hours: float = 1.0
    focus_interval_hours: float = 2.0
    startup_timeout: float = 300.0
    shutdown_timeout: float = 180.0

    # Focus parameters
    focus_filters: List[str] = field(default_factory=list)

    # Calibration parameters
    dark_exptimes: List[float] = field(default_factory=list)
    flat_filters: List[str] = field(default_factory=list)
    domeflat_filters: List[str] = field(default_factory=list)

    # Observing parameters
    pixscale: float = 1.0
    best_position: Dict[str, Any] = field(default_factory=dict)
    base_position: Dict[str, Any] = field(default_factory=dict)
    x_pixels: int = 0
    y_pixels: int = 0

    # Dither parameters
    dither_number: int = 5
    dither_min_step: float = 10.0
    dither_max_step: float = 15.0

    @classmethod
    def from_config(cls, camera_name: str, config: dict) -> "CameraInfo":
        """
        Factory method to create CameraInfo from distributed config structure.

        Extracts camera information from multiple config sections:
        - telescope.ports: port assignment
        - filters: available filters
        - cal_params: calibration settings
        - focus_loop_param: focus settings
        - observing_parameters: detector parameters
        """
        # Find which port this camera is on
        port = None
        for port_num, port_info in config["telescope"]["ports"].items():
            if camera_name in port_info.get("cameras", []):
                # Ensure port is int even if YAML keys are strings
                port = int(port_num)
                break

        if port is None:
            raise ValueError(f"Camera {camera_name} not found in any telescope port")

        # Extract filter list
        filters = list(config["filters"].get(camera_name, {}).keys())

        # Extract focus filters
        focus_filters = config["focus_loop_param"]["focus_filters"].get(camera_name, [])

        # Extract calibration parameters
        cal_params = config["cal_params"].get(camera_name, {})
        dark_exptimes = cal_params.get("darks", {}).get("exptimes", [])
        flat_filters = cal_params.get("flats", {}).get("filterIDs", [])
        domeflat_filters = cal_params.get("domeflats", {}).get("filterIDs", [])

        # Extract observing parameters
        obs_params = config["observing_parameters"].get(camera_name, {})
        dither_params = obs_params.get("dithers", {})

        # Look for cal interval in triggers (if they exist)
        cal_interval_hours = 1.0  # default
        focus_interval_hours = 2.0  # default

        # Extract timeouts if specified
        startup_timeout = cal_params.get("startup_timeout", 300.0)
        shutdown_timeout = cal_params.get("shutdown_timeout", 180.0)

        return cls(
            name=camera_name,
            port=port,
            filters=filters,
            cal_interval_hours=cal_interval_hours,
            focus_interval_hours=focus_interval_hours,
            startup_timeout=startup_timeout,
            shutdown_timeout=shutdown_timeout,
            focus_filters=focus_filters,
            dark_exptimes=dark_exptimes,
            flat_filters=flat_filters,
            domeflat_filters=domeflat_filters,
            pixscale=obs_params.get("pixscale", 1.0),
            best_position=obs_params.get("best_position", {}),
            base_position=obs_params.get("base_position", {}),
            x_pixels=obs_params.get("x_pixels", 0),
            y_pixels=obs_params.get("y_pixels", 0),
            dither_number=dither_params.get("ditherNumber", 5),
            dither_min_step=dither_params.get("ditherMinStep_as", 10.0),
            dither_max_step=dither_params.get("ditherMaxStep_as", 15.0),
        )


class CameraConfigManager:
    """
    Manages camera configurations and handles port assignments dynamically.

    This class provides a centralized interface for:
    - Discovering active cameras
    - Managing camera/port relationships
    - Caching camera configurations
    - Supporting dynamic camera swapping
    """

    def __init__(self, config: dict):
        """
        Initialize the camera configuration manager.

        Args:
            config: The full observatory configuration dictionary
        """
        self.config = config
        self._camera_info_cache = {}

    def get_active_cameras(self) -> List[str]:
        """Get list of currently active cameras from config."""
        return self.config.get("active_cameras", [])

    def get_camera_info(self, camera_name: str) -> CameraInfo:
        """
        Get CameraInfo for a specific camera, with caching.

        Args:
            camera_name: Name of the camera

        Returns:
            CameraInfo object for the specified camera

        Raises:
            ValueError: If camera configuration cannot be found
        """
        if camera_name not in self._camera_info_cache:
            self._camera_info_cache[camera_name] = CameraInfo.from_config(
                camera_name, self.config
            )
        return self._camera_info_cache[camera_name]

    def get_all_camera_info(self) -> List[CameraInfo]:
        """
        Get CameraInfo for all active cameras.

        Returns:
            List of CameraInfo objects for all active cameras
        """
        camera_infos = []
        for camera_name in self.get_active_cameras():
            try:
                camera_infos.append(self.get_camera_info(camera_name))
            except ValueError as e:
                print(f"Warning: {e}")
        return camera_infos

    def get_cameras_on_port(self, port: int) -> List[str]:
        """
        Get all cameras configured on a specific port.

        Args:
            port: Port number

        Returns:
            List of camera names on the specified port
        """
        port_info = self.config["telescope"]["ports"].get(port, {})
        return port_info.get("cameras", [])

    def get_port_for_camera(self, camera_name: str) -> Optional[int]:
        """
        Get the port number for a specific camera.

        Args:
            camera_name: Name of the camera

        Returns:
            Port number if found, None otherwise
        """
        for port_num, port_info in self.config["telescope"]["ports"].items():
            if camera_name in port_info.get("cameras", []):
                return int(port_num)
        return None

    def get_port_config(self, port: int) -> Dict[str, Any]:
        """
        Get the full configuration for a specific port.

        Args:
            port: Port number

        Returns:
            Port configuration dictionary
        """
        return self.config["telescope"]["ports"].get(port, {})


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
