#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Feb 20 10:37:25 2024

trigger handler

Copying over this logic from roboManager. There are other parts of the code
that could use this logic so I'm exicising it from there cleanly so as not
to mess with a working bit of code. Eventually could refactor roboManager
using this.

This bit of code can asseses whether it is time to do certain tasks within WSP

It replicates the assessment of trigger conditions in a single-threaded
manner.


@author: nlourie
"""

import json
import logging
import os
import pathlib
import signal

# import queue
import socket
import sys
import threading
import time
import traceback
from datetime import datetime, timedelta

# from astropy.io import fits
import numpy as np
import Pyro5.core
import Pyro5.server
import pytz
import yaml

# from PyQt5 import uic, QtGui, QtWidgets
from PyQt5 import QtCore

# add the wsp directory to the PATH
wsp_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "wsp"
)
# switch to this when ported to wsp
# wsp_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

sys.path.insert(1, wsp_path)
print(f"roboManager: wsp_path = {wsp_path}")


# from housekeeping import data_handler
from daemon import daemon_utils
from utils import logging_setup, utils

# from watchdog import watchdog
# from alerts import alert_handler


class RoboTriggerCond(object):

    def __init__(self, trigtype, val, cond):
        self.trigtype = trigtype
        self.val = val
        self.cond = cond


class RoboTrigger(object):
    def __init__(
        self, cmd, sundir, triglist=[], repeat_on_restart=False, nextmorning=False
    ):
        self.cmd = cmd
        self.sundir = int(sundir)
        self.triglist = triglist
        self.repeat_on_restart = repeat_on_restart
        self.nextmorning = nextmorning


class TriggerHandler(QtCore.QObject):
    """
    This is the pyro object that handles connections and communication with t
    the dome.

    This object has several threads within it for handling connection,
    communication, and commanding.

    NOTE:
        This inherets from QObject, which allows it to have custom signals
        which can communicate with the communication threads
    """

    def __init__(
        self, config, sunsim=False, logger=None, verbose=False, timeformat="%H:%M:%S.%f"
    ):
        super(TriggerHandler, self).__init__()
        # attributes describing the internet address of the dome server
        self.config = config
        self.logger = logger
        self.verbose = verbose
        self.timeformat = timeformat
        self.sunsim = sunsim

        # flag to indicate it's the first time running on restart
        self.first_time = True

        # dictionaries for the triggered commands
        self.triggers = dict()
        self.triglog = dict()

        self.tz = pytz.timezone("America/Los_Angeles")

        # if the status thread is request a reconnection, trigger the reconnection in the command thread too
        # THE STATUS THREAD IS A PYRO CONN, THE COMMAND THREAD IS A SOCKET, SO DON'T CONNECT THEIR RECONNECTION ATTEMPTS
        # self.statusThread.doReconnect.connect(self.commandThread.DoReconnect)

        # if the status thread gets the signbal that we've entered hand mode then enter hand mode
        # self.statusThread.enableHandMode.connect(self.handleHandMode)

        self.log(f"running in thread {threading.get_ident()}")

    def log(self, msg, level=logging.INFO):
        msg = "triggerHandler: " + msg
        if self.logger is None:
            print(msg)
        else:
            self.logger.log(level=level, msg=msg)

    def setupTrigs(self, trigdict, trigname_prefix=None):
        """
        tries to go through the dictionary provided to build a set of trigger
        objects. it searches for specifiers under a "triggers" keyword. Must
        follow the format below:

            Example:
                trigdict:
                    triggers:
                        startup:
                            type: 'sun'
                            val: 5.0
                            cond: '<'
                            cmd: 'total_startup'

        after creating this dictionary, the trigger log file is set up
        """

        # create local dictionary of triggers
        for trig in trigdict["triggers"]:
            triglist = list()
            self.log(f"setting up trigger: {trig}")

            trigsundir = trigdict["triggers"][trig]["sundir"]
            trignextmorning = trigdict["triggers"][trig].get("nextmorning", False)
            trigcmd = trigdict["triggers"][trig]["cmd"]
            repeat_on_restart = trigdict["triggers"][trig]["repeat_on_restart"]

            for cond in trigdict["triggers"][trig]["conds"]:
                self.log(f"adding condition: {cond}")
                trigtype = trigdict["triggers"][trig]["conds"][cond]["type"]
                trigcond = trigdict["triggers"][trig]["conds"][cond]["cond"]
                trigval = trigdict["triggers"][trig]["conds"][cond]["val"]

                # create a trigger object
                trigObj = RoboTriggerCond(trigtype=trigtype, val=trigval, cond=trigcond)
                # RoboTrigger
                # add the trigger object to the trigger list for this trigger
                triglist.append(trigObj)

            # add the trigger object to the trigger dictionary
            roboTrigger = RoboTrigger(
                trigcmd, trigsundir, triglist, repeat_on_restart, trignextmorning
            )
            if trigname_prefix is not None:
                trig_key = f"{trigname_prefix}-{trig}"
            else:
                trig_key = trig
            self.triggers.update({trig_key: roboTrigger})

        # # set up the log file

        # self.setupTrigLog()

    """
    # 2-20-24: for the moment, leaving out the logging portion of this
    """

    def resetTrigLog(self, updateFile=True):
        # make this exposed on the pyro server so we can externally reset the triglog

        # overwrites the triglog with all False, ie none of the commands have been sent
        for trigname in self.triggers.keys():
            # self.triglog.update({trigname : False})
            self.triglog.update(
                {trigname: {"sent": False, "sun_alt_sent": "", "time_sent": ""}}
            )
        if updateFile:
            self.updateTrigLogFile()

    def updateTrigLogFile(self):

        # saves the current value of the self.triglog to the self.triglog_filepath file
        # dump the yaml file
        with open(self.triglog_filepath, "w+") as file:
            # yaml.dump(self.triglog, file)#, default_flow_style = False)
            json.dump(self.triglog, file, indent=2)

    # def HandleUpdateTrigLog(self, trigname, sun_alt, timestamp):
    def logCommand(self, trigname, sun_alt, timestamp):
        """
        This handles updating the triglog and triglog file when requests
        are sent and properly received by WSP. It is triggered by the CommandHandler
        """
        # self.log(f'Main: caught signal to update triglog for {cmdRequest.trigname}')
        self.log(f"got request to log sequence for {trigname}")

        time_string = datetime.fromtimestamp(timestamp).isoformat(sep=" ")

        self.triglog.update(
            {
                trigname: {
                    "sent": True,
                    "sun_alt_sent": sun_alt,
                    "time_sent": time_string,
                }
            }
        )
        # update the triglog file
        self.updateTrigLogFile()
        pass

    def setupTrigLog(self, logpath, linkpath):
        """
        set up a yaml log file which records whether the command for each trigger
        has already been sent tonight.

        checks to see if tonight's triglog already exists. if not it makes a new one.
        """
        # file
        # self.triglog_dir = os.path.join(os.getenv("HOME"),'data','triglogs')
        # self.triglog_filename = f'triglog_{utils.tonight_local()}.json'
        self.triglog_filepath = logpath
        self.triglog_dir = os.path.dirname(self.triglog_filepath)

        # self.triglog_linkdir = os.path.join(os.getenv("HOME"),'data')
        # self.triglog_linkname = 'triglog_tonight.lnk'
        # self.triglog_linkpath = os.path.join(self.triglog_linkdir, self.triglog_linkname)
        self.triglog_linkpath = linkpath
        self.triglog_linkdir = os.path.dirname(self.triglog_linkpath)

        # create the data directory if it doesn't exist already
        pathlib.Path(self.triglog_dir).mkdir(parents=True, exist_ok=True)
        self.log(f"ensuring directory exists: {self.triglog_dir}")

        # create the data link directory if it doesn't exist already
        pathlib.Path(self.triglog_linkdir).mkdir(parents=True, exist_ok=True)
        self.log(f"ensuring directory exists: {self.triglog_linkdir}")

        # check if the file exists
        try:
            # assume file exists and try to load triglog from file
            self.log(f"loading triglog from file")
            self.triglog = json.load(open(self.triglog_filepath))

        except FileNotFoundError:
            # file does not exist: create it
            self.log("no triglog found: creating new one")

            # create the default triglog: no cmds have been sent
            self.resetTrigLog()

        # recreate a symlink to tonights trig log file
        self.log(f"trying to create link at {self.triglog_linkpath}")

        try:
            os.symlink(self.triglog_filepath, self.triglog_linkpath)
        except FileExistsError:
            self.log("deleting existing symbolic link")
            os.remove(self.triglog_linkpath)
            os.symlink(self.triglog_filepath, self.triglog_linkpath)

        print(f"\ntriglog = {json.dumps(self.triglog, indent = 2)}")

    def getTrigCurVals(self, triggercond, sun_alt, timestamp, nextmorning=False):
        """:
        get the trigger value (the value on which to trigger), and the current value of the given trigger
        trigger must be in self.config['robotic_manager_triggers']['triggers']

        this is trying to build a general framework where we can decide down the line that we want to trigger
        a command off of the sun altitude or a time.

        it may be too fussy and might not worth doing this way, but we shall see.
        """
        # triggercond must be a trigger cond object

        trigtype = triggercond.trigtype

        if trigtype == "sun":
            # print(f'handling sun trigger:')
            trigval = triggercond.val
            curval = sun_alt

        elif trigtype == "time":
            # print(f'handling time trigger:')
            trigval = triggercond.val
            trig_datetime = datetime.strptime(trigval, self.timeformat)

            if self.sunsim:

                now_datetime = datetime.fromtimestamp(timestamp)
                if self.verbose:
                    print(f"\t>>using suntim time: {now_datetime}")
            else:
                now_datetime = datetime.now()
                if self.verbose:
                    print(f"\t>> using local time: {now_datetime}")

            # now the issue is that the timestamp from trig_datetime has a real time but a nonsense date. so we can't subtract
            # to be able to subtract, let's make the two times on the same day, and use the now_datetime to get the day.

            # now_year = now_datetime.year
            # now_month = now_datetime.month
            # now_day = now_datetime.day

            trig_hour = trig_datetime.hour
            trig_minute = trig_datetime.minute
            trig_second = trig_datetime.second
            trig_microsecond = trig_datetime.microsecond

            # get the night of the observation.
            # use the utils.tonight_local() utility which returns a string, eg: '20220202'
            tonight = datetime.strptime(
                utils.tonight_local(now_datetime.timestamp()), "%Y%m%d"
            )

            trig_year = tonight.year
            trig_month = tonight.month
            trig_day = tonight.day

            trig_datetime_today = datetime(
                year=trig_year,
                month=trig_month,
                day=trig_day,
                hour=trig_hour,
                minute=trig_minute,
                second=trig_second,
                microsecond=trig_microsecond,
            )

            # HANDLE MORNING TIME TRIGGERS
            # NPL 2-2-22: update

            # if the trigger time is in the "next morning" then we need to shove the day forward by one
            if nextmorning:
                trig_datetime_today += timedelta(days=1)

            # NOW we have two times on the same day. subtract to get the
            # for the trigval and the curval we will return the timestamps of each. these can be compared easily
            trigval = trig_datetime_today.timestamp()
            curval = now_datetime.timestamp()
            if self.verbose:
                self.log(
                    f"trig_datetime_today = {trig_datetime_today}, timestamp = {trig_datetime_today.timestamp()}"
                )
                self.log(
                    f"now_datetime        = {now_datetime}, timestamp = {now_datetime.timestamp()}"
                )
                self.log("")

        return trigval, curval

    def triggerReady(self, trigname, sun_alt, timestamp, sun_rising) -> bool:
        trigger_ready = False
        # load up the trigger object
        trig = self.triggers[trigname]

        # get the triglist for the given trigger
        triglist = self.triggers[trigname].triglist
        num_trigs = len(triglist)

        # create a condition list to be met. initialize with all conditions false
        condlist = [False for i in range(num_trigs)]
        if self.verbose:
            self.log(f"----- assessing trigger conditions for {trigname} -----")
            self.log(f"\tinitializing condlist to: {condlist}")
            self.log(f"\tevaluating {num_trigs} triggers for trigger: {trigname}")
        # step through all the triggers and evaluate. add their condition result boolean to the condlist
        for i in range(num_trigs):

            trig_i = triglist[i]
            trigval, curval = self.getTrigCurVals(
                triggercond=trig_i,
                sun_alt=sun_alt,
                timestamp=timestamp,
                nextmorning=trig.nextmorning,
            )
            trig_condition = f"{curval} {trig_i.cond} {trigval}"
            trig_condition_met = eval(trig_condition)
            trig_type = trig_i.trigtype
            if self.verbose:
                self.log(f"\ttrig {i+1}:")

            if trig_type == "sun":
                trig_condition_text = f"\t\tsun_alt: {curval} {trig_i.cond} {trigval} --> {trig_condition_met}"
            elif trig_type == "time":
                trig_condition_text = f"\t\ttime: {datetime.fromtimestamp(curval)} {trig_i.cond} {datetime.fromtimestamp(trigval)} --> {trig_condition_met}"
            if self.verbose:
                self.log(trig_condition_text)

            # print(f'\t\ttrig condition: {trig_condition} --> {trig_condition_met}')
            # update the condlist with the value
            condlist[i] = trig_condition_met

        if self.verbose:
            self.log(f"\tcondlist = {condlist}")

        # flag describes whether ALL conditions are met
        all_conditions_met = all(condlist)
        if self.verbose:
            self.log(f"\t All conditions met: {all_conditions_met}")

        # check the sun direction (ie rising/setting)
        if trig.sundir == 0:
            trig_sun_ok = True
        elif trig.sundir < 0:
            # require sun to be setting
            if sun_rising:
                trig_sun_ok = False
            else:
                trig_sun_ok = True
        else:
            # require sun to be rising
            if state["sun_rising"]:
                trig_sun_ok = True
            else:
                trig_sun_ok = False
        if self.verbose:
            self.log(f"trigger sun rising condition okay: {trig_sun_ok}")

        # if nextmorning flag is true, check if it is the next morning
        if trig.nextmorning:
            if self.sunsim:

                now_datetime = datetime.fromtimestamp(timestamp)
                if self.verbose:
                    self.log(f"\t>>using suntim time: {now_datetime}")
            else:
                now_datetime = datetime.now()
                if self.verbose:
                    print(f"\t>> using local time: {now_datetime}")

            # get the night of the observation.
            # use the utils.tonight_local() utility which returns a string, eg: '20220202'
            tonight = datetime.strptime(
                utils.tonight_local(now_datetime.timestamp()), "%Y%m%d"
            )
            nextmorning = tonight + timedelta(days=1)

            # is the current time greater than the next morning?
            if now_datetime > nextmorning:
                nextmorning_ok = True
            else:
                nextmorning_ok = False
        else:
            # if no flag or false we don't care
            nextmorning_ok = True

        if self.verbose:
            self.log(f"trigger nextmorning condition okay: {nextmorning_ok}")

        # print(f'\ttrig condition: {trig_condition} --> {trig_condition_met}')

        if all_conditions_met & trig_sun_ok & nextmorning_ok:
            # the trigger condition is met!
            self.log("")
            self.log(f"Time to send the {trig.cmd} command!")
            # print(f'\ttrigval = {trigval}, curval = {curval}')
            for i in range(num_trigs):
                self.log(f"\ttrig {i+1}:")
                trig_i = triglist[i]
                trig_type = trig_i.trigtype
                trigval, curval = self.getTrigCurVals(
                    triggercond=trig_i, sun_alt=sun_alt, timestamp=timestamp
                )
                trig_condition = f"{curval} {trig_i.cond} {trigval}"
                trig_condition_met = eval(trig_condition)
                if trig_type == "sun":
                    trig_condition_text = f"\t\tsun_alt: {curval} {trig_i.cond} {trigval} --> {trig_condition_met}"
                elif trig_type == "time":
                    trig_condition_text = f"\t\ttime: {datetime.fromtimestamp(curval)} {trig_i.cond} {datetime.fromtimestamp(trigval)} --> {trig_condition_met}"
                self.log(trig_condition_text)
                # print(f'\t\ttrig condition: {trig_condition} --> {trig_condition_met}')
            self.log("")
            # send alert that we're sending the command
            # self.alertHandler.slack_log(f':futurama-bender-robot: roboManager: sending command *{trig.cmd}*')

            trigger_ready = True

        else:
            # trigger condition not met
            if self.verbose:
                self.log(f"\tNot yet time to send {trig.cmd} command")
                trigger_ready = False
            pass

        # return whether the trigger is ready
        return trigger_ready

    def getActiveTriggers(self, sun_alt, timestamp, sun_rising):
        """
        This is the main meat of this program. It checks the sun alt and time against a
        set of predefined tasks and then submits commands to the WSP wintercmd TCP/IP
        command interface.

        Returns
        -------
        None.

        """

        active_triggers = []

        try:
            # for trigname in ['startup']:
            for trigname in self.triggers.keys():
                if self.verbose:
                    self.log(f"evaluating trigger: {trigname}")
                # load up the trigger object
                trig = self.triggers[trigname]

                if self.triglog[trigname]["sent"]:
                    # check to see if the trigger has already been executed
                    if self.verbose:
                        self.log("\tcmd already sent")

                    if self.first_time:
                        # if it's the first time we may want to trigger the cmd anyway
                        if trig.repeat_on_restart:
                            if self.verbose:
                                print(
                                    "\tsending trigger anyway since it is the first time after restart"
                                )
                            # self.handleTrigger(trigname)

                            if self.triggerReady(
                                trigname, sun_alt, timestamp, sun_rising
                            ):
                                active_triggers.append(
                                    (trigname, self.triggers[trigname].cmd)
                                )

                    else:
                        # the trigger cmd has already been sent. do nothing.
                        pass
                else:
                    # self.handleTrigger(trigname)
                    if self.triggerReady(trigname, sun_alt, timestamp, sun_rising):
                        active_triggers.append((trigname, self.triggers[trigname].cmd))
            # change the first time flag
            self.first_time = False

        except Exception as e:
            if self.verbose:
                print(f"could not check what to do: {e}")
                print(traceback.format_exc())
            pass

        return active_triggers
