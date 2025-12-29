#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jan 27 17:48:35 2020

telescope.py

This file is part of wsp

# PURPOSE #

This is a wrapper for the pwi4_client.py program from planewave.

It is written mainly to add a current status object to the pwi4_client.PWI4 class

The goal is that this is written in such a way that we can update pwi4_client
when PlaneWave publishes updates without having to modify that code, but maintain
the extra functionality we need.




@author: nlourie
"""
import os
import time
from datetime import datetime

from PyQt5 import QtCore

from wsp.telescope.pwi4_client import PWI4
from wsp.utils import utils

# add the wsp directory to the PATH
wsp_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TelescopeSignals(QtCore.QObject):

    wrapWarning = QtCore.pyqtSignal(object)


class WrapWarningInfo:
    def __init__(self, port, angle, min_degs, max_degs):
        self.port = port
        self.angle = angle
        self.min_degs = min_degs
        self.max_degs = max_degs


class Telescope(PWI4):
    """
    This inherits from pwi4_client.PWI4
    """

    def __init__(
        self, config, host="localhost", port=8220, mountsim=False, logger=None
    ):

        super(Telescope, self).__init__(host=host, port=port)

        # create an empty state dictionary that will be updated
        self.state = dict()
        self.port = -1  # unknown port at start
        self.config = config
        self.signals = TelescopeSignals()
        self.wrap_check_enabled = True  # False
        self.wrap_status = False
        self.mountsim = mountsim
        self.logger = logger

        # put things in a safe position on startup
        try:
            self.mount_connect()
            time.sleep(1)
        except Exception as e:
            self.log(f"could not connect to telescope! error: {e}")
        try:
            self.mount_stop()
            time.sleep(1)
        except Exception as e:
            self.log(f"could not stop mount! error: {e}")
        try:
            self.mount_tracking_off()
            time.sleep(1)
        except Exception as e:
            self.log(f"could not turn mount tracking off! error: {e}")

        if not self.mountsim:
            try:
                self.rotator_stop()
                time.sleep(1)
            except Exception as e:
                self.log(f"could not stop rotator! error: {e}")

    def log(self, msg):
        msg = f"telescope: {msg}"
        if self.logger is None:
            print(msg)
        else:
            self.logger.warning(msg)

    def status_text_to_dict_parse(self, response):
        """
        Given text with keyword=value pairs separated by newlines,
        return a dictionary with the equivalent contents.
        """

        # In Python 3, response is of type "bytes".
        # Convert it to a string for processing below
        if type(response) == bytes:
            response = response.decode("utf-8")

        response_dict = {}

        lines = response.split("\n")

        for line in lines:
            fields = line.split("=", 1)
            if len(fields) == 2:
                name = fields[0]
                value = fields[1]
                """
                # NL: this is a departure from the planewave code.
                The idea is that instead of making a dictionary of just values
                directily it's a mixed type dictionary, so that if some value is False,
                the dictionary value is a python boolean False, not the string 'false'
                
                Note that all the entries in the dictionary by default are strings. 
                The PW code specifically says what type of entry each entry is,
                for now let's just try to force it to a float and pass if not.
                
                This should be okay, because floats will be floats, bools are parsed
                separately, and any ints will become floats, but can always
                be changed back to ints by data_handler. Strings that can't
                be turned into floats will stay strings, like the pwi4.version field. 
                """

                if value.lower() == "true":
                    value = True
                elif value.lower() == "false":
                    value = False
                elif "timestamp" in name:
                    # if timestampt is in the name the format is YYYY-MM-DD HH:MM:SS.S
                    datetime_obj = datetime.strptime(value, "%Y-%m-%d %H:%M:%S.%f")
                    value = datetime_obj.timestamp()
                else:
                    try:
                        value = float(value)
                    except:
                        pass
                # this is the normal thing:
                response_dict[name] = value

        return response_dict

    def update_state(self, verbose=False):
        # written by NPL
        # poll telescope status
        try:
            # self.state = self.status()
            # self.state = self.status_text_to_dict_parse(self.request("/status"))
            # get the mount status
            status = self.getStatus()
            # get the mirror temperatures
            mirror_temps = self.getMirrorTemps()
            # merge all status dictionaries into single self.state dictionary
            self.state = {**status, **mirror_temps}
            self.state.update({"rotator_wrap_check_enabled": self.wrap_check_enabled})
            # update the current port

            self.check_for_wrap()

        except Exception as e:
            """
            do nothing here. this avoids flooding the log with errors if
            the system is disconnected. Instead, this should be handled by the
            watchdog to signal/log when the system is offline at a reasonable
            cadance.

            if desired, we could set self.state_dict back to an empty dictionary.
            This would make housekeeping get the default values back, but otherwise
            let's just set mount.is_connected to False.
            """
            # for now if the state can't update, then set the connected key to false:
            self.state.update({"mount.is_connected": False})

            if verbose:
                print(f"could not update telescope status: {type(e)}: {e}")
        finally:
            self.port = self.getTelescopePort()

    def enable_wrap_check(self):
        self.wrap_check_enabled = True

    def disable_wrap_check(self):
        self.wrap_check_enabled = False

    def check_for_wrap(self):

        angle = self.state["rotator.mech_position_degs"]

        active_port = int(self.state["m3.port"])
        min_angle = self.config["telescope"]["ports"][self.port]["rotator"]["min_degs"]
        max_angle = self.config["telescope"]["ports"][self.port]["rotator"]["max_degs"]
        self.wrap_status = (angle <= min_angle) or (angle >= max_angle)

        self.state.update({"wrap_status": self.wrap_status})
        if self.wrap_check_enabled:
            if self.wrap_status:

                self.log("WRAP WARNING")
                # we're in danger of wrapping!!
                wrap_info = WrapWarningInfo(
                    port=active_port,
                    angle=angle,
                    min_degs=min_angle,
                    max_degs=max_angle,
                )
                self.signals.wrapWarning.emit(wrap_info)
                # set the flag to false so we don't send a billion signals
                self.wrap_check_enabled = False

    def fans_on(self):
        self.request_with_status("/fans/on")

    def fans_off(self):
        self.request_with_status("/fans/off")

    def getStatus(self):
        response = self.request("/status")
        status_dict = self.status_text_to_dict_parse(response)
        return status_dict

    def getMirrorTemps(self):
        response = self.request("/temperatures/pw1000")
        temp_dict = self.status_text_to_dict_parse(response)
        return temp_dict

    def getTelescopePort(self):
        port = int(self.state.get("m3.port", -1))
        self.port = port
        return port


if __name__ == "__main__":

    # load the config
    config_file = wsp_path + "/config/config.yaml"
    config = utils.loadconfig(config_file)
    host = "thor"
    host = "192.168.1.106"
    host = "localhost"
    telescope = Telescope(config, host, logger=None)
    telescope.update_state()
    print(f"telescope state = {telescope.state}")
    print(f"mount.is_connected = {telescope.state['mount.is_connected']}")
    print(f"rotator field angle = {telescope.state['rotator.field_angle_degs']}")
    print(f"connecting mount:")
    telescope.mount_connect()
    print()
    print("updating state: ")
    telescope.update_state()
    print(f"mount.is_connected = {telescope.state['mount.is_connected']}")
    print(f"rotator field angle = {telescope.state['rotator.field_angle_degs']}")
    print()
    target_field_angle = 45
    print(f"rotator slewing to field angle: {target_field_angle}")
    telescope.rotator_goto_field(target_field_angle)
    print()
    print("updating state: ")
    telescope.update_state()
    print(f"mount.is_connected = {telescope.state['mount.is_connected']}")
    print(f"rotator field angle = {telescope.state['rotator.field_angle_degs']}")
