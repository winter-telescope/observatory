#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Standalone web server for the SUMMER (ZWO EFW) filter wheel.

Runs on the viscam raspberry pi ALONGSIDE the legacy web_server.py (which
serves the spring FLI wheel + shutter on port 5001 under the pi's system
python 3.9, and must not be disturbed). This server runs on PORT 5002
under a NEWER python (>= 3.12, e.g. a miniforge env) because the zwo_efw
package requires it.

Deployment on the pi:
    1. install miniforge (aarch64/armv7), create an env with python >= 3.12
    2. <env python> -m pip install flask \
           git+https://github.com/mit-kavli-institute/python-zwo-efw-filter-wheel.git@main
    3. install the ZWO udev rules (bundled in the zwo_efw repo under
       zwo_efw/efw_sdk/EFW_SDK/EFW_linux_mac_SDK_V1.7/lib/efw.rules) into
       /etc/udev/rules.d/ and `sudo udevadm control --reload-rules`
       (without this, EFW initialize() fails with EFW_ERROR_REMOVED)
    4. add a cron keepalive line mirroring web_server.py's, pointing the
       new env's python at this script
    5. curl "http://localhost:5002/summer_filter_wheel?n=0" to verify

Protocol (matches wsp/filterwheel/summerFilterd.py; summer slots are
1-INDEXED, matching the labels printed on the physical ZWO wheel — the
poll sentinel is n=0, which can never collide with a slot number):
    n=0       : return current status (position refreshed live)
    n=-1      : home (move to slot 1; the EFW self-calibrates on power-up)
    n=1..N    : go to slot n, blocking until settled
Response codes:
    0  : command succeeds
    -2 : parameter is bad
    -3 : command cannot be executed at the current time
    -4 : could not communicate with device
"""

import json

from flask import Flask, request

app = Flask(__name__)

app.logger.info("starting up the summer filter wheel server")

# Same key names as the legacy /filter_wheel endpoint so the WSP-side
# daemons share parsing code.
SUMMER_FW_STATE = {
    "fw_pos": -1,
    "fw_status": 0,
    "fw_response_code": 0,
}

# persistent handle to the ZWO wheel (opened lazily, reopened on error)
_SUMMER_EFW = None  # zwo_efw.EFW instance
_SUMMER_EFW_INFO = None  # zwo_efw.EFWInformation for the (only) wheel

SUMMER_FW_MOVE_TIMEOUT = 30  # seconds


def _get_summer_fw():
    """Lazily initialize (and cache) the ZWO EFW connection.

    Returns (efw, info) where efw is the zwo_efw.EFW instance and info is
    the EFWInformation (with .ID and .NumberOfSlots) of the first — and
    only — wheel on this pi. Raises on failure.
    """
    global _SUMMER_EFW, _SUMMER_EFW_INFO
    if _SUMMER_EFW is None:
        from zwo_efw import EFW

        efw = EFW()
        efw.initialize()
        wheels = efw.filter_wheel_information
        if not wheels:
            efw.close()
            raise RuntimeError("no ZWO EFW filter wheels found")
        _SUMMER_EFW = efw
        _SUMMER_EFW_INFO = wheels[0]
    return _SUMMER_EFW, _SUMMER_EFW_INFO


def _drop_summer_fw():
    """Drop the cached EFW handle so the next request reopens it."""
    global _SUMMER_EFW, _SUMMER_EFW_INFO
    if _SUMMER_EFW is not None:
        try:
            _SUMMER_EFW.close()
        except Exception:
            pass
        _SUMMER_EFW = None
        _SUMMER_EFW_INFO = None


def _summer_fw_position(efw, info):
    """Current slot as an int; -1 while the wheel is moving.

    zwo_efw is 1-INDEXED (matches the labels on the physical wheel):
    get_position returns 1..N, or None mid-move (normalized to -1 here to
    match the legacy endpoint's "moving" convention).
    """
    pos = efw.get_position(info.ID)
    if pos is None:
        return -1
    return int(pos)


@app.route("/summer_filter_wheel", methods=["GET"])
def get_summer_filter_command():
    """See module docstring for the command/response conventions.

    NOTE: EFW moves are asynchronous at the SDK level; this endpoint uses
    zwo_efw's set_position(wait_until_done=True) so it blocks until the
    wheel settles. NEVER pass 0-indexed values to zwo_efw.set_position:
    slot-1 goes to the SDK, and an SDK position of -1 triggers a ~30 s
    calibration spin.
    """
    try:
        n = request.args.get("n")
        n = int(n)
    except (TypeError, ValueError):
        SUMMER_FW_STATE.update({"fw_pos": -9, "fw_status": 0, "fw_response_code": -2})
        return json.dumps(SUMMER_FW_STATE)

    try:
        efw, info = _get_summer_fw()

        if n == 0:
            # status poll: refresh the position live (cheap USB query);
            # -1 means the wheel is moving
            pos = _summer_fw_position(efw, info)
            SUMMER_FW_STATE.update(
                {"fw_pos": pos, "fw_status": 1, "fw_response_code": 0}
            )
            return json.dumps(SUMMER_FW_STATE)

        if n == -1:
            # home: the EFW self-calibrates on power-up; land on slot 1
            n = 1

        if 1 <= n <= info.NumberOfSlots:
            try:
                efw.set_position(
                    info.ID,
                    n,
                    wait_until_done=True,
                    timeout_seconds=SUMMER_FW_MOVE_TIMEOUT,
                )
                SUMMER_FW_STATE.update(
                    {
                        "fw_pos": _summer_fw_position(efw, info),
                        "fw_status": 1,
                        "fw_response_code": 0,
                    }
                )
            except Exception as e:
                print(f"error setting summer fw pos: {e}")
                SUMMER_FW_STATE.update(
                    {"fw_pos": -9, "fw_status": 0, "fw_response_code": -3}
                )
            return json.dumps(SUMMER_FW_STATE)

        # not a valid command
        SUMMER_FW_STATE.update({"fw_pos": -9, "fw_status": 0, "fw_response_code": -2})
        return json.dumps(SUMMER_FW_STATE)

    except Exception as e:
        print(f"error communicating with summer filter wheel: {e}")
        # drop the cached handle so the next request retries from scratch
        _drop_summer_fw()
        SUMMER_FW_STATE.update({"fw_pos": -9, "fw_status": 0, "fw_response_code": -4})
        return json.dumps(SUMMER_FW_STATE), 403


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002)
