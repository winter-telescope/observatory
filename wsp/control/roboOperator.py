#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Apr 27 22:56:08 2021

operator.py

@author: nlourie
"""


import glob
import json

# import json
import logging
import os
import pathlib
import subprocess
import sys
import threading
import time
import traceback
from datetime import datetime

import astropy.coordinates
import astropy.time
import astropy.units as u
import numpy as np
import pandas as pd
import Pyro5.client
import Pyro5.core
import pytz

# import pandas as pd
import sqlalchemy as db
from astropy.io import fits
from PyQt5 import QtCore

# import wintertoo.validate
# import winter_utils

# add the wsp directory to the PATH
wsp_path = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(1, wsp_path)

from cal import cal_tracker
from ephem import ephem_utils
from focuser import focus_tracker, focusing
from housekeeping import data_handler
from schedule import wintertoo_validate
from telescope import pointingModelBuilder

# print all the columns
pd.set_option("display.max_columns", None)
pd.set_option("display.expand_frame_repr", False)


class TargetError(Exception):
    pass


class TimerThread(QtCore.QThread):
    """
    This is a thread that just counts up the timeout and then emits a
    timeout signal. It will be connected to the worker thread so that it can
    run a separate thread that times each worker thread's execution
    """

    timerTimeout = QtCore.pyqtSignal()

    def __init__(self, timeout, *args, **kwargs):
        super(TimerThread, self).__init__()
        print("created a timer thread")
        # Set up the timeout. Convert seconds to ms
        self.timeout = timeout * 1000.0

    def run(self):
        def printTimeoutMessage():
            print(f"timer thread: timeout happened")

        print(f"running timer in thread {threading.get_ident()}")
        # run a single shot QTimer that emits the timerTimeout signal when complete
        self.timer = QtCore.QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(printTimeoutMessage)
        self.timer.timeout.connect(self.timerTimeout.emit)
        self.timer.start(self.timeout)
        self.exec_()


class WrapHandler(QtCore.QThread):
    """
    This is a dedicated thread which just handles rotator wrap issues
    """

    def __init__(self):
        super(WrapHandler, self).__init__()

    def run(self):
        self.exec_()


class RoboOperatorThread(QtCore.QThread):
    """
    A dedicated thread to handle all the robotic operations!

    This is basically a thread to handle all the commands which get sent in
    robotic mode
    """

    # this signal is connected to the RoboOperator's start_robo method
    restartRoboSignal = QtCore.pyqtSignal(str)

    # this signal is typically emitted by wintercmd, and is connected to the RoboOperators change_schedule method
    changeSchedule = QtCore.pyqtSignal(object)

    # this signal is typically emitted by wintercmd and is connected to the RoboOperator's do_currentObs method
    do_currentObs_Signal = QtCore.pyqtSignal()

    # this signal is typically emitted by wintercmd, it connected to RoboOperator's doExposure method.
    # this really just replicates calling ccd_do_exposure directly, but tests out all the connections between roboOperator and the ccd_daemon
    doExposureSignal = QtCore.pyqtSignal()

    # a generic do command signal for executing any command in robothread
    newCommand = QtCore.pyqtSignal(object)

    def __init__(
        self,
        base_directory,
        config,
        mode,
        state,
        wintercmd,
        logger,
        alertHandler,
        watchdog,
        schedule,
        telescope,
        dome,
        chiller,
        ephem,
        # viscam, ccd,
        camdict,
        fwdict,
        imghandlerdict,
        mirror_cover,
        robostate,
        sunsim,
        dometest,
        mountsim,
    ):
        super(QtCore.QThread, self).__init__()

        self.base_directory = base_directory
        self.config = config
        self.mode = mode
        self.state = state
        self.wintercmd = wintercmd
        self.wintercmd.roboThread = self
        self.schedule = schedule
        self.telescope = telescope
        self.dome = dome
        self.chiller = chiller
        self.logger = logger
        self.alertHandler = alertHandler
        self.watchdog = watchdog
        self.ephem = ephem
        # self.viscam = viscam
        # self.ccd = ccd
        self.camdict = camdict
        self.fwdict = fwdict
        self.imghandlerdict = imghandlerdict
        self.mirror_cover = mirror_cover
        self.robostate = robostate
        self.sunsim = sunsim
        self.dometest = dometest
        self.mountsim = mountsim

    def run(self):
        self.robo = RoboOperator(
            base_directory=self.base_directory,
            config=self.config,
            mode=self.mode,
            state=self.state,
            wintercmd=self.wintercmd,
            logger=self.logger,
            alertHandler=self.alertHandler,
            watchdog=self.watchdog,
            schedule=self.schedule,
            telescope=self.telescope,
            dome=self.dome,
            chiller=self.chiller,
            ephem=self.ephem,
            # viscam = self.viscam,
            # ccd = self.ccd,
            camdict=self.camdict,
            fwdict=self.fwdict,
            imghandlerdict=self.imghandlerdict,
            mirror_cover=self.mirror_cover,
            robostate=self.robostate,
            sunsim=self.sunsim,
            dometest=self.dometest,
            mountsim=self.mountsim,
        )

        # Put all the signal/slot connections here:
        ## if we get a signal to start the robotic operator, start it!
        self.restartRoboSignal.connect(self.robo.restart_robo)
        ## change schedule
        self.changeSchedule.connect(self.robo.change_schedule)
        ## do an exposure with the ccd
        self.doExposureSignal.connect(self.robo.doExposure)
        # do a command in the roboOperator thread
        # connect the signals and slots
        self.newCommand.connect(self.robo.doCommand)

        # Start the event loop
        self.exec_()


class roboError(object):
    """
    This is a class used to broadcast errors as pyqtSignals.
    The idea is that this will be caught elsewhere by the system monitor
    which can try to reboot or otherwise handle these errors.

    cmd:    the command that the roboOperator was trying to execute, eg 'dome_home'
    system: the system that the command involves, eg 'chiller'. this is used for rebooting
    err:    whatever error message goes along with this error
    """

    def __init__(self, context, cmd, system, msg):
        self.context = context
        self.cmd = cmd
        self.system = system
        self.msg = msg


class RoboOperator(QtCore.QObject):

    hardware_error = QtCore.pyqtSignal(object)

    startRoboSignal = QtCore.pyqtSignal()
    stopRoboSignal = QtCore.pyqtSignal()

    startExposure = QtCore.pyqtSignal(object)

    # alarm methods to trigger various issues
    cameraAlarm = QtCore.pyqtSignal(object)
    chillerAlarm = QtCore.pyqtSignal(object)

    # operator methods to clear/disable/enable alarms and lockouts
    clearAlarms = QtCore.pyqtSignal()
    disableAlarms = QtCore.pyqtSignal()
    enableAlarms = QtCore.pyqtSignal()

    def __init__(
        self,
        base_directory,
        config,
        mode,
        state,
        wintercmd,
        logger,
        alertHandler,
        watchdog,
        schedule,
        telescope,
        dome,
        chiller,
        ephem,
        # viscam, ccd,
        camdict,
        fwdict,
        imghandlerdict,
        mirror_cover,
        robostate,
        sunsim,
        dometest,
        mountsim,
    ):
        super(RoboOperator, self).__init__()

        self.base_directory = base_directory
        self.config = config
        self.mode = mode
        self.state = state
        self.wintercmd = wintercmd
        # assign self to wintercmd so that wintercmd has access to the signals
        self.wintercmd.roboOperator = self
        self.alertHandler = alertHandler
        self.watchdog = watchdog
        # set up the hardware systems
        self.telescope = telescope
        self.dome = dome
        self.chiller = chiller
        self.logger = logger
        self.ephem = ephem
        self.schedule = schedule
        # self.viscam = viscam
        # self.ccd = ccd
        self.camdict = camdict
        self.fwdict = fwdict
        self.imghandlerdict = imghandlerdict
        self.mirror_cover = mirror_cover
        self.robostate = robostate
        self.sunsim = sunsim
        self.dometest = dometest
        self.mountsim = mountsim

        # for now just trying to start leaving places in the code to swap between winter and summer
        self.camname = "winter"
        self.switchCamera(self.camname)

        ### FOCUS LOOP THINGS ###
        self.focusTracker = focus_tracker.FocusTracker(self.config, logger=self.logger)
        # a variable to keep track of how many times we've attempted to focus. different numbers have different affects on focus routine
        self.focus_attempt_number = 0

        ### A class to keep track of the calibration sequences
        self.caltracker = cal_tracker.CalTracker(
            config=self.config,
            active_cams=self.camdict.keys(),
            logger=self.logger,
            sunsim=self.sunsim,
            verbose=False,
        )

        # keep track of the last command executed so it can be broadcast as an error if needed
        self.lastcmd = None

        ### OBSERVING FLAGS ###
        # set attribute to indicate if robo operator is running (
        ## this flag is used to pause the schedule execution if we want to.
        ## ie we want to stop the schedule even though it's okay to observe
        self.running = False

        # set an attribute to indicate if we are okay to observe
        ## ie, if startup is complete, the calibration is complete, and the weather/dome is okay
        self.ok_to_observe = False
        self.estop_active = False

        # an override which will make the observatory keep running even if the autoStart is not fully complete
        # eg if the temps are not stablizing but you still want to observe NOW
        self.autostart_override = False

        # a flag to indicate we're in a daylight test mode which will spoof some observations and trigger
        ## off of schedule alt/az rather than ra/dec
        # NPL 1-12-21: making it so that if we are in dometest or sunsim mode that we turn on test_mode
        if self.sunsim or self.dometest or self.mountsim:
            self.test_mode = True
        else:
            self.test_mode = False

        # a flag to denote whether an observation (eg, roboOperator.do_observation) was completed successfully
        self.observation_completed = False

        # a flag to denote whether the observatory (ie telescope and dome) are ready to observe, not including whether dome is open
        self.observatory_ready = False
        # a similar flag to denote whether the observatory is safely stowed
        self.observatory_stowed = False

        ### ALARMS ###
        self.active_alarms = []
        self.alarm_enable = True

        """ TO PURGE! # NPL 10-3-23
        ### SET UP THE WRITER ###
        # init the database writer
        writerpath = self.config['obslog_directory'] + '/' + self.config['obslog_database_name']
        #self.writer = ObsWriter.ObsWriter('WINTER_ObsLog', self.base_directory, config = self.config, logger = self.logger) #the ObsWriter initialization
        self.writer = ObsWriter.ObsWriter(writerpath, self.base_directory, config = self.config, logger = self.logger) #the ObsWriter initialization
        # create an empty dict that will hold the data that will get written out to the fits header and the log db
        self.data_to_log = dict()
        """
        ### SCHEDULE ATTRIBUTES ###
        # hold a variable to track remaining dithers in kst
        self.remaining_dithers = 0

        # create exposure timer to wait for exposure to finish
        self.waiting_for_exposure = False
        self.exptimer = QtCore.QTimer()
        self.exptimer.setSingleShot(True)
        # if there's too many things i think they may not all get triggered?
        # self.exptimer.timeout.connect(self.log_timer_finished)
        # self.exptimer.timeout.connect(self.log_observation_and_gotoNext)
        # self.exptimer.timeout.connect(self.rotator_stop_and_reset)

        # when the image is saved, log the observation and go to the next
        #### FIX THIS SOON! NPL 6-13-21
        # self.ccd.imageSaved.connect(self.log_observation_and_gotoNext)

        ### a QTimer for handling the cadance of checking what to do
        self.checktimer = QtCore.QTimer()
        self.checktimer.setSingleShot(True)
        self.checktimer.setInterval(30 * 1000)
        self.checktimer.timeout.connect(self.checkWhatToDo)

        ### a QTimer for handling a longer pause before checking what to do
        self.waitAndCheckTimer = QtCore.QTimer()
        self.waitAndCheckTimer.setSingleShot(True)
        self.waitAndCheckTimer.timeout.connect(self.checkWhatToDo)

        ### Some methods which will log things we pass to the fits header info
        self.resetObsValues()

        """
        self.operator = self.config.get('fits_header',{}).get('default_operator','')
        self.programPI = ''
        self.programID = 0
        self.qcomment = ''
        self.targtype = ''
        self.targname = ''
        """

        ### CONNECT SIGNALS AND SLOTS ###
        self.startRoboSignal.connect(self.restart_robo)
        self.stopRoboSignal.connect(self.stop)
        # TODO: is this right (above)? NPL 4-30-21

        self.hardware_error.connect(self.broadcast_hardware_error)

        self.telescope.signals.wrapWarning.connect(self.handle_wrap_warning)
        # change schedule. for now commenting out bc i think its handled in the robo Thread def
        # self.changeSchedule.connect(self.change_schedule)

        self.watchdog.winterAlarm.connect(self.estop_camera)
        # self.cameraAlarm.connect(self.estop_camera)
        # self.chillerAlarm.connect(self.estop_camera)

        ## overrides
        """ Lets you run with the dome closed and ignore sun/weather/etc """
        if self.dometest:
            self.dome_override = True
            self.sun_override = True
        else:
            # override the dome.ok_to_open flag
            self.dome_override = False
            # override the sun altitude flag
            self.sun_override = False

        # some variables that hold the state of the sequences
        self.startup_complete = False
        self.calibration_complete = False

        ### SET UP THE SCHEDULE ###
        # dictionary to hold TOO schedules
        self.ToOschedules = dict()

        # set up the survey schedule. init it as self.schedule, but later self.schedule will switch if there's a TOO
        # self.surveySchedule = schedule.Schedule(base_directory = self.base_directory, config = self.config, logger = self.logger)

        # self.lastSeen = -1
        self.obsHistID = -1
        ## in robotic mode, the schedule file is the nightly schedule
        if self.mode == "r":
            self.survey_schedulefile_name = "nightly"
        ## in manual mode, the schedule file is set to None
        else:
            self.survey_schedulefile_name = None

        # set up the schedule
        ## after this point we should have something in self.schedule.currentObs
        self.change_schedule(self.survey_schedulefile_name, postPlot=True)
        # self.schedule.loadSchedule(self.survey_schedulefile_name, postPlot = True)

        ### SET UP POINTING MODEL BUILDER ###
        self.pointingModelBuilder = pointingModelBuilder.PointingModelBuilder()

        # set up poll status thread
        self.updateThread = data_handler.daq_loop(
            func=self.update_state, dt=500, name="robo_status_update"
        )

    def broadcast_hardware_error(self, error):
        msg = f":redsiren: *{error.system.upper()} ERROR* ocurred when attempting command: *_{error.cmd}_*, {error.msg}"
        group = "operator"
        self.alertHandler.slack_log(msg, group=group)

        # turn off tracking
        self.rotator_stop_and_reset()

    def waitAndCheck(self, seconds):
        """
        start a QTimer to wait the specified number of seconds, and then
        trigger roboOperator to execute self.CheckWhatToDo()
        """

        ms = int(seconds * 1000.0)

        self.waitAndCheckTimer.setInterval(ms)

        self.waitAndCheckTimer.start()

    def announce(self, msg, group=None):
        self.log(f"robo: {msg}")
        self.alertHandler.slack_log(msg, group=group)

    def doCommand(self, cmd_obj):
        """
        This is connected to the newCommand signal. It parses the command and
        then executes the corresponding command from the list below

        using this as a reference: (source: https://stackoverflow.com/questions/6321940/how-to-launch-getattr-function-in-python-with-additional-parameters)

        """
        # print(f'dome: caught doCommand signal: {cmd_obj.cmd}')
        cmd = cmd_obj.cmd
        args = cmd_obj.args
        kwargs = cmd_obj.kwargs

        try:
            getattr(self, cmd)(*args, **kwargs)
        except:
            pass

    def update_state(self, printstate=False):
        self.get_observatory_ready_status()
        self.get_observatory_stowed_status()
        fields = [
            "ok_to_observe",
            "target_alt",
            "target_az",
            "target_ra_j2000_hours",
            "target_dec_j2000_deg",
            "visitExpTime",
            "obsHistID",
            "targetPriority",
            "operator",
            "obstype",
            "programPI",
            "validStart",
            "validStop",
            "programID",
            "programName",
            "qcomment",
            "targtype",
            "targetName",
            "obsmode",
            "scheduleName",
            "scheduleType",
            "maxAirmass",
            #'ditherNumber',
            "num_dithers",
            "dithnum",
            "ditherStepSize",
            "fieldID",
            "observatory_stowed",
            "observatory_ready",
        ]

        for field in fields:
            try:
                val = getattr(self, field)
                # if type(val) is bool:
                #    val = int(val)
                self.robostate.update({field: val})
            except Exception as e:
                if printstate:
                    print(f"could not add {field} to robostate: {e}")
                pass
        if printstate:
            print(f"robostate = {json.dumps(self.robostate, indent = 3)}")

    def estop_camera(self):
        # self.announce('This is a test of the camera ESTOP!')
        self.announce(":redsiren: CAUGHT CRITICAL CAMERA ALARMS!", group="operator")

        self.estop_active = True

        self.announce("Sending TEC Stop Command to all FPAS")
        self.doTry("tecStop")
        time.sleep(2)

        self.announce("Sending camera shutdown to all FPAS")
        self.doTry("shutdownCamera")
        time.sleep(2)

        self.announce("Powering off sensor power with the labjack")
        self.doTry("fpa off")
        time.sleep(2)

        self.announce("Powering off the sensor power box AC input power with the PDU")
        self.doTry("pdu off fpas")
        time.sleep(2)

        self.announce("setting chiller setpoint to 20C to avoid possible condensation")
        self.doTry("chiller_set_setpoint 20")
        time.sleep(2)

        self.announce(
            "Completed camera ESTOP handling, locking out further observations until further operator intervention.",
            group="operator",
        )
        self.running = False

    def rotator_stop_and_reset(self):
        if self.mountsim:
            return

        self.log(f"stopping rotator and resetting to home position")
        # if the rotator is on do this:
        self.log(f'rotator_is_enabled = {self.state["rotator_is_enabled"]}')
        if self.state["rotator_is_enabled"]:
            # stop the rotator
            self.doTry("rotator_stop")
            # turn off tracking
            self.doTry("mount_tracking_off")
            self.doTry("rotator_home")
            # turn on wrap check again
            self.doTry("rotator_wrap_check_enable")

    def toggle_autostart_override(self, state: bool):
        """
        set the autostart override to the desired state

        """
        self.autostart_override = state

    def handle_wrap_warning(self, angle):

        # create a notification
        msg = f'*WRAP WARNING!!* rotator angle {angle} outside allowed range [{self.config["telescope"]["rotator_min_degs"]},{self.config["telescope"]["rotator_max_degs"]}])'
        context = ""
        system = "rotator"
        cmd = self.lastcmd
        """
        err = roboError(context, cmd, system, msg)
        # directly broadcast the error rather than use an event to keep it all within this event
        self.broadcast_hardware_error(err)
        self.log(msg)
        """
        msg = f":redsiren: *{system.upper()} ERROR* ocurred when attempting command: *_{cmd}_*, {msg}"
        group = "operator"
        self.alertHandler.slack_log(msg, group=group)

        # STOP THE ROTATOR
        self.rotator_stop_and_reset()

        # got to the next observation
        # NPL: comment this out while hunting the
        # self.checkWhatToDo()

    def updateOperator(self, operator_name):
        if type(operator_name) is str:
            self.operator = operator_name
            self.log(f"updating current operator to: {operator_name}")
        else:
            self.log(
                f"specified operator {operator_name} is not a valid string! doing nothing."
            )

    def updateObsType(self, obstype):
        if type(obstype) is str:
            self.obstype = obstype
            self.log(f"updating current obstype to: {obstype}")
        else:
            self.log(
                f"specified obstype {obstype} is not a valid string! doing nothing."
            )

    def updateQComment(self, qcomment):
        if type(qcomment) is str:
            self.qcomment = qcomment
            self.log(f"updating current qcomment to: {qcomment}")
        else:
            self.log(
                f"specified obstype {qcomment} is not a valid string! doing nothing."
            )

    def switchCamera(self, camname):

        try:
            camera = self.camdict[camname]
            fw = self.fwdict[camname]

            # if that worked then switch it
            self.camera = camera
            self.fw = fw
            self.camname = camname
            msg = f"switched roboOperator's camera to {self.camname}"

        except Exception as e:
            msg = f"could not switch camera to {camname}: {e}"

        self.log(msg)
        # print('\n\n\n\n')
        # print('######################################################')
        # print(msg)
        # print('######################################################')
        # print('\n\n\n\n')

    def getWhichCameraToUse(self, filterID):
        # look up which camera to use based on the specified filterID
        try:
            for camname in self.config["filters"]:
                for filt in self.config["filters"][camname]:
                    if filt == filterID:
                        return camname

            # if we're here we didn't find the filter
            self.log(
                f"no camera found with filter corresponding to filterID: {filterID}"
            )
            return None

        except Exception as e:
            self.log(
                f"could not look up which camera to use for specified filterID = {filterID} due to {type(e)}: {e}"
            )
            return None

    def restart_robo(self, arg="auto"):
        # run through the whole routine. if something isn't ready, then it waits a short period and restarts
        # if we get passed test mode, or have already started in test mode, then turn on sun_override
        if arg == "test" or self.test_mode == True:
            # we're in test mode. turn on the sun override
            self.sun_override = True
            self.test_mode = True

        else:
            self.sun_override = False
            self.test_mode = False

        # if we're in this loop, the robotic schedule operator is running:
        self.running = True

        self.checkWhatToDo()

    def get_dome_status(self, logcheck=False):
        """
        This checks for any weather and dome faults that would prevent observing
        THE ACTUAL DOME CHECKING HAPPENS IN THE DOME DAEMON (self.dome.ok_to_open)
        Examples:
            - Close_Status (remote closure)
            - Weather_Status (weather okay)
        Does not check:
            - Shutter_Status (dome open or closed)
            - Sun_Status (sun down)
        If things are okay it returns True, otherwise False
        """

        # make a note of why we're going ahead with opening the dome

        """
        # Check that the dome is okay to open
        want ot make sure the dome is okay. instead of just checking weather it 
        is okay NOW, check how long it has been since it was okay. this will
        effectively smooth out some issues where the dome reports back a single
        bad value. now that timeout (self.dome.dt_since_last_ok_to_open) will
        get reset to zero every time its okay.
        
        now it will continue to be happy as long until the dome has been reporting
        back that it is in a bad state for longer than dome_badness_timeout sec.
        """
        dome_badness_timeout = 5.0
        # if self.dome.ok_to_open & (self.dome.dt_since_last_ok_to_open < 5.0):
        if self.dome.dt_since_last_ok_to_open < dome_badness_timeout:

            # self.logger.info(f'robo: the dome says it is okay to open.')# sending open command.')
            return True
        elif self.dome_override:
            if logcheck:
                self.logger.warning(
                    f"robo: the DOME IS NOT OKAY TO OPEN, but dome_override is active so I'm sending open command"
                )
            return True
        else:
            # shouldn't ever be here
            self.logger.warning(f"robo: dome is NOT okay to open")
            return False

    def get_sun_status(self, logcheck=False):
        """
        This checks that the sun is low enough to observe

        If things are okay to observe it returns True, otherwise False
        """
        if self.dome.Sunlight_Status == "READY" or self.sun_override:
            # make a note of why we want to open the dome
            if self.dome.Sunlight_Status == "READY":
                return True
            elif self.sun_override:
                if logcheck:
                    self.logger.warning(
                        f"robo: the SUN IS ABOVE THE HORIZON, but sun_override is active so I want to open the dome"
                    )
                return True
            else:
                self.logger.warning(
                    f"robo: I shouldn't ever be here. something is wrong with sun handling"
                )
                return False

    def check_ok_to_observe(self, logcheck=False):
        """
        check if it's okay to observe/open the dome

        # NPL: 12-14-21 removed all the actions, this now is just a status check which can
        raise any necessary flags during observations. Mostly it's biggest contribution is that
        if the weather gets bad DURING an exposure that exposure will not be logged.


        # logcheck flag indicates whether the result of the check should be written to the log
            we want the result logged if we're checking from within the do_observing loop,
            but if we're just loopin through restart_robo we can safely ignore the constant logging'
        """

        # if estop active return false immediately
        if self.estop_active:
            self.ok_to_observe = False
            return

        # if we're in dometest mode, ignore the full tree
        if self.dometest:
            self.ok_to_observe = True
            return

        if self.get_sun_status():

            # if we can open up the dome, then do it!
            if self.get_dome_status():

                # Check if the dome is open:
                # if self.dome.Shutter_Status == 'OPEN':
                # NPL 4-23-23 this is a kluge to avoid issues when shutter status is "UNKNOWN"
                # eventually we want to move to smarter handling of these bad reads from the shutter
                if self.dome.Shutter_Status in ["OPEN", "UNKNOWN"]:
                    if logcheck:
                        self.logger.info(f"robo: okay to observe check passed")

                    #####
                    # We're good to observe
                    self.ok_to_observe = True
                    return
                    #####

                else:
                    # dome is closed.
                    self.alertHandler.slack_log(
                        f"the dome shutter is not reporting open, it says: dome.Shutter_Status = {self.dome.Shutter_Status}"
                    )
                    self.ok_to_observe = False
                    return

            else:
                # there is an issue with the dome

                self.ok_to_observe = False
                return

        else:
            # the sun is up
            self.ok_to_observe = False
            return

    def checkWhatToDo(self):
        """
        Created: NPL 12-14-21
        This is the new main method for the robotic loop!
        The idea is that the workflow is now:
            -> check if it's okay to observe:
                if yes:
                    -> check what we should be observing now: run schedule.gotoNextObs()
                        if schedule.currentObs is None:

                if no:
                    -> stow the telescope safely

        Loop-like Action:
            In some cases some action will be dispatched, and then it will be necessary to check again.
                ex: the dome wasn't open, so an open command was sent

            In other cases everything will check out okay, but there will be no valid observations.

            In both of the above cases, the desired action will be to re-check what to do after a short
            wait. This is handled by a one-shot QTimer which waits a predetermined amount of time. The timeout
            of the QTimer (self.checktimer) is connected to this method, so that anytime that QTimer is started
            checkWhatToDo will be rerun after the wait. This sets up looping events where this code will continue
            to flow as necessary, without firing at unwanted times.
        """
        self.log("checking what to do!")
        if self.running:
            self.log("robo operator is running")

            # ---------------------------------------------------------------------
            # check the camera(s)
            # ---------------------------------------------------------------------
            """
            - check if the camera(s) should be on
            - if they should be on:
                - see if startup has been requested. 
                - if startup requested already:
                    - pass
                - else if startup not requested yet:
                    - request startup
            - else if they should be off:
                - see if shutdown has been requested
                - if shutdown requested already:
                    - pass
                - else if shutdown not requested yet:
                    - request shutdown
            * Do not run checktimer here. it should always make it through
            this block, and down to the observatory checks below. That is
            where we will trigger the checktimer wait to run the loop again.
            """

            """
            Camera Startup:
                Camera is ready_to_startup if:
                    - power supplies are on
                    - chiller is in good shape
                Camera is ready_to_cool if:
                    - sensor daemons are connected
                    - sensors are connected
                    - sensors have a record of a good bias frame
                Camera is ready_to_observe if:
                    - TEC is running
                    - sensor temps are at setpoint
                    - sensor temps are steady 
            Camera Shutdown:
                Camera is ready_to_warm if:
                    - sensor daemons are connected
                    - sensors are connected 
                Camera is ready_to_shut down if:
                    - sensors are warm
                Camera is ready to power off if:
                    - TECs are off
                    - sensors are shutdown
            
                
                
            if camera_should_be_on:
                if camera_is_on:
                    # the camera is on as requested
                    if camera_is_ready_to_observe:
                        # good! fine to observe.
                        pass
                    else:
                        if taking_too_long_to_startup:
                            send_out_an_alert_about_this()
                        else:
                            # we're just waiting for the TEC to cool
                            self.checktimer.start()
                else:
                    # the camera is not on but it should be
                    robo_startup_camera()
                    
            else:
                # the camera should not be on
                if camera_is_on:
                    
                    if camera_is_shutting_down:
                        if taking_too_long_to_shutdown:
                            send_out_an_alert_about_this()
                        else:
                            # we're just waiting for the camera to '
                    # the camera is on and it should NOT be
                    robo_shutdown_camera()
                
                        
                
            
            """
            # WINTER camera
            self.log("checking if the camera should be on")
            if self.get_camera_should_be_running_status():
                self.log(f"the camera should be on!")

                self.log(
                    f"autoStartRequested = {self.camdict['winter'].state.get('autoStartRequested','?')}"
                )
                self.log(
                    f"autoStartComplete = {self.camdict['winter'].state.get('autoStartComplete','?')}"
                )

                # the camera should be running! make sure it is.
                if self.camdict["winter"].state["autoStartRequested"]:
                    # the camera should be on

                    if (
                        self.camdict["winter"].state["autoStartComplete"]
                        or self.autostart_override
                    ):
                        if self.autostart_override:
                            self.log(f"autostart override is ON")
                        self.log(f"autostart requested and complete.")
                        # the startup is complete!
                        # double check it
                        if (
                            True
                        ):  # self.get_winter_camera_ready_to_observe_status(): #NPL 7/3/24
                            self.log(f"camera is okay to observe!")
                            self.cameras_ready = True
                            # the camera is confirmed good to observe

                            # ---------------------------------------------------------------------
                            ### OBSERVING SEQUENCE ###
                            # ---------------------------------------------------------------------

                            # ---------------------------------------------------------------------
                            # check if we need to do any cals
                            # ---------------------------------------------------------------------
                            # note this needs to go first, otherwise cals won't happen if the weather is bad!

                            cals_to_do = self.caltracker.getCalsToDo(
                                sun_alt=self.state["sun_alt"],
                                timestamp=self.state["timestamp"],
                                sun_rising=self.state["sun_rising"],
                            )

                            # announce that we're going to dispatch the first cal to do:
                            if len(cals_to_do) > 0:
                                # announce the list of cals to do:
                                self.announce(f"required cals: {cals_to_do}")

                                for cal_desc, cal_cmd in cals_to_do:
                                    self.announce(
                                        f"dispatching first cal sequence on the list: {cals_to_do[0]}"
                                    )

                                    # log that we are attempting the cal sequence
                                    self.caltracker.logCommand(
                                        trigname=cal_desc,
                                        sun_alt=self.state["sun_alt"],
                                        timestamp=self.state["timestamp"],
                                    )

                                    self.doTry(cal_cmd)

                                    self.log(
                                        f"finished executing cal sequence {cal_desc}:"
                                    )
                                    QtCore.QCoreApplication.processEvents()

                                self.announce(
                                    f"finished executing all active requests for cal sequences, going to check what to do next"
                                )
                                self.checktimer.start()
                                return

                            else:
                                self.log(
                                    f"no required cals, proceeding to observing sequence"
                                )
                                pass

                            # ---------------------------------------------------------------------
                            ### check the dome
                            # ---------------------------------------------------------------------
                            if self.get_dome_status():
                                # if True, then the dome is fine
                                self.log("the dome status is good!")
                                pass
                            else:
                                self.log(
                                    "there is a problem with the dome (eg weather, etc). STOWING OBSERVATORY"
                                )
                                # there is a problem with the dome.
                                self.stow_observatory(force=False)
                                # skip the rest of the checks, just start the timer for the next check
                                self.checktimer.start()
                                return
                            # ---------------------------------------------------------------------
                            # check the sun
                            # ---------------------------------------------------------------------
                            if self.get_sun_status():
                                self.log(f"the sun is low are we are ready to go!")
                                # if True, then the sun is fine. just keep going
                                pass
                            else:
                                self.log(f"waiting for the sun to set")
                                # the sun is up, can't proceed. just hang out.
                                self.checktimer.start()
                                return
                            # ---------------------------------------------------------------------
                            # check if the observatory is ready
                            # ---------------------------------------------------------------------
                            if self.get_observatory_ready_status():
                                self.log(f"the observatory is ready to observe!")
                                # if True, then the observatory is ready (eg successful startup and focus sequence)
                                pass
                            else:
                                self.log(f"need to start up observatory")
                                # we need to (re)run do_startup
                                self.do_startup()
                                # after running do_startup, kick back to the top of the loop
                                self.checktimer.start()
                            # ---------------------------------------------------------------------
                            # check the dome
                            # ---------------------------------------------------------------------
                            if self.dometest:
                                self.log(
                                    "dometest mode: ignoring whether the shutter is open!"
                                )
                                pass
                            else:
                                if self.dome.Shutter_Status == "OPEN":
                                    self.log(
                                        f"the dome is open and we are ready to start taking data"
                                    )
                                    # the dome is open and we're ready for observations. just pass
                                    pass
                                else:
                                    # the dome and sun are okay, but the dome is closed. we should open the dome
                                    self.announce(
                                        "observatory and sun are ready for observing, but dome is closed. opening..."
                                    )
                                    self.doTry("dome_open")

                                    self.checktimer.start()
                                    return

                            # ---------------------------------------------------------------------
                            # check the filter wheel
                            # ---------------------------------------------------------------------

                            for camname in self.fwdict:
                                if self.state[f"{camname}_fw_is_homed"] != 1:
                                    # the filter wheel is not homed
                                    self.announce(
                                        f"{camname} filter wheel is not homed! sending fw_home command."
                                    )
                                    self.doTry(f"fw_home --{camname}")

                                    self.checktimer.start()
                                    return
                                else:
                                    pass

                            # ---------------------------------------------------------------------
                            # get the current timestamp and MJD
                            # ---------------------------------------------------------------------
                            # turn the timestamp into mjd

                            # TODO: NPL 8-17-22 there's no reason (I THINK) not to always use the time from self.ephem?
                            obstime_mjd = self.ephem.state.get("mjd", 0)
                            obstime_timestamp_utc = astropy.time.Time(
                                obstime_mjd, format="mjd"
                            ).unix

                            # ---------------------------------------------------------------------
                            # check if we need to focus the telescope
                            # ---------------------------------------------------------------------

                            if (
                                self.state["sun_alt"]
                                >= self.config["max_sun_alt_for_observing"]
                            ):
                                self.log(
                                    f"sun alt = {self.state['sun_alt']:.2f}, not yet ready for observing..."
                                )
                                self.checktimer.start()
                                return
                            else:
                                pass

                            graceperiod_hours = self.config["focus_loop_param"][
                                "focus_graceperiod_hours"
                            ]
                            if self.test_mode == True:
                                self.log(f"not checking focus bc we're in test mode")
                                pass
                            else:
                                filterIDs_to_focus = (
                                    self.focusTracker.getFiltersToFocus(
                                        obs_timestamp=obstime_timestamp_utc,
                                        graceperiod_hours=graceperiod_hours,
                                        cam=self.camname,
                                    )
                                )

                                # here is a good place to insert a good check on temperature change,
                                # or even better a check on FWHM of previous images

                                if not filterIDs_to_focus is None:
                                    print(
                                        f"robo: focus attempt #{self.focus_attempt_number}"
                                    )
                                    if (
                                        self.focus_attempt_number
                                        <= self.config["focus_loop_param"][
                                            "max_focus_attempts"
                                        ]
                                    ):
                                        self.announce(
                                            f"**Out of date focus results**: we need to focus the telescope in these filters: {filterIDs_to_focus}"
                                        )
                                        # there are filters to focus! run a focus sequence
                                        self.do_focus_sequence(
                                            filterIDs=filterIDs_to_focus
                                        )
                                        self.announce(
                                            f"got past the do_focus_sequence call in checkWhatToDo?"
                                        )
                                        self.focus_attempt_number += 1
                                        # now exit and rerun the check
                                        self.checktimer.start()
                                        return

                            # here we should check if the temperature has changed by some amount and nudge the focus if need be

                            # ---------------------------------------------------------------------
                            # check what we should be observing NOW
                            # ---------------------------------------------------------------------
                            # if it is low enough (typically between astronomical dusk and dawn)
                            # then check for targets, otherwise just stand by
                            # print(f'checking what to observe NOW')
                            if (
                                self.state["sun_alt"]
                                <= self.config["max_sun_alt_for_observing"]
                            ):
                                self.load_best_observing_target(obstime_mjd)

                                # print(f'currentObs = {self.schedule.currentObs}')
                                # print(f'self.schedule.schedulefile = {self.schedule.schedulefile}, self.schedule.scheduleType = {self.schedule.scheduleType}')
                                # print(f'type(self.schedule.currentObs) = {type(self.schedule.currentObs)}')
                                # print(f'self.schedule.currentObs == "default": {self.schedule.currentObs == "default"}')
                                if self.schedule.currentObs is None:
                                    # if currentObs is None:
                                    self.announce(
                                        f'no valid observations at this time (MJD = {self.state.get("ephem_mjd",-999)}), standing by...'
                                    )
                                    # first stow the rotator
                                    self.rotator_stop_and_reset()

                                    if self.schedule.end_of_schedule == True:
                                        if self.schedulefile_name is None:
                                            pass
                                        else:
                                            self.announce(
                                                f"{self.schedule.schedulefile_name} completed! shutting down schedule connection"
                                            )
                                        self.handle_end_of_schedule()
                                    # nothing is up right now, just loop back and check again
                                    self.checktimer.start()
                                    return

                                else:
                                    # if we got an observation, then let's go do it!!
                                    # log the observation to note that we ATTEMPTED the observation

                                    # for now, still logging the observation first.
                                    # next step is to move it to after.

                                    self.schedule.log_observation()

                                    self.do_currentObs(self.schedule.currentObs)

                                    # if we get here, then the observation is complete, either bc it's done or there was an error

                                    # now immediatly check what we should do now (eg don't wait)
                                    self.checkWhatToDo()

                            else:
                                # if we are here then the sun is not low enough to observe, stand by
                                self.checktimer.start()
                                return

                            pass
                        else:

                            # camera is not ready but autostart has been requested. stand by
                            self.log(
                                f"camera autostart not finished yet. Standing by..."
                            )
                            self.cameras_ready = False
                            self.checktimer.start()
                            return
                    else:
                        # camera is not ready but autostart has been requested. stand by
                        self.log(
                            f"camera autostart requested but not finished yet. Standing by..."
                        )
                        self.cameras_ready = False
                        self.checktimer.start()
                        return
                else:
                    # we need to request an autostart
                    # self.doTry('autoStartupCamera --winter', context = 'robo loop', system = 'camera')
                    self.log(
                        f"autoStartRequested is not True, even though the camera autostart should have been requested. Requesting again"
                    )
                    self.log(f"running do_camera_startup")
                    self.do_camera_startup("winter")
                    # self.cameras_ready = False
                    self.checktimer.start()
                    return
            else:
                # the camera should be off
                self.log(f"the camera should be off")
                self.log(
                    f"autoShutdownRequested = {self.camdict['winter'].state['autoShutdownRequested']}"
                )
                self.log(
                    f"autoShutdownComplete = {self.camdict['winter'].state['autoShutdownComplete']}"
                )

                # the camera should be running! make sure it is.
                if self.camdict["winter"].state["autoShutdownRequested"]:
                    # the camera should be on

                    if self.camdict["winter"].state["autoShutdownComplete"]:

                        self.log(f"auto shutdown complete.")
                        # check if the camera is actually stowed

                        # # the startup is complete!
                        # # double check it
                        # if self.get_winter_camera_ready_to_observe_status():
                        #     self.log(f'camera is okay to observe!')
                        #     # the camera is confirmed good to observe
                        #     pass
                        # else:

                        #     # camera is not ready but autostart has been requested. stand by
                        #     self.log(f'camera autostart not finished yet. Standing by...')
                        #     self.checktimer.start()
                        #     return
                        # camera is not ready but autostart has been requested. stand by
                        self.log(f"camera auto shutdown finished. ")

                        if self.get_winter_camera_stowed_status():

                            self.log(f"camera power already off. standing by.")
                            pass

                        else:
                            self.announce(
                                f"Camera Auto Shutdown Complete, but camera still powered. Shutting off focal plane power."
                            )

                            self.do_camera_power_shutdown("winter")

                            msg = "camera powered off!"
                            self.announce(msg)
                            pass

                        # stow the observatory if it is not already
                        if self.get_observatory_stowed_status():
                            self.log(f"observatory already stowed.")
                            pass
                        else:
                            self.announce(f"stowing observatory")
                            self.stow_observatory(force=False)

                        # self.running = False
                        self.checktimer.start()
                        return

                    else:
                        # camera is not ready but autostart has been requested. stand by
                        self.log(
                            f"camera auto shutdown requested but not finished yet. Standing by..."
                        )
                        # self.cameras_ready = False
                        self.checktimer.start()
                        return
                else:
                    # we need to request an autostart
                    # self.doTry('autoStartupCamera --winter', context = 'robo loop', system = 'camera')
                    self.log(
                        f"autoShutdown Requested is not True, even though the camera auto shutdown should have been requested. Requesting again"
                    )
                    self.log(f"running do_camera_shutdown")
                    self.do_camera_shutdown("winter")
                    # self.cameras_ready = False
                    self.checktimer.start()
                    return

                pass

            # if self.cameras_ready:
            #     self.log(f'cameras are ready. continuing with observatory checks')
            #     pass
            # else:
            #     self.log(f'cameras not ready. standing by while we wait for them...')
            #     self.checktimer.start()
            #     return

    def load_best_observing_target(self, obstime_mjd):
        """
        query all available schedules (survey + any schedules in the TOO folder),
        then rank them and return the highest ranked instance. this is what we want to observe
        """
        self.log(f"running load_best_observing_target routine...")

        # TODO: this is dumb and slow. all of wsp should be pulling obstime_mjd from ephem, not duplicating the effort here.
        if obstime_mjd == "now":
            obstime_mjd = float(astropy.time.Time(datetime.utcnow()).mjd)

        # get all the files in the ToO High Priority folder
        ToO_schedule_directory = os.path.join(
            os.getenv("HOME"), self.config["scheduleFile_ToO_directory"]
        )
        ToOscheduleFiles = glob.glob(os.path.join(ToO_schedule_directory, "*.db"))

        self.log(f"found these schedule files in the TOO directory: {ToOscheduleFiles}")
        self.log(f"analyzing schedules...")

        if len(ToOscheduleFiles) > 0:
            # bundle up all the schedule files in a single pandas dataframe
            full_df = pd.DataFrame()
            # add all the ToOs
            for too_file in ToOscheduleFiles:
                try:
                    ### try to read in the SQL file
                    self.log(f"validating too_file = {too_file}")
                    engine = db.create_engine("sqlite:///" + too_file)
                    conn = engine.connect()
                    df = pd.read_sql("SELECT * FROM summary;", conn)

                    # if targname not in the df, add in a default
                    if "targName" not in df:
                        df["targName"] = ""

                    # keep analyzing and making cuts unless you throw away all the entries
                    df["origin_filepath"] = too_file
                    df["origin_filename"] = os.path.basename(too_file)
                    conn.close()

                    ### if we were able to load and query the SQL db, check to make sure the schema are correct
                    wintertoo_validate.validate_schedule_df(df)
                    self.log(f"obstime_mjd = {obstime_mjd}")
                    select_cols = df[
                        [
                            "raDeg",
                            "decDeg",
                            "filter",
                            "progPI",
                            "priority",
                            "obsHistID",
                            "targName",
                            "observed",
                            "origin_filename",
                        ]
                    ]
                    self.log(f"entries before making any cuts: df = \n{select_cols}")

                    ### if the schema were correct, make cuts based on observability
                    # Note: if we don't do this we can end up in a situation where do_Observation will reject an
                    #       observation, but this will keep submitting it and we'll get stuck in a useless loop
                    # select only targets within their valid start and stop times
                    df = df.loc[
                        (obstime_mjd >= df["validStart"])
                        & (obstime_mjd <= df["validStop"])
                        & (df["observed"] == 0)
                    ]

                    select_cols = df[
                        [
                            "raDeg",
                            "decDeg",
                            "filter",
                            "progPI",
                            "priority",
                            "obsHistID",
                            "targName",
                            "observed",
                            "origin_filename",
                        ]
                    ]
                    self.log(
                        f"after making cuts on start/stop times and observed status: df = \n{select_cols}"
                    )

                    if len(df) == 0:
                        self.log(
                            f"{too_file}: no valid entries after start/stop/observed cuts"
                        )
                        continue
                    else:
                        pass
                    # if the maxAirmass is not specified, add it in
                    if "maxAirmass" not in df:
                        default_max_airmass = 1.0 / np.cos(
                            (90 - self.config["telescope"]["min_alt"]) * np.pi / 180.0
                        )
                        df["maxAirmass"] = default_max_airmass

                    # calculate the current airmass of all targets

                    obstime_astropy = astropy.time.Time(obstime_mjd, format="mjd")

                    frame = astropy.coordinates.AltAz(
                        obstime=obstime_astropy, location=self.ephem.site
                    )
                    self.log("made the frame ?")
                    self.log(f"df['raDeg'] = {df['raDeg']}")
                    self.log(f"df['decDeg'] = {df['decDeg']}")

                    j2000_coords = astropy.coordinates.SkyCoord(
                        ra=df["raDeg"] * u.deg,
                        dec=df["decDeg"] * u.deg,
                        frame="icrs",
                    )
                    self.log("made the j2000 coords?")

                    local_coords = j2000_coords.transform_to(frame)
                    local_alt_deg = local_coords.alt.deg
                    local_az_deg = local_coords.az.deg
                    airmass = 1 / np.cos((90 - local_alt_deg) * np.pi / 180.0)
                    df["currentAirmass"] = airmass
                    df["currentAltDeg"] = local_alt_deg
                    df["currentAzDeg"] = local_az_deg

                    # make a cut based on airmass
                    df = df.loc[
                        (df["currentAirmass"] < df["maxAirmass"])
                        & (df["currentAirmass"] > 0)
                    ]
                    select_cols = df[
                        [
                            "raDeg",
                            "decDeg",
                            "filter",
                            "progPI",
                            "priority",
                            "obsHistID",
                            "targName",
                            "origin_filename",
                        ]
                    ]
                    self.log(f"after airmass cuts: df = \n{select_cols}")

                    # do a cut on max altitude also to make sure we don't point too high
                    df = df.loc[
                        (df["currentAltDeg"] <= self.config["telescope"]["max_alt"])
                        & (df["currentAltDeg"] >= self.config["telescope"]["min_alt"])
                    ]

                    select_cols = df[
                        [
                            "raDeg",
                            "decDeg",
                            "filter",
                            "progPI",
                            "priority",
                            "obsHistID",
                            "targName",
                            "origin_filename",
                        ]
                    ]
                    self.log(f"after elevation cuts: df = \n{select_cols}")

                    if len(df) == 0:
                        self.log(
                            f"{too_file}: no valid entries after elevation & airmass cuts"
                        )
                        continue
                    else:
                        pass

                    # calculate whether each target will be too close to ephemeris at the current obstime
                    bodies_inview = np.array([])
                    bodies = list(self.config["ephem"]["min_target_separation"].keys())
                    for i in range(len(bodies)):

                        body = bodies[i]
                        mindist = self.config["ephem"]["min_target_separation"][body]

                        body_loc = astropy.coordinates.get_body(
                            body,
                            time=obstime_astropy,
                            location=self.ephem.site,
                        )
                        body_coords = body_loc.transform_to(frame)
                        body_alt = body_coords.alt
                        body_az = body_coords.az

                        dist = np.array(
                            (
                                (df["currentAzDeg"] - body_az.deg) ** 2
                                + (df["currentAltDeg"] - body_alt.deg) ** 2
                            )
                            ** 0.5
                        )

                        # make a list of whether the body is in view for each target
                        body_inview = dist < mindist

                        # now make a big array of all bodies and all targets
                        if i == 0:
                            bodies_inview = body_inview
                        else:
                            bodies_inview = np.vstack((bodies_inview, body_inview))

                        # now collapse the array of bodies and targests so it's just a list of targets and w
                        # wheather there are ANY bodies in view
                        ephem_inview = np.any(bodies_inview, axis=0)

                    # add the ephem in view to the dataframe
                    df["ephem_inview"] = ephem_inview

                    self.log(f'df["ephem_inview"]: \n{df["ephem_inview"]}')

                    # make a cut on only targets without ephemeris in the way
                    df = df.loc[df["ephem_inview"] == False]

                    if len(df) == 0:
                        self.log(
                            f"{too_file}: no valid entries after making cuts on nearby ephemeris"
                        )
                        continue
                    else:
                        pass

                    # if we got here then the list isn't empty

                    # now add the schedule to the master TOO list
                    full_df = pd.concat([full_df, df])

                except wintertoo_validate.RequestValidationError as e:
                    too_filename = os.path.basename(os.path.normpath(too_file))
                    # self.log(f'skipping TOO schedule {too_filename}, schema not valid: {e}')
                    self.log(traceback.format_exc())
                except Exception as e:
                    self.log(f"error running load_best_observing_target: {e}")
                    self.log(traceback.format_exc())

            if len(full_df) == 0:
                # there are no valid schedule files. break out to the handling at the bottom
                pass

            else:

                # now do the sorting

                # now sort by priority (highest to lowest)
                # full_df = full_df.sort_values(['priority'],ascending=False)

                # now sort by validStop (earliest to latest)
                # full_df = full_df.sort_values(['validStop'],ascending=True)

                # THIS HAS TO BE IN ONE LINE OTHERWISE IT WILL RE-SORT NOT SORT WITHIN VALS!
                full_df = full_df.sort_values(
                    by=["priority", "validStop"], ascending=[False, True]
                )

                # save the dataframe to csv for realtime reference
                rankedSummary = full_df[
                    ["obsHistID", "priority", "validStop", "origin_filename"]
                ]
                rankedSummary.to_csv(
                    os.path.join(
                        os.getenv("HOME"),
                        "data",
                        "Valid_ToO_Observations_Ranked.csv",
                    )
                )

                # the best target is the first one in this sorted pandas dataframe
                currentObs = dict(full_df.iloc[0])
                scheduleFile = currentObs["origin_filepath"]
                scheduleFile_without_path = scheduleFile.split("/")[-1]
                self.announce(
                    f'we should be observing from {scheduleFile_without_path}, obsHistID = {currentObs["obsHistID"]}'
                )
                # point self.schedule to the TOO
                self.schedule.loadSchedule(scheduleFile)
                self.schedule.updateCurrentObs(currentObs, obstime_mjd)
                return

        # if we're here, there are no TOO valid observations
        self.announce(f"there are no valid ToO observations, defaulting to survey")

        scheduleFile = self.survey_schedulefile_name
        # point self.schedule to the survey
        self.announce(f"loading survey schedule: {scheduleFile}")
        self.schedule.loadSchedule(scheduleFile)
        currentObs = self.schedule.getTopRankedObs(obstime_mjd)
        # self.announce(f'currentObs = {currentObs}')
        self.schedule.updateCurrentObs(currentObs, obstime_mjd)
        return

    def get_center_offset_coords(
        self,
        ra_hours: float,
        dec_deg: float,
        pa: float = 90.0,
        offsettype="best",
    ):
        """
        Calculate the pointing ra/dec required to put the desired ra/dec at the given pixel
        position of the given board.
        :param ra: ra of the target in hours
        :param dec: dec of the target in degrees
        :param pa: where is north with respect to top of detector, positive (same as target_field_angle)
        is counter-clockwise
        :return: new_base_ra required for the board pointing
        :return: new_base_dec required for the board pointing
        """

        if (offsettype is None) or (offsettype.lower() == "none"):
            # just return the input parameters
            return ra_hours, dec_deg

        elif offsettype == "center":
            # NPL 2/13/24: it seems like no offset is actually properly aligned
            # and the below stuff isn't putting it in the center, either bc
            # the math is wrong, or bc the coordinates are incorrect.
            # x_pixel = 0
            # y_pixel = 0
            return ra_hours, dec_deg

        elif offsettype == "best":
            # what is the pixel where the observation should be centered on the best detector?
            # x_pixel: x pixel position on requested board. This assumes the X pixel value
            # when an individual board image is opened in DS9. Default is slightly lower of center.
            x_pixel = self.config["observing_parameters"][self.camname][
                "best_position"
            ]["x_pixel"]
            y_pixel = self.config["observing_parameters"][self.camname][
                "best_position"
            ]["y_pixel"]

        else:
            # invalid offset type
            self.log(f"invalid offset type selected, defaulting to no offset")
            return ra_hours, dec_deg
        # where does the center of pointing land by default
        base_pointing_x_pixel = self.config["observing_parameters"][self.camname][
            "base_position"
        ]["x_pixel"]
        base_pointing_y_pixel = self.config["observing_parameters"][self.camname][
            "base_position"
        ]["y_pixel"]

        # what is the shape of the detector?
        x_pixels = self.config["observing_parameters"][self.camname]["x_pixels"]
        y_pixels = self.config["observing_parameters"][self.camname]["y_pixels"]

        if self.camname == "winter":

            # get the board id of the best detector
            board_id = self.config["observing_parameters"][self.camname][
                "best_position"
            ]["board_id"]

            y_board_id_mapping = {4: 0, 2: 0, 3: 1, 0: 1, 1: 2, 5: 2}

            x_board_id_mapping = {4: 1, 2: 0, 3: 1, 0: 0, 1: 1, 5: 0}

            if board_id in [1, 3, 4]:
                x_pixel = x_pixels - x_pixel
                y_pixel = y_pixels - y_pixel

            base_pointing_board = self.config["observing_parameters"][self.camname][
                "base_position"
            ]["board_id"]

            base_board_x = x_board_id_mapping[base_pointing_board]
            base_board_y = y_board_id_mapping[base_pointing_board]
            requested_board_x = x_board_id_mapping[board_id]
            requested_board_y = y_board_id_mapping[board_id]

            # Calculate the offset in pixels from the base pointing
            x_offset_pixels = (
                (requested_board_x - base_board_x) * x_pixels
                + x_pixel
                - base_pointing_x_pixel
            )
            y_offset_pixels = (
                (requested_board_y - base_board_y) * y_pixels
                + y_pixel
                - base_pointing_y_pixel
            )

        else:
            # eg, for summer or any normal non mosaic focal plane
            x_offset_pixels = x_pixel - base_pointing_x_pixel
            y_offset_pixels = y_pixel - base_pointing_y_pixel

        pixel_scale_arcsec = self.config["observing_parameters"][self.camname][
            "pixscale"
        ]

        # Calculate the offset in arcseconds
        x_offset_arcsec = x_offset_pixels * pixel_scale_arcsec
        y_offset_arcsec = y_offset_pixels * pixel_scale_arcsec

        # Calculate the offset in degrees
        x_offset_deg = x_offset_arcsec / 3600.0  # * np.cos(np.deg2rad(dec))
        y_offset_deg = y_offset_arcsec / 3600.0

        # Calculate the new ra/dec at the base pointing if the requested coordinates
        # need to be at the requested pixels, using the offset and PA,
        # but with astronomy parity
        # For WINTER: parity = 1
        # Note: viraj points out this might have to be flipped for SUMMER
        parity = 1
        ra_offset = (-(1**parity)) * (
            x_offset_deg * np.cos(np.deg2rad(pa))
            - y_offset_deg * np.sin(np.deg2rad(pa))
        )
        # nate changed the multiplier for the parity below:
        dec_offset = (-(1**parity)) * (
            x_offset_deg * np.sin(np.deg2rad(pa))
            + y_offset_deg * np.cos(np.deg2rad(pa))
        )

        self.log(f"calculated field offsets:")
        self.log(f"ra_offset = {ra_offset*60} arcmin")
        self.log(f"dec_offset = {dec_offset*60} arcmin")

        # convert RA to deg
        ra_deg = ra_hours * 15.0
        new_base_ra_deg = ra_deg + ra_offset / np.cos(
            np.deg2rad(dec_deg)
        )  # changing viraj's minus sign to plus sign

        # convert back to hours
        new_base_ra_hours = new_base_ra_deg / 15.0

        # calculate the new dec
        new_base_dec_deg = (
            dec_deg + dec_offset
        )  # changing viraj's minus sign to plus sign

        return new_base_ra_hours, new_base_dec_deg

    def get_observatory_ready_status(self):
        """
        Run a check to see if the observatory is ready. Basically:
            - did startup run successfully
            - has the telescope been focused recently
        """

        conds = []

        ### DOME CHECKS ###
        conds.append(self.dome.Control_Status == "REMOTE")
        # conds.append(self.state['dome_tracking_status'] == True)
        conds.append(self.dome.Home_Status == "READY")

        ### TELESCOPE CHECKS ###
        conds.append(self.state["mount_is_connected"] == True)
        conds.append(self.state["mount_alt_is_enabled"] == True)
        conds.append(self.state["mount_az_is_enabled"] == True)
        if not self.mountsim:
            conds.append(self.state["rotator_is_connected"] == True)
            conds.append(self.state["rotator_is_enabled"] == True)
            conds.append(self.state["rotator_wrap_check_enabled"] == True)
            conds.append(self.state["focuser_is_connected"] == True)
            conds.append(self.state["focuser_is_enabled"] == True)

        # TODO: UNCOMMENT
        # NPL: commenting out so that we can observe even though mirror cover is stuck open
        # 7-3-23
        # if not self.test_mode:
        if not self.mountsim:

            conds.append(self.state["Mirror_Cover_State"] == 0)

        # TODO: add something about the focus here

        self.observatory_ready = all(conds)

        return self.observatory_ready

    # def get_winter_camera_on_status(self):
    #     """
    #     Run a check to see if the camera started up properly, and is ready to
    #     start cooling. Specifically that each sensor:
    #         - the PDU is on
    #         - the labjack has enabled the power
    #         - is connected
    #         - we have a record of a successful bias frame
    #     """

    #     conds = []

    #     self.winter_camera_on_status = all(conds)
    #     return self.winter_camera_on_status

    def get_camera_should_be_running_status(self):

        ### Notes:
        """
        The plan here is that roboManager will set a flag. roboOperator
        will init to cameras should be off is unknown, and then roboManager
        will send a command that they should be on.

        Or the other option is to add in limits in the config and interpret
        them using the robo manager methods


        """

        # For now do the easy thing:
        if self.state["sun_alt"] <= 10.0:  # -5.0:
            # if self.state['sun_alt'] <= -12.0:
            return True

        else:
            return False

    def get_winter_camera_ready_to_observe_status(self):
        """
        Run a check to see if the WINTER camera is ready to observe, eg
        that it started properly and that it is cold and stable:
            - the camera is on (see get_winter_camera_on_status)
            - check that each sensor:
                - the TEC is running
                - the PID loop is steady
                - the PID loop is at temperature
        """
        conds = []

        # run through identical conditions for each sensor:
        for addr in self.camdict["winter"].state["addrs"]:

            # TODO:ADD BACK IN!?
            # NPL 11/9/23 removing this check in favor of letting the camera
            # daemon decide if startup is done

            # # check that the TEC temp is steady
            # conds.append(self.state[f'{addr}_pid_ramp_status'] == 0)

            # # check that the TEC temp is at the setpoint
            # conds.append(self.state[f'{addr}_pid_at_setpoint'] == True)

            # # check that we're connected
            # conds.append(self.state[f'{addr}_connected'] == True)

            # # check that there is a record of a successful bias frame for each sensor
            # conds.append(self.state[f'{addr}_startup_validated'] == True)

            # # check that the TEC is running
            # conds.append(self.state[f'{addr}_tec_status'] == True)

            # NPL see above: doing this now
            conds.append(self.state["winter_camera_autostart_complete"] == True)

        self.winter_camera_ready_to_observe = all(conds)

        return self.winter_camera_ready_to_observe

    def get_winter_camera_ready_to_stow_status(self):
        """
        Run a check to see if the WINTER camera is ready to be stowed. Basically,
        for each sensor:
            - the TEC is running
            - the PID loop is steady
            - the PID loop is at temperature
            - the PID loop is set to 15 C
        """
        conds = []

        # run through identical conditions for each sensor:
        for addr in self.camdict["winter"].state["addrs"]:

            # NPL: 11/9/23: instead of doing an independent check on ramp status
            # and setpoint and TEC, let camera daemon do that, and just check if
            # autoshutdown is complete

            # check if autoshutdown is complete
            conds.append(self.state["winter_camera_autoshutdown_complete"])

            # # check that the TEC is running
            # conds.append(self.state[f'{addr}_tec_status'] == True)

            # # check that the TEC temp is steady
            # conds.append(self.state[f'{addr}_pid_ramp_status'] == 0)

            # # check that the TEC temp is at the setpoint
            # conds.append(self.state[f'{addr}_pid_at_setpoint'] == True)

            # # check that all the TECs are set to 15 C
            # conds.append(self.state[f'{addr}_T_fpa_sp'] == 15.0)

        self.winter_camera_ready_to_stow_status = all(conds)

        return self.winter_camera_ready_to_stow_status

    def get_winter_camera_stowed_status(self):
        """
        Run a check to see if the WINTER camera is ready to be stowed. Basically,
        for each sensor:
            #- the TEC is off
            - is shut down
            - labjack power enable is off
            - pdu channel is off
        """
        conds = []

        # run through identical conditions for each sensor:
        # for addr in self.camdict['winter'].state['addrs']:

        #     # check that the TEC is off
        #     conds.append(self.state[f'{addr}_tec_status'] == False)

        # check that sensor is shutdown

        # check that labjack power inhibit is on
        # TODO: NPL 10-3-23 make these less hard coded
        conds.append(self.state["fpa_port_power_disabled"] == True)
        conds.append(self.state["fpa_star_power_disabled"] == True)

        # check that pdu is off
        conds.append(self.state["pdu2_2"] == False)

        self.winter_camera_stowed_status = all(conds)

        return self.winter_camera_stowed_status

    def get_observatory_stowed_status(self):
        """
        Run a check to see if the observatory is in a safe stowed state.
        This stowed state is where it should be during the daytime, and during
        any remote closures.
        """

        conds = []

        ### DOME CHECKS ###
        # make sure we've given back control
        conds.append(self.dome.Control_Status == "AVAILABLE")
        # make sure the dome is near it's park position
        # AZ: handle the fact that we may get something 359 or 0.6
        delta_az = np.abs(self.state["dome_az_deg"] - self.config["dome_home_az_degs"])
        min_delta_az = np.min([360 - delta_az, delta_az])
        conds.append(min_delta_az < 1.0)
        # make sure dome tracking is off
        conds.append(self.state["dome_tracking_status"] == False)

        # make sure the dome is closed
        conds.append(self.dome.Shutter_Status == "CLOSED")

        ### TELESCOPE CHECKS ###
        # make sure mount tracking is off
        conds.append(self.state["mount_is_tracking"] == False)

        # make sure the mount is near home
        delta_az = np.abs(
            self.state["mount_az_deg"] - self.config["telescope"]["home_az_degs"]
        )
        min_delta_az = np.min([360 - delta_az, delta_az])
        conds.append(min_delta_az < 1.0)

        # don't worry about the alt
        # conds.append(np.abs(self.state['mount_alt_deg'] - self.config['telescope']['home_alt_degs']) < 45.0) # home is 45 deg, so this isn't really doing anything

        if not self.mountsim:
            delta_rot_angle = np.abs(
                self.state["rotator_mech_position"]
                - self.config["telescope"]["rotator_home_degs"]
            )
            min_delta_rot_angle = np.min([360 - delta_rot_angle, delta_rot_angle])
            conds.append(
                min_delta_rot_angle < 15.0
            )  # NPL 12-15-21 these days it sags to ~ -27 from -25
        # NPL 8-9-22 these days it is sagging to ~38 for whatever reason

        # make sure the motors are off
        conds.append(self.state["mount_alt_is_enabled"] == False)
        conds.append(self.state["mount_az_is_enabled"] == False)
        if not self.mountsim:
            conds.append(self.state["rotator_is_enabled"] == False)
            conds.append(self.state["focuser_is_enabled"] == False)

        # make sure the mount is disconnected?
        # conds.append(self.state['mount_is_connected'] == False)

        ### MIRROR COVER ###
        # make sure the mirror cover is closed
        # TODO: UNCOMMENT
        # NPL: commenting out so that we can observe even though mirror cover is stuck open
        # 7-3-23
        # if not self.mountsim:
        #    conds.append(self.state['Mirror_Cover_State'] == 1)

        self.observatory_stowed = all(conds)

        return self.observatory_stowed

    def stow_observatory(self, shutdown_cameras=False, force=False):
        """
        This is a method which checks to see if the observatory is stowed,
        and if not stows everything safely.

        You can force it to stow, in which case it will first run startup and then
        run shutdown
        """
        # if the observatory is already stowed, do nothing
        if self.get_observatory_stowed_status():
            if force == False:
                # if True, then the observatory is stowed.
                # TODO: will want to mute this to avoid lots of messages.
                msg = "requested observatory be stowed, but it is already stowed. standing by."
                # self.log(msg)
                # self.announce(msg)
                return
            else:
                # the observatory is already stowed, but we demanded it be shut down anyway
                # just go down to the next part of the tree
                pass

        # if the observatory is in the ready state, then just shut down
        elif self.get_observatory_ready_status():
            self.announce(f"shutting down observatory from ready state:")
            self.do_shutdown(shutdown_cameras=shutdown_cameras)

        else:
            self.announce(
                f"stowing observatory from arbitrary state: starting up first and then shutting down"
            )
            # we need to shut down.
            # this may require turning things on to move them and shutdown. so we start up and then shut down
            self.do_startup()

            self.do_shutdown(shutdown_cameras=shutdown_cameras)

    def interrupt(self):
        self.schedule.currentObs = None

    def stop(self):
        self.running = False
        # TODO: Anything else that needs to happen before stopping the thread

    def change_schedule(self, schedulefile_name, postPlot=False):
        """
        This function handles the initialization needed to start observing a
        new schedule. It is called when the changeSchedule signal is caught,
        as well as when the thread is first initialized.
        """

        print(
            f"scheduleExecutor: setting up new survey schedule from file >> {schedulefile_name}"
        )
        # NPL 8-17-22 I don't think we want to stop the roboOperator in this case?
        """
        if self.running:
            self.stop()
        """
        self.survey_schedulefile_name = schedulefile_name
        self.schedulefile_name = schedulefile_name
        self.schedule.loadSchedule(schedulefile_name, postPlot=postPlot)

    def get_data_to_log(
        self,
        currentObs="default",
    ):

        if currentObs == "default":
            currentObs = self.schedule.currentObs

        data = {}
        # First, handle all the keys from self.schedule.currentObs.
        # THESE ARE SPECIAL KEYS WHICH ARE REQUIRED FOR THE SCHEDULER TO WORK PROPERLY

        keys_with_actual_vals = [
            "dist2Moon",
            "expMJD",
            "visitExpTime",
            "azimuth",
            "altitude",
        ]

        for key in currentObs:
            # Some entries need the scheduled AND actuals recorded

            if key in keys_with_actual_vals:
                data.update({f"{key}_scheduled": currentObs[key]})
            else:
                data.update({key: currentObs[key]})

        # now update the keys with actual vals with their actual vals
        data.update(
            {
                "dist2Moon": self.getDist2Moon(),
                "expMJD": self.getMJD(),
                "visitExpTime": self.exptime,  # self.waittime,
                "altitude": self.state["mount_az_deg"],
                "azimuth": self.state["mount_alt_deg"],
            }
        )
        # now step through the Observation entries in the dataconfig.json and grab them from state

        for key in self.writer.dbStructure["Observation"]:
            # make sure we don't overwrite an entry from the currentObs or the keys_with_actual_vals
            ## ie, make sure it's a key that's NOT already in data
            if key not in data.keys():
                # if the key is in state, then update data
                if key in self.state.keys():
                    data.update({key: self.state[key]})
                else:
                    pass
            else:
                pass
        # print(f'header data = {data}')
        return data

    def getMJD(self):
        now_utc = datetime.utcnow()
        T = astropy.time.Time(now_utc, format="datetime")
        mjd = T.mjd
        return mjd

    def getDist2Moon(self):
        delta_alt = self.state["mount_alt_deg"] - self.ephem.moonalt
        delta_az = self.state["mount_az_deg"] - self.ephem.moonaz
        dist2Moon = (delta_alt**2 + delta_az**2) ** 0.5
        return dist2Moon

    def log(self, msg, level=logging.INFO):
        if self.logger is None:
            print(msg)
        else:
            self.logger.log(level=level, msg=msg)

    def doTry(self, cmd, context="", system=""):
        """
        This does the command by calling wintercmd.parse.
        The command should be written the same way it would be from the command line
        The system is specified so that alert signals can be broadcast out to various

        This will emit an error signal if the command doesn't work, but it will not kill program
        """

        self.lastcmd = cmd
        try:
            self.wintercmd.parse(cmd)

        except Exception as e:
            tb = traceback.format_exc()
            msg = f"roboOperator: could not execute function {cmd} due to {e.__class__.__name__}, {e}"  #', traceback = {tb}'
            self.log(msg)
            err = roboError(context, cmd, system, msg)
            self.hardware_error.emit(err)

    def do(self, cmd):
        """
        This does the command by calling wintercmd.parse.
        The command should be written the same way it would be from the command line
        The system is specified so that alert signals can be broadcast out to various
        """
        self.lastcmd = cmd
        self.wintercmd.parse(cmd)

    def do_startup(self, startup_cameras=False):
        """
        NPL 12-15-21: porting over the steps from Josh's total_startup to here
        for better error handling.

        NPL 8-16-23: commenting out returns in exceptions at each step so that
        it will keep going down to attempt each step of the process
        """
        systems_started = []
        # this is for passing to errors
        context = "do_startup"

        ### DOME SET UP ###
        system = "dome"
        msg = "starting dome startup..."
        self.announce(msg)

        try:
            # take control of dome
            self.do("dome_takecontrol")

            self.do("dome_tracking_off")

            # re-home the dome (put the dome through it's homing routine)
            # TODO: NPL 12-15-21: we might want to move this elsewhere, we should do it nightly but it doesn't have to be here.
            # self.do('dome_home')

            # send the dome to it's home/park position
            self.do("dome_go_home")

            # signal we're complete
            msg = "dome startup complete"
            self.logger.info(f"robo: {msg}")
            self.alertHandler.slack_log(f":greentick: {msg}")
            systems_started.append(True)
        except Exception as e:
            msg = f"roboOperator: could not set up {system} due to {e.__class__.__name__}, {e}"
            self.log(msg)
            err = roboError(context, self.lastcmd, system, msg)
            self.hardware_error.emit(err)
            systems_started.append(False)
            # return

        ### MOUNT SETUP ###
        system = "telescope"
        msg = "starting telescope startup..."
        self.announce(msg)
        try:
            # start up the mount:
            # splitting this up so we get more feedback on where things crash
            # self.do('mount_startup')

            # connect the telescope
            self.do("mount_connect")

            # turn off tracking
            self.do("mount_tracking_off")

            # make sure we load the pointing model explicitly
            self.do(
                f'mount_model_load {self.config["pointing_model"]["pointing_model_file"]}'
            )

            # turn on the motors
            self.do("mount_az_on")
            self.do("mount_alt_on")

            # turn on the rotator
            if not self.mountsim:
                self.do("rotator_enable")
                # home the rotator
                self.do("rotator_home")

            # turn on the focuser
            if not self.mountsim:
                self.do("m2_focuser_enable")

            # poing the mount to home
            self.do("mount_home")

            self.announce(":greentick: telescope startup complete!")
            systems_started.append(True)
        except Exception as e:
            msg = f"roboOperator: could not set up {system} due to {e.__class__.__name__}, {e}"
            self.log(msg)
            self.alertHandler.slack_log(f"*ERROR:* {msg}", group=None)
            err = roboError(context, self.lastcmd, system, msg)
            self.hardware_error.emit(err)
            systems_started.append(False)
            # return

        system = "mirror cover"
        if self.mountsim:
            msg = "would open mirror covers now, but skipping this since we are in simulated mount mode"
            self.announce(msg)
        else:
            msg = "opening mirror covers"
            self.announce(msg)
            try:
                # connect to the mirror cover
                self.do("mirror_cover_connect")

                # open the mirror cover
                if not self.test_mode:
                    self.do("mirror_cover_open")
                self.announce(":greentick: mirror covers open!")
                systems_started.append(True)
            except Exception as e:
                msg = f"roboOperator: could not set up {system} due to {e.__class__.__name__}, {e}"
                self.log(msg)
                self.alertHandler.slack_log(f"*ERROR:* {msg}", group=None)
                err = roboError(context, self.lastcmd, system, msg)
                self.hardware_error.emit(err)
                systems_started.append(False)
                # return

        if startup_cameras:
            system = "camera"

            for camname in self.camdict:
                try:
                    # msg = f'starting up {camname} camera!'
                    # self.announce(msg)
                    # startup the camera
                    # self.do(f'startupCamera --{camname}')

                    time.sleep(2)

                    msg = f":cold_face: starting up the {camname} TECs!"
                    self.announce(msg)
                    self.do(f"tecStart --{camname}")
                    self.announce(":greentick: camera startup complete!")
                    systems_started.append(True)
                except Exception as e:
                    msg = f"roboOperator: could not set up {system} due to {e.__class__.__name__}, {e}"
                    self.log(msg)
                    self.alertHandler.slack_log(f"*ERROR:* {msg}", group=None)
                    err = roboError(context, self.lastcmd, system, msg)
                    self.hardware_error.emit(err)
                    systems_started.append(True)
                    # return

        # if we made it all the way to the bottom, say the startup is complete!

        if all(systems_started):
            self.startup_complete = True
            self.announce(":greentick: startup complete!")
            print(f"robo: do_startup complete")
        else:
            self.startup_complete = False

            self.announce(":caution: startup complete but with some errors")
            print(f"robo: do_startup complete but with some errors")

    def do_camera_startup(self, camname):
        system = "camera"
        context = "do_camera_startup"
        systems_started = []
        msg = "setting up chiller (if not already)"
        self.announce(msg)
        try:
            # make sure the chiller is on
            system = "chiller"

            self.do("chiller_start")
            time.sleep(2)
            self.do("chiller_set_setpoint 10")

            self.announce(":greentick: chiller startup complete")
            systems_started.append(True)
        except Exception as e:
            msg = f"roboOperator: could not set up {system} due to {e.__class__.__name__}, {e}"
            self.log(msg)
            self.alertHandler.slack_log(f"*ERROR:* {msg}", group=None)
            err = roboError(context, self.lastcmd, system, msg)
            self.hardware_error.emit(err)
            systems_started.append(False)

            # make sure the flow is going

            # # make sure the LJ is off
            # don't do this because it would turn sensor off while running
            # system = 'labjack'
            # self.do('fpa off')

        systems_started = []
        msg = "powering on the focal planes"
        self.announce(msg)
        try:
            # make sure the pdu is on
            self.announce("turning on PDU output channel for FPAs")
            system = "pdu"
            self.do("pdu on fpas")

            time.sleep(10)

            # make sure the LJ is on
            self.announce("enabling FPA power with labjack")
            system = "labjack"
            self.do("fpa on")

            time.sleep(10)

            self.announce(":greentick: camera power startup complete")
            systems_started.append(True)
        except Exception as e:
            msg = f"roboOperator: could not set up {system} due to {e.__class__.__name__}, {e}"
            self.log(msg)
            self.alertHandler.slack_log(f"*ERROR:* {msg}", group=None)
            err = roboError(context, self.lastcmd, system, msg)
            self.hardware_error.emit(err)
            systems_started.append(False)

        try:
            # make sure the pdu is on
            system = "camera"
            msg = f":cold_face: running autostart routine on {camname}!"
            self.announce(msg)
            self.do(f"autoStartupCamera --{camname}")

            self.announce(":greentick: camera power startup complete")
            systems_started.append(True)
        except Exception as e:
            msg = f"roboOperator: could not set up {system} due to {e.__class__.__name__}, {e}"
            self.log(msg)
            self.alertHandler.slack_log(f"*ERROR:* {msg}", group=None)
            err = roboError(context, self.lastcmd, system, msg)
            self.hardware_error.emit(err)
            systems_started.append(False)

        # if we made it all the way to the bottom, say the startup is complete!

        if all(systems_started):
            self.camera_startup_complete = True
            self.announce(
                ":greentick: startup initiation sequence complete. waitint for cameras to finish starting up!"
            )
        else:
            self.camera_startup_complete = False

            self.announce(":caution: camera startup complete but with some errors")
            self.log(f"do_startup complete but with some errors")

    def do_camera_power_shutdown(self, camname):
        system = "camera"
        context = "do_camera_startup"
        systems_started = []

        systems_started = []
        msg = "shutting off the focal plane power"
        self.announce(msg)
        try:

            # make sure the LJ is off
            system = "labjack"
            self.do("fpa off")

            # make sure the pdu is off
            system = "pdu"
            self.do("pdu off fpas")

            self.announce(":greentick: camera power shutdown complete")
            systems_started.append(True)
        except Exception as e:
            msg = f"roboOperator: could not set up {system} due to {e.__class__.__name__}, {e}"
            self.log(msg)
            self.alertHandler.slack_log(f"*ERROR:* {msg}", group=None)
            err = roboError(context, self.lastcmd, system, msg)
            self.hardware_error.emit(err)
            systems_started.append(False)

        # if we made it all the way to the bottom, say the startup is complete!

        if all(systems_started):
            self.camera_startup_complete = True
            self.announce(":greentick: startup complete!")
            self.log(f"robo: do_camera_startup complete")
        else:
            self.camera_startup_complete = False

            self.announce(
                ":caution: camera power shutdown complete but with some errors"
            )
            self.log(f"do_camera_power_shutdown complete but with some errors")

    def do_camera_shutdown(self, camname):
        system = "camera"
        context = "do_camera_startup"
        systems_started = []

        systems_started = []
        msg = "powering on the focal planes"
        self.announce(msg)

        try:
            # make sure the pdu is on
            system = "camera"
            msg = f":hot_garbage: running auto shutdown routine on {camname}!"
            self.announce(msg)
            self.do(f"autoShutdownCamera --{camname}")

            self.announce(":greentick: camera power startup complete")
            systems_started.append(True)
        except Exception as e:
            msg = f"roboOperator: could not set up {system} due to {e.__class__.__name__}, {e}"
            self.log(msg)
            self.alertHandler.slack_log(f"*ERROR:* {msg}", group=None)
            err = roboError(context, self.lastcmd, system, msg)
            self.hardware_error.emit(err)
            systems_started.append(False)

        # if we made it all the way to the bottom, say the startup is complete!

        if all(systems_started):
            self.camera_startup_complete = True
            self.announce(
                ":greentick: camera shutdown sequence initiated! waiting for camera to finish shutting down."
            )
        else:
            self.camera_startup_complete = False

            self.announce(
                ":caution: camera shutdown sequence initiated but with some errors"
            )

    def do_shutdown(self, shutdown_cameras=False):
        """
        This is the counterpart to do_startup. It supercedes the old "total_shutdown"
        script, replicating its essential functions but with better communications
        and error handling.
        """
        systems_shutdown = []
        # this is for passing to errors
        context = "do_startup"

        ### DOME SHUT DOWN ###
        system = "dome"
        msg = "starting dome shutdown..."
        self.announce(msg)

        try:
            # make sure dome isn't tracking telescope anymore
            self.do("dome_tracking_off")

            # send the dome to it's home/park position
            self.do("dome_go_home")

            # close the dome
            self.do("dome_close")

            # give control of dome
            self.do("dome_givecontrol")

            # signal we're complete
            msg = "dome shutdown complete"
            self.logger.info(f"robo: {msg}")
            self.alertHandler.slack_log(f":greentick: {msg}")
            systems_shutdown.append(True)
        except Exception as e:
            msg = f"roboOperator: could not shut down {system} due to {e.__class__.__name__}, {e}"
            self.log(msg)
            err = roboError(context, self.lastcmd, system, msg)
            self.hardware_error.emit(err)
            systems_shutdown.append(False)
            # return

        ### MOUNT SHUTDOWN ###
        system = "telescope"
        msg = "starting telescope shutdown..."
        self.announce(msg)
        try:
            # start up the mount:
            # splitting this up so we get more feedback on where things crash
            # self.do('mount_startup')

            # turn off tracking
            self.do("mount_tracking_off")

            # point the mount to home
            self.do("mount_home")

            if not self.mountsim:
                # turn off the focuser
                self.do("m2_focuser_disable")

                # home the rotator
                self.do("rotator_home")

                # turn off the rotator
                self.do("rotator_disable")

            # turn off the motors
            self.do("mount_az_off")
            self.do("mount_alt_off")

            # disconnect the telescope
            # self.do('mount_disconnect')

            self.announce(":greentick: telescope shutdown complete!")
            systems_shutdown.append(True)

        except Exception as e:
            msg = f"roboOperator: could not shut down {system} due to {e.__class__.__name__}, {e}"
            self.log(msg)
            self.alertHandler.slack_log(f"*ERROR:* {msg}", group=None)
            err = roboError(context, self.lastcmd, system, msg)
            self.hardware_error.emit(err)
            systems_shutdown.append(False)
            # return

        ### MIRROR COVER CLOSURE ###
        if not self.mountsim:
            system = "mirror cover"
            msg = "closing mirror covers"
            self.announce(msg)
            try:
                # connect to the mirror cover
                self.do("mirror_cover_connect")

                # open the mirror cover
                self.do("mirror_cover_close")

                self.announce(":greentick: mirror covers closed!")
                systems_shutdown.append(True)
            except Exception as e:
                msg = f"roboOperator: could not shut down {system} due to {e.__class__.__name__}, {e}"
                self.log(msg)
                self.alertHandler.slack_log(f"*ERROR:* {msg}", group=None)
                err = roboError(context, self.lastcmd, system, msg)
                self.hardware_error.emit(err)
                systems_shutdown.append(False)
                # return

        if shutdown_cameras:
            system = "camera"

            for camname in self.camdict:
                try:
                    # msg = f'shuttidn down {camname} camera!'
                    # self.announce(msg)
                    # shutdown the camera
                    # self.do(f'shutdownCamera --{camname}')

                    time.sleep(2)

                    msg = f":hot_garbage: warming TEC to 15C !"
                    self.announce(msg)
                    self.do(f"tecSetSetpoint 15 --{camname}")
                    self.announce(":greentick: camera startup complete!")
                    systems_shutdown.append(True)

                except Exception as e:
                    msg = f"roboOperator: could not set up {system} due to {e.__class__.__name__}, {e}"
                    self.log(msg)
                    self.alertHandler.slack_log(f"*ERROR:* {msg}", group=None)
                    err = roboError(context, self.lastcmd, system, msg)
                    self.hardware_error.emit(err)
                    systems_shutdown.append(False)
                    # return

        # if we made it all the way to the bottom, say the startup is complete!
        if all(systems_shutdown):
            self.shutdown_complete = True
            self.announce(":greentick: shutdown complete!")
            print(f"robo: do_shutdown complete")
        else:
            self.shutdown_complete = False
            self.announce(":caution: shutdown complete but with errors")
            print(f"robo: do_shutdown complete but with errors")

    def do_calibration(
        self, do_flats=False, do_domeflats=False, do_darks=False, do_bias=False
    ):

        # if we're in here set running to True
        self.running = True

        if do_flats:
            self.do_flats()

        if do_domeflats:
            self.do_domeflats()

        ### Take Darks ###
        if do_darks:
            self.do_darks()

        ### Take Bias ###
        if do_bias:
            self.do_bias()

        self.log(f"finished with calibration. no more to do.")
        self.announce("auto calibration sequence completed successfully!")

    def do_flats(self):
        # check to make sure conditions are okay before attempting cal routine. prevents weird hangups
        # copied logic from checkWhatToDo(), but don't actually command any systems if there's an issue.
        # instead just exit out of this routine. hopefully this avoids conflicting sets of instructions.
        #
        self.announce("checking conditions before running auto calibration routine")
        context = "do_calibration"

        # ---------------------------------------------------------------------
        ### check the dome
        # ---------------------------------------------------------------------
        if self.get_dome_status():
            # if True, then the dome is fine
            self.log("the dome status is good!")
            pass
        else:
            self.announce(
                f"there is a problem with the dome (eg weather, etc) preventing operation. exiting calibration routine..."
            )
            """
            self.log('there is a problem with the dome (eg weather, etc). STOWING OBSERVATORY')
            # there is a problem with the dome.
            self.stow_observatory(force = False)
            # skip the rest of the checks, just start the timer for the next check
            self.checktimer.start()
            """
            return
        # ---------------------------------------------------------------------
        # check the sun
        # ---------------------------------------------------------------------
        if self.get_sun_status():
            self.log(f"the sun is low are we are ready to go!")
            # if True, then the sun is fine. just keep going
            pass
        else:
            self.announce(
                f"the sun is not ready for operation. exiting calibration routine..."
            )
            """
            self.log(f'waiting for the sun to set')
            # the sun is up, can't proceed. just hang out.
            self.checktimer.start()
            """
            return
        # ---------------------------------------------------------------------
        # check if the observatory is ready
        # ---------------------------------------------------------------------
        if self.get_observatory_ready_status():
            self.log(f"the observatory is ready to observe!")
            # if True, then the observatory is ready (eg successful startup and focus sequence)
            pass
        else:
            self.announce(
                f"the observatory is not ready to observe! exiting calibration routine..."
            )
            """
            self.log(f'need to start up observatory')
            # we need to (re)run do_startup
            self.do_startup()
            # after running do_startup, kick back to the top of the loop
            self.checktimer.start()
            """
            return
        # ---------------------------------------------------------------------
        # check the dome
        # ---------------------------------------------------------------------
        if self.dome.Shutter_Status == "OPEN":
            self.log(f"the dome is open and we are ready to start taking data")
            # the dome is open and we're ready for observations. just pass
            pass
        else:
            if self.dometest:
                self.log(
                    "observatory and sun are ready for observing, ignoring the dome shutter in dometest mode"
                )
            else:
                # the dome and sun are okay, but the dome is closed. we should open the dome
                self.announce(
                    "observatory and sun are ready for observing, but dome is closed. opening..."
                )
                self.doTry("dome_open")
                """
                self.checktimer.start()
                return
                """

        # if we made it to here, we're good to do the auto calibration

        self.announce("starting auto calibration sequence.")
        # self.logger.info('robo: doing calibration routine. for now this does nothing.')

        ### TAKE SKY FLATS ###
        # for now some numbers are hard coded which should be in the config file
        # pick which direction to look: look away from the sun
        if self.state["sun_rising"]:
            flat_az = 270.0

        else:
            flat_az = 0.0

        # get the altitude
        flat_alt = 75.0

        system = "dome"
        try:
            # slew the dome
            self.do(f"dome_tracking_off")
            self.do(f"dome_goto {flat_az}")
            self.do(f"dome_tracking_on")

            system = "telescope"
            # slew the telescope
            self.do(f"mount_goto_alt_az {flat_alt} {flat_az}")

            self.log(f"starting the flat observations")

        except Exception as e:
            msg = f"roboOperator: could not set up {system} due to {e.__class__.__name__}, {e}"
            self.log(msg)
            self.alertHandler.slack_log(f"*ERROR:* {msg}", group=None)
            err = roboError(context, self.lastcmd, system, msg)
            self.hardware_error.emit(err)
            return

        # get the filters to cycle through
        # for now just do WINTER
        camname = "winter"
        filterIDs = self.config["cal_params"][camname]["flats"]["filterIDs"]

        nflats = self.config["cal_params"][camname]["flats"]["n_imgs"]
        ra_total_offset_arcmin = 0
        dec_total_offset_arcmin = 0

        self.log(f"sun alt: {self.state['sun_alt']}")
        self.log(
            f"min sun alt: {self.config['cal_params'][camname]['flats']['min_sunalt']}"
        )
        self.log(
            f"max sun alt: {self.config['cal_params'][camname]['flats']['max_sunalt']}"
        )
        self.log(
            f"sun alt > min alt: {(self.state['sun_alt'] > self.config['cal_params'][camname]['flats']['min_sunalt'])}"
        )
        self.log(
            f"sun alt < max alt: {(self.state['sun_alt'] < self.config['cal_params'][camname]['flats']['max_sunalt'])}"
        )

        # start a loop to take flats as long as we're within the allowed limits
        # while ((self.state['sun_alt'] > self.config['cal_params'][camname]['flats']['min_sunalt']) &
        # (self.state['sun_alt'] < self.config['cal_params'][camname]['flats']['max_sunalt'])):
        while True:

            self.log(f"taking {nflats} flats in each filter:")
            self.log(f"sun alt: {self.state['sun_alt']}")
            self.log(
                f"min sun alt: {self.config['cal_params'][camname]['flats']['min_sunalt']}"
            )
            self.log(
                f"max sun alt: {self.config['cal_params'][camname]['flats']['max_sunalt']}"
            )
            below_max = (
                self.state["sun_alt"]
                < self.config["cal_params"][camname]["flats"]["max_sunalt"]
            )
            above_min = (
                self.state["sun_alt"]
                > self.config["cal_params"][camname]["flats"]["min_sunalt"]
            )
            sun_in_range = below_max & above_min
            self.log(f"sun alt > min alt: {above_min}")
            self.log(f"sun alt < max alt: {below_max}")
            self.log(f"sun in range: {sun_in_range}")

            if sun_in_range:
                pass
            else:
                self.log(f"sun not in range! exiting autocal routine")

            # step through each filter
            for filterID in filterIDs:

                self.log(f"setting up flat for filterID: {filterID}")
                # go to the specified filter
                system = "filter wheel"
                try:
                    # get filter number
                    for position in self.config["filter_wheels"][camname]["positions"]:
                        if (
                            self.config["filter_wheels"][camname]["positions"][
                                position
                            ].lower()
                            == filterID.lower()
                        ):
                            filter_num = position
                        else:
                            pass
                    if filter_num == self.fw.state["filter_pos"]:
                        self.log(
                            "requested filter matches current, no further action taken"
                        )
                    else:
                        self.log(
                            f'current filter = {self.fw.state["filter_pos"]}, changing to {filter_num}'
                        )
                        # self.do(f'fw_goto {filter_num} --{self.camname}')
                        self.do(f"fw_goto {filter_num} --{camname}")
                except Exception as e:
                    msg = f"roboOperator: could not run flat loop instance due to error with {system}: due to {e.__class__.__name__}, {e}"
                    self.log(msg)
                    self.alertHandler.slack_log(f"*ERROR:* {msg}", group=None)
                    err = roboError(context, self.lastcmd, system, msg)
                    self.hardware_error.emit(err)
                    return
                # take the specified number of images
                for i in range(nflats):

                    # check if we're still running
                    if self.running:

                        # check for events. do we need this? unclear
                        QtCore.QCoreApplication.processEvents()

                        # check if it is ok to observe
                        self.check_ok_to_observe()
                        if self.ok_to_observe:
                            pass
                        else:
                            self.log(
                                "in do_flats but self.ok_to_observe is False. Returning."
                            )
                            return

                        # check if the sun is in range
                        below_max = (
                            self.state["sun_alt"]
                            < self.config["cal_params"][camname]["flats"]["max_sunalt"]
                        )
                        above_min = (
                            self.state["sun_alt"]
                            > self.config["cal_params"][camname]["flats"]["min_sunalt"]
                        )
                        sun_in_range = below_max & above_min
                        self.log(f"taking {nflats} flats in each filter:")
                        self.log(f"sun alt: {self.state['sun_alt']}")
                        self.log(
                            f"min sun alt: {self.config['cal_params'][camname]['flats']['min_sunalt']}"
                        )
                        self.log(
                            f"max sun alt: {self.config['cal_params'][camname]['flats']['max_sunalt']}"
                        )
                        self.log(f"sun alt > min alt: {above_min}")
                        self.log(f"sun alt < max alt: {below_max}")
                        self.log(f"sun in range: {sun_in_range}")

                        if sun_in_range:
                            pass
                        else:
                            self.log(f"sun not in range! exiting autocal routine")

                        # get the exposure time
                        if (
                            self.config["cal_params"][camname]["flats"]["exptime"][
                                filterID
                            ]
                            == "model"
                        ):

                            try:
                                a = self.config["cal_params"][camname]["flats"][
                                    "model"
                                ][filterID]["a"]
                                n = self.config["cal_params"][camname]["flats"][
                                    "model"
                                ][filterID]["n"]
                                scale = self.config["cal_params"][camname]["flats"][
                                    "model"
                                ][filterID]["scale"]
                                goal_counts = self.config["cal_params"][camname][
                                    "flats"
                                ]["model"]["goal_counts"]
                                sky_rate = np.exp(a * (-1 * self.state["sun_alt"]) ** n)
                                dark_rate = self.config["cal_params"][camname]["flats"][
                                    "model"
                                ]["dark_rate"]
                                flat_exptime_requested = scale * (
                                    goal_counts / (sky_rate + dark_rate)
                                )
                                # flat_exptime = scale*(goal_counts/(np.exp(a*(-1*self.state["sun_alt"])**n)))

                            except Exception as e:
                                flat_exptime_requested = 10.0
                                self.log(
                                    f"could not set up model flat exposure time for filter {camname}: {filterID} due to: {e}, setting to default {flat_exptime_requested} s"
                                )

                        else:
                            try:
                                flat_exptime_requested = self.config["cal_params"][
                                    camname
                                ]["flats"]["exptime"][filterID]
                            except Exception as e:
                                flat_exptime_requested = 10.0
                                self.log(
                                    f"could get exposure time for filter {camname}: {filterID} due to: {e}, setting to default {flat_exptime_requested} s"
                                )

                        try:

                            # set the exposure time
                            self.log(
                                f"requested flat exposure time: {flat_exptime_requested}"
                            )
                            allowed_exptimes = np.array(
                                self.config["cal_params"][camname]["dark"]["exptimes"]
                            )
                            self.log(f"allowed exposure times: {allowed_exptimes}")
                            if type(flat_exptime_requested) is complex:
                                self.log(
                                    f"calculation gave complex value of exptime ({flat_exptime_requested}), setting to {min(allowed_exptimes)}s"
                                )
                                flat_exptime = min(allowed_exptimes)

                            else:
                                # get the index of the closest allowed exposure time
                                index_of_nearest = np.abs(
                                    allowed_exptimes - flat_exptime_requested
                                ).argmin()
                                flat_exptime = allowed_exptimes[index_of_nearest]
                                self.log(f"setting exptime to {flat_exptime} s")
                            """
                            # set the exposure time
                            minexptime = self.config['cal_params'][camname]['flats']['exptime']['min']
                            maxexptime = self.config['cal_params'][camname]['flats']['exptime']['max']
                            
                            self.log(f'exptime = {flat_exptime} ({type(flat_exptime)})')
                            self.log(f'min exptime = {minexptime} ({type(minexptime)})')
                            self.log(f'max exptime = {maxexptime} ({type(maxexptime)})')
                            
                            if type(flat_exptime) is complex:
                                self.log(f'calculation gave complex value of exptime ({flat_exptime}), setting to {minexptime}s')
                                flat_exptime = minexptime
                                
                            elif (flat_exptime < minexptime):
                                self.log(f'calculated exptime too short ({flat_exptime} < {minexptime}), setting to {minexptime} s')
                                flat_exptime = minexptime
                            elif (flat_exptime > maxexptime):
                                self.log(f'calculated exptime too long ({flat_exptime} > {maxexptime}), setting to {maxexptime} s')
                                flat_exptime = maxexptime
                            else:
                                self.log(f'setting exptime to {flat_exptime} s')
                            """
                            system = "camera"
                            self.do(f"setExposure {flat_exptime:0.3f} --{self.camname}")
                        except Exception as e:
                            msg = f"roboOperator: could not run flat loop instance due to error with {system}: due to {e.__class__.__name__}, {e}"
                            self.log(msg)
                            self.alertHandler.slack_log(f"*ERROR:* {msg}", group=None)
                            err = roboError(context, self.lastcmd, system, msg)
                            self.hardware_error.emit(err)
                            return

                        # do the exposure!
                        try:
                            comment = f"Auto Flats {i+1}/{nflats} Alt/Az = ({flat_alt}, {flat_az}), RA +{ra_total_offset_arcmin} am, DEC +{dec_total_offset_arcmin} am"
                            # now trigger the actual observation. this also starts the mount tracking
                            self.announce(
                                f'Executing {filterID}: {comment}, sun alt = {self.state["sun_alt"]:.1f} deg, exptime = {flat_exptime:.1f} s'
                            )
                            if i == 0:
                                self.log("handling the i=0 case")
                                system = "robo routine"
                                self.do(
                                    f"robo_observe altaz {flat_alt} {flat_az} -f --calibration"
                                )
                            else:
                                system = "camera"
                                self.do("robo_do_exposure -f")

                            # now dither. if i is odd do ra, otherwise dec
                            dither_arcmin = 5
                            if i % 2:
                                axis = "ra"
                                ra_total_offset_arcmin += dither_arcmin
                            else:
                                axis = "dec"
                                dec_total_offset_arcmin += dither_arcmin

                            self.do(f"mount_dither {axis} {dither_arcmin}")

                        except Exception as e:
                            msg = f"roboOperator: could not run flat loop instance due to error with {system}: due to {e.__class__.__name__}, {e}"
                            self.log(msg)
                            self.alertHandler.slack_log(f"*ERROR:* {msg}", group=None)
                            err = roboError(context, self.lastcmd, system, msg)
                            self.hardware_error.emit(err)

                    else:
                        # we're not running! return now.
                        self.log(
                            "in do_flats method and self.running is False, likely a lockout? Returning."
                        )
                        return

        # if we get here, we're done with the light exposure, so turn off dome and mount tracking
        # so that the telescope doesn't drift

        system = "dome"
        try:
            self.do("dome_tracking_off")

            system = "telescope"
            self.do("mount_tracking_off")
        except Exception as e:
            msg = f"roboOperator: could not stop tracking after flat fields due to error with {system}: due to {e.__class__.__name__}, {e}"
            self.log(msg)
            self.alertHandler.slack_log(f"*ERROR:* {msg}", group=None)
            err = roboError(context, self.lastcmd, system, msg)
            self.hardware_error.emit(err)
            # return

    def do_domeflats(self):
        self.log(f"running dome flat sequence")
        """
        
        Dome flat sequence.
        
        Steps:
            1. Make sure the dome is closed
            2. Turn on the cal lamp
            3. Start up the telescope
            4. Open the telescope shutters
            5. Slew to the dome flat location
            6. Cycle through the filters and take the images
            7. turn off the cal lamp
            8. make sure the telescope is not tracking
        """
        # check to make sure conditions are okay before attempting cal routine. prevents weird hangups
        # copied logic from checkWhatToDo(), but don't actually command any systems if there's an issue.
        # instead just exit out of this routine. hopefully this avoids conflicting sets of instructions.
        #
        self.announce("checking conditions before running auto calibration routine")
        context = "do_calibration"

        # ---------------------------------------------------------------------
        # turn on the cal lamp
        # ---------------------------------------------------------------------

        self.announce(":lightbulb-happy: Turning on the cal lamp!")
        self.doTry("pdu on callamp")
        time.sleep(2)

        # ---------------------------------------------------------------------
        # check the dome
        # ---------------------------------------------------------------------
        if self.dome.Shutter_Status == "CLOSED":
            self.log(f"the dome is closed and we are ready to start taking dome flats")
            # the dome is open and we're ready for observations. just pass
            pass
        else:
            if self.dometest:
                self.log(
                    "observatory and sun are ready for observing, ignoring the dome shutter in dometest mode"
                )
            else:
                # the dome and sun are okay, but the dome is closed. we should open the dome
                self.announce("Need to close dome to do the dome flats. Closing...")
                self.doTry("dome_close")
                """
                self.checktimer.start()
                return
                """

        # ---------------------------------------------------------------------
        # check if the observatory is ready
        # ---------------------------------------------------------------------
        if self.get_observatory_ready_status():
            self.log(f"the observatory is ready to observe!")
            # if True, then the observatory is ready (eg successful startup and focus sequence)
            pass
        else:
            self.announce(
                f"The observatory is not ready to observe! running startup calibration routine..."
            )

            self.log(f"Need to start up observatory")
            # we need to (re)run do_startup
            self.do_startup()

            # did it work?
            if self.startup_complete:
                pass
            else:
                self.announce(
                    "exited the domeflats routine because startup was not completed properly"
                )
                operator_msg = ":redsiren: There was a startup issue preventing dome flats, please investigate!"
                self.alertHandler.slack_message_group("operator", operator_msg)
                return

        # if we made it to here, we're good to do the auto calibration

        self.announce("Starting auto dome flats sequence.")
        # self.logger.info('robo: doing calibration routine. for now this does nothing.')

        ### TAKE DOME FLATS ###
        # for now some numbers are hard coded which should be in the config file
        # pick which direction to look: look away from the sun
        try:
            flat_az = self.config["cal_params"][self.camname]["domeflats"]["target"][
                "az"
            ]
            # get the altitude
            flat_alt = self.config["cal_params"][self.camname]["domeflats"]["target"][
                "alt"
            ]
        except Exception as e:
            flat_az = 90.0
            flat_alt = 75.0
            msg = f"could not pull the dome flat alt/az for {self.camname} out of config. Defaulting to {flat_alt}, {flat_az}"
            self.log(msg)

        system = "dome"
        try:
            # slew the dome
            self.do(f"dome_tracking_off")
            self.do(f"dome_go_home")

            system = "telescope"
            # slew the telescope
            self.do(f"mount_goto_alt_az {flat_alt} {flat_az}")

            self.log(f"starting the flat observations")

        except Exception as e:
            msg = f"roboOperator: could not set up {system} due to {e.__class__.__name__}, {e}"
            self.log(msg)
            self.alertHandler.slack_log(f"*ERROR:* {msg}", group=None)
            err = roboError(context, self.lastcmd, system, msg)
            self.hardware_error.emit(err)
            return

        # get the filters to cycle through
        # for now just do WINTER
        camname = "winter"
        filterIDs = self.config["cal_params"][camname]["domeflats"]["filterIDs"]

        nflats = self.config["cal_params"][camname]["domeflats"]["n_imgs"]

        # start a loop to take flats as long as we're within the allowed limits
        # while ((self.state['sun_alt'] > self.config['cal_params'][camname]['flats']['min_sunalt']) &
        # (self.state['sun_alt'] < self.config['cal_params'][camname]['flats']['max_sunalt'])):

        # set the progID info here for the headers
        self.resetObsValues()
        try:
            self.programPI = self.config["cal_params"]["prog_params"]["cals"]["progPI"]
            self.programID = self.config["cal_params"]["prog_params"]["cals"]["progID"]
            self.programName = self.config["cal_params"]["prog_params"]["cals"][
                "progName"
            ]
            self.obstype = "DOMEFLAT"
            self.obsmode = "CALIBRATION"
        except Exception as e:
            self.log(f"could not update the header values for the dark sequence: {e}")

        # step through each filter
        for filterID in filterIDs:

            self.log(f"setting up flat for filterID: {filterID}")
            # go to the specified filter
            system = "filter wheel"
            try:
                # get filter number
                for position in self.config["filter_wheels"][camname]["positions"]:
                    if (
                        self.config["filter_wheels"][camname]["positions"][
                            position
                        ].lower()
                        == filterID.lower()
                    ):
                        filter_num = position
                    else:
                        pass
                if filter_num == self.fw.state["filter_pos"]:
                    self.log(
                        "requested filter matches current, no further action taken"
                    )
                else:
                    self.log(
                        f'current filter = {self.fw.state["filter_pos"]}, changing to {filter_num}'
                    )
                    # self.do(f'fw_goto {filter_num} --{self.camname}')
                    self.do(f"fw_goto {filter_num} --{camname}")
            except Exception as e:
                msg = f"roboOperator: could not run flat loop instance due to error with {system}: due to {e.__class__.__name__}, {e}"
                self.log(msg)
                self.alertHandler.slack_log(f"*ERROR:* {msg}", group=None)
                err = roboError(context, self.lastcmd, system, msg)
                self.hardware_error.emit(err)
                return

            # Get/Set the Exposure Time
            flat_exptimes = self.config["cal_params"][self.camname]["domeflats"][
                "exptime"
            ][filterID]

            for flat_exptime in flat_exptimes:

                try:

                    # set the exposure time
                    system = "camera"
                    self.do(f"setExposure {flat_exptime:0.3f} --{self.camname}")
                except Exception as e:
                    msg = f"roboOperator: could not run flat loop instance due to error with {system}: due to {e.__class__.__name__}, {e}"
                    self.log(msg)
                    self.alertHandler.slack_log(f"*ERROR:* {msg}", group=None)
                    err = roboError(context, self.lastcmd, system, msg)
                    self.hardware_error.emit(err)
                    return

                # take the specified number of images
                for i in range(nflats):

                    # check for events. do we need this? unclear
                    QtCore.QCoreApplication.processEvents()

                    # do the exposure!
                    try:
                        comment = f"Auto Dome Flats {i+1}/{nflats} Alt/Az = ({flat_alt}, {flat_az})"
                        # now trigger the actual observation. this also starts the mount tracking
                        self.announce(
                            f"Executing {filterID}: {comment}, exptime = {flat_exptime:.1f} s"
                        )
                        system = "robo routine"
                        self.do("doExposure -df")

                    except Exception as e:
                        msg = f"roboOperator: could not run flat loop instance due to error with {system}: due to {e.__class__.__name__}, {e}"
                        self.log(msg)
                        self.alertHandler.slack_log(f"*ERROR:* {msg}", group=None)
                        err = roboError(context, self.lastcmd, system, msg)
                        self.hardware_error.emit(err)

        self.announce("Turning OFF the cal lamp!")
        self.doTry("pdu off callamp", context="dome flats", system="pdu")
        time.sleep(2)

        self.announce("Dome flats sequence complete!")

    def do_bias(self):
        self.log(f"running bias image sequence")
        context = "do_bias"
        # stow the rotator
        self.rotator_stop_and_reset()
        try:
            # slew the dome
            system = "dome"
            self.do(f"dome_tracking_off")
            system = "telescope"
            self.do(f"mount_tracking_off")

            self.log(f"starting the bias observations")

        except Exception as e:
            msg = f"roboOperator: could not set up {system} due to {e.__class__.__name__}, {e}"
            self.log(msg)
            self.alertHandler.slack_log(f"*ERROR:* {msg}", group=None)
            err = roboError(context, self.lastcmd, system, msg)
            self.hardware_error.emit(err)
            return
        ### Take bias ###
        try:
            self.announce(f"doing bias seq")

            try:
                self.do(f"ccd_set_exposure 0.0")
                nbias = 5
                for i in range(nbias):
                    self.announce(f"Executing Auto Bias {i+1}/5")
                    qcomment = f"Auto Bias {i+1}/{nbias}"
                    self.do(f'robo_do_exposure -b --comment "{qcomment}"')

            except Exception as e:
                msg = f"roboOperator: could not set up bias routine due to error with {system} due to {e.__class__.__name__}, {e}"
                self.log(msg)
                self.alertHandler.slack_log(f"*ERROR:* {msg}", group=None)
                err = roboError(context, self.lastcmd, system, msg)
                self.hardware_error.emit(err)
                return
        except Exception as e:
            msg = f"roboOperator: could not complete bias image collection due to error with {system}: due to {e.__class__.__name__}, {e}"
            self.log(msg)
            self.alertHandler.slack_log(f"*ERROR:* {msg}", group=None)
            err = roboError(context, self.lastcmd, system, msg)
            self.hardware_error.emit(err)
            # return

        # self.log(f'finished with calibration. no more to do.')
        self.announce("bias sequence completed successfully!")

        # self.calibration_complete = True

        # set the exposure time back to something sensible to avoid errors
        try:
            self.do(f"ccd_set_exposure 30.0")

        except Exception as e:
            msg = f"roboOperator: could not set up bias routine due to error with {system} due to {e.__class__.__name__}, {e}"
            self.log(msg)
            self.alertHandler.slack_log(f"*ERROR:* {msg}", group=None)
            err = roboError(context, self.lastcmd, system, msg)
            self.hardware_error.emit(err)
            return

    def do_darks(self, n_imgs=None, exptimes=None, camname="winter"):
        """
        do a series of dark exposures in all active filteres

        """
        # change the camera to the specified camera for the darks
        if camname != self.camname:
            self.camname = camname
            self.switchCamera(self.camname)

        context = "do_darks"
        self.log(f"starting dark sequence")

        # set the progID info here for the headers
        self.resetObsValues()
        try:
            self.programPI = self.config["cal_params"]["prog_params"]["cals"]["progPI"]
            self.programID = self.config["cal_params"]["prog_params"]["cals"]["progID"]
            self.programName = self.config["cal_params"]["prog_params"]["cals"][
                "progName"
            ]
            self.obstype = "DARK"
            self.obsmode = "CALIBRATION"
        except Exception as e:
            self.log(f"could not update the header values for the dark sequence: {e}")

        # How many images do you want to take at each exposure time?
        if n_imgs is None:
            n_imgs = self.config["cal_params"][self.camname]["dark"]["n_imgs"]
        # What exposure times should we take darks at?
        # exptimes = [360.0, 180.0]

        # commenting this out for the moment to get things working in ndr-slope mode
        if (exptimes is None) or (exptimes == []):
            exptimes = self.config["cal_params"][self.camname]["dark"]["exptimes"]

            try:
                # try to run a query of scheduled exposure times:
                scheduled_exptimes = self.caltracker.getScheduledExptimes(self.camname)
                for exptime in scheduled_exptimes:
                    if exptime not in exptimes:
                        exptimes.append(exptime)
            except Exception as e:
                msg = f"could not run query on scheduled exposure times for {self.camname}: {e}"
                self.announce(msg, group="operator")
            # now order the exposure times?

        # stow the rotator
        self.rotator_stop_and_reset()
        try:
            # slew the dome
            system = "dome"
            self.do(f"dome_tracking_off")
            system = "telescope"
            self.do(f"mount_tracking_off")

        except Exception as e:
            msg = f"roboOperator: could not set up {system} due to {e.__class__.__name__}, {e}"
            self.log(msg)
            self.alertHandler.slack_log(f"*ERROR:* {msg}", group=None)
            err = roboError(context, self.lastcmd, system, msg)
            self.hardware_error.emit(err)
            return

        try:
            # slew the dome
            system = "dome"
            self.announce("closing dome...")
            self.do("dome_close")
            self.announce(":greentick: dome closed")
            system = "telescope"

            # as usual the mirror covers are a flaky mess
            # self.announce(f'closing mirror covers...')
            # self.do('mirror_cover_close')
            # self.announce(':greentick: mirror covers closed!')

        except Exception as e:
            msg = f"roboOperator: could not set up {system} due to {e.__class__.__name__}, {e}"
            self.log(msg)
            self.alertHandler.slack_log(f"*ERROR:* {msg}", group=None)
            self.announce(f"continuuing with dark sequence anyway")
            # err = roboError(context, self.lastcmd, system, msg)
            # self.hardware_error.emit(err)
        # cycle through all the active filters:for filterID in
        # filterIDs = self.focusTracker.getActiveFilters()
        self.log(f"starting the darks sequence")

        # just pick the first of the active filters to do the darks in
        try:
            self.announce(
                f"doing auto darks sequence with ndarks per exposure = {n_imgs}, exptimes = {exptimes}"
            )

            # send the filter to the specified position from the config file
            filterID = self.config["cal_params"][self.camname]["dark"]["filterID"]
            # get filter number
            for position in self.config["filter_wheels"][self.camname]["positions"]:
                if (
                    self.config["filter_wheels"][self.camname]["positions"][position]
                    == filterID
                ):
                    filter_num = position
                else:
                    pass
            system = "filter wheel"
            try:
                self.do(f"fw_goto {filter_num} --{self.camname}")
            except Exception as e:
                msg = f"roboOperator: could not set up dark routine due to error with {system} due to {e.__class__.__name__}, {e}"
                self.log(msg)
                self.alertHandler.slack_log(f"*ERROR:* {msg}", group=None)
                err = roboError(context, self.lastcmd, system, msg)
                self.hardware_error.emit(err)
                return

            system = "camera"
            # step through the specified exposure times:
            for exptime in exptimes:
                try:
                    # changing the exposure can take a little time, so only do it if the exposure is DIFFERENT than the current
                    if exptime == self.camera.state["exptime"]:
                        self.log(
                            "requested exposure time matches current setting, no further action taken"
                        )
                        pass
                    else:
                        self.log(
                            f'current exptime = {self.camera.state["exptime"]}, changing to {exptime}'
                        )
                        self.do(f"setExposure {exptime} --{self.camname}")

                    for i in range(n_imgs):
                        self.announce(
                            f"Executing Auto Darks {i+1}/{n_imgs} at exptime = {exptime} s"
                        )
                        qcomment = f"Auto Darks {i+1}/{n_imgs}"

                        self.do(f"robo_do_exposure -d --calibration")
                except Exception as e:
                    msg = f"roboOperator: could not set up dark routine due to error with {system} due to {e.__class__.__name__}, {e}"
                    self.log(msg)
                    self.alertHandler.slack_log(f"*ERROR:* {msg}", group=None)
                    err = roboError(context, self.lastcmd, system, msg)
                    self.hardware_error.emit(err)
                    return

        except Exception as e:
            msg = f"roboOperator: could not complete darks for  due to error with {system}: due to {e.__class__.__name__}, {e}"
            self.log(msg)
            self.alertHandler.slack_log(f"*ERROR:* {msg}", group=None)
            err = roboError(context, self.lastcmd, system, msg)
            self.hardware_error.emit(err)
            return

        self.announce(":greentick: auto darks image sequence completed successfully!")
        self.announce("setting system back up for observing")

        system = "telescope"
        self.announce(f"opening mirror covers...")
        self.doTry("mirror_cover_open", context=context, system=system)
        self.announce(":greentick: mirror covers open!")

        system = "dome"
        self.announce("opening dome...")
        self.doTry("dome_open", context=context, system=system)
        self.announce(":greentick: dome opened")

        # cycle through all the active filters:for filterID in
        # filterIDs = self.focusTracker.getActiveFilters()
        self.announce("auto darks completed, continuuing with observations!")

    def do_focusLoop(
        self,
        nom_focus="model",
        total_throw="default",
        nsteps="default",
        updateFocusTracker=True,
        focusType="Vcurve",
    ):
        """
        Runs a focus loop in the CURRENT filter.
        Adaptation of Cruz Soto's doFocusLoop in wintercmd

        This runs a focus loop for the current filter, and returns the best focus position

        Does this without regard to where telescope is pointing.

        # note the config has things like this:
        filters:
            summer:
                r:
                    name: "SDSS r' (Chroma)"
                    nominal_focus: 10150
                    active: True
        filter_wheels:
            summer:
                positions:
                    1: 'u'
                    2: 'other2'
                    3: 'r'
                    4: 'other4'
                    5: 'other5'
                    6: 'other6'
        """
        self.announce("running focus loop!")
        context = "do_focusLoop"

        # set the progID info here for the headers
        self.resetObsValues()
        try:
            self.programPI = self.config["cal_params"]["prog_params"]["focus"]["progPI"]
            self.programID = self.config["cal_params"]["prog_params"]["focus"]["progID"]
            self.programName = self.config["cal_params"]["prog_params"]["focus"][
                "progName"
            ]
            self.obstype = "FOCUS"
            self.obsmode = "CALIBRATION"
        except Exception as e:
            self.log(f"could not update the header field values in the focus loop: {e}")

        # get the current filter

        try:

            filterpos = self.fw.state["filter_pos"]
            # pixscale = self.config['focus_loop_param']['pixscale'][self.camname]
            pixscale = self.config["observing_parameters"][self.camname]["pixscale"]

            filterID = self.config["filter_wheels"][self.camname]["positions"][
                filterpos
            ]  # eg. 'r'
            filtername = self.config["filters"][self.camname][filterID][
                "name"
            ]  # eg. "SDSS r' (Chroma)"

            if nom_focus == "last":
                # TODO: make this query the focusTracker to find the last focus position
                try:
                    last_focus, last_focus_timestamp = self.focusTracker.checkLastFocus(
                        filterID
                    )
                    # set the nominal focus to the last focus positiion
                    nom_focus = last_focus
                    self.log(
                        f"focusing around previous best focus location: {nom_focus}"
                    )

                    if nom_focus is None:
                        self.log(
                            f"no previous focus position found, defaulting to nominal."
                        )
                        nom_focus = self.config["filters"][self.camname][filterID][
                            "nominal_focus"
                        ]

                except Exception as e:
                    self.log(
                        f"could not get a value for the last focus position. defaulting to default focus. Traceback = {traceback.format_exc()}"
                    )
                    nom_focus = self.config["filters"][self.camname][filterID][
                        "nominal_focus"
                    ]
            elif nom_focus == "default":
                nom_focus = self.config["filters"][self.camname][filterID][
                    "nominal_focus"
                ]

            elif nom_focus == "model":
                # put the model here
                nom_focus = 9.654 * self.state["telescope_temp_ambient"] + 9784.4

            if total_throw == "default":
                # total_throw = self.config['focus_loop_param']['total_throw']
                total_throw = self.config["focus_loop_param"]["sweep_param"]["wide"][
                    "total_throw"
                ]
            if nsteps == "default":
                # nsteps = self.config['focus_loop_param']['nsteps']
                nsteps = self.config["focus_loop_param"]["sweep_param"]["wide"][
                    "nsteps"
                ]

            # init a focus loop object on the current filter
            #    config, nom_focus, total_throw, nsteps, pixscale
            self.log(
                f"setting up focus loop object: nom_focus = {nom_focus}, total_throw = {total_throw}, nsteps = {nsteps}, pixscale = {pixscale}"
            )

            # what kind of focus loop do we want to do?
            if focusType.lower() == "parabola":
                loop = focusing.Focus_loop_v2(
                    self.config, nom_focus, total_throw, nsteps, pixscale
                )
            else:
                loop = focusing.Focus_loop_v3(
                    self.config,
                    nom_focus,
                    total_throw,
                    nsteps,
                    pixscale,
                    state=self.state,
                )
            self.log(f"focus loop: will take images at {loop.filter_range}")

        except Exception as e:
            msg = f"roboOperator: could not run focus loop due to  due to {e.__class__.__name__}, {e}"  #', tb = {traceback.format_exc()}'
            self.log(msg)
            self.alertHandler.slack_log(f"*ERROR:* {msg}", group=None)
            # err = roboError(context, self.lastcmd, system, msg)
            # self.hardware_error.emit(err)
            return

        # note that the list of focus positions is loop.filter_range

        #### START THE FOCUS LOOP ####
        self.log(
            f"setting up focus loop for {self.camname} {filtername} (filterpos = {filterpos}, filterID = {filterID})"
        )

        # first drive the focuser in past the first position
        # loop.filter_range is arranged small to big distances, so start smaller to ensure we approach all points from the same direction
        focuser_start_pos = np.min(loop.filter_range_nom) - 100

        system = "focuser"
        try:
            self.log(
                f"racking focuser below min position to pre-start position: {focuser_start_pos} before starting"
            )
            cur_focus = nom_focus
            while cur_focus > focuser_start_pos:
                next_pos = max([cur_focus - 100, focuser_start_pos])
                print(f"Current focus: {cur_focus} -> {next_pos}")
                # self.do(f'm2_focuser_goto {focuser_start_pos}')
                self.do(f"m2_focuser_goto {next_pos}")
                cur_focus = next_pos

        except Exception as e:
            msg = f"roboOperator: could not run focus loop due to error with {system} due to {e.__class__.__name__}, {e}"
            self.log(msg)
            self.alertHandler.slack_log(f"*ERROR:* {msg}", group=None)
            err = roboError(context, self.lastcmd, system, msg)
            self.hardware_error.emit(err)
            return
        # step through the focus positions and take images

        focuser_pos = []
        images = []
        image_log_path = self.config["focus_loop_param"]["image_log_path"]

        # keep track of which image we're on
        i = 0
        # for i in range(len(loop.filter_range_nom)):
        for dist in loop.filter_range_nom:

            try:
                self.log(f"taking filter image at focuser position = {dist}")

                # drive the focuser
                system = "focuser"
                self.do(f"m2_focuser_goto {dist}")

                self.exptime = self.config["filters"][self.camname][filterID][
                    "focus_exptime"
                ]
                self.logger.info(
                    f"robo: making sure exposure time on camera to is set to {self.exptime}"
                )

                # changing the exposure can take a little time, so only do it if the exposure is DIFFERENT than the current
                # if self.exptime == self.state['exptime']:
                if self.exptime == self.camera.state["exptime"]:
                    self.log(
                        "requested exposure time matches current setting, no further action taken"
                    )
                    pass
                else:
                    # self.log(f'current exptime = {self.state["exptime"]}, changing to {self.exptime}')
                    self.log(
                        f'current exptime = {self.camera.state["exptime"]}, changing to {self.exptime}'
                    )
                    self.do(f"setExposure {self.exptime} --{self.camname}")

                # take an image
                system = "camera"
                # self.do(f'robo_do_exposure -foc')

                qcomment = (
                    f"Focus Loop Image {i+1}/{nsteps} Focus Position = {dist:.0f} um"
                )
                # qcomment = f"(Alt, Az) = ({self.state['mount_alt_deg']:0.1f}, {self.state['mount_az_deg']:0.1f})"
                # now trigger the actual observation. this also starts the mount tracking
                self.announce(f"Executing {qcomment}")
                if i == 0:
                    self.log(f"handling the i=0 case")
                    # self.do(f'robo_set_qcomment "{qcomment}"')
                    # system = 'robo routine'

                    # observe the focus location

                    # be prepared to cycle through targets until one works
                    firstObsComplete = False
                    for target in self.config["focus_loop_param"]["targets"]:
                        focus_target_type = self.config["focus_loop_param"]["targets"][
                            target
                        ]["target_type"]
                        focus_target = self.config["focus_loop_param"]["targets"][
                            target
                        ]["target"]

                        try:
                            print(
                                f"Focus Loop Running in Thread: {threading.get_ident()}"
                            )
                            # raise TargetError('what happens if i explicitly raise an error???')
                            self.do(
                                f'robo_observe {focus_target_type} {focus_target} -foc --comment "{qcomment}" --calibration'
                            )

                            # check if the observation was completed successfully
                            if self.observation_completed:
                                self.announce(
                                    f"completed critical first observation, on to the rest..."
                                )
                                # if we get here, then break out of the loop!
                                firstObsComplete = True
                                break

                            else:
                                # if the problem was a target issue, try we'll try a new target
                                if self.target_ok == False:
                                    # if we're here, it means (probably) that there's some ephemeris near the target. go try another target
                                    self.announce(
                                        f"could not observe focus target, TargetError: type = {focus_target_type}, target = ({focus_target}), trying next one..."
                                    )

                                # if it was some other error, all bets are off. just bail.
                                else:
                                    # if we're here there's some generic error. raise it.
                                    self.announce(
                                        f"could not observe focus target exiting..."
                                    )
                                    return
                            # self.target_ok = True
                            # self.observation_completed = False
                            """    
                            # this logic isn't working... exception is NOT being caught!
                            self.announce(f'completed critical first observation, on to the rest...')
                            # if we get here, then break out of the loop!
                            firstObsComplete = True
                            break
                        
                        except TimeoutError as e:
                            # if we're here, it means (probably) that there's some ephemeris near the target. go try another target
                            print(e)
                            self.announce(f'could not observe focus target (error: {e}): type = {focus_target_type}, target = ({focus_target}), trying next one...')
                            """
                        except Exception as e:
                            # if we're here there's some generic error. raise it.
                            self.announce(
                                f"could not observe focus target (error: {e}), exiting..."
                            )
                            raise Exception(e)
                            return

                    if firstObsComplete:
                        pass
                    else:
                        # if we get down to here then we ran out of targets. stop what's happening
                        self.announce(
                            f"could not observe ANY of the focus targets from the list. exiting..."
                        )
                        return

                else:
                    # any observation besides the first
                    # do a dither:
                    system = "telescope"
                    dithersize = 5 * 60
                    self.do(f"mount_random_dither_arcsec {dithersize}")

                    system = "camera"
                    # self.do(f'robo_do_exposure --comment "{qcomment}" -foc ')
                    self.do(f"robo_do_exposure -foc ")

                image_directory, image_filename = self.camera.getLastImagePath()
                image_filepath = os.path.join(image_directory, image_filename)
                if self.camname == "winter":
                    image_filepath = image_filepath + "_mef.fits"

                # add the filter position and image path to the list to analyze
                focuser_pos.append(dist)
                images.append(image_filepath)
                self.log("focus image added to list")

            except Exception as e:
                msg = f"roboOperator: error while running focus loop with {system} due to {e.__class__.__name__}, {e}"
                self.log(msg)
                self.alertHandler.slack_log(f"*ERROR:* {msg}", group=None)
                err = roboError(context, self.lastcmd, system, msg)
                self.hardware_error.emit(err)
                # return
                # NPL 6-30-23 got rid of this return so it will keep trying if there's a problem with any given image
            # increase the image number counter
            i += 1
        # print out the files and positions to the terminal
        print("FOCUS LOOP DATA:")
        for i in range(len(focuser_pos)):
            print(f"     [{i+1}] Focuser Pos: {focuser_pos[i]:.1f}, {images[i]}")

        # handle what to do in test mode
        if self.test_mode:
            # focuser_pos = [9761.414819232772, 9861.414819232772, 9961.414819232772, 10061.414819232772, 10161.414819232772]
            # images = ['/home/winter/data/images/20220119/SUMMER_20220119_221347_Camera0.fits',
            #          '/home/winter/data/images/20220119/SUMMER_20220119_221444_Camera0.fits',
            #          '/home/winter/data/images/20220119/SUMMER_20220119_221541_Camera0.fits',
            #          '/home/winter/data/images/20220119/SUMMER_20220119_221641_Camera0.fits',
            #          '/home/winter/data/images/20220119/SUMMER_20220119_221741_Camera0.fits']

            imnames = [
                "WINTERcamera_20230711-051746-285",
                "WINTERcamera_20230711-051825-746",
                "WINTERcamera_20230711-051905-364",
                "WINTERcamera_20230711-051944-958",
                "WINTERcamera_20230711-052025-470",
                "WINTERcamera_20230711-052104-426",
                "WINTERcamera_20230711-052143-925",
            ]

            images = [
                "/home/winter/data/images/20230710/" + imname + "_mef.fits"
                for imname in imnames
            ]

        """
        # save the data to a csv for later access
        try:
            data = {'images': images, 'focuser_pos' : list(focuser_pos)}
            df = pd.DataFrame(data)
            df.to_csv(image_log_path + 'focusLoop' + self.state['mount_timestamp_utc'] + '.csv')
        
        except Exception as e:
            msg = f'Unable to save files to focus csv due to {e.__class__.__name__}, {e}'
            self.log(msg)
        """

        system = "focuser"
        # fit the data and find the best focus
        try:
            # drive back to start position so we approach from same direction
            self.log(f"Focuser re-aligning at pre-start position: focuser_start_pos")
            while cur_focus > focuser_start_pos:
                next_pos = max([cur_focus - 100, focuser_start_pos])
                print(f"Current focus: {cur_focus} -> {next_pos}")
                # self.do(f'm2_focuser_goto {focuser_start_pos}')
                self.do(f"m2_focuser_goto {next_pos}")
                cur_focus = next_pos

            # self.do(f'm2_focuser_goto {focuser_start_pos}')

            if self.sunsim:
                # TODO: needs testing to be sure this is right...
                obstime_mjd = self.ephem.state.get("mjd", 0)
                obstime = astropy.time.Time(
                    obstime_mjd, format="mjd", location=self.ephem.site
                )
                obstime_timestamp_utc = obstime.datetime.timestamp()
            else:
                obstime_timestamp_utc = datetime.now(tz=pytz.UTC).timestamp()

            # now analyze the data (rate the images and load the observed filterpositions)

            # TODO: this is where the focus is fit this will need to be updated
            # x0_fit = loop.analyzeData(focuser_pos, images)
            # for now just return 12000
            if self.camname == "winter":
                # make this better and less specific if possible...
                try:
                    ns = Pyro5.core.locate_ns(host="192.168.1.10")
                    uri = ns.lookup("WINTERImageDaemon")
                    self.image_daemon = Pyro5.client.Proxy(uri)
                    image_daemon_connected = True
                except Exception as e:
                    image_daemon_connected = False
                    self.log(
                        f"could not connect to WINTER image daemon",
                        exc_info=True,
                    )

                if image_daemon_connected:
                    # board_ids_to_use = [4, 3, 2]
                    # board_ids_to_use = [4, 3]
                    # board_ids_to_use = [4] # NL updated during the troubles with PB 7/2/24
                    board_ids_to_use = [1]
                    board_ids_to_use = [#2, #SA
                                        ##6, #SB
                                        #5, #SC
                                        1, #PA
                                        #3, #PB
                                        ##4, #PC
                                        ] 
                    x0_fit = self.image_daemon.get_focus_from_imgpathlist(
                        images,
                        board_ids_to_use=board_ids_to_use,
                        plot_all=False,
                    )
                    self.announce(
                        f"Ran the focus script on Freya and got best focus = {x0_fit:.1f}"
                    )
                    fit_successful = True
                else:
                    fit_successful = False
                    # x0_fit = 11797.657

            else:
                fit_successful = False
            # print(f'x0_fit = {x0_fit}, type(x0_fit) = {type(x0_fit)}')
            # print(f'x0_err = {x0_err}, type(x0_err) = {type(x0_err)}')

            # self.announce(f'Fit Results: x0 = [{x0_fit:.0f} +/- {x0_err:.0f}] microns ({(x0_err/x0_fit*100):.0f}%)')

            # validate that the fit was good enough
            if (
                not fit_successful
            ):  # False: #x0_err > self.config['focus_loop_param']['focus_error_max']:
                self.announce(f"FIT IS TOO BAD. Returning to nominal focus")
                self.do(f"m2_focuser_goto {nom_focus}")
                self.focus_attempt_number += 1

            else:
                self.logger.info(f"Focuser_going to final position at {x0_fit} microns")

                while cur_focus < x0_fit:
                    next_pos = min([cur_focus + 100, x0_fit])
                    print(f"Current focus: {cur_focus} -> {next_pos}")
                    # self.do(f'm2_focuser_goto {focuser_start_pos}')
                    self.do(f"m2_focuser_goto {next_pos}")
                    cur_focus = next_pos

                # take an image

                # note the path of the image and pass this to analyzer

                system = "camera"
                # self.do(f'robo_do_exposure --comment "{qcomment}" -foc ')
                self.do(f"robo_do_exposure -foc ")

                image_directory, image_filename = "", ""
                # image_directory, image_filename = self.ccd.getLastImagePath()
                best_focus_image_filepath = os.path.join(
                    image_directory, image_filename
                )

                # NPL 6-30-23 commenting out
                """
                loop.analyze_best_focus_image(best_focus_image_filepath)
                
                # save the data
                loop.save_focus_data()
                
                loop.plot_focus_curve(timestamp_utc = obstime_timestamp_utc)
                """

                if updateFocusTracker:

                    self.announce(
                        f"updating the focus position of filter {filterID} to {x0_fit}, timestamp = {obstime_timestamp_utc}"
                    )

                    self.focusTracker.updateFilterFocus(
                        filterID, x0_fit, obstime_timestamp_utc
                    )

                # we completed the focus! set the focus attempt number to zero
                self.focus_attempt_number = 0

        except FileNotFoundError as e:
            self.log(
                f"You are trying to modify a catalog file or an image with no stars , {e}"
            )
            pass

        except Exception as e:
            msg = f"roboOperator: could not run focus loop due to error with {system} due to {e.__class__.__name__}, {e}, traceback = {traceback.format_exc()}"
            self.log(msg)
            self.alertHandler.slack_log(f"*ERROR:* {msg}", group=None)
            err = roboError(context, self.lastcmd, system, msg)
            self.hardware_error.emit(err)
            return

        # now print the best fit focus to the slack
        """
        try:        
            focus_plot = '/home/winter/data/plots_focuser/latest_focusloop.jpg'
            self.alertHandler.slack_postImage(focus_plot)
        
        except Exception as e:
            msg = f'wintercmd: Unable to post focus graph to slack due to {e.__class__.__name__}, {e}'
            self.log(msg)
        """
        self.announce(
            f":greentick: completed focus loop. going to best focus = {x0_fit}"
        )

        return x0_fit

    def do_focus_sequence(self, filterIDs="reference", focusType="default"):
        """
        run a focus loop for each of the filters specified

        filterIDs should be a list of filter IDs for the current camera

        """
        context = "do_focus_sequence"
        system = ""

        if filterIDs == "active":
            # focus in all the active filters, eg all the filters installed
            filterIDs = self.focusTracker.getActiveFilters()

        elif filterIDs == "reference":
            # focus in the reference filters specified in focus_loop_param
            # filterIDs = self.config['focus_loop_param']['filters'][self.camname]
            filterIDs = self.focusTracker.getFocusFilters(self.camname)

        self.announce(
            f"running focus loops for {self.camname}, focus filters = {filterIDs}"
        )

        for filterID in filterIDs:
            self.announce(f"executing focus loop for filter: {filterID}")
            try:
                # step through each filter to focus, and run a focus loop
                # 1. change filter to filterID
                system = "filter wheel"
                # get filter number
                for position in self.config["filter_wheels"][self.camname]["positions"]:
                    if (
                        self.config["filter_wheels"][self.camname]["positions"][
                            position
                        ]
                        == filterID
                    ):
                        filter_num = position
                    else:
                        pass
                if filter_num == self.fw.state["filter_pos"]:
                    self.log(
                        "requested filter matches current, no further action taken"
                    )
                else:
                    self.log(
                        f'current filter = {self.fw.state["filter_pos"]}, changing to {filter_num}'
                    )
                    # self.do(f'command_filter_wheel {filter_num}')
                    self.do(f"fw_goto {filter_num} --{self.camname}")

                # 2. do a focus loop!!
                system = "focus_loop"

                # handle the loop parameters depending on what attempt this is:
                """
                if self.focus_attempt_number == 0:
                    total_throw = self.config['focus_loop_param']['sweep_param']['wide']['total_throw']
                    nsteps = self.config['focus_loop_param']['sweep_param']['wide']['nsteps']
                    nom_focus = 'last'
                    if focusType == 'default':    
                        focusType = 'Parabola'
                """
                # elif self.focus_attempt_number == 1:
                # if self.focus_attempt_number < self.config['focus_loop_param']['max_focus_attempts']:

                sweeptype = "narrow"  # one of 'narrow' or 'wide'
                total_throw = self.config["focus_loop_param"]["sweep_param"][sweeptype][
                    "total_throw"
                ]
                nsteps = self.config["focus_loop_param"]["sweep_param"][sweeptype][
                    "nsteps"
                ]
                nom_focus = "default"
                # nom_focus = 'last'
                # nom_focus = 'model'
                # nom_focus = 12000 #NPL 7-1-23 using this for now
                focusType = "Vcurve"
                """
                else:
                    # this should send focus to last good position
                    last_focus, last_focus_timestamp = self.focusTracker.checkLastFocus(filterID)
                    system = 'focuser'
                    try:
                        #TODO: do rob's thing of splitting into multiple steps
                        self.announce(f'having a bad time focusing. sending to last good focus')
                        self.do(f'm2_focuser_goto {last_focus}')
                            
                        
                        
        
                    except Exception as e:
                        msg = f'roboOperator: could not run focus loop due to error with {system} due to {e.__class__.__name__}, {e}'
                        self.log(msg)
                        self.alertHandler.slack_log(f'*ERROR:* {msg}', group = None)
                        err = roboError(context, self.lastcmd, system, msg)
                        self.hardware_error.emit(err)
                        return
                """
                self.do_focusLoop(
                    nom_focus=nom_focus,
                    total_throw=total_throw,
                    nsteps=nsteps,
                    updateFocusTracker=True,
                    focusType=focusType,
                )

            except Exception as e:
                msg = f"roboOperator: could not run focus loop due to error with {system} due to {e.__class__.__name__}, {e}, traceback = {traceback.format_exc()}"
                self.log(msg)
                self.alertHandler.slack_log(f"*ERROR:* {msg}", group=None)
                err = roboError(context, self.lastcmd, system, msg)
                self.hardware_error.emit(err)

                # increment the focus loop number
                self.focus_attempt_number += 1

                return

    def resetObsValues(self):
        """
        resets all the items which keep track of the schedule entries,
        like obsHistID, fieldID, etc
        this prevents them from dangling around and getting erroneously
        assigned to later images
        """
        self.obsHistID = -1
        self.ra_deg_scheduled = -1
        self.dec_deg_scheduled = -1
        self.filter_scheduled = ""
        self.visitExpTime = -1
        self.targetPriority = -1
        self.programPI = ""
        self.programID = -1
        self.programName = ""
        self.validStart = -1
        self.validStop = -1
        # get the max airmass: if none, default to the telescope upper limit: maxAirmass = sec(90 - min_telescope_alt)
        self.maxAirmass = 1.0 / np.cos(
            (90 - self.config["telescope"]["min_alt"]) * np.pi / 180.0
        )
        self.num_dithers = 1
        self.ditherStepSize = 0
        self.fieldID = -1
        self.targetName = ""
        self.scheduleName = ""
        self.scheduleType = ""
        self.qcomment = ""
        self.obstype = ""
        self.obsmode = ""
        self.num_dithers = 1
        self.dithnum = 1

    def do_currentObs(self, currentObs="default"):
        """
        do the observation of whatever is the current observation in self.schedule.currentObs

        then create the dictionary that will be used to log to the database, and create the fits header
            --> this uses self.writer.separate_data_dict
        then command the camerat to take an image and send it the fits header information

        then it starts the image wait QTimer, and returns
            --> the QTimer.finished signal is connected self.log_observation_and_gotoNext()
                which send the data from the observation to the log database, goes to the next line in the schedule,
                and then calls do_currentObs again
                BOTH do_currentObs and log_observation_and_gotoNext will only execute if self.running == True

        the WHOLE POINT of this event-based approach rather than using an infinite loop
        is to keep everything responsive, so that we can break into the loop if necessary.
        Using an infinite loop and a long wait is ~bad~ because if the thread is blocked
        it will miss outside signals.

        Things to handle:
            - how is the observing loop interuppted if there is something like a weather closure?
            - how is the observing loop restarted after a weather closure ends?

            --> possible solution:
                    create a signal which will:
                        1. set running to False to prevent any futher logging
                        2. kill the exposure QTimer
                        3. emit a restartRobo signal so it gets kicked back to the top of the tree

        """

        if currentObs == "default":
            currentObs = self.schedule.currentObs

        self.check_ok_to_observe(logcheck=True)
        self.logger.info(
            f"self.running = {self.running}, self.ok_to_observe = {self.ok_to_observe}"
        )

        if currentObs is None:
            """
            # NPL shouldn't ever get here, if we do just leave anc check what to do
            self.logger.info(f'robo: self.schedule.currentObs is None. Closing connection to db.')
            self.running = False

            self.handle_end_of_schedule()
            """
            # NPL: comment this out while hunting the cause of skipped observations
            # self.checkWhatToDo()
            return

        # reset all the header stuff
        self.resetObsValues()

        # print(f'currentObs = {currentObs}')
        # first grab some fields from the currentObs
        # NOTE THE RECASTING! Some of these things come out of the dataframe as np datatypes, which
        # borks up the housekeeping and the dirfile and is a big fat mess
        self.obsHistID = int(currentObs["obsHistID"])
        self.ra_deg_scheduled = float(currentObs["raDeg"])
        self.dec_deg_scheduled = float(currentObs["decDeg"])
        self.filter_scheduled = str(currentObs["filter"])
        self.visitExpTime = float(currentObs["visitExpTime"])
        self.targetPriority = float(currentObs["priority"])
        self.programPI = str(currentObs.get("progPI", ""))
        self.programID = int(currentObs.get("progID", -1))
        self.programName = str(currentObs.get("progName", ""))
        self.validStart = float(currentObs.get("validStart"))
        self.validStop = float(currentObs.get("validStop"))
        # self.observed is managed elsewhere
        # get the max airmass: if none, default to the telescope upper limit: maxAirmass = sec(90 - min_telescope_alt)
        self.maxAirmass = float(
            currentObs.get(
                "maxAirmass",
                1.0
                / np.cos((90 - self.config["telescope"]["min_alt"]) * np.pi / 180.0),
            )
        )
        # self.num_dithers = int(currentObs.get('ditherNumber', self.config['dither_defaults']['camera'][self.camname]['ditherNumber']))
        # self.num_dithers_per_pointing = int(currentObs.get('ditherNumber', self.config['dither_defaults']['camera'][self.camname]['ditherNumber']))

        # self.num_dithers_per_pointing = int(currentObs.get('ditherNumber', self.config['observing_parameters'][self.camname]['dithers']['ditherNumber']))
        # self.num_dithers_per_pointing = 5 # just commented out above line to force this to 3 for testing
        self.num_dithers_per_pointing = int(currentObs.get("ditherNumber", 10))

        # self.ditherStepSize = float(currentObs.get('ditherStepSize', self.config['dither_defaults']['camera'][self.camname]['ditherStepSize']))
        self.ditherStepSize = float(
            currentObs.get(
                "ditherStepSize",
                self.config["observing_parameters"][self.camname]["dithers"][
                    "ditherMaxStep_as"
                ],
            )
        )
        self.fieldID = int(
            currentObs.get("fieldID", -1)
        )  # previously was using 999999999 but that's annoying :D
        self.targetName = str(currentObs.get("targName", ""))
        self.scheduleName = str(currentObs.get("origin_filename", ""))
        self.scheduleType = str(currentObs.get("scheduleType", ""))
        self.qcomment = ""
        self.obstype = "SCIENCE"
        self.bestDetector = bool(
            currentObs.get("bestDetector", 1)
        )  # should we center the field on the best detector

        if self.bestDetector:
            center_offset = "best"
        else:
            center_offset = "center"

        # which camera should be used for the observation?
        cam_to_use = self.getWhichCameraToUse(filterID=self.filter_scheduled)
        if cam_to_use is None:
            self.log(f"not sure which camera to use! aborting current observation.")
            # NPL: comment this out while hunting the cause of skipped observations
            # self.checkWhatToDo()
            return

        # if we're in the right camera just continue, otherwise switch cameras
        if cam_to_use == self.camname:
            pass
        else:
            self.switchCamera(cam_to_use)

        # how many pointings will we do?
        pointing_offsets = [{"coords": {"dRA": 0, "dDec": 0}}]
        if "offset_pointings" in self.config["observing_parameters"][self.camname]:
            pointing_offsets = (
                pointing_offsets
                + self.config["observing_parameters"][self.camname]["offset_pointings"]
            )
        else:
            pass
        num_pointings = len(pointing_offsets)

        # how many dithers per pointing?
        # if num_dithers = 0, you'll get no images... so change it to 1
        if self.num_dithers == 0:
            self.num_dithers = 1

        # how many total dithers? we will multiply the number of dithers per pointing by the number of pointings
        self.num_dithers = self.num_dithers_per_pointing * num_pointings

        # calculate individual exposure time
        # NPL 9-19-23 for now multiply by 2 so that we get the expected 60s exposure times
        self.exptime = (
            self.visitExpTime / self.num_dithers
        )  # /num_pointings)*2 # NPL 9-23-23 reverting this so that we get mostly 120s exposures for now
        # self.exptime = 45.0 #120.0
        # start the dither number at 1, it gets incremented after the exposure is complete.
        self.dithnum = 1

        for pointing_num, pointing_offset in enumerate(pointing_offsets, 1):

            # convert ra and dec from radians to astropy objects
            self.j2000_ra_scheduled = astropy.coordinates.Angle(
                self.ra_deg_scheduled * u.deg
            )
            self.j2000_dec_scheduled = astropy.coordinates.Angle(
                self.dec_deg_scheduled * u.deg
            )

            # get the target RA (hours) and DEC (degs) in units we can pass to the telescope
            self.target_ra_j2000_hours = self.j2000_ra_scheduled.hour
            self.target_dec_j2000_deg = self.j2000_dec_scheduled.deg

            # calculate the current Alt and Az of the target
            if self.sunsim:
                obstime_mjd = self.ephem.state.get("mjd", 0)
                obstime_utc = astropy.time.Time(
                    obstime_mjd, format="mjd", location=self.ephem.site
                )
            else:
                obstime_utc = astropy.time.Time(datetime.utcnow(), format="datetime")

            frame = astropy.coordinates.AltAz(
                obstime=obstime_utc, location=self.ephem.site
            )
            scheduled_coords = astropy.coordinates.SkyCoord(
                ra=self.j2000_ra_scheduled,
                dec=self.j2000_dec_scheduled,
                frame="icrs",
            )
            scheduled_coords_local = scheduled_coords.transform_to(frame)
            self.target_alt = scheduled_coords_local.alt.deg
            self.target_az = scheduled_coords_local.az.deg

            # calculate the actual pointing coordinates, eg after applying the pointing offset
            # figure out where to go
            offset_ra = pointing_offset["coords"]["dRA"] * u.arcsecond
            offset_dec = pointing_offset["coords"]["dDec"] * u.arcsecond

            pointing_coords = scheduled_coords.spherical_offsets_by(
                offset_ra, offset_dec
            )
            self.pointing_ra_j2000_hours = pointing_coords.ra.hour
            self.pointing_dec_j2000_deg = pointing_coords.dec.deg

            pointing_coords_local = pointing_coords.transform_to(frame)
            self.pointing_alt = pointing_coords_local.alt.deg
            self.pointing_az = pointing_coords_local.az.deg

            # put the dither for loop here:
            # for dithnum in range(self.num_dithers):

            # NUMBERING DITHERS AS 1, 2, ... , self.num_dithers
            # e.g., if you want 5 dithers per pointing, then self.dithnum = 1, 2, 3, ... , self.num_dithers

            for dithnum_in_this_pointing in np.arange(
                1, self.num_dithers_per_pointing + 1, 1
            ):  # INDEX STARTS AT 1!!!

                # ex: dither 3/5 of the secoind pointing:
                # dithnum_in_this_pointing = 3
                # self.num_dithers_per_pointing = 5
                # self.dithnum = 8
                # self.remaining_dithers_in_this_pointing = 2

                # how many dithers remain AFTER this one in the current pointing
                self.remaining_dithers_in_this_pointing = (
                    self.num_dithers_per_pointing - dithnum_in_this_pointing
                )

                self.announce(
                    f"top of loop: self.dithnum = {self.dithnum}, self.num_dithers = {self.num_dithers}"
                )
                self.announce(
                    f"dithnum_in_this_pointing = {dithnum_in_this_pointing}, self.remaining_dithers_in_this_pointing = {self.remaining_dithers_in_this_pointing}"
                )
                # for each dither, execute the observation
                if self.running & self.ok_to_observe:

                    # msg = f'executing observation of obsHistID = {self.lastSeen} at (alt, az) = ({self.alt_scheduled:0.2f}, {self.az_scheduled:0.2f})'

                    # force the state to update so it has all the observation parameters
                    self.update_state(printstate=True)
                    # print(f'after updating state (in do_currentObs), self.dithnum = {self.dithnum}')
                    # now go off and execute the observation

                    # print out to the slack log a bunch of info (only once per target)
                    if dithnum_in_this_pointing == 1:
                        msg = f"Executing observation of obsHistID = {self.obsHistID}"
                        self.announce(msg)
                        self.announce(
                            f">> Target (RA, DEC) = ({self.j2000_ra_scheduled.hour} h, {self.j2000_dec_scheduled.deg} deg)"
                        )
                        self.announce(
                            f">> Target Current (ALT, AZ) = ({self.target_alt} deg, {self.target_az} deg)"
                        )

                    # Do the observation

                    context = "do_currentObs"
                    system = "observation"
                    try:

                        # 3: trigger image acquisition

                        self.logger.info(
                            f"robo: making sure exposure time on camera to is set to {self.exptime}"
                        )

                        # changing the exposure can take a little time, so only do it if the exposure is DIFFERENT than the current
                        # if self.exptime == self.state['exptime']:
                        if self.exptime == self.camera.state["exptime"]:
                            self.log(
                                "requested exposure time matches current setting, no further action taken"
                            )
                            pass
                        else:
                            # self.log(f'current exptime = {self.state["exptime"]}, changing to {self.exptime}')
                            self.log(
                                f'current exptime = {self.camera.state["exptime"]}, changing to {self.exptime}'
                            )
                            self.do(f"setExposure {self.exptime} --{self.camname}")

                        # TODO: we are currently not changing the focus based on the filter! whoopsy. add that here NPL 8-12-22
                        # change the m2 position if we have switched filters

                        # changing the filter can take a little time so only do it if the filter is DIFFERENT than the current
                        system = "filter wheel"

                        # get filter number
                        for position in self.config["filter_wheels"][self.camname][
                            "positions"
                        ]:
                            if (
                                self.config["filter_wheels"][self.camname]["positions"][
                                    position
                                ]
                                == self.filter_scheduled
                            ):
                                filter_num = position
                            else:
                                pass
                        if filter_num == self.fw.state["filter_pos"]:
                            self.log(
                                "requested filter matches current, no further action taken"
                            )
                        else:
                            self.log(
                                f'current filter = {self.fw.state["filter_pos"]}, changing to {filter_num}'
                            )
                            # self.do(f'command_filter_wheel {filter_num}')
                            self.do(f"fw_goto {filter_num} --{self.camname}")

                        # set up a big descriptive message for slack:
                        msg = f'>> Executing Observation: Pointing Number [{pointing_num}/{num_pointings}]: (dRA, dDec) = ({pointing_offset["coords"]["dRA"]}, {pointing_offset["coords"]["dDec"]})'

                        if dithnum_in_this_pointing == 1:

                            msg += f", Dither Number [{dithnum_in_this_pointing}/{self.num_dithers_per_pointing}], Dither (dRA, dDec) = (0, 0) as"
                            self.announce(msg)

                            if self.test_mode:
                                self.announce(
                                    f">> RUNNING IN TEST MODE: JUST OBSERVING THE ALT/AZ FROM SCHEDULE DIRECTLY"
                                )
                                # self.do(f'robo_observe altaz {self.target_alt} {self.target_az} --test --schedule')
                                self.do(
                                    f"robo_observe altaz {self.pointing_alt} {self.pointing_az} --test --schedule --offset {center_offset}"
                                )
                            else:

                                # now do the observation
                                # self.do(f'robo_observe radec {self.target_ra_j2000_hours} {self.target_dec_j2000_deg} --science --schedule')
                                self.do(
                                    f"robo_observe radec {self.pointing_ra_j2000_hours} {self.pointing_dec_j2000_deg} --science --schedule --offset {center_offset}"
                                )

                        else:
                            system = "camera"
                            # do the dither
                            if self.ditherStepSize > 0.0:

                                minradius = self.config["observing_parameters"][
                                    self.camname
                                ]["dithers"]["ditherMinStep_as"]
                                radius = self.ditherStepSize
                                radius = np.random.uniform(minradius, radius)
                                theta = np.random.uniform(0, np.pi)
                                ra_dither_arcsec = radius * np.cos(theta)
                                dec_dither_arcsec = radius * np.sin(theta)

                                msg += f", Dither Number [{dithnum_in_this_pointing}/{self.num_dithers}], Dither (dRA, dDec) = ({ra_dither_arcsec:0.1f}, {dec_dither_arcsec:.1f}) as"
                                self.announce(msg)

                                self.do(
                                    f"mount_dither_arcsec_radec {ra_dither_arcsec} {dec_dither_arcsec}"
                                )

                            # self.announce(msg)
                            if self.test_mode:
                                # self.announce(f'>> RUNNING IN TEST MODE: JUST OBSERVING THE ALT/AZ FROM SCHEDULE DIRECTLY')
                                self.do(f"robo_do_exposure --test")
                            else:
                                self.do(f"robo_do_exposure --science")

                        # check if the observation was completed successfully
                        if self.observation_completed:
                            pass

                        else:
                            # if the problem was a target issue, try we'll try a new target
                            if self.target_ok == False:
                                # if we're here, it means (probably) that there's some ephemeris near the target. go try another target
                                # msg = f'could not obserse target becase of target error (ephem nearby, etc). skipping this target...'
                                # self.announce(msg)
                                break
                            # if it was some other error, all bets are off. just bail.
                            else:
                                # if we're here there's some generic error. raise it.
                                self.announce(
                                    f"problem with this exposure, going to next..."
                                )

                        # no matter what happens, increment the dither
                        self.dithnum += 1

                        # NPL: comment this out while hunting the cause of skipped observations
                        # it is not clear to me that we need to keep any of this mess:
                        # instead! we should just put a call to something like:
                        # self.schedule.log_dither()
                        # which would write down that we've completed a dither
                        # if we get here, either it'll just loop back up and finish the dithers,
                        # or if there are no more dithers then will exit the loop and hit the bottom return

                        # # it is now okay to trigger going to the next observation
                        # # always log observation, but only gotoNext if we're on the last TOTAL dither
                        # if self.dithnum == self.num_dithers+1:
                        #     gotoNext = True
                        #     self.log_observation_and_gotoNext(gotoNext = gotoNext, logObservation = True)
                        # else:
                        #     gotoNext = False
                        #     self.log_observation_and_gotoNext(gotoNext = gotoNext, logObservation = False)
                        # #return #<- NPL 1/19/22 this return should never get executed, the log_observation_and_gotoNext call should handle exiting

                    except Exception as e:

                        tb = traceback.format_exc()
                        msg = f"roboOperator: could not execute current observation due to {e.__class__.__name__}, {e}"  #', traceback = {tb}'
                        self.log(msg)
                        err = roboError(context, self.lastcmd, system, msg)
                        self.hardware_error.emit(err)
                        # NPL 4-7-22 trying to get it to break out of the dither loop on error
                        break

                    # if we got here the observation wasn't completed properly
                    # return
                    # self.gotoNext()
                    # NPL 1/19/22: removing call to self.checkWhatToDo()
                    # self.checkWhatToDo()

                    # 5: exit

                # (self.running) & (self.ok_to_observe) is false:
                else:
                    # if it's not okay to observe, then restart the robo loop to wait for conditions to change
                    # self.restart_robo()
                    # NPL 1/19/22: replacing call to self.checkWhatToDo() with break to handle dither loop
                    # self.checkWhatToDo()
                    break

                msg = f"got to the end of the dither loop, should go to top of loop?"
                # self.log(msg)
                # self.announce(msg)

        # if we got here, then we are out of the loop, either because we did all the dithers, or there was a problem
        self.resetObsValues()
        # NPL: comment this out while hunting the cause of skipped observations
        # self.checkWhatToDo()
        return

    def log_observation_and_gotoNext(self, gotoNext=True, logObservation=True):
        self.announce(
            f"robo: handling end of observation with options gotoNext = {gotoNext}, logObservation = {logObservation}"
        )
        """
        if currentObs == 'default':
            currentObs = self.schedule.currentObs
        """
        # TODO: NPL 4-30-21 not totally sure about this tree. needs testing
        self.check_ok_to_observe(logcheck=True)
        if not self.ok_to_observe:
            # if it's not okay to observe, then restart the robo loop to wait for conditions to change
            # self.restart_robo()
            # return
            self.announce(
                f"in log_observation_and_gotoNext and it is no longer okay to observe!"
            )
            self.announce(f"dome.Shutter_Status = {self.dome.Shutter_Status}")

            self.checkWhatToDo()

        else:

            if self.schedule.currentObs is not None and self.running:

                if logObservation:
                    self.announce("robo: logging observation")
                    self.schedule.log_observation()
                    # self.logger.info('robo: logging observation')

            else:
                if self.schedule.currentObs is None:
                    self.logger.info(
                        "robo: in log and goto next, but there is no observation to log."
                    )
                elif self.running == False:
                    self.logger.info(
                        "robo: in log and goto next, but I caught a stop signal so I won't do anything"
                    )

            if gotoNext:
                msg = f" we're done with the observation and logging process. go figure out what to do next"
                self.log(msg)
                self.checkWhatToDo()

    def handle_end_of_schedule(self):
        # this handles when we get to the end of the schedule, ie when next observation is None:
        self.logger.info(f"robo: handling end of schedule")

        # FIRST: stow the rotator
        self.rotator_stop_and_reset()

        # Now shut down the connection to the databases
        # self.logger.info(f'robo: closing connection to schedule and obslog databases')
        # self.schedule.closeConnection()
        # self.writer.closeConnection()

    def log_timer_finished(self):
        self.logger.info("robo: exposure timer finished.")
        self.waiting_for_exposure = False

    def doExposure(self, obstype="TEST", postPlot=True, qcomment=None):
        # test method for making sure the roboOperator can communicate with the CCD daemon
        # 3: trigger image acquisition
        # self.exptime = float(self.schedule.currentObs['visitExpTime'])#/len(self.dither_alt)

        # self.announce(f'in doExposure: self.running = {self.running}')
        self.observation_completed = False
        self.logger.info(f"robo: running doExposure in thread {threading.get_ident()}")
        # if we got no comment, then do nothing
        """
        if qcomment == 'altaz':
            qcomment = f"(Alt, Az) = ({self.state['mount_alt_deg']:0.1f}, {self.state['mount_az_deg']:0.1f})"
        else:
            pass
        
        if qcomment is None:
            pass                
        else:
            # if the qcomment is the same as the current then do nothing
            if qcomment == self.qcomment:
                pass
            else:
                # if we got a new comment, set it
                self.doTry(f'robo_set_qcomment "{qcomment}"', context = 'doExposure')
        """
        # first check if any ephemeris bodies are near the target
        self.log("checking that target is not too close to ephemeris bodies")
        ephem_inview = self.ephemInViewTarget_AltAz(
            target_alt=self.state["mount_alt_deg"],
            target_az=self.state["mount_az_deg"],
        )

        # if doing a light exposure, make sure it's okay to open the shutter safely
        if obstype not in ["BIAS", "DARK"]:

            if not ephem_inview:
                self.log("ephem check okay: no ephemeris bodies in the field of view.")
                self.logger.info(f"robo: telling camera to take exposure!")
                pass
            else:
                msg = f">> ephemeris body is too close to target! skipping..."
                self.log(msg)
                self.alertHandler.slack_log(msg, group=None)
                self.target_ok = False
                raise TargetError(msg)

                # return

        # do the exposure and wrap with appropriate error handling
        system = "camera"
        context = "robo doExposure"
        self.logger.info(f"robo: telling camera to take exposure!")

        # pass the correct options to the ccd daemon
        obstype_dict = dict(
            {
                "FLAT": "-f",
                "BIAS": "-b",
                "DARK": "-d",
                "POINTING": "-p",
                "SCIENCE": "-s",
                "TEST": "-t",
                "FOCUS": "-foc",
            }
        )

        obstype_option = obstype_dict.get(obstype, "")
        self.log(f"updating self.obstype to {obstype}")
        self.obstype = obstype
        self.log(f"updating state")
        self.update_state()

        try:
            """
            if obstype == 'BIAS':
                self.do('ccd_do_bias')
            else:
                self.do(f'ccd_do_exposure {obstype_option}')
            """
            # TODO: need to reexamine how we're handling the image filenames and directories
            self.do(f"doExposure {obstype_option} --{self.camname}")

        except Exception as e:
            msg = f"roboOperator: could not set up {system} due to {e.__class__.__name__}, {e}"
            self.log(msg)
            err = roboError(context, self.lastcmd, system, msg)
            self.hardware_error.emit(err)
            self.target_ok = False
            raise Exception(msg)
            return

        # if we get to here then we have successfully saved the image
        self.log(f"exposure complete!")
        """
        if postPlot:
            # make a jpg of the last image and publish it to slack!
            postImage_process = subprocess.Popen(args = ['python','plotLastImg.py'])
        """
        # if we got here, the observation was complete
        self.observation_completed = True

    def is_rotator_mech_angle_possible(
        self, predicted_rotator_mechangle, rotator_min_degs, rotator_max_degs
    ):
        return (predicted_rotator_mechangle > rotator_min_degs) and (
            predicted_rotator_mechangle < rotator_max_degs
        )

    def get_safe_rotator_angle(
        self,
        ra_hours,
        dec_deg,
        target_field_angle,
        obstime=None,
        verbose=False,
    ):
        """
        takes in the target field angle, and then returns a field angle and
        mechanical angle pair that corresponds to the best safe rotator
        position within the allowed cable wrap range. Evaluates these 5
        choices (ranked best to worst):
            1. target field angle
            2. target field angle - 360 deg
            3. target field angle + 360 deg
            4. target field angle - 180 deg
            5. target field angle + 180 deg

        """

        if obstime is None:
            obstime = astropy.time.Time(datetime.utcnow(), location=self.ephem.site)

        self.target_ra_j2000_hours = ra_hours
        self.target_dec_j2000_deg = dec_deg

        j2000_ra = self.target_ra_j2000_hours * u.hour
        j2000_dec = self.target_dec_j2000_deg * u.deg
        j2000_coords = astropy.coordinates.SkyCoord(
            ra=j2000_ra, dec=j2000_dec, frame="icrs"
        )

        ra_deg = j2000_coords.ra.deg

        # lat = astropy.coordinates.Angle(self.config['site']['lat'])
        # lon = astropy.coordinates.Angle(self.config['site']['lon'])
        # height = self.config['site']['height'] * u.Unit(self.config['site']['height_units'])

        site = (
            self.ephem.site
        )  # astropy.coordinates.EarthLocation(lat = lat, lon = lon, height = height)
        frame = astropy.coordinates.AltAz(obstime=obstime, location=site)
        local_coords = j2000_coords.transform_to(frame)
        self.target_alt = local_coords.alt.deg
        self.target_az = local_coords.az.deg

        dec = dec_deg * np.pi / 180.0
        lst = obstime.sidereal_time("mean").rad
        hour_angle = lst - ra_deg * np.pi / 180.0
        if hour_angle < -1 * np.pi:
            hour_angle += 2 * np.pi
        if hour_angle > np.pi:
            hour_angle -= 2 * np.pi

        lat = astropy.coordinates.Angle(self.config["site"]["lat"]).rad

        parallactic_angle = (
            np.arctan2(
                np.sin(hour_angle),
                np.tan(lat) * np.cos(dec) - np.sin(dec) * np.cos(hour_angle),
            )
            * 180
            / np.pi
        )

        possible_target_field_angles = [
            target_field_angle,
            target_field_angle - 360.0,
            target_field_angle + 360.0,
            target_field_angle - 180.0,
            target_field_angle + 180.0,
        ]

        possible_target_mech_angles = [
            (target_field_angle - parallactic_angle - self.target_alt)
            for target_field_angle in possible_target_field_angles
        ]

        messages = [
            "No rotator wrap predicted",
            "Rotator wrapping < min, adjusting by -360 deg.",
            "Rotator wrapping > max, adjusting by +360 deg.",
            "Rotator wrapping < min, adjusting by -180 deg.",
            "Rotator wrapping > max, adjusting by +180 deg.",
        ]

        if verbose:
            print("\n##########################################")
        for ind, possible_target_mech_angle in enumerate(possible_target_mech_angles):
            if self.is_rotator_mech_angle_possible(
                predicted_rotator_mechangle=possible_target_mech_angle,
                rotator_min_degs=self.config["telescope"]["rotator"][self.camname][
                    "rotator_min_degs"
                ],
                rotator_max_degs=self.config["telescope"]["rotator"][self.camname][
                    "rotator_max_degs"
                ],
            ):
                self.target_mech_angle = possible_target_mech_angle
                self.target_field_angle = possible_target_field_angles[ind]
                if verbose:
                    print(messages[ind])
                    print(f"Adjusted field angle --> {self.target_field_angle}")
                    print(f"New target mech angle = {self.target_mech_angle}")
                break
        if verbose:
            print("##########################################")

        return self.target_field_angle, self.target_mech_angle

    def do_observation(
        self,
        targtype,
        target=None,
        tracking="auto",
        field_angle="auto",
        obstype="TEST",
        comment="",
        obsmode="SCHEDULE",
        offset="best",
    ):
        """
        A GENERIC OBSERVATION FUNCTION

        INPUTS:
            targtype: description of the observation type. can be any ONE of:
                'schedule'  : observes whatever the current observation in the schedule queue is
                                - exposure time and other parameters are set according to the current obs from the schedule file

                'altaz'     : observes the specified target = (alt_degs, az_degs):
                                - exposure time is NOT set, whatever the current time is set to is used
                                - tracking is turned on by default
                                - if tracking is on, field angle is set to config['telescope']['rotator_field_angle_zeropoint']
                'radec'     : observes the specified target = (ra_j2000_hours, dec_j2000_deg)
                                - exposure time is NOT set, whatever the current time is set to is used
                                - tracking is turned on by default
                                - if tracking is on, field angle is set to config['telescope']['rotator_field_angle_zeropoint']

            in all cases a check is done to make sure that:
                - it is okay to observe (eg dome/weather/sun/etc status)
                - there are no ephemeris bodies (from the tracked list) within the field of view margins

        """
        # the observation has not been completed
        self.observation_completed = False

        # tag the context for any error messages
        context = "do_observation"

        self.log(
            f"doing observation: targtype = {targtype}, target = {target}, tracking = {tracking}, field_angle = {field_angle}"
        )
        print(f"do_observation running in thread: {threading.get_ident()}")
        #### FIRST MAKE SURE IT'S OKAY TO OBSERVE ###
        self.check_ok_to_observe(logcheck=True)
        self.logger.info(
            f"self.running = {self.running}, self.ok_to_observe = {self.ok_to_observe}"
        )

        # TODO Uncomment this, for now it's commented out so that we can test with the dome closed
        # NPL 7-28-21

        if self.ok_to_observe:
            pass
        else:

            return

        # set the obsmode
        self.obsmode = obsmode.upper()

        # if observation mode is manual, reset all the header values
        if self.obsmode == "MANUAL":
            self.resetObsValues()

        ### Validate the observation ###
        # just make it lowercase to avoid any case issues
        targtype = targtype.lower()
        # set the target type
        self.targtype = targtype

        # set the obstype
        self.obstype = obstype

        # update the observation type: DO THIS THRU ROBO OPERATOR SO WE'RE SURE IT'S SET
        # self.doTry(f'robo_set_obstype {obstype}', context = context, system = '')

        # update the qcomment
        if comment != "":
            self.doTry(f"robo_set_qcomment {comment}")

        # first do some quality checks on the request
        # observation type
        # allowed_obstypes = ['schedule', 'altaz', 'radec']
        # for now only allow altaz, and we'll add on more as we go
        allowed_targtypes = ["altaz", "object", "radec"]

        # raise an exception is the type isn't allwed
        if not (targtype in allowed_targtypes):
            self.log(
                f"improper observation type {targtype}, must be one of {allowed_targtypes}"
            )
            return
        else:
            self.log(f"initiating observation type {targtype}")
        self.log("checking tracking")
        try:
            # raise an exception if tracking isn't a bool or 'auto'
            assert (not type(tracking) is bool) or (
                tracking.lower() != "auto"
            ), f'tracking option must be bool or "auto", got {tracking}'

            self.log("checking field_angle")
            # raise an exception if field_angle isn't a float or 'auto'
            assert (not type(field_angle) is float) or (
                field_angle.lower() != "auto"
            ), f'field_angle option must be float or "auto", got {field_angle}'
        except Exception as e:
            self.log(f"Problem while vetting observation: {e}")

        # now check that the target is appropriate to the observation type
        if targtype == "altaz":
            try:
                # make sure it's a tuple
                assert (
                    type(target) is tuple
                ), f"for {targtype} observation, target must be a tuple. got type = {type(target)}"

                # make sure it's the right length
                assert (
                    len(target) == 2
                ), f"for {targtype} observation, target must have 2 coordinates. got len(target) = {len(target)}"

                # make sure they're floats
                assert (type(target[0]) is float) & (
                    type(target[0]) is float
                ), f"for {targtype} observation, target vars must be floats"
            except Exception as e:
                self.log(f"Problem while vetting observation: {e}")
            # get the target alt and az
            self.target_alt = target[0]
            self.target_az = target[1]
            msg = f"Observing [{obstype}] Target @ (Alt, Az) = {self.target_alt:0.2f}, {self.target_az:0.2f}"
            self.alertHandler.slack_log(msg, group=None)

            self.log(
                f"target: (alt, az) = {self.target_alt:0.2f}, {self.target_az:0.2f}"
            )
            try:
                # calculate the nominal target ra and dec
                alt_object = astropy.coordinates.Angle(self.target_alt * u.deg)
                az_object = astropy.coordinates.Angle(self.target_az * u.deg)
                obstime = astropy.time.Time(datetime.utcnow(), location=self.ephem.site)

                altaz = astropy.coordinates.SkyCoord(
                    alt=alt_object,
                    az=az_object,
                    location=self.ephem.site,
                    obstime=obstime,
                    frame="altaz",
                )
                j2000 = altaz.transform_to("icrs")
                self.target_ra_j2000_hours = j2000.ra.hour
                self.target_dec_j2000_deg = j2000.dec.deg
                ra_deg = j2000.ra.deg
                msg = f"target: (ra, dec) = {self.target_ra_j2000_hours:0.1f}, {self.target_dec_j2000_deg:0.1f}"
                self.log(msg)
            except Exception as e:
                self.log(f"badness getting target nominal ra/dec: {e}")

            if tracking.lower() == "auto":
                tracking = True
            else:
                pass
        elif targtype == "radec":
            try:
                self.log(f"vetting target: {target}, targtype = {targtype}")
                # make sure it's a tuple
                assert (
                    type(target) is tuple
                ), f"for {targtype} observation, target must be a tuple. got type = {type(target)}"

                # make sure it's the right length
                assert (
                    len(target) == 2
                ), f"for {targtype} observation, target must have 2 coordinates. got len(target) = {len(target)}"

                # make sure they're floats
                # self.log(f'Targ[0]: val = {target[0]}, type = {type(target[0])}')
                assert (type(target[0]) is float) & (
                    type(target[1]) is float
                ), f"for {targtype} observation, target vars must be floats"
            except Exception as e:
                self.log(f"Problem while vetting observation: {e}")
            # get the target RA (hours) and DEC (degs)
            self.target_ra_j2000_hours = target[0]
            self.target_dec_j2000_deg = target[1]

            msg = f"Observing [{obstype}] Target @ (RA, DEC) = {self.target_ra_j2000_hours:0.2f}, {self.target_dec_j2000_deg:0.2f}"
            self.alertHandler.slack_log(msg, group=None)

            # j2000_coords = astropy.coordinates.SkyCoord.from_name(obj, frame = 'icrs')
            j2000_ra = self.target_ra_j2000_hours * u.hour
            j2000_dec = self.target_dec_j2000_deg * u.deg
            j2000_coords = astropy.coordinates.SkyCoord(
                ra=j2000_ra, dec=j2000_dec, frame="icrs"
            )

            ra_deg = j2000_coords.ra.deg

            if self.sunsim:
                obstime_mjd = self.ephem.state.get("mjd", 0)
                obstime = astropy.time.Time(
                    obstime_mjd, format="mjd", location=self.ephem.site
                )
            else:
                obstime = astropy.time.Time(datetime.utcnow(), location=self.ephem.site)

            # lat = astropy.coordinates.Angle(self.config['site']['lat'])
            # lon = astropy.coordinates.Angle(self.config['site']['lon'])
            # height = self.config['site']['height'] * u.Unit(self.config['site']['height_units'])
            # site = astropy.coordinates.EarthLocation(lat = lat, lon = lon, height = height)
            frame = astropy.coordinates.AltAz(obstime=obstime, location=self.ephem.site)
            local_coords = j2000_coords.transform_to(frame)
            self.target_alt = local_coords.alt.deg
            self.target_az = local_coords.az.deg

        elif targtype == "object":
            # do some asserts
            # TODO
            self.log(f"handling object observations")
            # set the comment on the fits header
            # self.log(f'setting qcomment to {target}')
            # self.qcomment = target
            self.log(f"setting targetName to {target}")
            self.targetName = target
            # make sure it's a string
            if not (type(target) is str):
                self.log(
                    f"for object observation, target must be a string object name, got type = {type(target)}"
                )
                return

            try:
                obj = target

                j2000_coords = astropy.coordinates.SkyCoord.from_name(obj, frame="icrs")

                self.target_ra_j2000_hours = j2000_coords.ra.hour
                self.target_dec_j2000_deg = j2000_coords.dec.deg
                ra_deg = j2000_coords.ra.deg

                obstime = astropy.time.Time(datetime.utcnow(), location=self.ephem.site)
                lat = astropy.coordinates.Angle(self.config["site"]["lat"])
                lon = astropy.coordinates.Angle(self.config["site"]["lon"])
                height = self.config["site"]["height"] * u.Unit(
                    self.config["site"]["height_units"]
                )

                site = astropy.coordinates.EarthLocation(
                    lat=lat, lon=lon, height=height
                )
                frame = astropy.coordinates.AltAz(obstime=obstime, location=site)
                local_coords = j2000_coords.transform_to(frame)
                self.target_alt = local_coords.alt.deg
                self.target_az = local_coords.az.deg

                msg = f"Doing [{obstype}] observation of {target} @ (RA, DEC) = ({self.target_ra_j2000_hours:0.2f}, {self.target_dec_j2000_deg:0.2f})"
                msg += f", (Alt, Az) = ({self.target_alt:0.2f}, {self.target_az:0.2f})"
                self.alertHandler.slack_log(msg, group=None)

            except Exception as e:
                self.log(f"error getting object coord: {e}")

        else:
            # we shouldn't ever get here because of the upper asserts
            return

        self.log(f"vetting field angle: {field_angle}")
        # handle the field angle
        if field_angle.lower() == "auto":
            # self.target_field_angle = self.config['telescope'] # this is wrong :D will give 155 instead of 65
            self.target_field_angle = self.config["telescope"]["rotator"]["winter"][
                "rotator_field_angle_zeropoint"
            ]
        else:
            self.target_field_angle = field_angle

        self.log("getting correct field angle to stay within rotator limits")

        try:
            """
        
            ####### Check if field angle will violate cable wrap limits
            #                 and adjust as needed.
            # Viraj's field rotation checker 6-11-23
            # allows pointing to north up (preference) or north down
            # handle the field angle
            
            lat = astropy.coordinates.Angle(self.config['site']['lat']).rad
            dec = self.target_dec_j2000_deg * np.pi / 180.0
            lst = obstime.sidereal_time('mean').rad
            hour_angle = lst - ra_deg * np.pi / 180.0
            if (hour_angle < -1 * np.pi):
                hour_angle += 2 * np.pi
            if (hour_angle > np.pi):
                hour_angle -= 2 * np.pi
    
            parallactic_angle = np.arctan2(np.sin(hour_angle), \
                                           np.tan(lat) * np.cos(dec) - \
                                           np.sin(dec) * np.cos(hour_angle)) * \
                                180 / np.pi
    
            
    
    
            possible_target_field_angles = [self.target_field_angle,
                                            self.target_field_angle - 360.0,
                                            self.target_field_angle + 360.0,
                                            self.target_field_angle - 180.0,
                                            self.target_field_angle + 180.0]
            
            self.log(f'possible target field angles = {possible_target_field_angles}')
            
            # NPL updated this formula, there was a bug here that's been around for a while.
            # copied the formula from Kevin Ivarsen's (Planewave) predict_pw1000_rotator_mech.py
            # script:
                # mech_degs = target_field_angle_degs - status.mount.altitude_degs - status.mount.field_angle_at_target_degs
    
            possible_target_mech_angles = [(target_field_angle - parallactic_angle -self.target_alt) 
                                          for target_field_angle in possible_target_field_angles]
            
            self.log(f'possible target mech angles = {possible_target_mech_angles}')
            
            messages = ["No rotator wrap predicted",
                        "Rotator wrapping < min, adjusting by -360 deg.",
                        "Rotator wrapping > max, adjusting by +360 deg.",
                        "Rotator wrapping < min, adjusting by -180 deg.",
                        "Rotator wrapping > max, adjusting by +180 deg.",
                        ]
    
            self.log("##########################################")
            for ind, possible_target_mech_angle in enumerate(possible_target_mech_angles):
                if self.is_rotator_mech_angle_possible(
                        predicted_rotator_mechangle=possible_target_mech_angle,
                        rotator_min_degs=self.config['telescope']['rotator'][self.camname][
                            'rotator_min_degs'],
                        rotator_max_degs=self.config['telescope']['rotator'][self.camname][
                            'rotator_max_degs']):
                    self.target_mech_angle = possible_target_mech_angle
                    self.target_field_angle = possible_target_field_angles[ind]
                    self.log(messages[ind])
                    self.log(f"Adjusted field angle --> {self.target_field_angle}")
                    self.log(f"New target mech angle = {self.target_mech_angle}")
                    break
            self.log("##########################################")
            """

            self.target_field_angle, self.target_mech_angle = (
                self.get_safe_rotator_angle(
                    ra_hours=self.target_ra_j2000_hours,
                    dec_deg=self.target_dec_j2000_deg,
                    target_field_angle=self.target_field_angle,
                    obstime=obstime,
                    verbose=True,
                )
            )

        except Exception as e:
            self.log(f"error calculating field and mechanical angles: {e}")

        # adjust the pointing center based on the offset
        self.log(
            f"calculating the new coordinates to center the field with offset type: {offset}"
        )
        try:
            # pass self.target_field_angle, the one that it chooses, and pass that to PA in the get_center_offset_coords function
            self.target_ra_j2000_hours, self.target_dec_j2000_deg = (
                self.get_center_offset_coords(
                    ra_hours=self.target_ra_j2000_hours,
                    dec_deg=self.target_dec_j2000_deg,
                    pa=self.target_field_angle
                    - self.config["telescope"]["rotator"]["winter"][
                        "rotator_field_angle_zeropoint"
                    ],
                    offsettype=offset,
                )
            )
        except Exception as e:
            self.log(f"error calculating new pointing center offset: {e}")
            return

        """
        # Rob's original version based on Viraj's memo
        if (True):
            lat = astropy.coordinates.Angle(self.config['site']['lat']).rad
            dec = self.target_dec_j2000_deg*np.pi/180.0
            lst = obstime.sidereal_time('mean').rad
            hour_angle = lst - ra_deg*np.pi/180.0
            if (hour_angle < -1*np.pi):
                hour_angle += 2 * np.pi
            if (hour_angle > np.pi):
                hour_angle -= 2 * np.pi

            parallactic_angle = np.arctan2(np.sin(hour_angle), \
                                         np.tan(lat)*np.cos(dec)- \
                                         np.sin(dec)*np.cos(hour_angle)) * \
                                         180 / np.pi
            
            predicted_rotator_mechangle = self.config['telescope']['rotator_field_angle_zeropoint'] - parallactic_angle + self.target_alt
            
            print("\n##########################################")
            print("Predicted rotator angle: {} degrees".format(predicted_rotator_mechangle))
            if (predicted_rotator_mechangle > \
                self.config['telescope']['rotator'][self.camname]['rotator_min_degs'] \
                and predicted_rotator_mechangle < \
                self.config['telescope']['rotator'][self.camname]['rotator_max_degs']):
                print("No rotator wrap predicted")
                self.target_mech_angle = predicted_rotator_mechangle
                
            if (predicted_rotator_mechangle < \
                self.config['telescope']['rotator'][self.camname]['rotator_min_degs']):
                print("Rotator wrapping < min, adjusting")
                self.target_field_angle -= 360.0
                self.target_mech_angle = predicted_rotator_mechangle + 360.0
                print(f"Adjusted field angle --> {self.target_field_angle}")
                print(f"New target mech angle = {self.target_mech_angle}")
                
            if (predicted_rotator_mechangle > \
                self.config['telescope']['rotator'][self.camname]['rotator_max_degs']):
                print("Rotator wrapping > max, adjusting")
                # Changed line below from + to -= as a test...RAS
                self.target_field_angle -= 360.0
                self.target_mech_angle = predicted_rotator_mechangle - 360.0
                print(f"Adjusted field angle --> {self.target_field_angle}")
                print(f"New target mech angle = {self.target_mech_angle}")
            # Check!

            # self.state['rotator_mech_position']
            # self.state['rotator_field_angle']
            
            # print("\nlatitude: {}".format(lat))
            # print("ra,dec: {},{}".format(ra_deg*np.pi/180.0,dec))
            # print("lst: {}".format(lst))
            # print("HA: {}".format(hour_angle))
            # print("Par. Angle: {}".format(parallactic_angle))

                
            print("##########################################")
            
            ###########################################

        """

        #### Validate the observation ###
        # check if alt and az are in allowed ranges
        not_too_low = self.target_alt >= self.config["telescope"]["min_alt"]
        not_too_high = self.target_alt <= self.config["telescope"]["max_alt"]
        in_view = not_too_low & not_too_high

        if in_view:
            pass
        else:
            if not not_too_low:
                reason = f"(TOO LOW, Target Alt {self.target_alt:0.1f} < Min Allowed Alt {self.config['telescope']['min_alt']:0.1f})"
            elif not not_too_high:
                reason = f"(TOO HIGH, Target Alt {self.target_alt:0.1f} > Max Allowed Alt {self.config['telescope']['max_alt']:0.1f})"
            else:
                reason = f"(unknown reason??)"
            msg = f">> do_observation: target not within view! {reason} skipping..."
            print(msg)
            self.log(msg)
            self.alertHandler.slack_log(msg, group=None)
            self.target_ok = False
            # raise TypeError(msg)#TargetError(msg)
            raise TimeoutError(msg)
            print("I got below the exeption... this is bad :(")
            # return

        # now check if the target alt and az are too near the tracked ephemeris bodies
        # first check if any ephemeris bodies are near the target
        self.log("checking that target is not too close to ephemeris bodies")
        ephem_inview = self.ephemInViewTarget_AltAz(
            target_alt=self.target_alt, target_az=self.target_az
        )

        if not ephem_inview:
            self.log("ephem check okay: no ephemeris bodies in the field of view.")

            pass
        else:
            msg = f">> ephemeris body is too close to target! skipping..."
            self.log(msg)
            self.alertHandler.slack_log(msg, group=None)
            self.target_ok = False
            raise TargetError(msg)
            # return

        # if we get here the target is okay
        self.target_ok = True

        ### SLEW THE DOME ###
        # start with the dome because it can take forever

        system = "dome"
        try:
            # turn off dome tracking while slewing
            self.do("dome_tracking_off")

            self.do(f"dome_goto {self.target_az}")

            # NPL 8-16-23 commented out this sleep! why is it here!!??
            # time.sleep(5)

            # turn tracking back on
            # self.do('dome_tracking_on')

        except Exception as e:
            msg = f"roboOperator: could not set up {system} due to {e.__class__.__name__}, {e}"
            self.log(msg)
            err = roboError(context, self.lastcmd, system, msg)
            self.hardware_error.emit(err)
            self.target_ok = False
            return

        ### SLEW THE TELESCOPE ###
        # start with the dome because it can take forever

        system = "telescope"
        try:

            if targtype == "altaz":
                # slew to the requested alt/az
                self.do(f"mount_goto_alt_az {self.target_alt} {self.target_az}")

            elif targtype in ["radec", "object"]:
                # slew to the requested ra/dec
                self.logger.info(
                    f"robo: mount_goto_ra_dec_j2000 running in thread {threading.get_ident()}"
                )
                self.do(
                    f"mount_goto_ra_dec_j2000 {self.target_ra_j2000_hours} {self.target_dec_j2000_deg}"
                )

            # NPL 6-11-23 moved the tracking on call to after the rotator move

            # slew the rotator
            if not self.mountsim:
                self.do(f"rotator_goto_field {self.target_field_angle}")

                # TODO: remove when we know how to run the winter rotator
                # NPL 6-11-23
                # rotator_home_pos = self.config['telescope']['rotator'][self.camname]['rotator_home_degs']
                # self.do(f'rotator_goto_mech {rotator_home_pos}')
                # self.do(f'rotator_goto_mech {self.target_mech_angle}')

                # TODO: NPL 5/23/23 wtf is this 3 second sleep doing here??
                # time.sleep(3)

            self.current_mech_angle = self.target_mech_angle

            # turn on tracking
            if tracking:
                self.do(f"mount_tracking_on")

        except Exception as e:
            msg = f"roboOperator: could not set up {system} due to {e.__class__.__name__}, {e}"
            self.log(msg)
            err = roboError(context, self.lastcmd, system, msg)
            self.hardware_error.emit(err)
            self.target_ok = False
            return

        ### TURN DOME TRACKING BACK ON ###

        system = "dome"
        try:
            # turn tracking back on
            self.do("dome_tracking_on")

        except Exception as e:
            msg = f"roboOperator: could not set up {system} due to {e.__class__.__name__}, {e}"
            self.log(msg)
            err = roboError(context, self.lastcmd, system, msg)
            self.hardware_error.emit(err)
            self.target_ok = False
            return

        ### DO THE EXPOSURE ###

        # 2: create the log dictionary & FITS header. save log dict to self.lastObs_record
        # for now this is happeningin the ccd_daemon, but we need to make this better
        # and get the info from the database, etc

        # 3: trigger image acquisition

        # do the exposure and wrap with appropriate error handling
        system = "camera"
        self.logger.info(f"robo: telling camera to take exposure!")

        # pass the correct options to the ccd daemon
        obstype_dict = dict(
            {
                "FLAT": "-f",
                "BIAS": "-b",
                "DARK": "-d",
                "POINTING": "-p",
                "SCIENCE": "-s",
                "TEST": "-t",
                "FOCUS": "-foc",
            }
        )

        obstype_option = obstype_dict.get(obstype, "")
        self.log(f"updating self.obstype to {obstype}")
        self.obstype = obstype
        self.log(f"updating state")
        self.update_state()

        try:
            self.do(f"doExposure {obstype_option} --{self.camname}")

        except Exception as e:
            tb = traceback.format_exc()
            msg = f"roboOperator: could not set up {system} due to {e.__class__.__name__}, {e}"  #', traceback: {tb}'
            self.log(msg)
            err = roboError(context, self.lastcmd, system, msg)
            self.hardware_error.emit(err)
            self.target_ok = False
            raise Exception(msg)
            return

        # if we get to here then we have successfully saved the image
        self.log(f"exposure complete!")

        if self.camname in ["summer"]:
            # make a jpg of the last image and publish it to slack!
            postImage_process = subprocess.Popen(args=["python", "plotLastImg.py"])

        # the observation has been completed successfully :D
        self.observation_completed = True

    def remakePointingModel(self, append=False, firstpoint=0):
        context = "Pointing Model"
        self.alertHandler.slack_log("Setting Up a New Pointing Model!", group=None)
        if append:
            # if in append mode, don't clear the old points
            pass
        else:
            # clear the current pointing model
            self.do("mount_model_clear_points")

        time.sleep(2)

        # load up the points
        pointlist_filepath = os.path.join(
            os.getenv("HOME"),
            self.config["pointing_model"]["default_pointlist"],
        )
        self.pointingModelBuilder.load_point_list(pointlist_filepath)

        # now go through the list one by one, and observe each point!
        altaz_mapped = []
        radec_mapped = []
        # how many points are there to do?
        npoints = len(self.pointingModelBuilder.altaz_points)

        # make a list of all the points to step through
        indices = np.arange(firstpoint - 1, npoints, 1)

        # randomly shuffle the indices so that we slowly fill out a full model in random order
        np.random.shuffle(indices)

        for i in indices:
            altaz_point = self.pointingModelBuilder.altaz_points[i]
            target_alt = altaz_point[0]
            target_az = altaz_point[1]

            self.alertHandler.slack_log(f"Target {i+1}/{npoints}:")

            system = "Observe and Platesolve"
            try:

                # do the observation
                # self.do(f'robo_observe_altaz {target_alt} {target_az}')
                self.do(
                    f"robo_observe altaz {target_alt} {target_az} --pointing --calibration"
                )

                if self.target_ok:

                    # time.sleep(10)
                    # ADD A CASE TO HANDLE SITUATIONS WHERE THE OBSERVATION DOESN'T WORK

                    # platesolve the image
                    # TODO: fill this in from the config instead of hard coding
                    lastimagefile = os.readlink(
                        os.path.join(os.getenv("HOME"), "data", "last_image.lnk")
                    )
                    # lastimagefile = os.path.join(os.getenv("HOME"), 'data','images','20210730','SUMMER_20210730_043149_Camera0.fits')

                    # check if file exists
                    imgpath = pathlib.Path(lastimagefile)
                    timeout = 20
                    dt = 0.5
                    t_elapsed = 0
                    self.log(f"waiting for image path {lastimagefile}")
                    while t_elapsed < timeout:

                        file_exists = imgpath.is_file()
                        self.log(f"Last Image File Exists? {file_exists}")
                        if file_exists:
                            break
                        else:
                            time.sleep(dt)
                            t_elapsed += dt

                    msg = f"running platesolve on image: {lastimagefile}"
                    self.log(msg)
                    print(msg)
                    solved = self.pointingModelBuilder.plateSolver.platesolve(
                        lastimagefile, 0.47
                    )
                    if solved:
                        ra_j2000_hours = (
                            self.pointingModelBuilder.plateSolver.results.get(
                                "ra_j2000_hours"
                            )
                        )
                        dec_j2000_degrees = (
                            self.pointingModelBuilder.plateSolver.results.get(
                                "dec_j2000_degrees"
                            )
                        )
                        platescale = self.pointingModelBuilder.plateSolver.results.get(
                            "arcsec_per_pixel"
                        )
                        field_angle = self.pointingModelBuilder.plateSolver.results.get(
                            "rot_angle_degs"
                        )

                        ra_j2000 = astropy.coordinates.Angle(ra_j2000_hours * u.hour)
                        dec_j2000 = astropy.coordinates.Angle(dec_j2000_degrees * u.deg)

                        ######################################################################
                        ### RUN IN SIMULATION MODE ###
                        # Get the nominal RA/DEC from the fits header. Could do this different ways.
                        # TODO: is this the approach we want? should it calculate it from the current position instead?
                        hdu_list = fits.open(lastimagefile, ignore_missing_end=True)
                        header = hdu_list[0].header

                        ra_j2000_nom = astropy.coordinates.Angle(
                            header["RA"], unit="deg"
                        )
                        dec_j2000_nom = astropy.coordinates.Angle(
                            header["DEC"], unit="deg"
                        )
                        ######################################################################""

                        self.log("RUNNING PLATESOLVE ON LAST IMAGE")
                        self.log(
                            f'Platesolve Astrometry Solution: RA = {ra_j2000.to_string("hour")}, DEC = {dec_j2000.to_string("deg")}'
                        )
                        self.log(
                            f'Nominal Position:               RA = {ra_j2000_nom.to_string("hour")}, DEC = {dec_j2000_nom.to_string("deg")}'
                        )
                        self.log(
                            f"Platesolve:     Platescale = {platescale:.4f} arcsec/pix, Field Angle = {field_angle:.4f} deg"
                        )
                        """
                        #TODO: REMOVE THIS
                        # overwrite the solution with the nominal values so we can actually get a model
                        ra_j2000_hours = self.target_ra_j2000_hours
                        dec_j2000_degrees = self.target_dec_j2000_deg
                        """
                        msg = f"Adding model point (alt, az) = ({self.target_alt:0.1f}, {self.target_az:0.1f}) --> (ra, dec) = ({ra_j2000_hours:0.2f}, {dec_j2000_degrees:0.2f}), Nominal (ra, dec) = ({ra_j2000_nom.hour:0.2f}, {dec_j2000_nom.deg:0.2f})"
                        self.alertHandler.slack_log(msg, group=None)
                        # add the RA_hours and DEC_deg point to the telescope pointing model
                        self.doTry(
                            f"mount_model_add_point {ra_j2000_hours} {dec_j2000_degrees}"
                        )

                        radec_mapped.append((ra_j2000_hours, dec_j2000_degrees))
                        altaz_mapped.append((self.target_alt, self.target_az))
                    else:
                        msg = f"> platesolve could not find a solution :( "
                        self.log(msg)
                        self.alertHandler.slack_log(msg)

            except Exception as e:
                msg = f"roboOperator: could not set up {system} due to {e.__class__.__name__}, {e}"
                self.log(msg)
                err = roboError(context, self.lastcmd, system, msg)
                self.hardware_error.emit(err)
                # return

        self.log(f"finished getting all the new points!")
        self.log(f"saving points")
        self.savePointingModePoints(altaz_tuple=altaz_mapped, radec_tuple=radec_mapped)

    def savePointingModePoints(self, altaz_tuple, radec_tuple, filename=""):
        if filename == "":
            outfile = os.path.join(
                os.getenv("HOME"), "data", "current_pointing_model_points.txt"
            )
        else:
            outfile = filename

        altlist, azlist = zip(*altaz_tuple)
        ralist, declist = zip(*radec_tuple)

        out = np.column_stack((altlist, azlist, ralist, declist))

        np.savetxt(
            outfile,
            out,
            delimiter="\t",
            comments="# ",
            header="Alt (deg) Az (deg) RA (hour) DEC (deg)",
        )

    def ephemInViewTarget_AltAz(
        self, target_alt, target_az, obstime="now", time_format="datetime"
    ):
        # check if any of the ephemeris bodies are too close to the given target alt/az
        inview = list()
        for body in self.config["ephem"]["min_target_separation"]:
            mindist = self.config["ephem"]["min_target_separation"][body]
            dist = ephem_utils.getTargetEphemDist_AltAz(
                target_alt=target_alt,
                target_az=target_az,
                body=body,
                location=self.ephem.site,
                obstime=obstime,
                time_format=time_format,
            )
            if dist < mindist:
                inview.append(True)
            else:
                inview.append(False)

        if any(inview):
            return True
        else:
            return False

    def startupWINTERCamera(self):
        """
        This is a method which starts up the WINTER cameara is online,
        and healthy. If all daemons are connected it will take a bias image
        """
        pass

    def checkWINTERCamera(self):
        """
        Takes a bias image with WINTER, then checks if it is okay

        returns status, bad_chans, where badchans is a list of bad channels
        """

        bias_ok = False
        bad_chans = []

        context = "checkWINTERCameraBias"

        # take a bias image
        system = "camera"
        try:
            # set exposure time to zero
            self.do("setExposure 0.0")

            # take an image
            self.do("doExposure -b")

        except Exception as e:
            msg = f"roboOperator: could not set up {system} due to {e.__class__.__name__}, {e}"
            self.log(msg)
            err = roboError(context, self.lastcmd, system, msg)
            self.hardware_error.emit(err)
            self.target_ok = False
            return False, []

        # ask the WINTER image daemon if the image is okay
        system = "WINTER Image Daemon"
        try:

            image_directory, image_filename = self.camera.getLastImagePath()
            # remember that it doesn't return the _mef.fits part of the filename!
            image_filepath = os.path.join(image_directory, image_filename + "_mef.fits")
        except Exception as e:
            msg = f"roboOperator: could not get last image filename from {system} due to {e.__class__.__name__}, {e}"
            self.log(msg)
            err = roboError(context, self.lastcmd, system, msg)
            self.hardware_error.emit(err)
            self.target_ok = False
            return False, []

        try:
            results = self.imghandlerdict["winter"].validate_bias(image_filepath)
            """
            Note: the results are a dictionary with these entries for 
            each addr (eg, sa, sb, sc, ... , pc)
                results = { 'sa' : {'okay' : False,
                                    'mean' : 0.15,
                                    'std'  : 0.01,
                                    },
                            etc...
                           }
            """
            self.log(f"bias validation results: {results}")
            bad_chans = results["bad_chans"]
            if len(bad_chans):
                bias_ok = True
            all_addrs = results["bad_chans"] + results["good_chans"]
            # update the record of the validation status with the camera daemon
            for addr in all_addrs:
                self.log(
                    f" updating sensor addr = {addr}, results[addr] = {results[addr]}"
                )
                self.do(f'updateSensorValidation {results[addr]["okay"]} -n {addr}')
                # self.camdict['winter'].updateStartupValidation(results[addr]['okay'], addrs = addr)

            return bias_ok, bad_chans

        except Exception as e:
            msg = f"roboOperator: could not update sensor validation on {system} due to {e.__class__.__name__}, {e}"
            self.log(msg)
            err = roboError(context, self.lastcmd, system, msg)
            self.log(traceback.format_exc())
            self.hardware_error.emit(err)
            self.target_ok = False
            return False, []
