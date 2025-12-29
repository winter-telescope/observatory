# camera/config.py

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Iterator, List, Optional, Tuple


@dataclass
class CameraInfo:
    """
    Camera configuration information extracted from distributed config.
    """

    # Non-defaulted fields FIRST (dataclass requirement)
    name: str
    port: int
    filters: List[str]

    # Defaulted fields after
    daemon_name: Optional[str] = None
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
        Build CameraInfo from the distributed config.
        """

        # --- Find which port this camera is on (new per-camera mapping) ---
        ports = config["telescope"]["ports"]

        def _iter_numbered_ports() -> Iterator[Tuple[int, Dict[str, Any]]]:
            for k, v in ports.items():
                # skip non-numbered keys like "default"
                try:
                    pn = int(k)
                except (ValueError, TypeError):
                    continue
                yield pn, v if isinstance(v, dict) else {}

        port: Optional[int] = None
        for pn, pinfo in _iter_numbered_ports():
            cams = pinfo.get("cameras", {})
            # cameras is now a dict: {camera_name: {pointing_model_file: ...}}
            if isinstance(cams, dict) and camera_name in cams.keys():
                port = pn
                break

        if port is None:
            raise ValueError(f"Camera {camera_name!r} not found in any telescope port")

        # --- Extract filter list (by camera) ---
        filters = list(config.get("filters", {}).get(camera_name, {}).keys())

        # --- Focus filters ---
        focus_filters = (
            config.get("focus_loop_param", {})
            .get("focus_filters", {})
            .get(camera_name, [])
        )

        # --- Calibration params ---
        cal_params = config.get("cal_params", {}).get(camera_name, {})
        dark_exptimes = cal_params.get("darks", {}).get("exptimes", [])
        flat_filters = cal_params.get("flats", {}).get("filterIDs", [])
        domeflat_filters = cal_params.get("domeflats", {}).get("filterIDs", [])

        # --- Observing params ---
        obs_params = config.get("observing_parameters", {}).get(camera_name, {})
        dither_params = obs_params.get("dithers", {})

        # --- Timeouts (optional) ---
        startup_timeout = cal_params.get("startup_timeout", 300.0)
        shutdown_timeout = cal_params.get("shutdown_timeout", 180.0)

        return cls(
            name=camera_name,
            port=port,
            filters=filters,
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
            startup_timeout=startup_timeout,
            shutdown_timeout=shutdown_timeout,
        )


class CameraConfigManager:
    """
    Manages camera configurations and handles port assignments dynamically.
    """

    def __init__(self, config: dict):
        self.config = config
        self._camera_info_cache: Dict[str, CameraInfo] = {}

    # -------- helpers --------
    def _iter_numbered_ports(self) -> Iterator[Tuple[int, Dict[str, Any]]]:
        ports = self.config["telescope"]["ports"]
        for k, v in ports.items():
            try:
                pn = int(k)
            except (ValueError, TypeError):
                continue  # skip "default" and any non-numeric keys
            yield pn, v if isinstance(v, dict) else {}

    # -------- public API --------
    def get_active_cameras(self) -> List[str]:
        return self.config.get("active_cameras", [])

    def get_camera_info(self, camera_name: str) -> CameraInfo:
        if camera_name not in self._camera_info_cache:
            self._camera_info_cache[camera_name] = CameraInfo.from_config(
                camera_name, self.config
            )
        return self._camera_info_cache[camera_name]

    def get_all_camera_info(self) -> List[CameraInfo]:
        infos: List[CameraInfo] = []
        for cam in self.get_active_cameras():
            try:
                infos.append(self.get_camera_info(cam))
            except ValueError as e:
                print(f"Warning: {e}")
        return infos

    def get_cameras_on_port(self, port: int) -> List[str]:
        """Return camera names on a given port (keys of the per-camera mapping)."""
        ports = self.config["telescope"]["ports"]
        pinfo = ports.get(str(port)) or ports.get(port) or {}
        cams = pinfo.get("cameras", {})
        if isinstance(cams, dict):
            return list(cams.keys())
        # Backwards-compat: if someone still has a list, return it
        if isinstance(cams, list):
            return cams
        return []

    def get_port_for_camera(self, camera_name: str) -> Optional[int]:
        """
        Return the port number hosting this camera (None if not found).
        """
        for pn, pinfo in self._iter_numbered_ports():
            cams = pinfo.get("cameras", {})
            if isinstance(cams, dict) and camera_name in cams.keys():
                return pn
            if isinstance(cams, list) and camera_name in cams:
                return pn  # backwards-compat path
        return None

    def get_port_config(self, port: int) -> Dict[str, Any]:
        ports = self.config["telescope"]["ports"]
        return ports.get(str(port)) or ports.get(port) or {}

    # ----- optional conveniences (useful with per-camera pointing models) -----
    def get_camera_pointing_model_file(self, camera_name: str) -> Optional[str]:
        """
        Return the pointing model file for a given camera, with fallbacks:
        1) telescope.ports[port].cameras[camera].pointing_model_file
        2) pointing_model.default_pointing_model_file
        """
        pn = self.get_port_for_camera(camera_name)
        if pn is not None:
            pinfo = self.get_port_config(pn)
            cams = pinfo.get("cameras", {})
            if isinstance(cams, dict):
                cm = cams.get(camera_name, {})
                if isinstance(cm, dict):
                    pm = cm.get("pointing_model_file")
                    if pm:
                        return pm
        # fallback to global default
        return self.config.get("pointing_model", {}).get("default_pointing_model_file")

    def camera_port_map(self) -> Dict[str, int]:
        """Return {camera_name: port} for all ports/cameras in the config."""
        mapping: Dict[str, int] = {}
        for pn, pinfo in self._iter_numbered_ports():
            cams = pinfo.get("cameras", {})
            if isinstance(cams, dict):
                for cam in cams.keys():
                    mapping[cam] = pn
            elif isinstance(cams, list):
                for cam in cams:
                    mapping[cam] = pn
        return mapping


class CameraPort(Enum):
    PORT_1 = 1
    PORT_2 = 2


if __name__ == "__main__":
    import json

    from wsp.utils.paths import CONFIG_PATH
    from wsp.utils.utils import loadconfig

    config = loadconfig(CONFIG_PATH)
    camera_manager = CameraConfigManager(config)

    # some checks:
    print(f"Camera to port mapping: {camera_manager.camera_port_map()}")
    try:
        assert camera_manager.get_port_for_camera("winter") == 1
        assert camera_manager.get_port_for_camera("spring") == 2
        print("All assertions passed")
    except AssertionError:
        print("Assertion failed")

    print("Active cameras:", camera_manager.get_active_cameras())
    for cam in camera_manager.get_active_cameras():
        info = camera_manager.get_camera_info(cam)
        print(f"{cam} info")
        print(json.dumps(info.__dict__, indent=4))

    # get info for a specific camera
    cam_name = "spring"
    cam_info = camera_manager.get_camera_info(cam_name)
    print(f"{cam_name} is on port {cam_info.port} with filters {cam_info.filters}")
