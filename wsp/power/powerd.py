#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Feb 16 17:42:28 2021

PDU Daemon

@author: nlourie
"""
import getopt
import json
import logging
import os
import signal

# from astropy.io import fits
# import numpy as np
import sys

# import queue
import threading
import time

import Pyro5.core
import Pyro5.server

# import time
# from PyQt5 import uic, QtGui, QtWidgets
from PyQt5 import QtCore

# add the wsp directory to the PATH
wsp_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(1, wsp_path)
print(f"wsp_path = {wsp_path}")


from daemon import daemon_utils
from housekeeping import data_handler

try:
    from power import pdu
except:
    import pdu
from utils import logging_setup, utils


class PowerManager(QtCore.QObject):
    def __init__(
        self, pdu_config, auth_config, dt=1000, name="power", logger=None, verbose=False
    ):

        super(PowerManager, self).__init__()

        self.pdu_config = pdu_config
        self.auth_config = auth_config
        self.name = name
        self.dt = dt
        self.logger = logger

        self.state = dict()
        self.teststate = dict({"thing": "blarg"})
        self.pdu_dict = dict()
        self.setup_pdu_dict()

        self.log("finished init, starting monitoring loop")

        self.timer = QtCore.QTimer()
        self.timer.setInterval(self.dt)
        self.timer.timeout.connect(self.update)
        self.timer.start()
        """
        if verbose:
            self.daqloop = data_handler.daq_loop(self.update, dt = self.dt, name = self.name, print_thread_name_in_update = True, thread_numbering = 'norm')
        else:
            self.daqloop = data_handler.daq_loop(self.update, dt = self.dt, name = self.name)
        """

    def log(self, msg, level=logging.INFO):

        msg = f"powerd: {msg}"

        if self.logger is None:
            print(msg)
        else:
            self.logger.log(level=level, msg=msg)

    def setup_pdu_dict(self):
        # make a dictionary of all the pdus
        for pduname in self.pdu_config["pdus"]:
            try:
                pduObj = pdu.PDU(
                    pduname,
                    self.pdu_config,
                    self.auth_config,
                    autostart=True,
                    logger=self.logger,
                )
                pdunumber = self.pdu_config["pdus"][pduname]["pdu_number"]
                index = pdunumber
                self.pdu_dict.update({index: pduObj})
                self.log(f"Successfully initialized PDU {pduname} at index {index}")
            except Exception as e:
                self.log(
                    f"Failed to initialize PDU {pduname}: {e}", level=logging.ERROR
                )
                # Optionally, you could add a placeholder or None for this PDU
                # pdunumber = self.pdu_config['pdus'][pduname]['pdu_number']
                # self.pdu_dict.update({pdunumber : None})

    def update(self):
        """query the pdus for their status and update the state dict"""
        for pduname in self.pdu_dict:
            if self.pdu_dict[pduname] is not None:  # Check if PDU exists
                try:
                    # query the pdu status
                    pdustate = self.pdu_dict[pduname].getState()
                    self.state.update({pduname: pdustate})
                except Exception as e:
                    self.log(
                        f"Failed to get state from PDU {pduname}: {e}",
                        level=logging.WARNING,
                    )
                    # Optionally set a error state
                    self.state.update({pduname: {"error": str(e), "status": "offline"}})

    def lookup_channel(self, chanargs):
        """takes in args that should define channel. outputs the pdu
        and the channel number. If there's one arg, it will try to treat it
        as a string and do a lookup by outlet label.

        if there are two args it will treat them as ints and do a lookup
        by args = [pdu#, outlet#]

        if there are more than two args it will log an error and return
        """
        try:
            if chanargs is None:
                raise ValueError("you gave me chanargs = None, cannot look that up")

            if type(chanargs) is list:
                if len(chanargs) == 1:
                    # if we only got one item in the list, assume it's the name
                    name_lookup = True
                    chan = str(chanargs[0])

                elif len(chanargs) == 2:
                    pduaddr = int(chanargs[0])
                    outletnum = int(chanargs[1])
                    assert (
                        pduaddr in self.pdu_dict.keys()
                    ), f"pdu address {pduaddr} not found in pdu dictionary"
                    assert (
                        outletnum in self.pdu_dict[pduaddr].outletnums2names
                    ), f"outlet number {outletnum} not found in outlet list for pdu {pduaddr}"

                    return pduaddr, outletnum
                else:
                    raise ValueError(
                        f"unexpected number of channel arguments when looking up pdu outlet = {chanargs}"
                    )

            else:  # treat the input like a string
                # if we just got a single thing not a list, assume it's a name
                name_lookup = True
                chan = str(chanargs)

            if name_lookup == True:
                # init a list to hold the (pdu_addr, chan_num) tuple that
                # corresponds to the chan specified
                chanaddr = []
                # now look up the str channel
                for pduaddr in self.pdu_dict:
                    for outletnum in self.pdu_dict[pduaddr].outletnums2names:
                        outletname = self.pdu_dict[pduaddr].outletnums2names[outletnum]
                        # check if the outlet name is the same as the requested one
                        # note that this is being forced to be CASE INSENSITVE
                        if outletname.lower() == chan.lower():
                            chanaddr.append((pduaddr, outletnum))
                self.log(f"(pduaddr, outletnum) matching chan = {chan}: {chanaddr}")
                # what it there is degeneracy in outlet names?
                if len(chanaddr) > 1:
                    raise ValueError(
                        f"there are {len(chanaddr)} outlets named {chan}, not sure which to use!"
                    )
                elif len(chanaddr) == 0:
                    raise ValueError(f"found no outlets named {chan}!")
                else:
                    pduaddr, outletnum = chanaddr[0]
                    return pduaddr, outletnum

        except Exception as e:
            self.log(f"error doing name lookup of PDU outlet names: {e}")
            return None, None

    @Pyro5.server.expose
    def pdu_do(self, action, outlet_specifier):
        """
        execute a generic action on the power distribution units
        this will execute action (one of [on, off, cycle]) on the PDU
        on the specified outlet. the outlet specifier can either be a tuple
        descritbing the pdu number and the outlet number, eg (1,3) for pdu #1,
        outlet #3, or it can be a string which corresponds to the name given to
        the outlet number. it will use self.lookup_channel to find the pdu
        address and outlet number and do nothing if the outlet name/specifier
        is invalid or not unique.
        """
        action = action.lower()

        if action not in ["on", "off", "cycle"]:
            self.log(f"action {action} not in allowed actions of [on, off, cycle]")
            return

        # now get the pdu address (in the pdu_dict) and the outlet number
        pdu_addr, outletnum = self.lookup_channel(outlet_specifier)

        if any([item is None for item in [pdu_addr, outletnum]]):
            self.log("bad outlet lookup. no action executed.")
            return
        # now do the action
        func = getattr(self, f"pdu_{action}")
        func(pdu_addr, outletnum)

    @Pyro5.server.expose
    def pdu_off(self, addr, outlet):
        # protect odin!
        # TODO: make this less hard coded

        if (addr == 2) and (outlet == 5):
            self.log("got command to turn off Odin. This is not allowed! Ignoring.")
            return
        self.log(f"sending OFF command to pdu {addr}, outlet {outlet}")
        self.pdu_dict[addr].off(outlet)
        self.update()

    @Pyro5.server.expose
    def pdu_on(self, addr, outlet):
        self.log(f"sending ON command to pdu {addr}, outlet {outlet}")
        self.pdu_dict[addr].on(outlet)
        self.update()

    @Pyro5.server.expose
    def pdu_cycle(self, addr, outlet):
        self.log(f"sending cycle command to pdu {addr}, outlet {outlet}")
        self.pdu_dict[addr].cycle(outlet)
        self.update()

    @Pyro5.server.expose
    def getState(self):
        # print(self.state)
        return self.state

    @Pyro5.server.expose
    def test(self):
        print("TEST")
        return "TEST"


class PyroGUI(QtCore.QObject):

    def __init__(self, pdu_config, auth_config, ns_host, logger, verbose, parent=None):
        super(PyroGUI, self).__init__(parent)
        print(f"main: running in thread {threading.get_ident()}")

        self.powerManager = PowerManager(
            pdu_config,
            auth_config,
            dt=5000,
            name="power",
            verbose=verbose,
            logger=logger,
        )

        self.pyro_thread = daemon_utils.PyroDaemon(
            obj=self.powerManager, name="power", ns_host=ns_host
        )
        self.pyro_thread.start()

        """
        self.timer = QtCore.QTimer()
        self.timer.setInterval(500)
        self.timer.timeout.connect(self.check_pyro_queue)
        self.timer.start()
        """


def sigint_handler(*args):
    """Handler for the SIGINT signal."""
    sys.stderr.write("\r")

    # main.powerManager.daqloop.quit()

    QtCore.QCoreApplication.quit()


if __name__ == "__main__":

    #### GET ANY COMMAND LINE ARGUMENTS #####

    args = sys.argv[1:]
    print(f"args = {args}")

    # set the defaults
    verbose = False
    doLogging = True
    ns_host = "192.168.1.10"

    options = "vpn:s"
    long_options = ["verbose", "print", "ns_host:"]
    arguments, values = getopt.getopt(args, options, long_options)
    # checking each argument
    print()
    print(f"Parsing sys.argv...")
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

    print(f"powerd: launching with ns_host = {ns_host}")

    ##### RUN THE APP #####
    app = QtCore.QCoreApplication(sys.argv)

    # set the wsp path as the base directory
    base_directory = wsp_path

    # load the config
    config_file = base_directory + "/config/config.yaml"
    config = utils.loadconfig(config_file)

    # set up the logger
    if doLogging:
        logger = logging_setup.setup_logger(base_directory, config)
    else:
        logger = None

    pdu_config = utils.loadconfig(os.path.join(wsp_path, "config", "powerconfig.yaml"))
    auth_config = utils.loadconfig(
        os.path.join(wsp_path, "credentials", "authentication.yaml")
    )

    main = PyroGUI(pdu_config, auth_config, ns_host, logger, verbose)

    signal.signal(signal.SIGINT, sigint_handler)

    # Run the interpreter every so often to catch SIGINT
    timer = QtCore.QTimer()
    timer.start(500)
    timer.timeout.connect(lambda: None)

    sys.exit(app.exec_())
