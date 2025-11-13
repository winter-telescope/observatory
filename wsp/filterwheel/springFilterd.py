#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Spring Filter Wheel Daemon

@author: winter
"""

import getopt
import logging
import os
import signal
import sys
import threading
import time
from datetime import datetime

import Pyro5.server
import requests
import yaml
from PyQt5 import QtCore

from wsp.daemon import daemon_utils
from wsp.utils import logging_setup
from wsp.utils.paths import WSP_PATH


class SpringFilterWheel(QtCore.QObject):
    newReply = QtCore.pyqtSignal(int)
    newStatus = QtCore.pyqtSignal(object)
    newCommand = QtCore.pyqtSignal(str)
    updateStateSignal = QtCore.pyqtSignal(object)
    resetCommandPassSignal = QtCore.pyqtSignal(int)

    def __init__(self, config, logger=None, verbose=False):
        super(SpringFilterWheel, self).__init__()

        self.config = config
        self.verbose = verbose
        self.logger = logger
        self.connected = False
        self.command_pass = 0
        self.timestamp = datetime.utcnow().timestamp()
        self.log("initing SpringFilterWheel object")

        # housekeeping attributes
        self.state = dict()

        # connect the update state signal
        self.updateStateSignal.connect(self.updateState)
        self.resetCommandPassSignal.connect(self.resetCommandPass)

        # web interface settings
        self.base_url = config["web_interface"]["base_url"]
        self.request_timeout = config["web_interface"].get("request_timeout", 10)

        # filter wheel settings
        self.filter_positions = config["filters"]["positions"]
        self.dark_filter = config["filters"].get("dark_filter", None)

        # startup values
        self.filter_pos = -1
        self.filter_goal = -1
        self.fw_status = 0
        self.fw_response_code = 0
        self.shutter_open = -1
        self.shutter_status = 0
        self.shutter_response_code = 0
        self.is_moving = 0
        self.homed = 0

        # timers
        self.state_update_dt = config["state_update_dt"]

        ## Startup:
        self.testConnection()
        time.sleep(0.5)
        self.home(verbose=verbose)

    def log(self, msg, level=logging.INFO):
        msg = f"SpringFilterWheel: {msg}"
        if self.logger is None:
            print(msg)
        else:
            self.logger.log(level=level, msg=msg)

    def updateState(self, dict_to_add):
        for key in dict_to_add:
            self.state.update({key: dict_to_add[key]})

    def resetCommandPass(self, val):
        self.log(f"running resetCommandPass: {val}")
        self.command_pass = val
        self.state.update({"command_pass": val})

    def pollStatus(self):
        """Get housekeeping status"""
        self.getStatus()
        self.update_state()

    def update_state(self):
        self.state.update(
            {
                "timestamp": datetime.utcnow().timestamp(),
                "is_moving": self.is_moving,
                "filter_pos": self.filter_pos,
                "filter_goal": self.filter_goal,
                "fw_status": self.fw_status,
                "fw_response_code": self.fw_response_code,
                "shutter_open": self.shutter_open,
                "shutter_status": self.shutter_status,
                "shutter_response_code": self.shutter_response_code,
                "homed": self.homed,
                "connected": self.connected,
            }
        )

        # emit a signal and pass the new state dict out
        self.newStatus.emit(self.state)

    def doCommand(self, cmd_obj):
        """
        Execute commands from signal/slot
        """
        cmd = cmd_obj.cmd
        args = cmd_obj.args
        kwargs = cmd_obj.kwargs

        msg = f"(Thread {threading.get_ident()}: caught doCommand signal: {cmd_obj.cmd}, args = {args}, kwargs = {kwargs}"
        if self.verbose:
            self.log(msg)
        try:
            getattr(self, cmd)(*args, **kwargs)
        except Exception as e:
            self.log(f"Error executing command {cmd}: {e}")

    def testConnection(self):
        """Test connection to web interface"""
        try:
            # Try to get status
            url = f"{self.base_url}/filter_wheel?n=8"
            response = requests.get(url, timeout=self.request_timeout)
            if response.status_code == 200:
                self.connected = True
                self.log("Successfully connected to Spring filter wheel")
            else:
                self.connected = False
                self.log(
                    f"Connection test failed with status code: {response.status_code}"
                )
        except Exception as e:
            self.connected = False
            self.log(f"Connection test failed: {e}")

    def parseResponse(self, response_dict):
        """Parse the JSON response from the web interface"""
        self.filter_pos = response_dict.get("fw_pos", -1)
        self.fw_status = response_dict.get("fw_status", 0)
        self.fw_response_code = response_dict.get("fw_response_code", 0)
        self.shutter_open = response_dict.get("shutter_open", -1)
        self.shutter_status = response_dict.get("shutter_status", 0)
        self.shutter_response_code = response_dict.get("shutter_response_code", 0)

    def getStatus(self, verbose=False):
        """Get current filter wheel status"""
        try:
            url = f"{self.base_url}/filter_wheel?n=8"
            response = requests.get(url, timeout=self.request_timeout)
            if response.status_code == 200:
                response_dict = response.json()
                self.parseResponse(response_dict)
                if verbose:
                    self.log(f"Status: {response_dict}")
                return True
            else:
                self.connected = False
                return False
        except Exception as e:
            self.connected = False
            self.log(f"Error getting status: {e}")
            return False

    def home(self, verbose=False):
        """Home the filter wheel (go to position 0 or 1)"""
        self.log("Homing filter wheel")
        self.homed = 0
        self.is_moving = 1
        self.filter_goal = 0
        self.update_state()

        try:
            # Go to position -1 or 0 (home position)
            url = f"{self.base_url}/filter_wheel?n=-1"
            response = requests.get(url, timeout=self.request_timeout)

            if response.status_code == 200:
                response_dict = response.json()
                self.parseResponse(response_dict)

                # Wait for move to complete
                start_time = time.time()
                timeout = self.config.get("timeout_secs", 60)

                while time.time() - start_time < timeout:
                    self.getStatus()
                    if self.filter_pos in [0, 1] and self.fw_status == 1:
                        self.homed = 1
                        self.is_moving = 0
                        self.log("Homing complete")
                        self.update_state()
                        return True
                    time.sleep(self.state_update_dt)

                self.log("Homing timed out")
                self.is_moving = 0
                self.update_state()
                return False
            else:
                self.log(f"Homing failed with status code: {response.status_code}")
                self.is_moving = 0
                self.update_state()
                return False

        except Exception as e:
            self.log(f"Homing error: {e}")
            self.is_moving = 0
            self.update_state()
            return False

    def goToFilter(self, filter_num, verbose=False):
        """
        Move to specified filter position

        Parameters
        ----------
        filter_num : int
            Filter position (typically 0-6)
        """
        if filter_num not in self.filter_positions:
            self.log(f"Invalid filter position: {filter_num}")
            return False

        self.log(f"Moving to filter {filter_num}")
        self.filter_goal = filter_num
        self.is_moving = 1
        self.update_state()

        try:
            # Move to filter position
            url = f"{self.base_url}/filter_wheel?n={filter_num}"
            response = requests.get(url, timeout=self.request_timeout)

            if response.status_code == 200:
                response_dict = response.json()
                self.parseResponse(response_dict)

                # Handle shutter for dark filter
                if filter_num == self.dark_filter:
                    self.closeShutter()
                else:
                    self.openShutter()

                # Wait for move to complete
                start_time = time.time()
                timeout = self.config.get("timeout_secs", 60)

                while time.time() - start_time < timeout:
                    self.getStatus()
                    if self.filter_pos == filter_num and self.fw_status == 1:
                        self.is_moving = 0
                        self.log(f"Move to filter {filter_num} complete")
                        self.update_state()
                        return True
                    time.sleep(self.state_update_dt)

                self.log("Move timed out")
                self.is_moving = 0
                self.update_state()
                return False
            else:
                self.log(f"Move failed with status code: {response.status_code}")
                self.is_moving = 0
                self.update_state()
                return False

        except Exception as e:
            self.log(f"Move error: {e}")
            self.is_moving = 0
            self.update_state()
            return False

    def openShutter(self, verbose=False):
        """Open the shutter"""
        try:
            url = f"{self.base_url}/shutter?open=1"
            response = requests.get(url, timeout=self.request_timeout)

            if response.status_code == 200:
                response_dict = response.json()
                self.parseResponse(response_dict)
                if verbose:
                    self.log("Shutter opened")
                self.update_state()
                return True
            else:
                self.log(
                    f"Shutter open failed with status code: {response.status_code}"
                )
                return False
        except Exception as e:
            self.log(f"Shutter open error: {e}")
            return False

    def closeShutter(self, verbose=False):
        """Close the shutter"""
        try:
            url = f"{self.base_url}/shutter?open=0"
            response = requests.get(url, timeout=self.request_timeout)

            if response.status_code == 200:
                response_dict = response.json()
                self.parseResponse(response_dict)
                if verbose:
                    self.log("Shutter closed")
                self.update_state()
                return True
            else:
                self.log(
                    f"Shutter close failed with status code: {response.status_code}"
                )
                return False
        except Exception as e:
            self.log(f"Shutter close error: {e}")
            return False

    def goto(self, pos):
        """Alias for goToFilter"""
        return self.goToFilter(pos)


class signalCmd(object):
    """Command object for signal/slot communication"""

    def __init__(self, cmd, *args, **kwargs):
        self.cmd = cmd
        self.args = args
        self.kwargs = kwargs


class CommThread(QtCore.QThread):
    """Communication Thread"""

    newReply = QtCore.pyqtSignal(int)
    newCmdRequest = QtCore.pyqtSignal(object)
    newStatus = QtCore.pyqtSignal(object)
    stopPollTimer = QtCore.pyqtSignal()

    def __init__(self, config, logger=None, verbose=False):
        super(QtCore.QThread, self).__init__()
        self.config = config
        self.logger = logger
        self.verbose = verbose
        print("initing comm thread")

    def HandleCommandRequest(self, cmdRequest):
        self.newCmdRequest.emit(cmdRequest)

    def run(self):
        print("in the run method for the comm thread")

        def SignalNewReply(reply):
            self.newReply.emit(reply)

        def SignalNewStatus(newStatus):
            self.newStatus.emit(newStatus)

        def StopPollTimer():
            print("stopping poll timer")
            self.pollTimer.stop()

        self.fw = SpringFilterWheel(
            config=self.config, logger=self.logger, verbose=self.verbose
        )

        self.newCmdRequest.connect(self.fw.doCommand)
        self.fw.newReply.connect(SignalNewReply)
        self.fw.newStatus.connect(SignalNewStatus)
        self.stopPollTimer.connect(StopPollTimer)

        self.pollTimer = QtCore.QTimer()
        self.pollTimer.setSingleShot(False)
        self.pollTimer.timeout.connect(self.fw.pollStatus)

        poll_interval_ms = 1000
        self.pollTimer.start(poll_interval_ms)

        self.exec_()


class SPRINGfw(QtCore.QObject):
    """Main filter wheel object exposed via Pyro"""

    newCmdRequest = QtCore.pyqtSignal(object)

    def __init__(self, config, logger=None, verbose=False):
        super(SPRINGfw, self).__init__()

        self.config = config
        self.logger = logger
        self.verbose = verbose
        self.state = dict()

        # set up the other threads
        self.commthread = CommThread(
            self.config, logger=self.logger, verbose=self.verbose
        )

        # start up the other threads
        self.commthread.start()

        # set up the signal/slot connections
        self.commthread.newStatus.connect(self.updateStatus)
        self.newCmdRequest.connect(self.commthread.HandleCommandRequest)

    def log(self, msg, level=logging.INFO):
        msg = f"SPRINGfw: {msg}"
        if self.logger is None:
            print(msg)
        else:
            self.logger.log(level=level, msg=msg)

    def updateStatus(self, newStatus):
        """Update local status dictionary"""
        if type(newStatus) is dict:
            for key in newStatus.keys():
                try:
                    self.state.update({key: newStatus[key]})
                except:
                    pass

    @Pyro5.server.expose
    def getStatus(self):
        """Return current status"""
        if self.verbose:
            self.log("got command to return state dict")
        try:
            self.timestamp = datetime.utcnow().timestamp()
            self.state.update({"timestamp": self.timestamp})
        except Exception as e:
            if self.verbose:
                self.log(f"Could not run getStatus: {e}")
            pass
        return self.state

    @Pyro5.server.expose
    def goto(self, pos):
        """Move to filter position"""
        sigcmd = signalCmd("goto", pos)
        self.newCmdRequest.emit(sigcmd)

    @Pyro5.server.expose
    def home(self):
        """Home the filter wheel"""
        sigcmd = signalCmd("home")
        self.newCmdRequest.emit(sigcmd)

    @Pyro5.server.expose
    def goToFilter(self, filter_num):
        """Move to specific filter"""
        sigcmd = signalCmd("goToFilter", filter_num)
        self.newCmdRequest.emit(sigcmd)

    @Pyro5.server.expose
    def openShutter(self):
        """Open the shutter"""
        sigcmd = signalCmd("openShutter")
        self.newCmdRequest.emit(sigcmd)

    @Pyro5.server.expose
    def closeShutter(self):
        """Close the shutter"""
        sigcmd = signalCmd("closeShutter")
        self.newCmdRequest.emit(sigcmd)


class PyroGUI(QtCore.QObject):
    """Main daemon class"""

    def __init__(self, config, ns_host=None, logger=None, verbose=False, parent=None):
        super(PyroGUI, self).__init__(parent)

        self.config = config
        self.ns_host = ns_host
        self.logger = logger
        self.verbose = verbose

        msg = f"(Thread {threading.get_ident()}: Starting up Spring Filter Daemon"
        if logger is None:
            print(msg)
        else:
            logger.info(msg)

        self.fw = SPRINGfw(
            config=self.config,
            logger=self.logger,
            verbose=self.verbose,
        )

        self.pyro_thread = daemon_utils.PyroDaemon(
            obj=self.fw,
            name="SPRINGfw",
            ns_host=self.ns_host,
        )
        self.pyro_thread.start()


def sigint_handler(*args):
    """Handler for the SIGINT signal"""
    sys.stderr.write("\r")
    print("CAUGHT SIGINT, KILLING PROGRAM")

    main.fw.commthread.stopPollTimer.emit()
    time.sleep(0.5)
    main.fw.commthread.quit()

    print("KILLING APPLICATION")
    QtCore.QCoreApplication.quit()


if __name__ == "__main__":
    argumentList = sys.argv[1:]

    verbose = False
    doLogging = True
    ns_host = "192.168.1.10"

    options = "vpn:"
    long_options = ["verbose", "print", "ns_host="]

    try:
        arguments, values = getopt.getopt(argumentList, options, long_options)
        print(f"springfilterd: arguments: {arguments}")

        for currentArgument, currentValue in arguments:
            if currentArgument in ("-v", "--verbose"):
                verbose = True
            elif currentArgument in ("-n", "--ns_host"):
                ns_host = currentValue
            elif currentArgument in ("-p", "--print"):
                doLogging = False

    except getopt.error as err:
        print(str(err))

    print(f"springfilterd: verbose = {verbose}")
    print(f"springfilterd: logging mode = {doLogging}")

    # load the config
    fwconfig = os.path.join(WSP_PATH, "filterwheel", "springfw_config.yaml")
    config = yaml.load(open(fwconfig), Loader=yaml.FullLoader)

    app = QtCore.QCoreApplication(sys.argv)

    if doLogging:
        logger = logging_setup.setup_logger(os.getenv("HOME"), config)
    else:
        logger = None

    main = PyroGUI(config=config, ns_host=ns_host, logger=logger, verbose=verbose)

    signal.signal(signal.SIGINT, sigint_handler)

    timer = QtCore.QTimer()
    timer.start(500)
    timer.timeout.connect(lambda: None)

    sys.exit(app.exec_())
