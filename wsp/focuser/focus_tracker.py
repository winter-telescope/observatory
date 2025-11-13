#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import logging
import os
import traceback
from datetime import datetime
from typing import Dict, List, Optional

import pytz
import yaml

from wsp.utils.paths import WSP_PATH

CAMERA_ENTRY_KEYS = {
    "camera",
    "focus_filter",
    "nominal_focus",
    "last_focus",
    "last_focus_timestamp_utc",
    "last_focus_time_local",
    # NEW:
    "attempts_since_success",
    "last_attempt_timestamp_utc",
}


class FocusTracker:
    """
    Camera-centric focus tracker.

    Persisted JSON schema (keyed by camera name):
    {
      "<camera>": {
        "camera": "<camera>",
        "focus_filter": "<filterID used for focusing>",
        "nominal_focus": <float|None>,
        "last_focus": <float|None>,
        "last_focus_timestamp_utc": <float|None>,  # unix seconds
        "last_focus_time_local": <str|None>,       # site-tz formatted
        "attempts_since_success": <int>,           # NEW
        "last_attempt_timestamp_utc": <float|None> # NEW (last try; success or fail)
      },
      ...
    }
    """

    def __init__(self, config: dict, logger: Optional[logging.Logger] = None):
        self.config = config
        self.logger = logger

        self.focus_log_path = os.path.join(
            os.getenv("HOME"), self.config["focus_loop_param"]["focus_log_path"]
        )
        self.focus_log: Dict[str, dict] = {}

        self.setupFocusLog()

    # -----------------------------
    # Logging
    # -----------------------------
    def log(self, msg, level=logging.INFO):
        if self.logger is None:
            print(msg)
        else:
            self.logger.log(level=level, msg=msg)

    # -----------------------------
    # File IO / initialization
    # -----------------------------
    def setupFocusLog(self):
        """
        Load the camera-keyed focus log. If the file is missing, empty, or not
        compliant with the camera schema, **delete it** and build a fresh one.
        """

        def _compliant_camera_log(data: dict) -> bool:
            if not isinstance(data, dict) or not data:
                return False
            sample = next(iter(data.values()))
            return isinstance(sample, dict) and CAMERA_ENTRY_KEYS.issubset(
                sample.keys()
            )

        try:
            with open(self.focus_log_path, "r") as f:
                data = json.load(f)
            if _compliant_camera_log(data):
                self.focus_log = data
                self.log("loaded existing camera-aware focus log")
            else:
                self.log("focus log not compliant; deleting and resetting")
                self._delete_log_file()
                self.resetFocusLog()
        except (json.decoder.JSONDecodeError, FileNotFoundError):
            self.log("no usable focus log found; creating a fresh camera-keyed log")
            self.resetFocusLog()

    def _delete_log_file(self):
        try:
            if os.path.exists(self.focus_log_path):
                os.remove(self.focus_log_path)
        except Exception as e:
            self.log(f"failed to delete non-compliant focus log: {e}", logging.WARNING)

    def updateFocusLogFile(self):
        directory = os.path.dirname(self.focus_log_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)
        with open(self.focus_log_path, "w+") as f:
            json.dump(self.focus_log, f, indent=2)

    def resetFocusLog(self, updateFile: bool = True):
        self.log("resetting focus log (camera-keyed)")
        self.focus_log = self._build_default_camera_log()
        if updateFile:
            self.updateFocusLogFile()

    def _build_default_camera_log(self) -> Dict[str, dict]:
        """
        Build from config['focus_loop_param']['cameras'].
        """
        out = {}
        cameras_cfg = self.config["focus_loop_param"].get("cameras", {})
        for cam, info in cameras_cfg.items():
            out[cam] = {
                "camera": cam,
                "focus_filter": info.get("filterID"),
                "nominal_focus": info.get("nominal_focus"),
                "last_focus": None,
                "last_focus_timestamp_utc": None,
                "last_focus_time_local": None,
                # NEW fields
                "attempts_since_success": 0,
                "last_attempt_timestamp_utc": None,
            }
        return out

    # Ensure a camera entry exists
    def _ensure_camera_entry(self, camera: str):
        if camera not in self.focus_log:
            self.focus_log[camera] = {
                "camera": camera,
                "focus_filter": None,
                "nominal_focus": None,
                "last_focus": None,
                "last_focus_timestamp_utc": None,
                "last_focus_time_local": None,
                "attempts_since_success": 0,
                "last_attempt_timestamp_utc": None,
            }

    # -----------------------------
    # Public API (camera-centric)
    # -----------------------------
    def _normalize_timestamp(self, ts):
        if ts == "now":
            return datetime.now(tz=pytz.UTC).timestamp()
        return ts

    def updateCameraFocus(
        self,
        camera: str,
        focus_pos: float,
        timestamp="now",
        used_filter: Optional[str] = None,
    ):
        """
        Record a new (successful) focus result for a camera.
        Resets attempts_since_success to 0.
        """
        self._ensure_camera_entry(camera)
        timestamp = self._normalize_timestamp(timestamp)

        # human-friendly local time
        try:
            utc_dt = datetime.fromtimestamp(timestamp, tz=pytz.utc)
            local_str = datetime.strftime(
                utc_dt.astimezone(tz=pytz.timezone(self.config["site"]["timezone"])),
                "%Y-%m-%d %H:%M:%S.%f",
            )
        except Exception as e:
            self.log(
                f"could not format local timestamp: {e}\n{traceback.format_exc()}",
                level=logging.WARNING,
            )
            local_str = None

        if used_filter is not None:
            self.focus_log[camera]["focus_filter"] = used_filter

        self.focus_log[camera].update(
            {
                "last_focus": focus_pos,
                "last_focus_timestamp_utc": timestamp,
                "last_focus_time_local": local_str,
                "attempts_since_success": 0,  # reset on success
                "last_attempt_timestamp_utc": timestamp,  # the last attempt was this success
            }
        )
        self.updateFocusLogFile()

    def record_focus_attempt(self, camera: str, success: bool, timestamp="now"):
        """
        Record an attempt outcome (success/failure) for a camera.
        - success=True: calls updateCameraFocus(...) semantics (attempts reset).
        - success=False: increments attempts_since_success and updates last_attempt_timestamp_utc.
        """
        self._ensure_camera_entry(camera)
        timestamp = self._normalize_timestamp(timestamp)

        if success:
            # If you also know the best position, call updateCameraFocus directly instead
            # This path just resets attempts without updating a position.
            self.focus_log[camera]["attempts_since_success"] = 0
            self.focus_log[camera]["last_attempt_timestamp_utc"] = timestamp
            self.updateFocusLogFile()
            return

        # failure path
        attempts = self.focus_log[camera].get("attempts_since_success", 0) or 0
        self.focus_log[camera]["attempts_since_success"] = attempts + 1
        self.focus_log[camera]["last_attempt_timestamp_utc"] = timestamp
        self.updateFocusLogFile()

    def getCamerasToFocus(
        self,
        obs_timestamp="now",
        graceperiod_hours: float = 6.0,
        cameras: Optional[List[str]] = None,
        max_attempts: int = 3,
    ) -> Optional[List[str]]:
        """
        Return list of cameras that need focus:
          - never focused, or
          - last focused earlier than graceperiod_hours,
        AND (attempt gating):
          - If attempts_since_success >= max_attempts AND the last attempt was within graceperiod_hours,
            DO NOT include (cool-down). Otherwise include.
        Returns None if nothing needs focus.
        """
        obs_timestamp = self._normalize_timestamp(obs_timestamp)
        grace_s = graceperiod_hours * 3600.0

        if cameras is None:
            cameras = list(self.focus_log.keys())

        needs: List[str] = []
        for cam in cameras:
            e = self.focus_log.get(cam)
            if not e:
                # no record: needs focus
                needs.append(cam)
                continue

            ts_success = e.get("last_focus_timestamp_utc")
            ts_last_attempt = e.get("last_attempt_timestamp_utc")
            attempts = int(e.get("attempts_since_success", 0) or 0)

            # Determine if the camera is stale (needs focus by age)
            is_never_focused = ts_success is None
            is_past_grace = (ts_success is not None) and (
                (obs_timestamp - ts_success) > grace_s
            )
            needs_by_age = is_never_focused or is_past_grace

            if not needs_by_age:
                # Up-to-date; skip
                continue

            # Attempt gating
            if attempts >= max_attempts and ts_last_attempt is not None:
                in_cooldown = (obs_timestamp - ts_last_attempt) <= grace_s
                if in_cooldown:
                    # Hit attempt cap recently; wait for cool-down to expire
                    continue
                # Cool-down window elapsed; eligible again
                # (We don't mutate attempts here; reset will happen on first new attempt/success.)
                needs.append(cam)
            else:
                # Below cap or no recent attempt => eligible
                needs.append(cam)

        return needs or None

    def timeSinceFocus(self, camera: str, now="now") -> Optional[float]:
        """
        Seconds since last focus for a camera, or None if unknown.
        """
        now = self._normalize_timestamp(now)
        entry = self.focus_log.get(camera)
        if not entry:
            return None
        ts = entry.get("last_focus_timestamp_utc")
        if ts is None:
            return None
        return float(now) - float(ts)

    def get_focus_filter(self, camera: str) -> Optional[str]:
        """
        Return the focus filter ID for the given camera.
        Priority:
          1. focus_log entry (may have been updated dynamically)
          2. config['focus_loop_param']['cameras'][camera]['filterID']
          3. None if not found
        """
        # 1. check focus log entry
        if camera in self.focus_log:
            filt = self.focus_log[camera].get("focus_filter")
            if filt:
                return filt

        # 2. fallback to config
        cameras_cfg = self.config["focus_loop_param"].get("cameras", {})
        if camera in cameras_cfg:
            return cameras_cfg[camera].get("filterID")

        # 3. not found
        self.log(f"no focus filter found for camera {camera}", logging.WARNING)
        return None

    # helpers to get focus
    def get_last_focus(self, camera: str) -> Optional[float]:
        """Return the last measured best focus for camera, or None."""
        e = self.focus_log.get(camera)
        if not e:
            return None
        return e.get("last_focus")

    def get_nominal_focus(self, camera: str) -> Optional[float]:
        """Return the nominal (default) focus from config, or None if missing."""
        cam_cfg = (
            self.config.get("focus_loop_param", {}).get("cameras", {}).get(camera, {})
        )
        return cam_cfg.get("nominal_focus")

    def get_best_focus(self, camera: str) -> Optional[float]:
        """
        Programmatic best focus for a camera:
        1) last measured focus if available
        2) else nominal focus from config
        3) else None (and logs a warning)
        """
        last = self.get_last_focus(camera)
        if last is not None:
            return last
        nominal = self.get_nominal_focus(camera)
        if nominal is not None:
            return nominal
        self.log(
            f"no last or nominal focus available for camera '{camera}'", logging.WARNING
        )
        return None

    # Debug helper
    def printFocusLog(self):
        print("Focus Log (camera-keyed):", json.dumps(self.focus_log, indent=2))


if __name__ == "__main__":
    config = yaml.load(
        open(os.path.join(WSP_PATH, "config/config.yaml")), Loader=yaml.FullLoader
    )
    ft = FocusTracker(config)
    ft.printFocusLog()
