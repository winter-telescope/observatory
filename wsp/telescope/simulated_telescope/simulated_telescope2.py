import json
import logging
import os
import sys
import threading
import time
from datetime import datetime

from flask import Flask, request
from PyQt5 import QtCore, QtWidgets

# Flask app for HTTP simulation
flask_app = Flask(__name__)


class FlaskServer(QtCore.QThread):
    """
    QThread to run Flask server in the background.
    """

    def __init__(self, state, parent=None):
        super(FlaskServer, self).__init__(parent)
        self.state = state

    def run(self):
        """
        Start the Flask server.
        """

        @flask_app.route("/mount/connect", methods=["POST", "GET"])
        def mount_connect():
            self.state["mount"]["is_connected"] = True
            self.state["mount"]["timestamp_utc"] = str(datetime.now())
            print("Mount connected")  # Log message
            return self.serialize_state_to_bytes()

        @flask_app.route("/status", methods=["GET"])
        def status():
            self.state["response"]["timestamp_utc"] = str(
                datetime.now()
            )  # Update timestamp
            return self.serialize_state_to_bytes()

        flask_app.run(
            host="localhost", port=8220, debug=False, use_reloader=False, threaded=True
        )

    def serialize_state_to_bytes(self):
        """
        Converts the nested dictionary `state` into a formatted byte string.
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

        flatten("", self.state)
        return "\n".join(lines).encode("utf-8")


class MainWindow(QtWidgets.QMainWindow):
    """This is the main GUI window for the simulated telescope."""

    def __init__(self):
        super(MainWindow, self).__init__()
        self.setWindowTitle("Simulated Telescope")
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)

        self.init_state()

        # Start Flask server in a background thread
        self.flask_thread = FlaskServer(self.state)
        self.flask_thread.start()

        # UI Setup
        self.init_ui()

    def init_state(self):
        """Initialize the simulated telescope state."""
        self.state = {
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

    def init_ui(self):
        """Initialize the UI layout."""
        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)

        layout = QtWidgets.QVBoxLayout()

        self.status_label = QtWidgets.QLabel("Mount Connected: False")
        layout.addWidget(self.status_label)

        connect_button = QtWidgets.QPushButton("Connect Mount")
        connect_button.clicked.connect(self.mount_connect)
        layout.addWidget(connect_button)

        central_widget.setLayout(layout)

    def mount_connect(self):
        """Simulate mount connect."""
        self.state["mount"]["is_connected"] = True
        self.state["mount"]["timestamp_utc"] = str(datetime.now())
        self.status_label.setText("Mount Connected: True")
        self.logger.info("Mount connected")

    def closeEvent(self, event):
        """Handle GUI close event to stop the Flask server."""
        self.flask_thread.terminate()
        self.flask_thread.wait()
        event.accept()


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
