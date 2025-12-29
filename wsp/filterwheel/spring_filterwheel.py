#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Spring Filter Wheel Client

@author: winterpi
"""

import json
import logging
import time

import Pyro5.client
import Pyro5.core
import Pyro5.errors
from PyQt5 import QtCore

from wsp.utils import logging_setup, utils
from wsp.utils.paths import WSP_PATH


class local_filterwheel(QtCore.QObject):
    """
    Client for Spring filter wheel daemon
    """

    newCommand = QtCore.pyqtSignal(object)

    def __init__(
        self,
        base_directory,
        config,
        daemon_pyro_name,
        ns_host=None,
        logger=None,
        verbose=False,
    ):
        super(local_filterwheel, self).__init__()

        # Define attributes
        self.base_directory = base_directory
        self.config = config
        self.daemonname = daemon_pyro_name
        self.ns_host = ns_host
        self.logger = logger
        self.verbose = verbose
        self.state = dict()

        self.defaultval = -888

        # connect the signals and slots
        self.newCommand.connect(self.doCommand)

        # Startup
        self.init_remote_object()
        self.update_state()

    def log(self, msg, level=logging.INFO):
        msg = f"{self.daemonname}: {msg}"
        if self.logger is None:
            print(msg)
        else:
            self.logger.log(level=level, msg=msg)

    def init_remote_object(self):
        """Initialize connection to remote daemon"""
        try:
            if self.verbose:
                self.log(f"init_remote_object: trying to connect to {self.daemonname}")
            ns = Pyro5.core.locate_ns(host=self.ns_host)
            uri = ns.lookup(self.daemonname)
            self.remote_object = Pyro5.client.Proxy(uri)
            self.connected = True
        except Exception as e:
            self.connected = False
            if self.verbose:
                self.log(f"connection to remote object failed: {e}")
            pass

    def update_state(self):
        """Update state from remote daemon"""
        if not self.connected:
            if self.verbose:
                self.log(
                    f"self.connected = {self.connected}: try to init_remote_object again"
                )
            self.init_remote_object()
        else:
            try:
                self.remote_state = self.remote_object.getStatus()
            except Exception as e:
                if self.verbose:
                    self.log(f"could not update remote state: {e}")
                self.connected = False
                pass

            try:
                self.parse_state()
            except Exception as e:
                if self.verbose:
                    self.log(f"could not parse remote state: {e}")
                pass

    def parse_state(self):
        """Parse and condition the remote state dictionary"""
        for key in self.remote_state.keys():
            self.state.update({key: self.remote_state[key]})

        self.state.update(
            {"is_connected": bool(self.remote_state.get("connected", self.defaultval))}
        )

    def goto(self, pos):
        """Move to filter position"""
        self.remote_object.goto(pos)

    def home(self):
        """Home the filter wheel"""
        self.remote_object.home()

    def goToFilter(self, filter_num):
        """Move to specific filter"""
        return self.remote_object.goToFilter(filter_num)

    def openShutter(self):
        """Open the shutter"""
        return self.remote_object.openShutter()

    def closeShutter(self):
        """Close the shutter"""
        return self.remote_object.closeShutter()

    def doCommand(self, cmd_obj):
        """Execute command from signal"""
        cmd = cmd_obj.cmd
        args = cmd_obj.args
        kwargs = cmd_obj.kwargs

        try:
            getattr(self, cmd)(*args, **kwargs)
        except:
            pass

    def printState(self, update=True):
        """Print current state"""
        if update:
            self.update_state()
        print()
        print(json.dumps(self.state, indent=3))


# Try it out
if __name__ == "__main__":
    config = utils.loadconfig(WSP_PATH + "/config/config.yaml")
    logger = logging_setup.setup_logger(WSP_PATH, config)

    # Use None for testing without full logging
    logger = None
    verbose = True

    fw = local_filterwheel(
        WSP_PATH,
        config,
        daemon_pyro_name="SPRINGfw",
        ns_host="192.168.1.10",
        logger=logger,
        verbose=verbose,
    )

    fw.printState()

    # Test filter movements
    fw.goToFilter(2)

    while True:
        try:
            fw.printState()
            time.sleep(1)
        except KeyboardInterrupt:
            break
