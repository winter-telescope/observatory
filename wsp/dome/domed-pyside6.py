import sys
import urllib.parse
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer

from PySide6.QtCore import (
    QCoreApplication,
    QEventLoop,
    QMetaObject,
    QObject,
    Qt,
    QThread,
    Signal,
)
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class GUICommunicator(QObject):
    # Signals from the HTTP server requesting GUI updates
    mountConnectedRequested = Signal()
    callExampleMethodRequested = Signal()

    # GUI will emit this once it has updated the state
    stateUpdated = Signal(bytes)


class MainWindow(QMainWindow):
    def __init__(self, communicator):
        super().__init__()
        self.setWindowTitle("PySide6 GUI + QThread HTTP Server with Signals")

        layout = QVBoxLayout()
        self.button = QPushButton("Click Me")
        self.button.clicked.connect(self.example_method)
        layout.addWidget(self.button)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        self.communicator = communicator
        # Connect server requests to GUI slots
        self.communicator.mountConnectedRequested.connect(self.on_mount_connected)
        self.communicator.callExampleMethodRequested.connect(
            self.on_call_example_method_requested
        )

        self.init_state()

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

    def example_method(self):
        # Triggered by GUI or via HTTP request
        print("example_method executed.")

    def on_mount_connected(self):
        # Update GUI state upon mount connection event
        self.state["mount"]["is_connected"] = True
        self.state["mount"]["timestamp_utc"] = str(datetime.now())
        print("Mount connected (updated in GUI). Current state:", self.state)
        # Emit the updated state
        self.communicator.stateUpdated.emit(self.serialize_state_to_bytes())

    def on_call_example_method_requested(self):
        self.example_method()
        # Emit the updated state after the method call
        self.communicator.stateUpdated.emit(self.serialize_state_to_bytes())


class RequestContext(QObject):
    """
    A per-request context object that uses an event loop to wait for stateUpdated signal.
    """

    def __init__(self, communicator, parent=None):
        super().__init__(parent)
        self.communicator = communicator
        self.updatedData = None
        # Connect to stateUpdated signal
        self.communicator.stateUpdated.connect(self.on_state_updated)

    def on_state_updated(self, data: bytes):
        self.updatedData = data
        # Stop the event loop
        QCoreApplication.quit()  # We'll run a local event loop, so we quit that loop

    def wait_for_state(self):
        # Run a local QEventLoop until we get the updated data
        # Use a nested event loop so we don't block the main thread
        loop = QEventLoop()
        # Temporarily disconnect communicator.stateUpdated from self.on_state_updated after loop exit
        # Actually, we don't need disconnection if we rely on this object once per request
        # Start event loop, will quit when on_state_updated calls quit()
        loop.exec()
        return self.updatedData


class RequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path

        if path == "/mount/connect":
            # Create a request context to wait for state updates
            ctx = RequestContext(self.server.communicator)
            # Emit a signal requesting GUI to update state
            self.server.communicator.mountConnectedRequested.emit()
            # Wait for GUI to update state and signal back
            updated_data = ctx.wait_for_state()
            self.respond(200, updated_data)
        else:
            self.respond(404, b"Not Found")

    def do_POST(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path

        if path == "/call_method":
            ctx = RequestContext(self.server.communicator)
            self.server.communicator.callExampleMethodRequested.emit()
            updated_data = ctx.wait_for_state()
            self.respond(200, updated_data)
        else:
            self.respond(404, b"Not Found")

    def respond(self, status, body):
        self.send_response(status)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(body)


class ServerWorker(QObject):
    def __init__(self, communicator, parent=None):
        super().__init__(parent)
        self.communicator = communicator
        self.server = None

    def start_server(self, host="127.0.0.1", port=8220):
        server_address = (host, port)
        self.server = HTTPServer(server_address, RequestHandler)
        # Store communicator on the server so handler can access it
        self.server.communicator = self.communicator
        print(f"HTTP Server started on http://{host}:{port}")
        self.server.serve_forever()

    def stop_server(self):
        if self.server:
            self.server.shutdown()


class ServerThread(QThread):
    def __init__(self, worker, parent=None):
        super().__init__(parent)
        self.worker = worker

    def run(self):
        # This will be executed in a separate thread.
        self.worker.start_server()


if __name__ == "__main__":
    app = QApplication(sys.argv)

    communicator = GUICommunicator()
    main_window = MainWindow(communicator)
    main_window.show()

    # Set up the server worker and thread
    worker = ServerWorker(communicator)
    server_thread = ServerThread(worker)
    server_thread.start()

    sys.exit(app.exec())
