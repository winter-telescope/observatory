from flask import Flask, request
from threading import Thread
from datetime import datetime
import sys
import time

# Flask app for HTTP simulation
app = Flask(__name__)

# Simulated telescope state with all real hardware fields
telescope_state = {
    "pwi4": {
        "version": "4.0.11 beta 18",
        "version_field": [4, 0, 11, 18],
    },
    "response": {
        "timestamp_utc": str(datetime.now()),
    },
    "site": {
        "latitude_degs": 33.356,
        "longitude_degs": -116.863,
        "height_meters": 1706,
        "lmst_hours": 13.1019349683461,
    },
    "mount": {
        "is_connected": False,
        "geometry": 0,
        "timestamp_utc": str(datetime.now()),
        "julian_date": 2460635.2033245,
        "slew_time_constant": 0.5,
        "ra_apparent_hours": 13.101869788432,
        "dec_apparent_degs": 76.3257813491194,
        "ra_j2000_hours": 13.0919127072532,
        "dec_j2000_degs": 76.4626467841981,
        "target_ra_apparent_hours": 0,
        "target_dec_apparent_degs": 0,
        "azimuth_degs": 359.999660955666,
        "altitude_degs": 47.0457410047775,
        "is_slewing": False,
        "is_tracking": False,
    },
    "focuser": {
        "is_connected": True,
        "is_enabled": False,
        "position": 11650.4762327022,
        "is_moving": False,
    },
    "rotator": {
        "is_connected": True,
        "is_enabled": False,
        "field_angle_degs": 292.245563757596,
        "is_moving": False,
    },
    "m3": {"port": 1},
    "autofocus": {
        "is_running": False,
        "success": False,
        "best_position": 0,
        "tolerance": 0,
    },
}

def serialize_state_to_bytes():
    """
    Converts the nested dictionary `telescope_state` into a formatted byte string.
    """
    lines = []

    def flatten(prefix, value):
        if isinstance(value, dict):
            for k, v in value.items():
                flatten(f"{prefix}.{k}" if prefix else k, v)
        elif isinstance(value, list):
            for i, v in enumerate(value):
                flatten(f"{prefix}[{i}]", v)
        else:
            lines.append(f"{prefix}={value}")

    flatten("", telescope_state)
    return "\n".join(lines).encode("utf-8")


@app.route("/status", methods=["GET"])
def status():
    telescope_state["response"]["timestamp_utc"] = str(datetime.utcnow())  # Update timestamp
    return serialize_state_to_bytes()


@app.route("/mount/connect", methods=["POST", "GET"])
def mount_connect():
    telescope_state["mount"]["is_connected"] = True
    return serialize_state_to_bytes()


@app.route("/mount/disconnect", methods=["POST", "GET"])
def mount_disconnect():
    telescope_state["mount"]["is_connected"] = False
    return serialize_state_to_bytes()


@app.route("/mount/goto_ra_dec_apparent", methods=["POST", "GET"])
def goto_ra_dec_j2000():
    if not telescope_state["mount"]["is_connected"]:
        return serialize_state_to_bytes()

    ra_hours = float(request.args.get("ra_hours", 0.0))
    dec_degs = float(request.args.get("dec_degs", 0.0))
    telescope_state["mount"]["target_ra_apparent_hours"] = ra_hours
    telescope_state["mount"]["target_dec_apparent_degs"] = dec_degs
    telescope_state["mount"]["is_slewing"] = True

    def simulate_slew():
        while telescope_state["mount"]["is_slewing"]:
            current_ra = telescope_state["mount"]["ra_apparent_hours"]
            current_dec = telescope_state["mount"]["dec_apparent_degs"]
            target_ra = telescope_state["mount"]["target_ra_apparent_hours"]
            target_dec = telescope_state["mount"]["target_dec_apparent_degs"]

            # Simulate RA and DEC slewing towards targets
            if abs(current_ra - target_ra) < 0.01 and abs(current_dec - target_dec) < 0.01:
                telescope_state["mount"]["is_slewing"] = False
                break

            telescope_state["mount"]["ra_apparent_hours"] += (target_ra - current_ra) * 0.1
            telescope_state["mount"]["dec_apparent_degs"] += (target_dec - current_dec) * 0.1
            time.sleep(0.5)

    Thread(target=simulate_slew).start()
    return serialize_state_to_bytes()


@app.route("/rotator/goto_field", methods=["POST", "GET"])
def rotator_goto_field():
    if not telescope_state["rotator"]["is_connected"]:
        return serialize_state_to_bytes()

    target_angle = float(request.args.get("field_angle_degs", 0.0))
    telescope_state["rotator"]["is_moving"] = True

    def simulate_rotator_slew():
        while telescope_state["rotator"]["is_moving"]:
            current_angle = telescope_state["rotator"]["field_angle_degs"]

            if abs(current_angle - target_angle) < 0.01:
                telescope_state["rotator"]["is_moving"] = False
                break

            telescope_state["rotator"]["field_angle_degs"] += (target_angle - current_angle) * 0.1
            time.sleep(0.5)

    Thread(target=simulate_rotator_slew).start()
    return serialize_state_to_bytes()




def start_http_server():
    app.run(host="localhost", port=8220, debug=False, use_reloader=False)


if __name__ == "__main__":
    # Start Flask server in a separate thread
    http_thread = Thread(target=start_http_server)
    http_thread.daemon = True
    http_thread.start()

