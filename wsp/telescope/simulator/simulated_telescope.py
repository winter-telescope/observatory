import getopt
import os
import sys
import time
import urllib.parse
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer

import Pyro5.core
import Pyro5.server
from astropy import units as u
from astropy.coordinates import ICRS, AltAz, EarthLocation, SkyCoord
from astropy.time import Time
from PySide6.QtCore import QMetaObject, QObject, Qt, QThread, QTimer, Signal
from PySide6.QtWidgets import (
    QApplication,
    QFormLayout,
    QGroupBox,
    QLabel,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

# add the wsp directory to the PATH
wsp_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(1, wsp_path)
print(f"simulated telescope: wsp_path = {wsp_path}")

from simulator.simulated_rotator import (
    get_rotator_field_angle,
    get_rotator_mech_angle,
)


def fmt3(value):
    """Format float to 3 decimal places."""
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


# lat/lon/height for the site
SITE_LATITUDE = "33d21m21.6s"
SITE_LONGITUDE = "-116d51m46.8s"
SITE_HEIGHT = 1706  # meters
SITE = EarthLocation(lat=SITE_LATITUDE, lon=SITE_LONGITUDE, height=SITE_HEIGHT)

# Telescope slew rates
SLEW_RATE = 10.0  # deg/s


class GUICommunicator(QObject):
    # Mount control signals
    mountConnect = Signal()
    mountDisconnect = Signal()
    mountEnableAxis = Signal(int)
    mountDisableAxis = Signal(int)
    mountGotoRaDecJ2000 = Signal(float, float)
    mountGotoAltAz = Signal(float, float)
    mountOffsetAddArcsec = Signal(str, float)
    mountModelLoad = Signal(str)
    mountTrackingOn = Signal()
    mountTrackingOff = Signal()

    # Focuser signals
    mountFocuserEnable = Signal()
    mountFocuserDisable = Signal()
    focuserGoto = Signal(float)

    # Rotator signals
    rotatorGotoField = Signal(float)
    rotatorGotoMech = Signal(float)
    rotatorEnable = Signal()
    rotatorDisable = Signal()

    # M3 signals
    m3Goto = Signal(int)

    # Generic method call
    callExampleMethod = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.currentState = b""  # Will hold the latest serialized state after an action


class MainWindow(QMainWindow):
    def __init__(self, communicator, sunsim=False, ns_host="localhost"):
        super().__init__()
        self.setWindowTitle("PW1000 Telescope Simulator")

        # run in sun simulator mode? this mode needs to connect with a running sun simulator
        self.sunsim = sunsim
        self.ns_host = ns_host
        self.sunsim_connected = False
        self.sunsimState = dict()

        self.communicator = communicator

        # Overall layout
        main_layout = QVBoxLayout()

        #
        # Mount Group
        #
        mount_group = QGroupBox("Mount")
        mount_form = QFormLayout()

        self.label_mount_is_connected = QLabel("False")
        self.label_axis0_is_enabled = QLabel("False")
        self.label_axis1_is_enabled = QLabel("False")
        self.label_mount_azimuth_degs = QLabel("0.0")
        self.label_mount_altitude_degs = QLabel("0.0")
        self.label_mount_ra_j2000_hours = QLabel("0.0")
        self.label_mount_dec_j2000_degs = QLabel("0.0")
        self.label_mount_current_state = QLabel("idle")  # new label for state machine

        mount_form.addRow("Connected:", self.label_mount_is_connected)
        mount_form.addRow("Axis 0 Enabled:", self.label_axis0_is_enabled)
        mount_form.addRow("Axis 1 Enabled:", self.label_axis1_is_enabled)
        mount_form.addRow("Az (deg):", self.label_mount_azimuth_degs)
        mount_form.addRow("Alt (deg):", self.label_mount_altitude_degs)
        mount_form.addRow("RA (hours):", self.label_mount_ra_j2000_hours)
        mount_form.addRow("Dec (deg):", self.label_mount_dec_j2000_degs)
        mount_form.addRow(
            "Mount State:", self.label_mount_current_state
        )  # display state

        mount_group.setLayout(mount_form)
        main_layout.addWidget(mount_group)

        #
        # Focuser Group
        #
        focuser_group = QGroupBox("Focuser")
        focuser_form = QFormLayout()

        self.label_focuser_is_enabled = QLabel("False")
        self.label_focuser_position = QLabel("0.0")

        focuser_form.addRow("Enabled:", self.label_focuser_is_enabled)
        focuser_form.addRow("Position:", self.label_focuser_position)

        focuser_group.setLayout(focuser_form)
        main_layout.addWidget(focuser_group)

        #
        # Rotator Group
        #
        rotator_group = QGroupBox("Rotator")
        rotator_form = QFormLayout()

        self.label_rotator_is_enabled = QLabel("False")
        self.label_rotator_tracking_is_enabled = QLabel("False")
        self.label_rotator_field_angle_degs = QLabel("0.0")
        self.label_rotator_mech_angle_degs = QLabel("0.0")

        rotator_form.addRow("Enabled:", self.label_rotator_is_enabled)
        rotator_form.addRow("Tracking Enabled:", self.label_rotator_tracking_is_enabled)
        rotator_form.addRow("Field Angle (deg):", self.label_rotator_field_angle_degs)
        rotator_form.addRow("Mech Angle (deg):", self.label_rotator_mech_angle_degs)

        rotator_group.setLayout(rotator_form)
        main_layout.addWidget(rotator_group)

        #
        # M3 Group
        #
        m3_group = QGroupBox("M3")
        m3_form = QFormLayout()

        self.label_m3_port = QLabel("1")
        m3_form.addRow("Port:", self.label_m3_port)

        m3_group.setLayout(m3_form)
        main_layout.addWidget(m3_group)

        #
        # Timestamp Section
        #
        timestamp_group = QGroupBox("Timestamp")
        timestamp_form = QFormLayout()

        self.label_timestamp_utc = QLabel("N/A")
        timestamp_form.addRow("UTC:", self.label_timestamp_utc)

        timestamp_group.setLayout(timestamp_form)
        main_layout.addWidget(timestamp_group)

        #
        # Example Button
        #
        self.button = QPushButton("Click Me")
        self.button.clicked.connect(self.example_method)
        main_layout.addWidget(self.button)

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

        # Connect communicator signals to their handlers
        self.connect_signals()

        # Initialize state
        self.init_state()

        # Timer refresh
        self.refresh_dt = 500  # ms
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.on_timer_refresh)
        self.timer.start(self.refresh_dt)

    def connect_signals(self):
        self.communicator.mountConnect.connect(self.mount_connect)
        self.communicator.mountGotoRaDecJ2000.connect(self.mount_goto_ra_dec_j2000)
        self.communicator.mountGotoAltAz.connect(self.mount_goto_alt_az)
        self.communicator.callExampleMethod.connect(self.example_method)
        self.communicator.mountEnableAxis.connect(self.mount_enable)
        self.communicator.mountDisableAxis.connect(self.mount_disable)
        self.communicator.mountFocuserEnable.connect(self.focuser_enable)
        self.communicator.mountFocuserDisable.connect(self.focuser_disable)
        self.communicator.focuserGoto.connect(self.focuser_goto)
        self.communicator.m3Goto.connect(self.m3_goto)
        self.communicator.rotatorGotoField.connect(self.rotator_goto_field)
        self.communicator.rotatorGotoMech.connect(self.rotator_goto_mech)
        self.communicator.rotatorEnable.connect(self.rotator_enable)
        self.communicator.rotatorDisable.connect(self.rotator_disable)
        self.communicator.mountModelLoad.connect(self.mount_model_load)
        self.communicator.mountTrackingOn.connect(self.mount_tracking_on)
        self.communicator.mountTrackingOff.connect(self.mount_tracking_off)
        self.communicator.mountDisconnect.connect(self.mount_disconnect)
        self.communicator.mountOffsetAddArcsec.connect(self.mount_offset_add_arcsec)

    def parse_version(self, version_str):
        parts = version_str.split()

        # The first part (e.g., "4.0.11") always contains the base version numbers.
        major_minor_patch = parts[0].split(".")
        result = [int(x) for x in major_minor_patch]

        # If there's more than one whitespace-separated part,
        # we might have something like "beta 18" at the end.
        # So we check if the second part is "beta" (or any other label)
        # and parse the third part as an integer if it exists.
        if len(parts) >= 3 and parts[1].lower() == "beta":
            result.append(int(parts[2]))

        return result

    def init_state(self):
        """Initialize the telescope state with a new 'current_state' field, now 'slewing' replaced with 'slewing'."""
        pwi4_version = "4.0.11 beta 18"

        self.state = {
            "pwi4": {
                "version": pwi4_version,
                "version_field": self.parse_version(pwi4_version),
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
                "field_angle_here_degs": 0,
                "field_angle_at_target_degs": 0,
                "field_angle_rate_at_target_degs_per_sec": 0,
                "axis0": {
                    "is_enabled": False,
                    "rms_error_arcsec": 0,
                    "dist_to_target_arcsec": 0,
                    "servo_error_arcsec": 0,
                    "position_degs": 0.0,
                },
                "axis1": {
                    "is_enabled": False,
                    "rms_error_arcsec": 0,
                    "dist_to_target_arcsec": 0,
                    "servo_error_arcsec": 0,
                    "position_degs": 0.0,
                },
                "model": {
                    "filename": "model.dat",
                    "num_points_total": 0,
                    "num_points_enabled": 0,
                    "rms_error_arcsec": 0,
                },
                # Things not parsed by PWI4 but used for internal logic
                "current_state": "idle",  # idle, tracking, or slewing
                "target_ra_j2000_hours": None,
                "target_dec_j2000_degs": None,
                "target_alt_degs": None,
                "target_az_degs": None,
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
                "mech_position_degs": 65.5,
                "is_moving": False,
                "is_slewing": False,
                # Things not parsed by PWI4 but used for internal logic
                "is_tracking": False,
            },
            "m3": {"port": 1},
            "autofocus": {
                "is_running": False,
                "success": False,
                "best_position": 0,
                "tolerance": 0,
            },
        }

        self.update_gui_display()

    def init_sunsim_remote_object(self):
        try:
            ns = Pyro5.core.locate_ns(host=self.ns_host)
            uri = ns.lookup("sunsim")
            self.sunsim_remote_object = Pyro5.client.Proxy(uri)
            self.sunsim_connected = True
        except Exception as e:
            self.sunsim_connected = False
            print(f"connection with sunsim remote object failed: {e}")

    def _get_time(self):
        if self.sunsim:
            if not self.sunsim_connected:
                self.init_sunsim_remote_object()
                # the sunsim state isn't working yet, just return the real current time
            else:
                try:
                    self.sunsimState = self.sunsim_remote_object.GetStatus()
                    if self.verbose:
                        print(f"sunsim state: {self.sunsimState}")
                except Exception as e:
                    self.sunsim_connected = False

            timestamp = self.sunsimState.get("timestamp", datetime.utcnow().timestamp())
            return Time(datetime.fromtimestamp(timestamp), location=SITE)

        else:
            return Time(datetime.utcnow(), location=SITE)

    def _update_mount_state(self, dt=0.5):
        mount = self.state["mount"]
        current_state = mount["current_state"]

        if current_state == "slewing":
            self._update_slewing(dt)
        elif mount["is_tracking"]:
            mount["current_state"] = "tracking"
            self._update_tracking(dt)
        else:
            mount["current_state"] = "idle"
            self._update_idle(dt)

    def _update_idle(self, dt):
        """
        Idle: Alt/Az fixed, but RA/Dec changes due to Earth's rotation.
        """
        mount = self.state["mount"]
        rotator = self.state["rotator"]
        alt = mount["altitude_degs"]
        az = mount["azimuth_degs"]

        altaz_frame = AltAz(obstime=self.now, location=SITE)

        altaz = SkyCoord(alt=alt * u.deg, az=az * u.deg, frame=altaz_frame)
        icrs = altaz.icrs  # convert to RA/Dec

        mount["ra_j2000_hours"] = icrs.ra.hour
        mount["dec_j2000_degs"] = icrs.dec.deg

        # Update field angle
        field_angle = get_rotator_field_angle(
            SITE,
            mount["ra_j2000_hours"],
            mount["dec_j2000_degs"],
            rotator["mech_position_degs"],
            port=self.state["m3"]["port"],
            obstime=self.now,
        )
        mount["field_angle_here_degs"] = field_angle
        rotator["field_angle_degs"] = field_angle

    def _update_tracking(self, dt):
        """
        Tracking: RA/Dec is fixed, but Alt/Az changes with Earth’s rotation.
        """
        mount = self.state["mount"]
        rotator = self.state["rotator"]
        ra = mount["ra_j2000_hours"]
        dec = mount["dec_j2000_degs"]

        icrs = SkyCoord(ra=ra * u.hour, dec=dec * u.deg, frame="icrs")
        altaz_frame = AltAz(obstime=self.now, location=SITE)
        altaz = icrs.transform_to(altaz_frame)

        mount["azimuth_degs"] = altaz.az.deg
        mount["altitude_degs"] = altaz.alt.deg

        # If the rotator is tracking, update the mechanical angle from the current field angle
        if rotator["is_tracking"]:
            rotator["mech_position_degs"] = get_rotator_mech_angle(
                SITE,
                ra,
                dec,
                rotator["field_angle_degs"],
                port=self.state["m3"]["port"],
                obstime=self.now,
            )
            mount["field_angle_here_degs"] = rotator["field_angle_degs"]
        else:
            # update the field angle based on the current (fixed) mechanical angle
            rotator["field_angle_degs"] = get_rotator_field_angle(
                SITE,
                ra,
                dec,
                rotator["mech_position_degs"],
                port=self.state["m3"]["port"],
                obstime=self.now,
            )
            mount["field_angle_here_degs"] = rotator["field_angle_degs"]

    def _update_slewing(self, dt):
        """
        Slewing logic with RA/Dec or Alt/Az, plus:
          (1) Update RA/Dec from Alt/Az each time if slewing in alt/az
          (2) Automatically switch to tracking if it's a RA/Dec goto
        """
        mount = self.state["mount"]

        # Are we slewing in RA/Dec space?
        if (
            mount["target_ra_j2000_hours"] is not None
            and mount["target_dec_j2000_degs"] is not None
        ):

            # Step RA/Dec
            step = SLEW_RATE * dt
            diff_ra = mount["target_ra_j2000_hours"] - mount["ra_j2000_hours"]
            if abs(diff_ra) < step / 15.0:
                mount["ra_j2000_hours"] = mount["target_ra_j2000_hours"]
            else:
                mount["ra_j2000_hours"] += (step / 15.0) * (1 if diff_ra > 0 else -1)

            diff_dec = mount["target_dec_j2000_degs"] - mount["dec_j2000_degs"]
            if abs(diff_dec) < step:
                mount["dec_j2000_degs"] = mount["target_dec_j2000_degs"]
            else:
                mount["dec_j2000_degs"] += step * (1 if diff_dec > 0 else -1)

            # Recalculate Alt/Az from updated RA/Dec
            icrs = SkyCoord(
                ra=mount["ra_j2000_hours"] * u.hour,
                dec=mount["dec_j2000_degs"] * u.deg,
                frame="icrs",
            )
            altaz_frame = AltAz(obstime=self.now, location=SITE)
            altaz = icrs.transform_to(altaz_frame)
            mount["azimuth_degs"] = altaz.az.deg
            mount["altitude_degs"] = altaz.alt.deg

            # Check arrival
            arrived = (mount["ra_j2000_hours"] == mount["target_ra_j2000_hours"]) and (
                mount["dec_j2000_degs"] == mount["target_dec_j2000_degs"]
            )
            if arrived:
                # (2) Automatically switch to tracking on RA/Dec goto
                mount["is_tracking"] = True
                mount["current_state"] = "tracking"
                mount["target_ra_j2000_hours"] = None
                mount["target_dec_j2000_degs"] = None

        # Are we slewing in Alt/Az space?
        elif (
            mount["target_alt_degs"] is not None and mount["target_az_degs"] is not None
        ):

            step = SLEW_RATE * dt
            diff_alt = mount["target_alt_degs"] - mount["altitude_degs"]
            if abs(diff_alt) < step:
                mount["altitude_degs"] = mount["target_alt_degs"]
            else:
                mount["altitude_degs"] += step * (1 if diff_alt > 0 else -1)

            diff_az = mount["target_az_degs"] - mount["azimuth_degs"]
            if abs(diff_az) < step:
                mount["azimuth_degs"] = mount["target_az_degs"]
            else:
                mount["azimuth_degs"] += step * (1 if diff_az > 0 else -1)

            # (1) Update RA/Dec from current Alt/Az each iteration
            altaz_frame = AltAz(obstime=self.now, location=SITE)
            altaz = SkyCoord(
                alt=mount["altitude_degs"] * u.deg,
                az=mount["azimuth_degs"] * u.deg,
                frame=altaz_frame,
            )
            icrs = altaz.icrs
            mount["ra_j2000_hours"] = icrs.ra.hour
            mount["dec_j2000_degs"] = icrs.dec.deg

            # Check arrival
            arrived = (mount["altitude_degs"] == mount["target_alt_degs"]) and (
                mount["azimuth_degs"] == mount["target_az_degs"]
            )
            if arrived:
                if mount["is_tracking"]:
                    mount["current_state"] = "tracking"
                else:
                    mount["current_state"] = "idle"
                mount["target_alt_degs"] = None
                mount["target_az_degs"] = None

    def on_timer_refresh(self):
        mount = self.state["mount"]
        last_timestamp = mount.get("timestamp_utc", None)
        self.now = self._get_time()
        mount["timestamp_utc"] = self.now.isot
        if last_timestamp is not None:
            elapsed_time = (
                self.now.datetime - datetime.fromisoformat(last_timestamp)
            ).total_seconds()
        else:
            elapsed_time = self.refresh_dt / 1000
        self._update_mount_state(elapsed_time)
        self.update_gui_display()

    def update_gui_display(self):
        mount = self.state["mount"]
        focuser = self.state["focuser"]
        rotator = self.state["rotator"]
        m3 = self.state["m3"]

        self.label_mount_is_connected.setText(str(mount["is_connected"]))
        self.label_axis0_is_enabled.setText(str(mount["axis0"]["is_enabled"]))
        self.label_axis1_is_enabled.setText(str(mount["axis1"]["is_enabled"]))
        self.label_mount_azimuth_degs.setText(fmt3(mount["azimuth_degs"]))
        self.label_mount_altitude_degs.setText(fmt3(mount["altitude_degs"]))
        self.label_mount_ra_j2000_hours.setText(fmt3(mount["ra_j2000_hours"]))
        self.label_mount_dec_j2000_degs.setText(fmt3(mount["dec_j2000_degs"]))

        # Show the current machine state
        self.label_mount_current_state.setText(mount["current_state"])

        self.label_focuser_is_enabled.setText(str(focuser["is_enabled"]))
        self.label_focuser_position.setText(fmt3(focuser["position"]))

        self.label_rotator_is_enabled.setText(str(rotator["is_enabled"]))
        self.label_rotator_tracking_is_enabled.setText(str(rotator["is_tracking"]))
        self.label_rotator_field_angle_degs.setText(fmt3(rotator["field_angle_degs"]))
        self.label_rotator_mech_angle_degs.setText(fmt3(rotator["mech_position_degs"]))

        self.label_m3_port.setText(str(m3["port"]))

        # Timestamp
        timestamp_utc = mount.get("timestamp_utc", "N/A")
        self.label_timestamp_utc.setText(timestamp_utc)

    def serialize_state_to_bytes(self):
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
        print("example_method executed.")
        self.communicator.currentState = self.serialize_state_to_bytes()
        self.update_gui_display()

    # State event handlers
    def mount_connect(self):
        mount = self.state["mount"]
        mount["is_connected"] = True
        mount["timestamp_utc"] = str(datetime.now())
        print("Mount connected.")
        self.communicator.currentState = self.serialize_state_to_bytes()
        self.update_gui_display()

    def mount_goto_ra_dec_j2000(self, ra_hours, dec_deg):
        mount = self.state["mount"]
        mount["target_ra_j2000_hours"] = ra_hours
        mount["target_dec_j2000_degs"] = dec_deg
        mount["current_state"] = "slewing"
        print("Mount slewing to RA/Dec J2000:", ra_hours, dec_deg)
        self.communicator.currentState = self.serialize_state_to_bytes()
        self.update_gui_display()

    def mount_goto_alt_az(self, alt_degs, az_degs):
        mount = self.state["mount"]
        mount["target_alt_degs"] = alt_degs
        mount["target_az_degs"] = az_degs
        mount["current_state"] = "slewing"
        print("Mount slewing to Alt/Az:", alt_degs, az_degs)
        self.communicator.currentState = self.serialize_state_to_bytes()
        self.update_gui_display()

    def mount_tracking_on(self):
        mount = self.state["mount"]
        mount["is_tracking"] = True
        # If not slewing, we switch to "tracking"
        if mount["current_state"] != "slewing":
            mount["current_state"] = "tracking"
        print("Mount tracking enabled")
        self.communicator.currentState = self.serialize_state_to_bytes()
        self.update_gui_display()

    def mount_tracking_off(self):
        mount = self.state["mount"]
        mount["is_tracking"] = False
        # If not slewing, revert to "idle"
        if mount["current_state"] != "slewing":
            mount["current_state"] = "idle"
        print("Mount tracking disabled")
        self.communicator.currentState = self.serialize_state_to_bytes()
        self.update_gui_display()

    def mount_disconnect(self):
        mount = self.state["mount"]
        mount["is_connected"] = False
        mount["current_state"] = "idle"
        print("Mount disconnected")
        self.communicator.currentState = self.serialize_state_to_bytes()
        self.update_gui_display()

    def mount_enable(self, axisNum):
        mount = self.state["mount"]
        axis_key = "axis" + str(axisNum)
        mount[axis_key]["is_enabled"] = True
        print(f"Mount axis {axisNum} enabled")
        self.communicator.currentState = self.serialize_state_to_bytes()
        self.update_gui_display()

    def mount_disable(self, axisNum):
        mount = self.state["mount"]
        axis_key = "axis" + str(axisNum)
        mount[axis_key]["is_enabled"] = False
        print(f"Mount axis {axisNum} disabled")
        self.communicator.currentState = self.serialize_state_to_bytes()
        self.update_gui_display()

    def mount_offset_add_arcsec(self, axis, offset):
        print("Mount axis", axis, "offset by", offset, "arcsec")
        self.communicator.currentState = self.serialize_state_to_bytes()
        self.update_gui_display()

    def focuser_enable(self):
        self.state["focuser"]["is_enabled"] = True
        print("Focuser enabled")
        self.communicator.currentState = self.serialize_state_to_bytes()
        self.update_gui_display()

    def focuser_disable(self):
        self.state["focuser"]["is_enabled"] = False
        print("Focuser disabled")
        self.communicator.currentState = self.serialize_state_to_bytes()
        self.update_gui_display()

    def focuser_goto(self, target):
        self.state["focuser"]["position"] = target
        print("Focuser moving to position", target)
        self.communicator.currentState = self.serialize_state_to_bytes()
        self.update_gui_display()

    def m3_goto(self, target_port):
        self.state["m3"]["port"] = target_port
        print("M3 port set to", target_port)
        self.communicator.currentState = self.serialize_state_to_bytes()
        self.update_gui_display()

    def rotator_goto_field(self, field_angle):
        self.state["rotator"]["field_angle_degs"] = field_angle
        print("Rotator slewing to field angle:", field_angle)
        # now turn on the rotator tracking
        self.state["rotator"]["is_tracking"] = True
        self.communicator.currentState = self.serialize_state_to_bytes()
        self.update_gui_display()

    def rotator_goto_mech(self, mech_angle):
        self.state["rotator"]["mech_position_degs"] = mech_angle
        # now turn off the rotator tracking
        self.state["rotator"]["is_tracking"] = False
        print("Rotator slewing to mechanical angle:", mech_angle)
        self.communicator.currentState = self.serialize_state_to_bytes()
        self.update_gui_display()

    def rotator_enable(self):
        self.state["rotator"]["is_enabled"] = True
        # enable with tracking off
        self.state["rotator"]["is_tracking"] = False
        print("Rotator enabled")
        self.communicator.currentState = self.serialize_state_to_bytes()
        self.update_gui_display()

    def rotator_disable(self):
        self.state["rotator"]["is_enabled"] = False
        self.state["rotator"]["is_tracking"] = False
        print("Rotator disabled")
        self.communicator.currentState = self.serialize_state_to_bytes()
        self.update_gui_display()

    def mount_model_load(self, filename):
        self.state["mount"]["model"]["filename"] = filename
        print("Mount model loaded:", filename)
        self.communicator.currentState = self.serialize_state_to_bytes()
        self.update_gui_display()


class RequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        print(f"Received GET request for {path}")

        if path == "/status":
            # Return the current state as is
            self.respond(200, self.server.communicator.currentState)

        elif path == "/temperatures/pw1000":
            # return a string like this:
            self.respond(
                200,
                b"temperature.primary=8.926\r\ntemperature.secondary=8.926\r\ntemperature.m3=25.0\r\ntemperature.ambient=12.67\r\n",
            )

        elif path == "/mount/connect":
            self.server.communicator.currentState = b""
            self.server.communicator.mountConnect.emit()
            self.wait_for_state_update()
            self.respond(200, self.server.communicator.currentState)

        elif path == "/mount/disconnect":
            self.server.communicator.currentState = b""
            self.server.communicator.mountDisconnect.emit()
            self.wait_for_state_update()
            self.respond(200, self.server.communicator.currentState)

        elif path == "/rotator/goto_field":
            # e.g. /rotator/goto_field?degs=123.45
            query = urllib.parse.parse_qs(parsed_url.query)
            field_angle = float(query["degs"][0])
            self.server.communicator.currentState = b""
            self.server.communicator.rotatorGotoField.emit(field_angle)
            self.wait_for_state_update()
            self.respond(200, self.server.communicator.currentState)

        elif path == "/rotator/goto_mech":
            # e.g. /rotator/goto_mech?degs=123.45
            query = urllib.parse.parse_qs(parsed_url.query)
            field_angle = float(query["degs"][0])
            self.server.communicator.currentState = b""
            self.server.communicator.rotatorGotoMech.emit(field_angle)
            self.wait_for_state_update()
            self.respond(200, self.server.communicator.currentState)

        elif path == "/mount/goto_ra_dec_j2000":
            # e.g. /mount/goto_ra_dec_j2000?ra_hours=12.34&dec_degs=56.78
            query = urllib.parse.parse_qs(parsed_url.query)
            ra_hours = float(query["ra_hours"][0])
            dec_degs = float(query["dec_degs"][0])
            self.server.communicator.currentState = b""
            self.server.communicator.mountGotoRaDecJ2000.emit(ra_hours, dec_degs)
            self.wait_for_state_update()
            self.respond(200, self.server.communicator.currentState)

        elif path == "/mount/enable":
            # e.g. /mount/enable?axis=0
            query = urllib.parse.parse_qs(parsed_url.query)
            axis_num = int(query["axis"][0])
            self.server.communicator.currentState = b""
            self.server.communicator.mountEnableAxis.emit(axis_num)
            self.wait_for_state_update()
            self.respond(200, self.server.communicator.currentState)

        elif path == "/mount/disable":
            # e.g. /mount/disable?axis=1
            query = urllib.parse.parse_qs(parsed_url.query)
            axis_num = int(query["axis"][0])
            self.server.communicator.currentState = b""
            self.server.communicator.mountDisableAxis.emit(axis_num)
            self.wait_for_state_update()
            self.respond(200, self.server.communicator.currentState)

        elif path == "/focuser/enable":
            self.server.communicator.currentState = b""
            self.server.communicator.mountFocuserEnable.emit()
            self.wait_for_state_update()
            self.respond(200, self.server.communicator.currentState)

        elif path == "/focuser/disable":
            self.server.communicator.currentState = b""
            self.server.communicator.mountFocuserDisable.emit()
            self.wait_for_state_update()
            self.respond(200, self.server.communicator.currentState)

        elif path == "/focuser/goto":
            # e.g. /focuser/goto?target=12345
            query = urllib.parse.parse_qs(parsed_url.query)
            target = float(query["target"][0])
            self.server.communicator.currentState = b""
            self.server.communicator.focuserGoto.emit(target)
            self.wait_for_state_update()
            self.respond(200, self.server.communicator.currentState)

        elif path == "/rotator/enable":
            self.server.communicator.currentState = b""
            self.server.communicator.rotatorEnable.emit()
            self.wait_for_state_update()
            self.respond(200, self.server.communicator.currentState)

        elif path == "/rotator/disable":
            self.server.communicator.currentState = b""
            self.server.communicator.rotatorDisable.emit()
            self.wait_for_state_update()
            self.respond(200, self.server.communicator.currentState)

        elif path == "/mount/model/load":
            # e.g. /mount/model/load?filename=model.dat
            query = urllib.parse.parse_qs(parsed_url.query)
            filename = query["filename"][0]
            self.server.communicator.currentState = b""
            self.server.communicator.mountModelLoad.emit(filename)
            self.wait_for_state_update()
            self.respond(200, self.server.communicator.currentState)

        elif path == "/mount/tracking_on":
            self.server.communicator.currentState = b""
            self.server.communicator.mountTrackingOn.emit()
            self.wait_for_state_update()
            self.respond(200, self.server.communicator.currentState)

        elif path == "/mount/tracking_off":
            self.server.communicator.currentState = b""
            self.server.communicator.mountTrackingOff.emit()
            self.wait_for_state_update()
            self.respond(200, self.server.communicator.currentState)

        elif path == "/mount/goto_alt_az":
            # e.g. /mount/goto_alt_az?alt_degs=30.5&az_degs=179.3
            query = urllib.parse.parse_qs(parsed_url.query)
            alt_degs = float(query["alt_degs"][0])
            az_degs = float(query["az_degs"][0])
            self.server.communicator.currentState = b""
            self.server.communicator.mountGotoAltAz.emit(alt_degs, az_degs)
            self.wait_for_state_update()
            self.respond(200, self.server.communicator.currentState)

        elif path == "/m3/goto":
            # e.g. /m3/goto?port=2
            query = urllib.parse.parse_qs(parsed_url.query)
            port_num = int(query["port"][0])
            self.server.communicator.currentState = b""
            self.server.communicator.m3Goto.emit(port_num)
            self.wait_for_state_update()
            self.respond(200, self.server.communicator.currentState)

        elif path == "/mount/offset":
            # e.g. /mount/offset?ra_add_arcsec=-30
            # or /mount/offset?dec_add_arcsec=15
            query = urllib.parse.parse_qs(parsed_url.query)
            command = list(query.keys())[0]
            axis = command.split("_")[0]
            action = command.split(f"{axis}_")[1]
            print(f"Received offset command for {axis} axis: {action}")
            if action == "add_arcsec":
                offset = float(query[command][0])
                self.server.communicator.currentState = b""
                self.server.communicator.mountOffsetAddArcsec.emit(axis, offset)
                self.wait_for_state_update()
                self.respond(200, self.server.communicator.currentState)

        else:
            self.respond(404, b"Not Found")

    def do_POST(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path

        if path == "/call_method":
            # Reset currentState so we know when it's updated
            self.server.communicator.currentState = b""
            QMetaObject.invokeMethod(
                self.server.communicator, "callExampleMethod", Qt.QueuedConnection
            )
            # Wait until the state is updated
            self.wait_for_state_update()
            self.respond(200, self.server.communicator.currentState)
        else:
            self.respond(404, b"Not Found")

    def wait_for_state_update(self):
        # Busy-wait until communicator.currentState is not empty
        while not self.server.communicator.currentState:
            time.sleep(0.01)

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

    # parse command line arguments

    args = sys.argv[1:]
    # set the defaults
    verbose = False
    doLogging = True
    ns_host = "localhost"
    sunsim = False

    options = "vpn:s"
    long_options = ["verbose", "print", "ns_host:", "sunsim"]
    arguments, values = getopt.getopt(args, options, long_options)

    # checking each argument
    print()
    print("Parsing sys.argv...")
    print(f"arguments = {arguments}")
    print(f"values = {values}")
    for currentArgument, currentValue in arguments:
        if currentArgument in ("-v", "--verbose"):
            verbose = True
            print("Running in VERBOSE mode")

        elif currentArgument in ("-p", "--print"):
            doLogging = False
            print("Running in PRINT mode (instead of log mode).")

        elif currentArgument in ("-n", "--ns_host"):
            ns_host = currentValue

        elif currentArgument in ("-s", "--sunsim"):
            sunsim = True

    print(f"Launching telescope simulator with sunsim={sunsim}")

    app = QApplication(sys.argv)

    communicator = GUICommunicator()
    main_window = MainWindow(communicator, sunsim=sunsim, ns_host=ns_host)
    main_window.show()

    # Set up the server worker and thread
    worker = ServerWorker(communicator)
    server_thread = ServerThread(worker)
    server_thread.start()

    sys.exit(app.exec())
