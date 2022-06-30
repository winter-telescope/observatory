#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Apr 27 22:56:08 2021

operator.py

@author: nlourie
"""


import os
import numpy as np
import sys
from datetime import datetime
from PyQt5 import QtCore
import time
#import json
import logging
import threading
import astropy.time
import astropy.coordinates
import astropy.units as u
from astropy.io import fits
import pathlib
import subprocess
import pandas as pd
import traceback
import glob
import pytz
import pandas as pd
import sqlalchemy as db

import wintertoo.validate

# add the wsp directory to the PATH
wsp_path = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(1, wsp_path)

from utils import utils
from schedule import schedule
from schedule import ObsWriter
from ephem import ephem_utils
from telescope import pointingModelBuilder
from housekeeping import data_handler
from focuser import focusing
from focuser import focus_tracker
from viscam import summerRebootTracker

class TargetError(Exception):
    pass

class TimerThread(QtCore.QThread):
    '''
    This is a thread that just counts up the timeout and then emits a 
    timeout signal. It will be connected to the worker thread so that it can
    run a separate thread that times each worker thread's execution
    '''
    timerTimeout = QtCore.pyqtSignal()
    
    def __init__(self, timeout, *args, **kwargs):
        super(TimerThread, self).__init__()
        print('created a timer thread')
        # Set up the timeout. Convert seconds to ms
        self.timeout = timeout*1000.0
    
        
    def run(self):
        def printTimeoutMessage():
            print(f'timer thread: timeout happened')
        print(f'running timer in thread {threading.get_ident()}')
        # run a single shot QTimer that emits the timerTimeout signal when complete
        self.timer= QtCore.QTimer()
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
    
    def __init__(self, base_directory, config, mode, state, wintercmd, logger, alertHandler, schedule, telescope, dome, chiller, ephem, viscam, ccd, mirror_cover, robostate, sunsim, dometest):
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
        self.ephem = ephem
        self.viscam = viscam
        self.ccd = ccd
        self.mirror_cover = mirror_cover
        self.robostate = robostate
        self.sunsim = sunsim
        self.dometest = dometest
    
    def run(self):           
        self.robo = RoboOperator(base_directory = self.base_directory, 
                                     config = self.config, 
                                     mode = self.mode,
                                     state = self.state, 
                                     wintercmd = self.wintercmd,
                                     logger = self.logger,
                                     alertHandler = self.alertHandler,
                                     schedule = self.schedule,
                                     telescope = self.telescope, 
                                     dome = self.dome, 
                                     chiller = self.chiller, 
                                     ephem = self.ephem,
                                     viscam = self.viscam,
                                     ccd = self.ccd,
                                     mirror_cover = self.mirror_cover,
                                     robostate = self.robostate,
                                     sunsim = self.sunsim,
                                     dometest = self.dometest
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

    

    def __init__(self, base_directory, config, mode, state, wintercmd, logger, alertHandler, schedule, telescope, dome, chiller, ephem, viscam, ccd, mirror_cover, robostate, sunsim, dometest):
        super(RoboOperator, self).__init__()
        
        self.base_directory = base_directory
        self.config = config
        self.mode = mode
        self.state = state
        self.wintercmd = wintercmd
        # assign self to wintercmd so that wintercmd has access to the signals
        self.wintercmd.roboOperator = self
        self.alertHandler = alertHandler
        # set up the hardware systems
        self.telescope = telescope
        self.dome = dome
        self.chiller = chiller
        self.logger = logger
        self.alertHandler = alertHandler
        self.ephem = ephem
        self.schedule = schedule
        self.viscam = viscam
        self.ccd = ccd
        self.mirror_cover = mirror_cover
        self.robostate = robostate
        self.sunsim = sunsim
        self.dometest = dometest
        
        # for now just trying to start leaving places in the code to swap between winter and summer
        self.cam = 'summer'
        
        ### FOCUS LOOP THINGS ###
        self.focusTracker = focus_tracker.FocusTracker(self.config, logger = self.logger)
        # a variable to keep track of how many times we've attempted to focus. different numbers have different affects on focus routine
        self.focus_attempt_number = 0
        
        ### A class to keep track of how often buggy systems have been rebooted
        self.SUMMERrebootTracker = summerRebootTracker.SUMMERrebootTracker(self.config)
        
        
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
    
        # a flag to indicate we're in a daylight test mode which will spoof some observations and trigger
        ## off of schedule alt/az rather than ra/dec
        #NPL 1-12-21: making it so that if we are in dometest or sunsim mode that we turn on test_mode
        if self.sunsim or self.dometest:
            self.test_mode = True
        else:
            self.test_mode = False
        
        # a flag to denote whether an observation (eg, roboOperator.do_observation) was completed successfully
        self.observation_completed = False
        
        
        # a flag to denote whether the observatory (ie telescope and dome) are ready to observe, not including whether dome is open
        self.observatory_ready = False
        # a similar flag to denote whether the observatory is safely stowed
        self.observatory_stowed = False
        
        
        ### SET UP THE WRITER ###
        # init the database writer
        writerpath = self.config['obslog_directory'] + '/' + self.config['obslog_database_name']
        #self.writer = ObsWriter.ObsWriter('WINTER_ObsLog', self.base_directory, config = self.config, logger = self.logger) #the ObsWriter initialization
        self.writer = ObsWriter.ObsWriter(writerpath, self.base_directory, config = self.config, logger = self.logger) #the ObsWriter initialization
        # create an empty dict that will hold the data that will get written out to the fits header and the log db
        self.data_to_log = dict()
        
        ### SCHEDULE ATTRIBUTES ###
        # load the dither list
        self.default_ditherfile_path = os.path.join(self.base_directory, self.config['dither_file'])
        self.default_dither_ra_arcsec, self.default_dither_dec_arcsec = np.loadtxt(self.default_ditherfile_path, unpack = True)
        # hold a variable to track remaining dithers in kst
        self.remaining_dithers = 0 
        
        
        
        # create exposure timer to wait for exposure to finish
        self.waiting_for_exposure = False
        self.exptimer = QtCore.QTimer()
        self.exptimer.setSingleShot(True)
        # if there's too many things i think they may not all get triggered?
        #self.exptimer.timeout.connect(self.log_timer_finished)
        #self.exptimer.timeout.connect(self.log_observation_and_gotoNext)
        #self.exptimer.timeout.connect(self.rotator_stop_and_reset)
        
        # when the image is saved, log the observation and go to the next
        #### FIX THIS SOON! NPL 6-13-21
        #self.ccd.imageSaved.connect(self.log_observation_and_gotoNext)
        
        
        ### a QTimer for handling the cadance of checking what to do
        self.checktimer = QtCore.QTimer()
        self.checktimer.setSingleShot(True)
        self.checktimer.setInterval(30*1000)
        self.checktimer.timeout.connect(self.checkWhatToDo)
        
        ### a QTimer for handling a longer pause before checking what to do
        self.waitAndCheckTimer = QtCore.QTimer()
        self.waitAndCheckTimer.setSingleShot(True)
        self.waitAndCheckTimer.timeout.connect(self.checkWhatToDo)
        
        
        ### Some methods which will log things we pass to the fits header info
        self.operator = self.config.get('fits_header',{}).get('default_operator','')
        self.programPI = ''
        self.programID = 0
        self.qcomment = ''
        self.targtype = ''
        self.targname = ''
        
        
        
        ### CONNECT SIGNALS AND SLOTS ###
        self.startRoboSignal.connect(self.restart_robo)
        self.stopRoboSignal.connect(self.stop)
        #TODO: is this right (above)? NPL 4-30-21
        
        self.hardware_error.connect(self.broadcast_hardware_error)
        
        self.telescope.signals.wrapWarning.connect(self.handle_wrap_warning)
        # change schedule. for now commenting out bc i think its handled in the robo Thread def
        #self.changeSchedule.connect(self.change_schedule)
        
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
        #self.surveySchedule = schedule.Schedule(base_directory = self.base_directory, config = self.config, logger = self.logger)
        
        #self.lastSeen = -1
        self.obsHistID = -1
        ## in robotic mode, the schedule file is the nightly schedule
        if self.mode == 'r':
            self.survey_schedulefile_name = 'nightly'
        ## in manual mode, the schedule file is set to None
        else:
            self.survey_schedulefile_name = None
            
        # set up the schedule
        ## after this point we should have something in self.schedule.currentObs
        self.schedule.loadSchedule(self.survey_schedulefile_name, postPlot = True)
        
        
        ### SET UP POINTING MODEL BUILDER ###
        self.pointingModelBuilder = pointingModelBuilder.PointingModelBuilder()
        
        
        # set up poll status thread
        self.updateThread = data_handler.daq_loop(func = self.update_state, 
                                                       dt = 1000,
                                                       name = 'robo_status_update'
                                                       )
        
        
    def broadcast_hardware_error(self, error):
        msg = f':redsiren: *{error.system.upper()} ERROR* ocurred when attempting command: *_{error.cmd}_*, {error.msg}'
        group = 'operator'
        self.alertHandler.slack_log(msg, group = group)
        
        # turn off tracking
        self.rotator_stop_and_reset()
    
    def waitAndCheck(self, seconds):
        """
        start a QTimer to wait the specified number of seconds, and then
        trigger roboOperator to execute self.CheckWhatToDo()
        """
        
        ms = int(seconds*1000.0)
        
        self.waitAndCheckTimer.setInterval(ms)
        
        self.waitAndCheckTimer.start()
    
    
    def announce(self, msg):
        self.log(f'robo: {msg}')
        self.alertHandler.slack_log(msg, group = None)
    
    def doCommand(self, cmd_obj):
        """
        This is connected to the newCommand signal. It parses the command and
        then executes the corresponding command from the list below

        using this as a reference: (source: https://stackoverflow.com/questions/6321940/how-to-launch-getattr-function-in-python-with-additional-parameters)     
        
        """
        #print(f'dome: caught doCommand signal: {cmd_obj.cmd}')
        cmd = cmd_obj.cmd
        args = cmd_obj.args
        kwargs = cmd_obj.kwargs
        
        try:
            getattr(self, cmd)(*args, **kwargs)
        except:
            pass
    
    
    def update_state(self):
        self.get_observatory_ready_status()
        self.get_observatory_stowed_status()
        fields = ['ok_to_observe', 
                  'target_alt', 
                  'target_az',
                  'target_ra_j2000_hours',
                  'target_dec_j2000_deg',
                  #'lastSeen',
                  'obsHistID',
                  'priority',
                  'operator',
                  'obstype',     
                  'programPI',
                  'programID',
                  'progName',
                  'qcomment',
                  'targtype',
                  'targName',
                  'maxAirmass',
                  'ditherNumber',
                  'ditherStepSize',
                  'fieldID',
                  'observatory_stowed',
                  'observatory_ready',
                  ]

        for field in fields:
            try:
                val = getattr(self, field)
                #if type(val) is bool:
                #    val = int(val)
                self.robostate.update({field : val})
            except Exception as e:
                #print(f'error: {e}')
                pass
         
        #print(json.dumps(self.robostate, indent = 2))
            
    
    def rotator_stop_and_reset(self):
        self.log(f'stopping rotator and resetting to home position')
        # if the rotator is on do this:
        if self.state['rotator_is_enabled']:
            # turn off tracking
            self.doTry('mount_tracking_off')
            self.doTry('rotator_home')
            # turn on wrap check again
            self.doTry('rotator_wrap_check_enable')
        
    def handle_wrap_warning(self, angle):
        
        # create a notification
        msg = f'*WRAP WARNING!!* rotator angle {angle} outside allowed range [{self.config["telescope"]["rotator_min_degs"]},{self.config["telescope"]["rotator_max_degs"]}])'       
        context = ''
        system = 'rotator'
        cmd = self.lastcmd
        """
        err = roboError(context, cmd, system, msg)
        # directly broadcast the error rather than use an event to keep it all within this event
        self.broadcast_hardware_error(err)
        self.log(msg)
        """
        msg = f':redsiren: *{system.upper()} ERROR* ocurred when attempting command: *_{cmd}_*, {msg}'
        group = 'operator'
        self.alertHandler.slack_log(msg, group = group)
        
        # STOP THE ROTATOR
        self.rotator_stop_and_reset()
        
        # got to the next observation
        #self.gotoNext()
        self.checkWhatToDo()
        
    def updateOperator(self, operator_name):
        if type(operator_name) is str:
            self.operator = operator_name
            self.log(f'updating current operator to: {operator_name}')
        else:
            self.log(f'specified operator {operator_name} is not a valid string! doing nothing.')
    
    def updateObsType(self, obstype):
        if type(obstype) is str:
            self.obstype = obstype
            self.log(f'updating current obstype to: {obstype}')
        else:
            self.log(f'specified obstype {obstype} is not a valid string! doing nothing.')
    
    def updateQComment(self, qcomment):
        if type(qcomment) is str:
            self.qcomment = qcomment
            self.log(f'updating current qcomment to: {qcomment}')
        else:
            self.log(f'specified obstype {qcomment} is not a valid string! doing nothing.')
    
    def restart_robo(self, arg = 'auto'):
        # run through the whole routine. if something isn't ready, then it waits a short period and restarts
        # if we get passed test mode, or have already started in test mode, then turn on sun_override
        if arg == 'test' or self.test_mode == True:
            # we're in test mode. turn on the sun override
            self.sun_override = True
            self.test_mode = True
            
        else:
            self.sun_override = False
            self.test_mode = False
        
        # if we're in this loop, the robotic schedule operator is running:
        self.running = True
        
        self.checkWhatToDo()
    
    def get_dome_status(self, logcheck = False):
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
        if self.dome.ok_to_open:
            #self.logger.info(f'robo: the dome says it is okay to open.')# sending open command.')
            return True
        elif self.dome_override:
            if logcheck:
                self.logger.warning(f"robo: the DOME IS NOT OKAY TO OPEN, but dome_override is active so I'm sending open command")
            return True
        else:
            # shouldn't ever be here
            self.logger.warning(f"robo: dome is NOT okay to open")
            return False
        
            
    def get_sun_status(self, logcheck = False):
        """
        This checks that the sun is low enough to observe
        
        If things are okay to observe it returns True, otherwise False
        """
        if self.dome.Sunlight_Status == 'READY' or self.sun_override:
            # make a note of why we want to open the dome
            if self.dome.Sunlight_Status == 'READY': 
                return True
            elif self.sun_override:
                if logcheck:
                    self.logger.warning(f"robo: the SUN IS ABOVE THE HORIZON, but sun_override is active so I want to open the dome")
                return True
            else:
                self.logger.warning(f"robo: I shouldn't ever be here. something is wrong with sun handling")
                return False

    
    def check_ok_to_observe(self, logcheck = False):
        """
        check if it's okay to observe/open the dome
        
        # NPL: 12-14-21 removed all the actions, this now is just a status check which can
        raise any necessary flags during observations. Mostly it's biggest contribution is that
        if the weather gets bad DURING an exposure that exposure will not be logged.
        
        
        # logcheck flag indicates whether the result of the check should be written to the log
            we want the result logged if we're checking from within the do_observing loop,
            but if we're just loopin through restart_robo we can safely ignore the constant logging'
        """
        
        # if we're in dometest mode, ignore the full tree
        if self.dometest:
            self.ok_to_observe = True
            return
        
        if self.get_sun_status():
            
            # if we can open up the dome, then do it!
            if self.get_dome_status():
            
                # Check if the dome is open:
                if self.dome.Shutter_Status == 'OPEN':
                    if logcheck:
                        self.logger.info(f'robo: okay to observe check passed')
                    
                    #####
                    # We're good to observe
                    self.ok_to_observe = True
                    return
                    #####
                
                else:
                    # dome is closed.
                    self.alertHandler.slack_log(f'the dome shutter is not reporting open, it says: dome.Shutter_Status = {"self.dome.Shutter_Status"}')
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
        self.log('checking what to do!')
        if self.running:
            self.log('robo operator is running')
            #---------------------------------------------------------------------
            ### check the dome
            #---------------------------------------------------------------------
            if self.get_dome_status():
                # if True, then the dome is fine
                self.log('the dome status is good!')
                pass
            else:
                self.log('there is a problem with the dome (eg weather, etc). STOWING OBSERVATORY')
                # there is a problem with the dome.
                self.stow_observatory(force = False)
                # skip the rest of the checks, just start the timer for the next check
                self.checktimer.start()
                return
            #---------------------------------------------------------------------
            # check the sun
            #---------------------------------------------------------------------
            if self.get_sun_status():
                self.log(f'the sun is low are we are ready to go!')
                # if True, then the sun is fine. just keep going
                pass
            else:
                self.log(f'waiting for the sun to set')
                # the sun is up, can't proceed. just hang out.
                self.checktimer.start()
                return
            #---------------------------------------------------------------------
            # check if the observatory is ready
            #---------------------------------------------------------------------
            if self.get_observatory_ready_status():
                self.log(f'the observatory is ready to observe!')
                # if True, then the observatory is ready (eg successful startup and focus sequence)
                pass
            else:
                self.log(f'need to start up observatory')
                # we need to (re)run do_startup
                self.do_startup()
                # after running do_startup, kick back to the top of the loop
                self.checktimer.start()
            #---------------------------------------------------------------------        
            # check the dome
            #---------------------------------------------------------------------
            if self.dometest:
                self.log('dometest mode: ignoring whether the shutter is open!')
                pass
            else:
                if self.dome.Shutter_Status == 'OPEN':
                    self.log(f'the dome is open and we are ready to start taking data')
                    # the dome is open and we're ready for observations. just pass
                    pass
                else:
                    # the dome and sun are okay, but the dome is closed. we should open the dome
                    self.announce('observatory and sun are ready for observing, but dome is closed. opening...')
                    self.doTry('dome_open')
                    
                    self.checktimer.start()
                    return
            #---------------------------------------------------------------------
            # get the current timestamp and MJD
            #---------------------------------------------------------------------
                # turn the timestamp into mjd
            if self.sunsim:
                # for some reason self.state doesn't update if it's in this loop. look into that.
                obstime_mjd = self.ephem.state.get('mjd',0)
                obstime_timestamp_utc = astropy.time.Time(obstime_mjd, format = 'mjd').unix
            else:
                obstime_mjd = 'now'
                obstime_timestamp_utc = datetime.now(tz = pytz.utc).timestamp()
                
                
            #---------------------------------------------------------------------
            # check if we need to focus the telescope
            #---------------------------------------------------------------------
            graceperiod_hours = self.config['focus_loop_param']['focus_graceperiod_hours']
            if self.test_mode == True:
                print(f"not checking focus bc we're in test mode")
                pass
            else:
                filterIDs_to_focus = self.focusTracker.getFiltersToFocus(obs_timestamp = obstime_timestamp_utc, graceperiod_hours = graceperiod_hours)
            
                # here is a good place to insert a good check on temperature change,
                # or even better a check on FWHM of previous images
            
                if not filterIDs_to_focus is None:   
                    print(f'robo: focus attempt #{self.focus_attempt_number}')
                    if self.focus_attempt_number <= self.config['focus_loop_param']['max_focus_attempts']:
                        self.announce(f'**Out of date focus results**: we need to focus the telescope in these filters: {filterIDs_to_focus}')
                        # there are filters to focus! run a focus sequence
                        self.do_focus_sequence(filterIDs = filterIDs_to_focus)
                        self.announce(f'got past the do_focus_sequence call in checkWhatToDo?')
                        self.focus_attempt_number += 1
                        # now exit and rerun the check
                        self.checktimer.start()
                        return
            
            #---------------------------------------------------------------------
            # check if we should reboot the SUMMER accessories
            #---------------------------------------------------------------------
            #TODO: 4-19-22 clean this up and make it less hard coded and sucky
            dt_hr_since_last_reboot = self.SUMMERrebootTracker.getHoursSinceLastReboot()
            if dt_hr_since_last_reboot > self.config['viscam_accessories_reboot_param']['reboot_graceperiod_hours']:
                # it has been too long since the last reboot... power cycle the accessories
                self.announce(f'It has been {dt_hr_since_last_reboot} hrs since last SUMMER accessories reboot. Attempting to power cycle now...')
                
                # first get the proper outlet
                pdu_conf = utils.loadconfig(os.path.join(self.base_directory, 'config', 'powerconfig.yaml'))
                for pdu in pdu_conf['pdus']:
                    pdu_num = pdu_conf['pdus'][pdu]['pdu_number']
                    for outlet_num in pdu_conf['pdus'][pdu]['outlets']:
                        device = pdu_conf['pdus'][pdu]['outlets'][outlet_num]
                        if  device == 'SUMMERacc':
                            break
                            
                # we now have all the infor topower cycle 'SUMMERacc'
                self.doTry(f'pdu_cycle {pdu_num} {outlet_num}')
                                
                # now update the reboot log that we tried
                self.SUMMERrebootTracker.updateRebootTime()
                
                # now wait for a bit and check the status again
                self.waitAndCheck(2*60)
                return
                
            #---------------------------------------------------------------------
            # check what we should be observing NOW
            #---------------------------------------------------------------------
            # if it is low enough (typically between astronomical dusk and dawn)
            # then check for targets, otherwise just stand by
            #print(f'checking what to observe NOW')
            if self.state['sun_alt'] <= self.config['max_sun_alt_for_observing']:
                self.load_best_observing_target(obstime_mjd)
                
                #print(f'currentObs = {self.schedule.currentObs}')
                #print(f'self.schedule.schedulefile = {self.schedule.schedulefile}, self.schedule.scheduleType = {self.schedule.scheduleType}')
                #print(f'type(self.schedule.currentObs) = {type(self.schedule.currentObs)}')
                #print(f'self.schedule.currentObs == "default": {self.schedule.currentObs == "default"}')
                if self.schedule.currentObs is None:
                #if currentObs is None:
                    self.announce(f'no valid observations at this time (MJD = {self.state.get("ephem_mjd",-999)}), standing by...')
                    # first stow the rotator
                    self.rotator_stop_and_reset()
                    
                    # if we're at the bottom of the schedule, then handle the end of the schedule
                    if self.schedule.end_of_schedule == True:
                            self.announce('schedule complete! shutting down schedule connection')
                            self.handle_end_of_schedule()
                    else:
                        # nothing is up right now, just loop back and check again
                        self.checktimer.start()
                    return
                else:
                    # if we got an observation, then let's go do it!!
                    #self.do_currentObs(currentObs)
                    # log the observation to note that we ATTEMPTED the observation
                    self.schedule.log_observation()
                    self.do_currentObs(self.schedule.currentObs)
            
            else:
                # if we are here then the sun is not low enough to observe, stand by
                self.checktimer.start()
                return
            
        
    
    def load_best_observing_target(self, obstime_mjd):
        """
        query all available schedules (survey + any schedules in the TOO folder),
        then rank them and return the highest ranked instance. this is what we want to observe
        """
        # get all the files in the ToO High Priority folder
        ToO_schedule_directory = os.path.join(os.getenv("HOME"), self.config['scheduleFile_ToO_directory'])
        ToOscheduleFiles = glob.glob(os.path.join(ToO_schedule_directory, '*.db'))
        
        if len(ToOscheduleFiles) > 0:
            # bundle up all the schedule files in a single pandas dataframe
            full_df = pd.DataFrame()
            # add all the ToOs
            for too_file in ToOscheduleFiles:
                engine = db.create_engine('sqlite:///'+too_file)
                conn = engine.connect()
                df = pd.read_sql('SELECT * FROM summary;',conn)
                df['origin_filename'] = too_file
                
                conn.close()
                
                # now validate the scheudle. if valid, add to list of schedules.
                try:
                    wintertoo.validate.validate_schedule_df(df)
                    full_df = pd.concat([full_df,df])
                
                except Exception as e:
                    too_filename = os.path.basename(os.path.normpath(too_file))
                    self.log(f'skipping TOO schedule {too_filename}, schema not valid: {e}')
                    
            
            # now sort by priority (highest to lowest)
            full_df = full_df.sort_values(['Priority'],ascending=False)
            
            # now sort by validStop (earliest to latest)
            full_df = full_df.sort_values(['validStop'],ascending=True)
            
            # save the dataframe to csv for realtime reference
            rankedSummary = full_df[['obsHistID', 'Priority', 'validStop', 'origin_filename']]
            rankedSummary.to_csv(os.path.join(os.getenv("HOME"), 'data', 'Valid_ToO_Observations_Ranked.csv'))
            
            if len(full_df) == 0:
                # there are no valid schedule files. break out to the handling at the bottom
                pass
            
            else:
                # the best target is the first one in this sorted pandas dataframe
                currentObs = dict(full_df.iloc[0])
                scheduleFile = currentObs['origin_filename']
                scheduleFile_without_path = scheduleFile.split('/')[-1]
                self.announce(f'we should be observing from {scheduleFile_without_path}, obsHistID = {currentObs["obsHistID"]}')
                # point self.schedule to the TOO
                self.schedule.loadSchedule(scheduleFile)
                self.schedule.updateCurrentObs(currentObs, obstime_mjd)
                return

        # if we're here, there are no TOO valid observations
        self.announce(f'there are no valid ToO observations, defaulting to survey')
        
        scheduleFile = self.survey_schedulefile_name
        # point self.schedule to the survey
        self.announce(f'loading survey schedule: {scheduleFile}')
        self.schedule.loadSchedule(scheduleFile)
        currentObs = self.schedule.getTopRankedObs(obstime_mjd)
        #self.announce(f'currentObs = {currentObs}')
        self.schedule.updateCurrentObs(currentObs, obstime_mjd)
        return
        

    
        
    def get_observatory_ready_status(self):
        """
        Run a check to see if the observatory is ready. Basically:
            - did startup run successfully
            - has the telescope been focused recently
        """
        
        conds = []
        
        ### DOME CHECKS ###
        conds.append(self.dome.Control_Status == 'REMOTE')
        #conds.append(self.state['dome_tracking_status'] == True)
        conds.append(self.dome.Home_Status == 'READY')
        
        ### TELESCOPE CHECKS ###
        conds.append(self.state['mount_is_connected'] == True)
        conds.append(self.state['mount_alt_is_enabled'] == True)
        conds.append(self.state['mount_az_is_enabled'] == True)
        conds.append(self.state['rotator_is_connected'] == True)
        conds.append(self.state['rotator_is_enabled'] == True)
        conds.append(self.state['rotator_wrap_check_enabled'] == True)
        conds.append(self.state['focuser_is_connected'] == True)
        conds.append(self.state['focuser_is_enabled'] == True)
        conds.append(self.state['Mirror_Cover_State'] == 0)
        
        #TODO: add something about the focus here
        
        self.observatory_ready = all(conds)
        
        return self.observatory_ready
    
    def get_observatory_stowed_status(self):
        """
        Run a check to see if the observatory is in a safe stowed state.
        This stowed state is where it should be during the daytime, and during
        any remote closures.
        """
        
        conds = []
        
        ### DOME CHECKS ###
        # make sure we've given back control
        conds.append(self.dome.Control_Status == 'AVAILABLE')
        # make sure the dome is near it's park position
        # AZ: handle the fact that we may get something 359 or 0.6
        delta_az = np.abs(self.state['dome_az_deg'] - self.config['dome_home_az_degs']) 
        min_delta_az = np.min([360 - delta_az, delta_az])
        conds.append(min_delta_az < 1.0)
        # make sure dome tracking is off
        conds.append(self.state['dome_tracking_status'] == False)
        
        # make sure the dome is closed
        conds.append(self.dome.Shutter_Status == 'CLOSED')
        
        ### TELESCOPE CHECKS ###
        # make sure mount tracking is off
        conds.append(self.state['mount_is_tracking'] == False)
        
        # make sure the mount is near home
        delta_az = np.abs(self.state['mount_az_deg'] - self.config['telescope']['home_az_degs']) 
        min_delta_az = np.min([360 - delta_az, delta_az])
        conds.append(min_delta_az < 1.0)
        
        # don't worry about the alt
        #conds.append(np.abs(self.state['mount_alt_deg'] - self.config['telescope']['home_alt_degs']) < 45.0) # home is 45 deg, so this isn't really doing anything
        
        delta_rot_angle = np.abs(self.state['rotator_mech_position'] - self.config['telescope']['rotator_home_degs'])
        min_delta_rot_angle = np.min([360 - delta_rot_angle, delta_rot_angle])
        conds.append( min_delta_rot_angle < 10.0) #NPL 12-15-21 these days it sags to ~ -27 from -25
        
        # make sure the motors are off
        conds.append(self.state['mount_alt_is_enabled'] == False)
        conds.append(self.state['mount_az_is_enabled'] == False)
        conds.append(self.state['rotator_is_enabled'] == False)
        conds.append(self.state['focuser_is_enabled'] == False)
        
        # make sure the mount is disconnected?
        # conds.append(self.state['mount_is_connected'] == False)
        
        ### MIRROR COVER ###
        # make sure the mirror cover is closed
        conds.append(self.state['Mirror_Cover_State'] == 1)
        
        self.observatory_stowed = all(conds)
        
        return self.observatory_stowed
        
    
    def stow_observatory(self, force = False):
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
                #TODO: will want to mute this to avoid lots of messages.
                msg = 'requested observatory be stowed, but it is already stowed. standing by.'
                #self.log(msg)
                #self.announce(msg)
                return
            else:
                # the observatory is already stowed, but we demanded it be shut down anyway
                # just go down to the next part of the tree
                pass
            
        # if the observatory is in the ready state, then just shut down
        elif self.get_observatory_ready_status():
            self.announce(f'shutting down observatory from ready state:')
            self.do_shutdown()
            
            
        else:
            self.announce(f'stowing observatory from arbitrary state: starting up first and then shutting down')
            # we need to shut down.
            # this may require turning things on to move them and shutdown. so we start up and then shut down
            self.do_startup()
            
            self.do_shutdown()
   
        
    


    def interrupt(self):
        self.schedule.currentObs = None

    def stop(self):
        self.running = False
        #TODO: Anything else that needs to happen before stopping the thread

    def change_schedule(self, schedulefile_name):
        """
        This function handles the initialization needed to start observing a
        new schedule. It is called when the changeSchedule signal is caught,
        as well as when the thread is first initialized.
        """

        print(f'scheduleExecutor: setting up new survey schedule from file >> {schedulefile_name}')

        if self.running:
            self.stop()
        self.survey_schedulefile_name = schedulefile_name
        self.schedulefile_name = schedulefile_name
        self.schedule.loadSchedule(schedulefile_name)

    def get_data_to_log(self,currentObs = 'default',):
        
        if currentObs == 'default':
            currentObs = self.schedule.currentObs
            
        data = {}
        # First, handle all the keys from self.schedule.currentObs.
        # THESE ARE SPECIAL KEYS WHICH ARE REQUIRED FOR THE SCHEDULER TO WORK PROPERLY
        
        keys_with_actual_vals = ["dist2Moon", "expMJD", "visitExpTime", "azimuth", "altitude"]
        
        for key in currentObs:
            # Some entries need the scheduled AND actuals recorded
                    
            if key in keys_with_actual_vals:
                data.update({f'{key}_scheduled': currentObs[key]})
            else:
                data.update({key: currentObs[key]})
        
        # now update the keys with actual vals with their actual vals
        data.update({'dist2Moon'    : self.getDist2Moon(),
                     'expMJD'       : self.getMJD(),
                     'visitExpTime' : self.exptime,# self.waittime, 
                     'altitude'     : self.state['mount_az_deg'], 
                     'azimuth'      : self.state['mount_alt_deg']
                     })
        # now step through the Observation entries in the dataconfig.json and grab them from state
        
        for key in self.writer.dbStructure['Observation']:
            # make sure we don't overwrite an entry from the currentObs or the keys_with_actual_vals
            ## ie, make sure it's a key that's NOT already in data
            if (key not in data.keys()):
                # if the key is in state, then update data
                if key in self.state.keys():
                    data.update({key : self.state[key]})
                else:
                    pass
            else:
                pass
        #print(f'header data = {data}')
        return data
        
    def getMJD(self):
        now_utc = datetime.utcnow()
        T = astropy.time.Time(now_utc, format = 'datetime')
        mjd = T.mjd
        return mjd
        
    
    def getDist2Moon(self):
        delta_alt = self.state['mount_alt_deg'] - self.ephem.moonalt
        delta_az = self.state['mount_az_deg'] - self.ephem.moonaz
        dist2Moon = (delta_alt**2 + delta_az**2)**0.5
        return dist2Moon
    
    def log(self, msg, level = logging.INFO):
        if self.logger is None:
                print(msg)
        else:
            self.logger.log(level = level, msg = msg)
    
    def doTry(self, cmd, context = '', system = ''):
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
            msg = f'roboOperator: could not execute function {cmd} due to {e.__class__.__name__}, {e}'#', traceback = {tb}'
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
    
    def do_startup(self):
        """
        NPL 12-15-21: porting over the steps from Josh's total_startup to here
        for better error handling.
        """
        
        # this is for passing to errors
        context = 'do_startup'
        
        ### DOME SET UP ###
        system = 'dome'
        msg = 'starting dome startup...'
        self.announce(msg)

        try:
            # take control of dome        
            self.do('dome_takecontrol')
            
            self.do('dome_tracking_off')
    
            # re-home the dome (put the dome through it's homing routine)
            #TODO: NPL 12-15-21: we might want to move this elsewhere, we should do it nightly but it doesn't have to be here.
            #self.do('dome_home')
            
            # send the dome to it's home/park position
            self.do('dome_go_home')
            
            # signal we're complete
            msg = 'dome startup complete'
            self.logger.info(f'robo: {msg}')
            self.alertHandler.slack_log(f':greentick: {msg}')
        except Exception as e:
            msg = f'roboOperator: could not set up {system} due to {e.__class__.__name__}, {e}'
            self.log(msg)
            err = roboError(context, self.lastcmd, system, msg)
            self.hardware_error.emit(err)
            return
        
        
        ### MOUNT SETUP ###
        system = 'telescope'
        msg = 'starting telescope startup...'
        self.announce(msg)
        try:
            # start up the mount: 
                # splitting this up so we get more feedback on where things crash
            #self.do('mount_startup')
            
            # connect the telescope
            self.do('mount_connect')
            
            # turn off tracking
            self.do('mount_tracking_off')
            
            # make sure we load the pointing model explicitly
            self.do(f'mount_model_load {self.config["pointing_model"]["pointing_model_file"]}')
            
            # turn on the motors
            self.do('mount_az_on')
            self.do('mount_alt_on')

            # turn on the rotator
            self.do('rotator_enable')
            # home the rotator
            self.do('rotator_home')
            
            # turn on the focuser
            self.do('m2_focuser_enable')
            
            # poing the mount to home
            self.do('mount_home')
            
            self.announce(':greentick: telescope startup complete!')
            
        except Exception as e:
            msg = f'roboOperator: could not set up {system} due to {e.__class__.__name__}, {e}'
            self.log(msg)
            self.alertHandler.slack_log(f'*ERROR:* {msg}', group = None)
            err = roboError(context, self.lastcmd, system, msg)
            self.hardware_error.emit(err)
            return
        
        
        system = 'mirror cover'
        msg = 'opening mirror covers'
        self.announce(msg)
        try:
            # connect to the mirror cover
            self.do('mirror_cover_connect')
            
            # open the mirror cover
            self.do('mirror_cover_open')
        
        except Exception as e:
            msg = f'roboOperator: could not set up {system} due to {e.__class__.__name__}, {e}'
            self.log(msg)
            self.alertHandler.slack_log(f'*ERROR:* {msg}', group = None)
            err = roboError(context, self.lastcmd, system, msg)
            self.hardware_error.emit(err)
            return
        
        self.announce(':greentick: mirror covers open!')

        # if we made it all the way to the bottom, say the startup is complete!
        self.startup_complete = True
            
        self.announce(':greentick: startup complete!')
        print(f'robo: do_startup complete')
        
    def do_shutdown(self):
        """
        This is the counterpart to do_startup. It supercedes the old "total_shutdown"
        script, replicating its essential functions but with better communications
        and error handling.
        """
        
        # this is for passing to errors
        context = 'do_startup'
        
        ### DOME SHUT DOWN ###
        system = 'dome'
        msg = 'starting dome shutdown...'
        self.announce(msg)

        try:
            # make sure dome isn't tracking telescope anymore
            self.do('dome_tracking_off')
            
            # send the dome to it's home/park position
            self.do('dome_go_home')
            
            # close the dome
            self.do('dome_close')
            
            # give control of dome        
            self.do('dome_givecontrol')
            
            
            # signal we're complete
            msg = 'dome shutdown complete'
            self.logger.info(f'robo: {msg}')
            self.alertHandler.slack_log(f':greentick: {msg}')
        except Exception as e:
            msg = f'roboOperator: could not shut down {system} due to {e.__class__.__name__}, {e}'
            self.log(msg)
            err = roboError(context, self.lastcmd, system, msg)
            self.hardware_error.emit(err)
            return
    
        ### MOUNT SHUTDOWN ###
        system = 'telescope'
        msg = 'starting telescope shutdown...'
        self.announce(msg)
        try:
            # start up the mount: 
                # splitting this up so we get more feedback on where things crash
            #self.do('mount_startup')
            
            # turn off tracking
            self.do('mount_tracking_off')
            
            # point the mount to home
            self.do('mount_home')
            
            # turn off the focuser
            self.do('m2_focuser_disable')
            
            # home the rotator
            self.do('rotator_home')
            
            # turn off the rotator
            self.do('rotator_disable')
            
            # turn off the motors
            self.do('mount_az_off')
            self.do('mount_alt_off')

            # disconnect the telescope
            #self.do('mount_disconnect')
            
            self.announce(':greentick: telescope shutdown complete!')
            
        except Exception as e:
            msg = f'roboOperator: could not shut down {system} due to {e.__class__.__name__}, {e}'
            self.log(msg)
            self.alertHandler.slack_log(f'*ERROR:* {msg}', group = None)
            err = roboError(context, self.lastcmd, system, msg)
            self.hardware_error.emit(err)
            return
        
        ### MIRROR COVER CLOSURE ###
    
        system = 'mirror cover'
        msg = 'closing mirror covers'
        self.announce(msg)
        try:
            # connect to the mirror cover
            self.do('mirror_cover_connect')
            
            # open the mirror cover
            self.do('mirror_cover_close')
        
        except Exception as e:
            msg = f'roboOperator: could not shut down {system} due to {e.__class__.__name__}, {e}'
            self.log(msg)
            self.alertHandler.slack_log(f'*ERROR:* {msg}', group = None)
            err = roboError(context, self.lastcmd, system, msg)
            self.hardware_error.emit(err)
            return
        
        self.announce(':greentick: mirror covers closed!')

        # if we made it all the way to the bottom, say the startup is complete!
        self.shutdown_complete = True
            
        self.announce(':greentick: shutdown complete!')
        print(f'robo: do_shutdown complete')

    
    
    
    

    
    def do_calibration(self, do_flats = True, do_darks = True, do_bias = True):
        
        # if we're in here set running to True
        self.running = True
        
        context = 'do_calibration'
        if do_flats:
            # check to make sure conditions are okay before attempting cal routine. prevents weird hangups
            # copied logic from checkWhatToDo(), but don't actually command any systems if there's an issue.
            # instead just exit out of this routine. hopefully this avoids conflicting sets of instructions.
            # 
            self.announce('checking conditions before running auto calibration routine')
    
            #---------------------------------------------------------------------
            ### check the dome
            #---------------------------------------------------------------------
            if self.get_dome_status():
                # if True, then the dome is fine
                self.log('the dome status is good!')
                pass
            else:
                self.announce(f'there is a problem with the dome (eg weather, etc) preventing operation. exiting calibration routine...')
                """
                self.log('there is a problem with the dome (eg weather, etc). STOWING OBSERVATORY')
                # there is a problem with the dome.
                self.stow_observatory(force = False)
                # skip the rest of the checks, just start the timer for the next check
                self.checktimer.start()
                """
                return
            #---------------------------------------------------------------------
            # check the sun
            #---------------------------------------------------------------------
            if self.get_sun_status():
                self.log(f'the sun is low are we are ready to go!')
                # if True, then the sun is fine. just keep going
                pass
            else:
                self.announce(f'the sun is not ready for operation. exiting calibration routine...')
                """
                self.log(f'waiting for the sun to set')
                # the sun is up, can't proceed. just hang out.
                self.checktimer.start()
                """
                return
            #---------------------------------------------------------------------
            # check if the observatory is ready
            #---------------------------------------------------------------------
            if self.get_observatory_ready_status():
                self.log(f'the observatory is ready to observe!')
                # if True, then the observatory is ready (eg successful startup and focus sequence)
                pass
            else:
                self.announce(f'the observatory is not ready to observe! exiting calibration routine...')
                """
                self.log(f'need to start up observatory')
                # we need to (re)run do_startup
                self.do_startup()
                # after running do_startup, kick back to the top of the loop
                self.checktimer.start()
                """
                return
            #---------------------------------------------------------------------        
            # check the dome
            #---------------------------------------------------------------------
            if self.dome.Shutter_Status == 'OPEN':
                self.log(f'the dome is open and we are ready to start taking data')
                # the dome is open and we're ready for observations. just pass
                pass
            else:
                # the dome and sun are okay, but the dome is closed. we should open the dome
                self.announce('observatory and sun are ready for observing, but dome is closed. opening...')
                self.doTry('dome_open')
                """
                self.checktimer.start()
                return
                """
                
            # if we made it to here, we're good to do the auto calibration
            
            self.announce('starting auto calibration sequence.')
            #self.logger.info('robo: doing calibration routine. for now this does nothing.')
            
            ### TAKE SKY FLATS ###
            # for now some numbers are hard coded which should be in the config file
            # pick which direction to look: look away from the sun
            if self.state['sun_rising']:
                flat_az = 270.0
                
            else:
                flat_az = 0.0
                
            
                
            # get the altitude
            flat_alt = 75.0
            
            
            system = 'dome'
            try:
                # slew the dome
                self.do(f'dome_tracking_off')
                self.do(f'dome_goto {flat_az}')
                self.do(f'dome_tracking_on')
                
                system = 'telescope'
                # slew the telescope
                self.do(f'mount_goto_alt_az {flat_alt} {flat_az}')
               
               
                self.log(f'starting the flat observations')
            
            except Exception as e:
                msg = f'roboOperator: could not set up {system} due to {e.__class__.__name__}, {e}'
                self.log(msg)
                self.alertHandler.slack_log(f'*ERROR:* {msg}', group = None)
                err = roboError(context, self.lastcmd, system, msg)
                self.hardware_error.emit(err)
                return
            # if we got here we're good to start
            # take  flats!
            nflats = 2
            
            ra_total_offset_arcmin = 0
            dec_total_offset_arcmin = 0
            
            #cycle through all the active filters:for filterID in 
            filterIDs = self.focusTracker.getActiveFilters()
                    
            for filterID in filterIDs:
                self.announce(f'executing focus loop for filter: {filterID}')
                try:
                    self.announce(f'doing flats for filter: {filterID}')
    
                    # step through each filter to focus, and run a focus loop
                    # 1. change filter to filterID
                    system = 'filter wheel'
                    if self.cam == 'summer':
                        # get filter number
                        for position in self.config['filter_wheels'][self.cam]['positions']:
                            if self.config['filter_wheels'][self.cam]['positions'][position] == filterID:
                                filter_num = position
                            else:
                                pass
                            
                        #self.do(f'command_filter_wheel {filter_num}')
                        if filter_num == self.state['Viscam_Filter_Wheel_Position']:
                            self.log('requested filter matches current, no further action taken')
                        else:
                            self.log(f'current filter = {self.state["Viscam_Filter_Wheel_Position"]}, changing to {filter_num}')
                            self.do(f'command_filter_wheel {filter_num}')
            
                    for i in range(nflats):
                        try:
                            self.log(f'setting up flat #{i + 1}')
                    
                            # estimate required exposure time
                            flat_exptime = 40000.0/(2.319937e9 * (-1*self.state["sun_alt"])**(-8.004657))
                            
                            
                            
                            minexptime = 2.5 + i
                            maxexptime = 60
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
                                self.log(f'setting exptime to estimated {flat_exptime} s')
                            
                            system = 'ccd'
                            self.do(f'ccd_set_exposure {flat_exptime:0.3f}')
                            time.sleep(2)
                            
                            qcomment = f"Auto Flats {i+1}/{nflats} Alt/Az = ({flat_alt}, {flat_az}), RA +{ra_total_offset_arcmin} am, DEC +{dec_total_offset_arcmin} am"
                            #qcomment = f"(Alt, Az) = ({self.state['mount_alt_deg']:0.1f}, {self.state['mount_az_deg']:0.1f})"
                            # now trigger the actual observation. this also starts the mount tracking
                            self.announce(f'Executing {qcomment}')
                            if i==0:
                                self.log(f'handling the i=0 case')
                                #self.do(f'robo_set_qcomment "{qcomment}"')
                                system = 'robo routine'
                                self.do(f'robo_observe altaz {flat_alt} {flat_az} -f --comment "{qcomment}"')
                            else:
                                system = 'ccd'
                                self.do(f'robo_do_exposure --comment "{qcomment}" -f ')
                            
                            # now dither. if i is odd do ra, otherwise dec
                            dither_arcmin = 5
                            if i%2:
                                axis = 'ra'
                                ra_total_offset_arcmin += dither_arcmin
                            else:
                                axis = 'dec'
                                dec_total_offset_arcmin += dither_arcmin
                                
                            #self.do(f'mount_offset {axis} add_arcsec {dither_arcsec}')
                            self.do(f'mount_dither {axis} {dither_arcmin}')
                        
                        except Exception as e:
                            msg = f'roboOperator: could not run flat loop instance due to error with {system}: due to {e.__class__.__name__}, {e}'
                            self.log(msg)
                            self.alertHandler.slack_log(f'*ERROR:* {msg}', group = None)
                            err = roboError(context, self.lastcmd, system, msg)
                            self.hardware_error.emit(err)
                            #return
                    
                except Exception as e:
                    msg = f'roboOperator: could not complete flats for {filterID} due to error with {system}: due to {e.__class__.__name__}, {e}'
                    self.log(msg)
                    self.alertHandler.slack_log(f'*ERROR:* {msg}', group = None)
                    err = roboError(context, self.lastcmd, system, msg)
                    self.hardware_error.emit(err)
                    #return
            
            # if we get here, we're done with the light exposure, so turn off dome and mount tracking
                    # so that the telescope doesn't drift
            
            system = 'dome'
            try:
                self.do('dome_tracking_off')
                
                system = 'telescope'
                self.do('mount_tracking_off')
            except Exception as e:
                msg = f'roboOperator: could not stop tracking after flat fields due to error with {system}: due to {e.__class__.__name__}, {e}'
                self.log(msg)
                self.alertHandler.slack_log(f'*ERROR:* {msg}', group = None)
                err = roboError(context, self.lastcmd, system, msg)
                self.hardware_error.emit(err)
                #return
        
        ### Take Darks ###
        if do_darks:
            self.do_darks()
        
        ### Take Bias ###
        if do_bias:
            self.do_bias()
        
        self.log(f'finished with calibration. no more to do.')    
        self.announce('auto calibration sequence completed successfully!')
        
    def do_bias(self):
        self.log(f'running bias image sequence')
        context = 'do_bias'
        # stow the rotator
        self.rotator_stop_and_reset()
        try:
            # slew the dome
            system = 'dome'
            self.do(f'dome_tracking_off')
            system = 'telescope'
            self.do(f'mount_tracking_off')
            
            self.log(f'starting the bias observations')
        
        except Exception as e:
            msg = f'roboOperator: could not set up {system} due to {e.__class__.__name__}, {e}'
            self.log(msg)
            self.alertHandler.slack_log(f'*ERROR:* {msg}', group = None)
            err = roboError(context, self.lastcmd, system, msg)
            self.hardware_error.emit(err)
            return
        ### Take bias ###
        try:
            self.announce(f'doing bias seq')

            try:
                self.do(f'ccd_set_exposure 0.0')
                nbias = 5
                for i in range(nbias):
                    self.announce(f'Executing Auto Bias {i+1}/5')
                    qcomment = f"Auto Bias {i+1}/{nbias}"
                    self.do(f'robo_do_exposure -b --comment "{qcomment}"')
                    
            except Exception as e:
                msg = f'roboOperator: could not set up bias routine due to error with {system} due to {e.__class__.__name__}, {e}'
                self.log(msg)
                self.alertHandler.slack_log(f'*ERROR:* {msg}', group = None)
                err = roboError(context, self.lastcmd, system, msg)
                self.hardware_error.emit(err)
                return
        except Exception as e:
            msg = f'roboOperator: could not complete bias image collection due to error with {system}: due to {e.__class__.__name__}, {e}'
            self.log(msg)
            self.alertHandler.slack_log(f'*ERROR:* {msg}', group = None)
            err = roboError(context, self.lastcmd, system, msg)
            self.hardware_error.emit(err)
            #return
        
        #self.log(f'finished with calibration. no more to do.')    
        self.announce('bias sequence completed successfully!')
        
        
        #self.calibration_complete = True
        
        # set the exposure time back to something sensible to avoid errors
        try:
            self.do(f'ccd_set_exposure 30.0')
                
        except Exception as e:
            msg = f'roboOperator: could not set up bias routine due to error with {system} due to {e.__class__.__name__}, {e}'
            self.log(msg)
            self.alertHandler.slack_log(f'*ERROR:* {msg}', group = None)
            err = roboError(context, self.lastcmd, system, msg)
            self.hardware_error.emit(err)
            return
        
    def do_darks(self):
        """
        do a series of dark exposures in all active filteres
        
        """
        context = 'do_darks'
        # stow the rotator
        self.rotator_stop_and_reset()
        try:
            # slew the dome
            system = 'dome'
            self.do(f'dome_tracking_off')
            system = 'telescope'
            self.do(f'mount_tracking_off')
            
            self.log(f'starting the bias observations')
        
        except Exception as e:
            msg = f'roboOperator: could not set up {system} due to {e.__class__.__name__}, {e}'
            self.log(msg)
            self.alertHandler.slack_log(f'*ERROR:* {msg}', group = None)
            err = roboError(context, self.lastcmd, system, msg)
            self.hardware_error.emit(err)
            return
        #cycle through all the active filters:for filterID in 
        filterIDs = self.focusTracker.getActiveFilters()
        for filterID in filterIDs:
            try:
                self.announce(f'doing darks for filter: {filterID}')

                # step through each filter to focus, and run a focus loop
                # 1. change filter to filterID
                system = 'filter wheel'
                if self.cam == 'summer':
                    # get filter number
                    for position in self.config['filter_wheels'][self.cam]['positions']:
                        if self.config['filter_wheels'][self.cam]['positions'][position] == filterID:
                            filter_num = position
                        else:
                            pass
                        
                    self.do(f'command_filter_wheel {filter_num}')
        
        
                system = 'rotator'
                try:
                    self.do('rotator_stop')
                    self.do('rotator_home')
                
                except Exception as e:
                    msg = f'roboOperator: could not set up dark routine due to error with {system} due to {e.__class__.__name__}, {e}'
                    self.log(msg)
                    self.alertHandler.slack_log(f'*ERROR:* {msg}', group = None)
                    err = roboError(context, self.lastcmd, system, msg)
                    self.hardware_error.emit(err)
                    return
                    
                system = 'ccd'
                try:
                    self.do(f'ccd_set_exposure 30.0')
                    ndarks = 5
                    for i in range(ndarks):
                        self.announce(f'Executing Auto Darks {i+1}/5')
                        qcomment = f"Auto Darks {i+1}/{ndarks}"
            
                        self.do(f'robo_do_exposure -d --comment "{qcomment}"')
                except Exception as e:
                    msg = f'roboOperator: could not set up dark routine due to error with {system} due to {e.__class__.__name__}, {e}'
                    self.log(msg)
                    self.alertHandler.slack_log(f'*ERROR:* {msg}', group = None)
                    err = roboError(context, self.lastcmd, system, msg)
                    self.hardware_error.emit(err)
                    return
            except Exception as e:
                msg = f'roboOperator: could not complete darks for {filterID} due to error with {system}: due to {e.__class__.__name__}, {e}'
                self.log(msg)
                self.alertHandler.slack_log(f'*ERROR:* {msg}', group = None)
                err = roboError(context, self.lastcmd, system, msg)
                self.hardware_error.emit(err)
                #return

        self.announce('darks sequence completed successfully!')
    
    def do_focusLoop(self, nom_focus = 'default', total_throw = 'default', nsteps = 'default', updateFocusTracker = True, focusType = 'Vcurve'):
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
        self.announce('running focus loop!')
        context = 'do_focusLoop'
        # get the current filter
        #TODO: make this flexible to handle winter or summer. eg, if cam == 'summer': ... elif cam == 'winter': ...
        
        
        
        try:
            if self.cam == 'summer':
                
                filterpos = self.state['Viscam_Filter_Wheel_Position'] # eg. 3
                pixscale = self.config['viscam_platescale_as']
                
                
            
            filterID = self.config['filter_wheels'][self.cam]['positions'][filterpos] # eg. 'r'
            filtername = self.config['filters'][self.cam][filterID]['name'] # eg. "SDSS r' (Chroma)"
            
            if nom_focus == 'last':
                #TODO: make this query the focusTracker to find the last focus position
                try:
                    last_focus, last_focus_timestamp = self.focusTracker.checkLastFocus(filterID)
                    # set the nominal focus to the last focus positiion
                    nom_focus = last_focus
                    self.log(f'focusing around previous best focus location: {nom_focus}')

                    
                    if nom_focus is None:
                        self.log(f'no previous focus position found, defaulting to nominal.')
                        nom_focus = self.config['filters'][self.cam][filterID]['nominal_focus']
                    
                except Exception as e:
                    self.log(f'could not get a value for the last focus position. defaulting to default focus. Traceback = {traceback.format_exc()}')
                    nom_focus = self.config['filters'][self.cam][filterID]['nominal_focus']                    
            elif nom_focus == 'default':
                nom_focus = self.config['filters'][self.cam][filterID]['nominal_focus']
            
            if total_throw == 'default':
                #total_throw = self.config['focus_loop_param']['total_throw']
                total_throw = self.config['focus_loop_param']['sweep_param']['wide']['total_throw']
            if nsteps == 'default':
                #nsteps = self.config['focus_loop_param']['nsteps']
                nsteps = self.config['focus_loop_param']['sweep_param']['wide']['nsteps']
                
            # init a focus loop object on the current filter
            #    config, nom_focus, total_throw, nsteps, pixscale
            self.log(f'setting up focus loop object: nom_focus = {nom_focus}, total_throw = {total_throw}, nsteps = {nsteps}, pixscale = {pixscale}')
            
            # what kind of focus loop do we want to do?
            if focusType.lower() == 'parabola':
                loop = focusing.Focus_loop_v2(self.config, nom_focus, total_throw, nsteps, pixscale)
            else:
                loop = focusing.Focus_loop_v3(self.config, nom_focus, total_throw, nsteps, pixscale, state = self.state)
            self.log(f'focus loop: will take images at {loop.filter_range}')
        
        except Exception as e:
            msg = f'roboOperator: could not run focus loop due to  due to {e.__class__.__name__}, {e}'#', tb = {traceback.format_exc()}'
            self.log(msg)
            self.alertHandler.slack_log(f'*ERROR:* {msg}', group = None)
            #err = roboError(context, self.lastcmd, system, msg)
            #self.hardware_error.emit(err)
            return
        
        # note that the list of focus positions is loop.filter_range
        
        #### START THE FOCUS LOOP ####
        self.log(f'setting up focus loop for {self.cam} {filtername} (filterpos = {filterpos}, filterID = {filterID})')
        
        # first drive the focuser in past the first position
        # loop.filter_range is arranged small to big distances, so start smaller to ensure we approach all points from the same direction
        focuser_start_pos = np.min(loop.filter_range_nom) - 100
        
        system = 'focuser'
        try:
            self.log(f'racking focuser below min position to pre-start position: {focuser_start_pos} before starting')
            cur_focus = nom_focus
            while (cur_focus > focuser_start_pos):
                next_pos = max([cur_focus-100,focuser_start_pos])
                print(f"Current focus: {cur_focus} -> {next_pos}")
                # self.do(f'm2_focuser_goto {focuser_start_pos}')
                self.do(f'm2_focuser_goto {next_pos}')
                cur_focus = next_pos
        
        except Exception as e:
            msg = f'roboOperator: could not run focus loop due to error with {system} due to {e.__class__.__name__}, {e}'
            self.log(msg)
            self.alertHandler.slack_log(f'*ERROR:* {msg}', group = None)
            err = roboError(context, self.lastcmd, system, msg)
            self.hardware_error.emit(err)
            return
        # step through the focus positions and take images
        
        focuser_pos = []
        images = []
        image_log_path = self.config['focus_loop_param']['image_log_path']
        
        # keep track of which image we're on
        i = 0
        #for i in range(len(loop.filter_range_nom)):
        for dist in loop.filter_range_nom:
            
            try:
                self.log(f'taking filter image at focuser position = {dist}')
                
                # drive the focuser
                system = 'focuser'
                self.do(f'm2_focuser_goto {dist}')
                
                self.exptime = self.config['filters'][self.cam][filterID]['focus_exptime']
                self.logger.info(f'robo: making sure exposure time on ccd to is set to {self.exptime}')
                
                # changing the exposure can take a little time, so only do it if the exposure is DIFFERENT than the current
                if self.exptime == self.state['ccd_exptime']:
                    self.log('requested exposure time matches current setting, no further action taken')
                    pass
                else:
                    self.log(f'current exptime = {self.state["ccd_exptime"]}, changing to {self.exptime}')
                    self.do(f'ccd_set_exposure {self.exptime}')
                
                
                # take an image
                system = 'ccd'
                #self.do(f'robo_do_exposure -foc')
                
                qcomment = f"Focus Loop Image {i+1}/{nsteps} Focus Position = {dist:.0f} um"
                #qcomment = f"(Alt, Az) = ({self.state['mount_alt_deg']:0.1f}, {self.state['mount_az_deg']:0.1f})"
                # now trigger the actual observation. this also starts the mount tracking
                self.announce(f'Executing {qcomment}')
                if i==0:
                    self.log(f'handling the i=0 case')
                    #self.do(f'robo_set_qcomment "{qcomment}"')
                    #system = 'robo routine'
                    
                    # observe the focus location
                    
                    # be prepared to cycle through targets until one works
                    firstObsComplete = False
                    for target in self.config['focus_loop_param']['targets']:
                        focus_target_type = self.config['focus_loop_param']['targets'][target]['target_type']
                        focus_target = self.config['focus_loop_param']['targets'][target]['target']
                        
                        
                        
                        try:
                            print(f'Focus Loop Running in Thread: {threading.get_ident()}')
                            #raise TargetError('what happens if i explicitly raise an error???')
                            self.do(f'robo_observe {focus_target_type} {focus_target} -foc --comment "{qcomment}"')
                            
                            # check if the observation was completed successfully
                            if self.observation_completed:
                                self.announce(f'completed critical first observation, on to the rest...')
                                # if we get here, then break out of the loop!
                                firstObsComplete = True
                                break
                            
                            else:
                                # if the problem was a target issue, try we'll try a new target
                                if self.target_ok == False:
                                    # if we're here, it means (probably) that there's some ephemeris near the target. go try another target
                                    self.announce(f'could not observe focus target, TargetError: type = {focus_target_type}, target = ({focus_target}), trying next one...')
                                
                                # if it was some other error, all bets are off. just bail.
                                else:
                                    #if we're here there's some generic error. raise it.
                                    self.announce(f'could not observe focus target exiting...')
                                    return
                            #self.target_ok = True
                            #self.observation_completed = False
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
                            self.announce(f'could not observe focus target (error: {e}), exiting...')
                            raise Exception(e)
                            return
                         
                    if firstObsComplete:
                        pass
                    else:
                        # if we get down to here then we ran out of targets. stop what's happening
                        self.announce(f'could not observe ANY of the focus targets from the list. exiting...')
                        return
                            
                    
                else:
                    system = 'ccd'
                    self.do(f'robo_do_exposure --comment "{qcomment}" -foc ')

                
                
                
                
                
                image_directory, image_filename = self.ccd.getLastImagePath()
                image_filepath = os.path.join(image_directory, image_filename)
                
                # add the filter position and image path to the list to analyze
                focuser_pos.append(dist)
                images.append(image_filepath)
                self.log("focus image added to list")            
                
            except Exception as e:
                msg = f'roboOperator: could not run focus loop due to error with {system} due to {e.__class__.__name__}, {e}'
                self.log(msg)
                self.alertHandler.slack_log(f'*ERROR:* {msg}', group = None)
                err = roboError(context, self.lastcmd, system, msg)
                self.hardware_error.emit(err)
                return
            # increase the image number counter
            i += 1
        # print out the files and positions to the terminal
        print("FOCUS LOOP DATA:")
        for i in range(len(focuser_pos)):
            print(f'     [{i+1}] Focuser Pos: {focuser_pos[i]}, {images[i]}')
        
        # handle what to do in test mode
        if self.test_mode:
            focuser_pos = [9761.414819232772, 9861.414819232772, 9961.414819232772, 10061.414819232772, 10161.414819232772]
            images = ['/home/winter/data/images/20220119/SUMMER_20220119_221347_Camera0.fits',
                      '/home/winter/data/images/20220119/SUMMER_20220119_221444_Camera0.fits',
                      '/home/winter/data/images/20220119/SUMMER_20220119_221541_Camera0.fits',
                      '/home/winter/data/images/20220119/SUMMER_20220119_221641_Camera0.fits',
                      '/home/winter/data/images/20220119/SUMMER_20220119_221741_Camera0.fits']
        
        
        # save the data to a csv for later access
        try:
            data = {'images': images, 'focuser_pos' : list(focuser_pos)}
            df = pd.DataFrame(data)
            df.to_csv(image_log_path + 'focusLoop' + self.state['mount_timestamp_utc'] + '.csv')
        
        except Exception as e:
            msg = f'Unable to save files to focus csv due to {e.__class__.__name__}, {e}'
            self.log(msg)
        
        
        system = 'focuser'
        # fit the data and find the best focus
        try:
            # drive back to start position so we approach from same direction
            self.log(f'Focuser re-aligning at pre-start position: focuser_start_pos')
            while (cur_focus > focuser_start_pos):
                next_pos = max([cur_focus-100,focuser_start_pos])
                print(f"Current focus: {cur_focus} -> {next_pos}")
                # self.do(f'm2_focuser_goto {focuser_start_pos}')
                self.do(f'm2_focuser_goto {next_pos}')
                cur_focus = next_pos

            # self.do(f'm2_focuser_goto {focuser_start_pos}')
            
            if self.sunsim:
                #TODO: needs testing to be sure this is right...
                obstime_mjd = self.ephem.state.get('mjd',0)
                obstime = astropy.time.Time(obstime_mjd, format = 'mjd', \
                                            location=self.ephem.site)
                obstime_timestamp_utc = obstime.datetime.timestamp()
            else:
                obstime_timestamp_utc = datetime.now(tz = pytz.UTC).timestamp()
            
            # now analyze the data (rate the images and load the observed filterpositions)
            x0_fit, x0_err = loop.analyzeData(focuser_pos, images)
            
            loop.plot_focus_curve(timestamp_utc = obstime_timestamp_utc)
            
            
            #print(f'x0_fit = {x0_fit}, type(x0_fit) = {type(x0_fit)}')
            #print(f'x0_err = {x0_err}, type(x0_err) = {type(x0_err)}')
            
            self.announce(f'Fit Results: x0 = [{x0_fit:.0f} +/- {x0_err:.0f}] microns ({(x0_err/x0_fit*100):.0f}%)')
            
            # validate that the fit was good enough
            if x0_err > self.config['focus_loop_param']['focus_error_max']:
                self.announce(f'FIT IS TOO BAD. Returning to nominal focus')
                self.do(f'm2_focuser_goto {nom_focus}')
                self.focus_attempt_number +=1 
            
            else:
                self.logger.info(f'Focuser_going to final position at {x0_fit} microns')

                while (cur_focus < x0_fit):
                    next_pos = min([cur_focus+100,x0_fit])
                    print(f"Current focus: {cur_focus} -> {next_pos}")
                    # self.do(f'm2_focuser_goto {focuser_start_pos}')
                    self.do(f'm2_focuser_goto {next_pos}')
                    cur_focus = next_pos

                self.do(f'm2_focuser_goto {x0_fit}')
                #TODO: update the focusTracker
                
                if updateFocusTracker:
                    
    
                    self.announce(f'updating the focus position of filter {filterID} to {x0_fit}, timestamp = {obstime_timestamp_utc}')

                    self.focusTracker.updateFilterFocus(filterID, x0_fit, obstime_timestamp_utc) 
               
                # we completed the focus! set the focus attempt number to zero
                self.focus_attempt_number = 0
                    
        except FileNotFoundError as e:
            self.log(f"You are trying to modify a catalog file or an image with no stars , {e}")
            pass

        except Exception as e:
            msg = f'roboOperator: could not run focus loop due to error with {system} due to {e.__class__.__name__}, {e}, traceback = {traceback.format_exc()}'
            self.log(msg)
            self.alertHandler.slack_log(f'*ERROR:* {msg}', group = None)
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
        return x0_fit
    
    
    def do_focus_sequence(self, filterIDs = 'active', focusType = 'default'):
        """
        run a focus loop for each of the filters specified
        
        filterIDs should be a list of filter IDs for the current camera
            
        """
        context = 'do_focus_sequence'
        system = ''
        
        
        if filterIDs == 'active':
            filterIDs = self.focusTracker.getActiveFilters()
        
        self.announce(f'running focus loops for filters: {filterIDs}')
        
        for filterID in filterIDs:
            self.announce(f'executing focus loop for filter: {filterID}')
            try:
                # step through each filter to focus, and run a focus loop
                # 1. change filter to filterID
                system = 'filter wheel'
                if self.cam == 'summer':
                    # get filter number
                    for position in self.config['filter_wheels'][self.cam]['positions']:
                        if self.config['filter_wheels'][self.cam]['positions'][position] == filterID:
                            filter_num = position
                        else:
                            pass
                        
                    self.do(f'command_filter_wheel {filter_num}')
                    
                # 2. do a focus loop!!
                system = 'focus_loop'
                
                # handle the loop parameters depending on what attempt this is:
                """
                if self.focus_attempt_number == 0:
                    total_throw = self.config['focus_loop_param']['sweep_param']['narrow']['total_throw']
                    nsteps = self.config['focus_loop_param']['sweep_param']['narrow']['nsteps']
                    nom_focus = 'last'
                    if focusType == 'default':    
                        focusType = 'Parabola'
                """
                #elif self.focus_attempt_number == 1:
                #if self.focus_attempt_number < self.config['focus_loop_param']['max_focus_attempts']:
                total_throw = self.config['focus_loop_param']['sweep_param']['wide']['total_throw']
                nsteps = self.config['focus_loop_param']['sweep_param']['wide']['nsteps']
                #nom_focus = 'default'
                nom_focus = 'last'
                focusType = 'Vcurve'
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
                self.do_focusLoop(nom_focus = nom_focus, 
                                  total_throw = total_throw, 
                                  nsteps = nsteps, 
                                  updateFocusTracker = True, 
                                  focusType = focusType)
                
                
                
            except Exception as e:
                msg = f'roboOperator: could not run focus loop due to error with {system} due to {e.__class__.__name__}, {e}, traceback = {traceback.format_exc()}'
                self.log(msg)
                self.alertHandler.slack_log(f'*ERROR:* {msg}', group = None)
                err = roboError(context, self.lastcmd, system, msg)
                self.hardware_error.emit(err)
                
                # increment the focus loop number
                self.focus_attempt_number += 1
                
                return
                
            
    def do_currentObs(self, currentObs = 'default'):
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
        
        if currentObs == 'default':
            currentObs = self.schedule.currentObs
        
        self.check_ok_to_observe(logcheck = True)
        self.logger.info(f'self.running = {self.running}, self.ok_to_observe = {self.ok_to_observe}')
        
        if currentObs is None:
            """
            # NPL shouldn't ever get here, if we do just leave anc check what to do
            self.logger.info(f'robo: self.schedule.currentObs is None. Closing connection to db.')
            self.running = False
            
            self.handle_end_of_schedule()
            """
            self.checkWhatToDo()
            return
        
        
        # first get the dither parameters. put this first so we can set up the for loop through the dithers below
        # set up the dithers
        dither_scheduled = currentObs['dither']
        #print(f'dither_scheduled = {dither_scheduled}')
        if dither_scheduled.lower() == 'n':
            self.do_dithers = False
            self.num_dithers = 1
            
        elif dither_scheduled.lower() == 'y':
            self.do_dithers = True
            # set the dithers to the default
            ditherfile_path = self.default_ditherfile_path
            dither_ra_arcsec = self.default_dither_ra_arcsec
            dither_dec_arcsec = self.default_dither_dec_arcsec
            
            # insert a zero dither at the beginning of the list:
            dither_ra_arcsec = np.insert(dither_ra_arcsec, 0, 0.0)
            dither_dec_arcsec = np.insert(dither_dec_arcsec, 0, 0.0)
            
            self.num_dithers = len(dither_ra_arcsec)
        else:
            ditherfile_path = os.path.join(os.getenv("HOME"), dither_scheduled)
            if os.path.exists(ditherfile_path):
                self.do_dithers = True
                dither_ra_arcsec, dither_dec_arcsec = np.loadtxt(ditherfile_path, unpack = True)
                
                # insert a zero dither at the beginning of the list:
                dither_ra_arcsec = np.insert(dither_ra_arcsec, 0, 0.0)
                dither_dec_arcsec = np.insert(dither_dec_arcsec, 0, 0.0)
                
                self.num_dithers = len(dither_ra_arcsec)
            else:
                self.do_dithers = False
                self.num_dithers = 1
        
        
        
        # put the dither for loop here:
        for dithnum in range(self.num_dithers):
            
            # how many dithers remain AFTER this one?
            self.remaining_dithers = self.num_dithers - dithnum
            #self.log(f'top of loop: dithnum = {dithnum}, self.num_dithers = {self.num_dithers}, self.remaining_dithers = {self.remaining_dithers}')
            # for each dither, execute the observation
            if self.running & self.ok_to_observe:
                
                # grab some fields from the currentObs
                # NOTE THE RECASTING! Some of these things come out of the dataframe as np datatypes, which 
                # borks up the housekeeping and the dirfile and is a big fat mess
                #self.lastSeen = currentObs['obsHistID']
                self.obsHistID = int(currentObs['obsHistID'])
                self.ra_deg_scheduled = float(currentObs['raDeg'])
                self.dec_deg_scheduled = float(currentObs['decDeg'])
                self.filter_scheduled = str(currentObs['filter'])
                self.visitExpTime = float(currentObs['visitExptime'])
                self.targetPriority = float(currentObs['priority'])
                self.programPI = currentObs.get('progPI','')
                self.programID = int(currentObs.get('progID', -1))
                self.programName = currentObs.get('progName','')

                self.fieldID = int(currentObs.get('fieldID', -1)) # previously was using 999999999 but that's annoying :D
                
                
                """ 
                self.ra_radians_scheduled = float(currentObs['fieldRA'])
                self.dec_radians_scheduled = float(currentObs['fieldDec'])
                
                self.alt_deg_scheduled = float(currentObs['altitude'])
                self.az_deg_scheduled = float(currentObs['azimuth'])            
                """
                # convert ra and dec from radians to astropy objects
                self.j2000_ra_scheduled = astropy.coordinates.Angle(self.ra_deg_scheduled * u.deg)
                self.j2000_dec_scheduled = astropy.coordinates.Angle(self.dec_deg_scheduled * u.deg)
                
                # get the target RA (hours) and DEC (degs) in units we can pass to the telescope
                self.target_ra_j2000_hours = self.j2000_ra_scheduled.hour
                self.target_dec_j2000_deg  = self.j2000_dec_scheduled.deg
                
                # calculate the current Alt and Az of the target 
                if self.sunsim:
                    obstime_mjd = self.ephem.state.get('mjd',0)
                    obstime_utc = astropy.time.Time(obstime_mjd, format = 'mjd', \
                                                location=self.ephem.site)
                else:
                    obstime_utc = astropy.time.Time(datetime.utcnow(), format = 'datetime')
                    
                frame = astropy.coordinates.AltAz(obstime = obstime_utc, location = self.ephem.site)
                j2000_coords = astropy.coordinates.SkyCoord(ra = self.j2000_ra_scheduled, dec = self.j2000_dec_scheduled, frame = 'icrs')
                local_coords = j2000_coords.transform_to(frame)
                self.local_alt_deg = local_coords.alt.deg
                self.local_az_deg = local_coords.az.deg
                
                #msg = f'executing observation of obsHistID = {self.lastSeen} at (alt, az) = ({self.alt_scheduled:0.2f}, {self.az_scheduled:0.2f})'
                
                # print out to the slack log a bunch of info (only once per target)
                if dithnum == 0:
                    #msg = f'Executing observation of obsHistID = {self.lastSeen}'
                    msg = f'Executing observation of obsHistID = {self.obsHistID}'
                    #self.qcomment = f'obsHistID = {self.lastSeen}, requestID = {self.requestID}'
                    self.qcomment = f'obsHistID = {self.obsHistID}'#', requestID = {self.requestID}'
                    self.announce(msg)
                    self.announce(f'>> Target (RA, DEC) = ({self.ra_radians_scheduled:0.2f} rad, {self.dec_radians_scheduled:0.2f} rad)')
                    
                    self.announce(f'>> Target (RA, DEC) = ({self.j2000_ra_scheduled.hour} h, {self.j2000_dec_scheduled.deg} deg)')
                    
                    self.announce(f'>> Target Current (ALT, AZ) = ({self.local_alt_deg} deg, {self.local_az_deg} deg)')
                
                if self.do_dithers:
                    self.announce(f'>> Executing Dither Number [{dithnum +1}/{self.num_dithers}]')
                
                # Do the observation
                
                context = 'do_currentObs'
                system = 'observation'
                try:
                    
                    # now dither the RA and DEC axes (don't do for dithnum = 0, that's the nominal pointing)
                    if dithnum > 0:
                        
                        self.do(f'mount_dither_arcsec ra {dither_ra_arcsec[dithnum]}')
                        self.do(f'mount_dither_arcsec dec {dither_dec_arcsec[dithnum]}')
                    
                    # 3: trigger image acquisition
                    #NPL 1-19-22 re-adding chopping up exposure time by number of dithers
                    self.exptime = float(currentObs['visitExpTime'])/self.num_dithers
                    self.logger.info(f'robo: making sure exposure time on ccd to is set to {self.exptime}')
                    
                    # changing the exposure can take a little time, so only do it if the exposure is DIFFERENT than the current
                    if self.exptime == self.state['ccd_exptime']:
                        self.log('requested exposure time matches current setting, no further action taken')
                        pass
                    else:
                        self.log(f'current exptime = {self.state["ccd_exptime"]}, changing to {self.exptime}')
                        self.do(f'ccd_set_exposure {self.exptime}')
                    
                    # changing the filter can take a little time so only do it if the filter is DIFFERENT than the current
                    system = 'filter wheel'
                    if self.cam == 'summer':
                        # get filter number
                        for position in self.config['filter_wheels'][self.cam]['positions']:
                            if self.config['filter_wheels'][self.cam]['positions'][position] == self.filter_scheduled:
                                filter_num = position
                            else:
                                pass
                        if filter_num == self.state['Viscam_Filter_Wheel_Position']:
                            self.log('requested filter matches current, no further action taken')
                        else:
                            self.log(f'current filter = {self.state["Viscam_Filter_Wheel_Position"]}, changing to {filter_num}')
                            self.do(f'command_filter_wheel {filter_num}')
                    
                    time.sleep(0.5)
                    
                    # do the observation. what we do depends on if we're in test mode
                    #self.announce(f'dither [{dithnum+1}/{self.num_dithers}]')

                    if dithnum == 0:
                        if self.test_mode:
                            self.announce(f'>> RUNNING IN TEST MODE: JUST OBSERVING THE ALT/AZ FROM SCHEDULE DIRECTLY')
                            #self.do(f'robo_observe_altaz {self.alt_deg_scheduled} {self.az_deg_scheduled}')
                            self.do(f'robo_observe altaz {self.alt_deg_scheduled} {self.az_deg_scheduled} --test')
                        else:
                            #self.do(f'robo_observe_radec {self.target_ra_j2000_hours} {self.target_dec_j2000_deg}')
                            self.do(f'robo_observe radec {self.target_ra_j2000_hours} {self.target_dec_j2000_deg} --science')
                        
                        
                        
                        
                    else:
                        system = 'ccd'
                        if self.test_mode:
                            self.announce(f'>> RUNNING IN TEST MODE: JUST OBSERVING THE ALT/AZ FROM SCHEDULE DIRECTLY')
                            self.do(f'robo_do_exposure --test')
                        else:
                            self.do(f'robo_do_exposure --science')
                    
                    # check if the observation was completed successfully
                    if self.observation_completed:
                        pass
                    
                    else:
                        # if the problem was a target issue, try we'll try a new target
                        if self.target_ok == False:
                            # if we're here, it means (probably) that there's some ephemeris near the target. go try another target
                            #msg = f'could not obserse target becase of target error (ephem nearby, etc). skipping this target...'
                            #self.announce(msg)
                            break
                        # if it was some other error, all bets are off. just bail.
                        else:
                            #if we're here there's some generic error. raise it.
                            self.announce(f'problem with this exposure, going to next...')
                            
                    
                    # it is now okay to trigger going to the next observation
                    # always log observation, but only gotoNext if we're on the last dither
                    if self.remaining_dithers == 0:
                        gotoNext = True
                        self.log_observation_and_gotoNext(gotoNext = gotoNext, logObservation = True)
                    else:
                        gotoNext = False
                        self.log_observation_and_gotoNext(gotoNext = gotoNext, logObservation = False)
                    #return #<- NPL 1/19/22 this return should never get executed, the log_observation_and_gotoNext call should handle exiting
                    
                except Exception as e:
                    
                    tb = traceback.format_exc()
                    msg = f'roboOperator: could not execute current observation due to {e.__class__.__name__}, {e}'#', traceback = {tb}'
                    self.log(msg)
                    err = roboError(context, self.lastcmd, system, msg)
                    self.hardware_error.emit(err)
                    #NPL 4-7-22 trying to get it to break out of the dither loop on error
                    break
                # if we got here the observation wasn't completed properly
                #return
                #self.gotoNext()
                # NPL 1/19/22: removing call to self.checkWhatToDo() 
                #self.checkWhatToDo()
                
                # 5: exit
                
                
                
            else:
                # if it's not okay to observe, then restart the robo loop to wait for conditions to change
                #self.restart_robo()
                # NPL 1/19/22: replacing call to self.checkWhatToDo() with break to handle dither loop
                #self.checkWhatToDo()
                break
            
            msg = f'got to the end of the dither loop, should go to top of loop?'
            #self.log(msg)
            #self.announce(msg)

            
        # if we got here, then we are out of the loop, either because we did all the dithers, or there was a problem
        self.checkWhatToDo()
    '''
    def gotoNext(self): 
        # NPL 12-16-21: this is now deprecated.
        
        
        #TODO: NPL 4-30-21 not totally sure about this tree. needs testing
        self.check_ok_to_observe(logcheck = True)
        if not self.ok_to_observe:
            # if it's not okay to observe, then restart the robo loop to wait for conditions to change
            if self.running:
                # if the robo operator is running then restart, if not just pass
                self.restart_robo()
            else:
                pass
            return
            
        if self.schedule.currentObs is not None and self.running:
            """self.logger.info('robo: logging observation')
            
            
            if self.state["ok_to_observe"]:
                    image_filename = str(self.lastSeen)+'.FITS'
                    image_filepath = os.path.join(self.writer.base_directory, self.config['image_directory'], image_filename) 
                    # self.telescope_mount.virtualcamera_take_image_and_save(imagename)
                    header_data = self.get_data_to_log()
                    # self.state.update(currentData)
                    # data_to_write = {**self.state}
                    #data_to_write = {**self.state, **header_data} ## can add other dictionaries here
                    #self.writer.log_observation(data_to_write, imagename)
                    self.writer.log_observation(header_data, image_filepath)"""
            
            # get the next observation
            self.announce('getting next observation from schedule database')
            self.schedule.gotoNextObs()
            
            # do the next observation and continue the cycle
            self.do_currentObs()
            
        else:  
            if self.schedule.currentObs is None:
                self.logger.info('robo: in log and goto next, but either there is no observation to log.')
            elif self.running == False:
                self.logger.info("robo: in log and goto next, but I caught a stop signal so I won't do anything")
                self.rotator_stop_and_reset()
            
            
            """
            # don't want to do this if we just paused the schedule. need to figure that out, mauybe move it to a new shutdown method?
            if not self.schedulefile_name is None:
                self.logger.info('robo: no more observations to execute. shutting down connection to schedule and logging databases')
                ## TODO: Code to close connections to the databases.
                self.schedule.closeConnection()
                self.writer.closeConnection()
            """
    '''           
    def log_observation_and_gotoNext(self, gotoNext = True, logObservation = True):
        #self.logger.info(f'robo: image timer finished, logging observation with option gotoNext = {gotoNext}')
        """
        if currentObs == 'default':
            currentObs = self.schedule.currentObs
        """
        #TODO: NPL 4-30-21 not totally sure about this tree. needs testing
        self.check_ok_to_observe(logcheck = True)
        if not self.ok_to_observe:
            # if it's not okay to observe, then restart the robo loop to wait for conditions to change
            #self.restart_robo()
            #return
            self.announce(f'in log_observation_and_gotoNext and it is no longer okay to observe!')
            self.announce(f'dome.Shutter_Status = {self.dome.Shutter_Status}')

            self.checkWhatToDo()
            
        else:    
    
            if self.schedule.currentObs is not None and self.running:
                if logObservation:
                    self.schedule.log_observation()
                    self.logger.info('robo: logging observation')
                
                """
                image_directory, image_filename = self.ccd.getLastImagePath()
                image_filepath = os.path.join(image_directory, image_filename)
            
                header_data = self.get_data_to_log(currentObs)
                
                if not self.test_mode:
                    # don't log if we're in test mode.
                    #self.writer.log_observation(header_data, image_filepath)
                    if logObservation:
                        self.schedule.log_observation()
                
                else:
                    self.log(f"in test mode, so won't actually log_observation")
                """
            else:  
                if currentObs is None:
                    self.logger.info('robo: in log and goto next, but there is no observation to log.')
                elif self.running == False:
                    self.logger.info("robo: in log and goto next, but I caught a stop signal so I won't do anything")
                
            if gotoNext:
                msg = f" we're done with the observation and logging process. go figure out what to do next"
                self.log(msg)
                self.checkWhatToDo()
        
        
    
    def handle_end_of_schedule(self):
        # this handles when we get to the end of the schedule, ie when next observation is None:
        self.logger.info(f'robo: handling end of schedule')
            
        # FIRST: stow the rotator
        self.rotator_stop_and_reset()
        
        # Now shut down the connection to the databases
        #self.logger.info(f'robo: closing connection to schedule and obslog databases')
        #self.schedule.closeConnection()
        #self.writer.closeConnection()
    
    def log_timer_finished(self):
        self.logger.info('robo: exposure timer finished.')
        self.waiting_for_exposure = False
    
    
    def doExposure(self, obstype = 'TEST', postPlot = True, qcomment = None):
        # test method for making sure the roboOperator can communicate with the CCD daemon
        # 3: trigger image acquisition
        #self.exptime = float(self.schedule.currentObs['visitExpTime'])#/len(self.dither_alt)
        
        #self.announce(f'in doExposure: self.running = {self.running}')
        self.observation_completed = False
        self.logger.info(f'robo: running ccd_do_exposure in thread {threading.get_ident()}')
        # if we got no comment, then do nothing
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
        
        # first check if any ephemeris bodies are near the target
        self.log('checking that target is not too close to ephemeris bodies')
        ephem_inview = self.ephemInViewTarget_AltAz(target_alt = self.state['mount_alt_deg'],
                                                    target_az = self.state['mount_az_deg'])
        
        # if doing a light exposure, make sure it's okay to open the shutter safely
        if obstype not in ['BIAS', 'DARK']:
            
            if not ephem_inview:
                self.log('ephem check okay: no ephemeris bodies in the field of view.')
                self.logger.info(f'robo: telling ccd to take exposure!')
                #self.do(f'ccd_do_exposure')
                #self.log(f'exposure complete!')
                pass
            else:
                msg = f'>> ephemeris body is too close to target! skipping...'
                #self.log(msg)
                #self.alertHandler.slack_log(msg, group = 'sudo')
                #self.gotoNext()
                #NOTE: NPL 9-27-21: don't want to put a gotoNext here b ecause it will start the schedule even if we're not running one yet
                self.log(msg)
                self.alertHandler.slack_log(msg, group = None)
                self.target_ok = False
                raise TargetError(msg)
                
                #return
        
        # do the exposure and wrap with appropriate error handling
        system = 'ccd'
        context = 'robo doExposure'
        self.logger.info(f'robo: telling ccd to take exposure!')
        
        # pass the correct options to the ccd daemon
        obstype_dict = dict({'FLAT'     : '-f',
                             'BIAS'     : '-b',
                             'DARK'     : '-d',
                             'POINTING' : '-p',
                             'SCIENCE'  : '-s',
                             'TEST'     : '-t',
                             'FOCUS'    : '-foc'})
        
        obstype_option = obstype_dict.get(obstype, '')
        
        try:
            
            if obstype == 'BIAS':
                self.do('ccd_do_bias')
            else:
                self.do(f'ccd_do_exposure {obstype_option}')
            
            
        except Exception as e:
            msg = f'roboOperator: could not set up {system} due to {e.__class__.__name__}, {e}'
            self.log(msg)
            err = roboError(context, self.lastcmd, system, msg)
            self.hardware_error.emit(err)
            self.target_ok = False
            raise Exception(msg)
            return
        
        # if we get to here then we have successfully saved the image
        self.log(f'exposure complete!')
        if postPlot:
            # make a jpg of the last image and publish it to slack!
            postImage_process = subprocess.Popen(args = ['python','plotLastImg.py'])
        
        # if we got here, the observation was complete
        self.observation_completed = True
    
    def do_observation(self, targtype, target = None, tracking = 'auto', field_angle = 'auto', obstype = 'TEST', comment = ''):
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
        context = 'do_observation'
        
        self.log(f'doing observation: targtype = {targtype}, target = {target}, tracking = {tracking}, field_angle = {field_angle}')
        print(f'do_observation running in thread: {threading.get_ident()}')
        #### FIRST MAKE SURE IT'S OKAY TO OBSERVE ###
        self.check_ok_to_observe(logcheck = True)
        self.logger.info(f'self.running = {self.running}, self.ok_to_observe = {self.ok_to_observe}')
        
        #TODO Uncomment this, for now it's commented out so that we can test with the dome closed
        # NPL 7-28-21
        
        if self.ok_to_observe:
            pass
        else:
            
            return
        
        ### Validate the observation ###
        # just make it lowercase to avoid any case issues
        targtype = targtype.lower()
        # set the target type
        self.targtype = targtype
        
        # update the observation type: DO THIS THRU ROBO OPERATOR SO WE'RE SURE IT'S SET
        #self.doTry(f'robo_set_obstype {obstype}', context = context, system = '')
        
        # update the qcomment
        if comment != '':
            self.doTry(f'robo_set_qcomment {comment}')
        
        # first do some quality checks on the request
        # observation type
        #allowed_obstypes = ['schedule', 'altaz', 'radec']
        # for now only allow altaz, and we'll add on more as we go
        allowed_targtypes = ['altaz', 'object', 'radec']
        
        # raise an exception is the type isn't allwed
        if not (targtype in allowed_targtypes):
            self.log(f'improper observation type {targtype}, must be one of {allowed_targtypes}')
            return
        else:
            self.log(f'initiating observation type {targtype}')
        self.log('checking tracking')
        try:
            # raise an exception if tracking isn't a bool or 'auto'
            assert ((not type(tracking) is bool) or (tracking.lower() != 'auto')), f'tracking option must be bool or "auto", got {tracking}'
            
            self.log('checking field_angle')
            # raise an exception if field_angle isn't a float or 'auto'
            assert ((not type(field_angle) is float) or (field_angle.lower() != 'auto')), f'field_angle option must be float or "auto", got {field_angle}'
        except Exception as e:
                self.log(f'Problem while vetting observation: {e}')
                
        # now check that the target is appropriate to the observation type
        if targtype == 'altaz':
            try:
                # make sure it's a tuple
                assert (type(target) is tuple), f'for {targtype} observation, target must be a tuple. got type = {type(target)}'
                
                # make sure it's the right length
                assert (len(target) == 2), f'for {targtype} observation, target must have 2 coordinates. got len(target) = {len(target)}'
                
                # make sure they're floats
                assert ( (type(target[0]) is float) & (type(target[0]) is float) ), f'for {targtype} observation, target vars must be floats'
            except Exception as e:
                self.log(f'Problem while vetting observation: {e}')
            # get the target alt and az
            self.target_alt = target[0]
            self.target_az  = target[1]
            msg = f'Observing [{obstype}] Target @ (Alt, Az) = {self.target_alt:0.2f}, {self.target_az:0.2f}'
            self.alertHandler.slack_log(msg, group = None)

            self.log(f'target: (alt, az) = {self.target_alt:0.2f}, {self.target_az:0.2f}')
            try:
                # calculate the nominal target ra and dec
                alt_object = astropy.coordinates.Angle(self.target_alt*u.deg)
                az_object = astropy.coordinates.Angle(self.target_az*u.deg)
                obstime = astropy.time.Time(datetime.utcnow(), \
                                    location=self.ephem.site)
                
                altaz = astropy.coordinates.SkyCoord(alt = alt_object, az = az_object, 
                                                     location = self.ephem.site, 
                                                     obstime = obstime, 
                                                     frame = 'altaz')
                j2000 = altaz.transform_to('icrs')
                self.target_ra_j2000_hours = j2000.ra.hour
                self.target_dec_j2000_deg = j2000.dec.deg
                ra_deg = j2000.ra.deg
                msg = f'target: (ra, dec) = {self.target_ra_j2000_hours:0.1f}, {self.target_dec_j2000_deg:0.1f}'
                self.log(msg)
            except Exception as e:
                self.log(f'badness getting target nominal ra/dec: {e}')
            
            if tracking.lower() == 'auto':
                tracking = True
            else:
                pass
        elif targtype == 'radec':
            try:
                # make sure it's a tuple
                assert (type(target) is tuple), f'for {targtype} observation, target must be a tuple. got type = {type(target)}'
                
                # make sure it's the right length
                assert (len(target) == 2), f'for {targtype} observation, target must have 2 coordinates. got len(target) = {len(target)}'
                
                # make sure they're floats
                #self.log(f'Targ[0]: val = {target[0]}, type = {type(target[0])}')
                assert ( (type(target[0]) is float) & (type(target[1]) is float) ), f'for {targtype} observation, target vars must be floats'
            except Exception as e:
                self.log(f'Problem while vetting observation: {e}')
            # get the target RA (hours) and DEC (degs)
            self.target_ra_j2000_hours = target[0]
            self.target_dec_j2000_deg = target[1]
            
            msg = f'Observing [{obstype}] Target @ (RA, DEC) = {self.target_ra_j2000_hours:0.2f}, {self.target_dec_j2000_deg:0.2f}'
            self.alertHandler.slack_log(msg, group = None)
            
            #j2000_coords = astropy.coordinates.SkyCoord.from_name(obj, frame = 'icrs')
            j2000_ra = self.target_ra_j2000_hours * u.hour
            j2000_dec = self.target_dec_j2000_deg * u.deg
            j2000_coords = astropy.coordinates.SkyCoord(ra = j2000_ra, dec = j2000_dec, frame = 'icrs')

            ra_deg = j2000_coords.ra.deg
            
            if self.sunsim:
                obstime_mjd = self.ephem.state.get('mjd',0)
                obstime = astropy.time.Time(obstime_mjd, format = 'mjd', \
                                            location=self.ephem.site)
            else:
                obstime = astropy.time.Time(datetime.utcnow(),\
                                            location=self.ephem.site)
            
            #lat = astropy.coordinates.Angle(self.config['site']['lat'])
            #lon = astropy.coordinates.Angle(self.config['site']['lon'])
            #height = self.config['site']['height'] * u.Unit(self.config['site']['height_units'])
            #site = astropy.coordinates.EarthLocation(lat = lat, lon = lon, height = height)
            frame = astropy.coordinates.AltAz(obstime = obstime, location = self.ephem.site)
            local_coords = j2000_coords.transform_to(frame)
            self.target_alt = local_coords.alt.deg
            self.target_az = local_coords.az.deg
        
        elif targtype == 'object':
            # do some asserts
            # TODO
            self.log(f'handling object observations')
            # set the comment on the fits header 
            self.log(f'setting qcomment to {target}')
            self.qcomment = target
            # make sure it's a string
            if not (type(target) is str):
                self.log(f'for object observation, target must be a string object name, got type = {type(target)}')
                return
            
            
            
            try:
                obj = target
                
                j2000_coords = astropy.coordinates.SkyCoord.from_name(obj, frame = 'icrs')
                self.target_ra_j2000_hours = j2000_coords.ra.hour
                self.target_dec_j2000_deg = j2000_coords.dec.deg
                ra_deg = j2000_coords.ra.deg
                
                
                obstime = astropy.time.Time(datetime.utcnow(),\
                                            location=self.ephem.site)
                lat = astropy.coordinates.Angle(self.config['site']['lat'])
                lon = astropy.coordinates.Angle(self.config['site']['lon'])
                height = self.config['site']['height'] * u.Unit(self.config['site']['height_units'])
                                                
                site = astropy.coordinates.EarthLocation(lat = lat, lon = lon, height = height)
                frame = astropy.coordinates.AltAz(obstime = obstime, location = site)
                local_coords = j2000_coords.transform_to(frame)
                self.target_alt = local_coords.alt.deg
                self.target_az = local_coords.az.deg
                
                msg = f'Doing [{obstype}] observation of {target} @ (RA, DEC) = ({self.target_ra_j2000_hours:0.2f}, {self.target_dec_j2000_deg:0.2f})'
                msg+= f', (Alt, Az) = ({self.target_alt:0.2f}, {self.target_az:0.2f})'
                self.alertHandler.slack_log(msg, group = None)
                
            except Exception as e:
                self.log(f'error getting object coord: {e}')
        
        
        else:
            # we shouldn't ever get here because of the upper asserts
            return
        
        
        # handle the field angle
        if field_angle.lower() == 'auto':
            self.target_field_angle = self.config['telescope']['rotator_field_angle_zeropoint']
        else:
            self.target_field_angle = field_angle

        ####### Check if field angle will violate cable wrap limits
        #                 and adjust as needed.

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
                self.config['telescope']['rotator_min_degs'] \
                and predicted_rotator_mechangle < \
                self.config['telescope']['rotator_max_degs']):
                print("No rotator wrap predicted")
                self.target_mech_angle = predicted_rotator_mechangle
                
            if (predicted_rotator_mechangle < \
                self.config['telescope']['rotator_min_degs']):
                print("Rotator wrapping < min, adjusting")
                self.target_field_angle -= 360.0
                self.target_mech_angle = predicted_rotator_mechangle + 360.0
                print(f"Adjusted field angle --> {self.target_field_angle}")
                print(f"New target mech angle = {self.target_mech_angle}")
                
            if (predicted_rotator_mechangle > \
                self.config['telescope']['rotator_max_degs']):
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


        
        #### Validate the observation ###
        # check if alt and az are in allowed ranges
        not_too_low = (self.target_alt >= self.config['telescope']['min_alt'])
        not_too_high = (self.target_alt <= self.config['telescope']['max_alt'])
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
            msg = f'>> do_observation: target not within view! {reason} skipping...'
            print(msg)
            self.log(msg)
            self.alertHandler.slack_log(msg, group = None)
            self.target_ok = False
            #raise TypeError(msg)#TargetError(msg)
            raise TimeoutError(msg)
            print('I got below the exeption... this is bad :(')
            #return
        
        # now check if the target alt and az are too near the tracked ephemeris bodies
        # first check if any ephemeris bodies are near the target
        self.log('checking that target is not too close to ephemeris bodies')
        ephem_inview = self.ephemInViewTarget_AltAz(target_alt = self.target_alt,
                                                    target_az = self.target_az)
        
        if not ephem_inview:
            self.log('ephem check okay: no ephemeris bodies in the field of view.')
            
            pass
        else:
            msg = f'>> ephemeris body is too close to target! skipping...'
            self.log(msg)
            self.alertHandler.slack_log(msg, group = None)
            self.target_ok = False
            raise TargetError(msg)
            #return            
       
        # if we get here the target is okay
        self.target_ok = True
        
        ### SLEW THE DOME ###
        # start with the dome because it can take forever
        
        system = 'dome'
        try:
            # turn off dome tracking while slewing
            self.do('dome_tracking_off')
            
            self.do(f'dome_goto {self.target_az}')
            
            time.sleep(5)
            
            # turn tracking back on 
            #self.do('dome_tracking_on')
            
        except Exception as e:
            msg = f'roboOperator: could not set up {system} due to {e.__class__.__name__}, {e}'
            self.log(msg)
            err = roboError(context, self.lastcmd, system, msg)
            self.hardware_error.emit(err)
            self.target_ok = False
            return
            
            
        ### SLEW THE TELESCOPE ###
        # start with the dome because it can take forever
        
        system = 'telescope'
        try:
            
            if targtype == 'altaz':
                # slew to the requested alt/az
                self.do(f'mount_goto_alt_az {self.target_alt} {self.target_az}')
            
            elif targtype in ['radec', 'object']:
                # slew to the requested ra/dec
                self.logger.info(f'robo: mount_goto_ra_dec_j2000 running in thread {threading.get_ident()}')
                self.do(f'mount_goto_ra_dec_j2000 {self.target_ra_j2000_hours} {self.target_dec_j2000_deg}')
            
            # turn on tracking
            if tracking:
                self.do(f'mount_tracking_on')
            """
            #I SHOULDN'T HAVE TO WAIT FOR ALL THIS HERE!
            ## Wait until end condition is satisfied, or timeout ##
            timeout = 60
            # wait for the telescope to stop moving before returning
            # create a buffer list to hold several samples over which the stop condition must be true
            n_buffer_samples = self.config.get('cmd_satisfied_N_samples')
            stop_condition_buffer = [(False) for i in range(n_buffer_samples)]
    
            # get the current timestamp
            start_timestamp = datetime.utcnow().timestamp()
            while True:
                #print('entering loop')
                time.sleep(self.config['cmd_status_dt'])
                timestamp = datetime.utcnow().timestamp()
                dt = (timestamp - start_timestamp)
                #print(f'wintercmd: wait time so far = {dt}')
                if dt > timeout:
                    raise TimeoutError(f'command timed out after {timeout} seconds before completing')
                
                stop_condition = (self.telescope.state["mount.is_slewing"] != True)
                # do this in 2 steps. first shift the buffer forward (up to the last one. you end up with the last element twice)
                stop_condition_buffer[:-1] = stop_condition_buffer[1:]
                # now replace the last element
                stop_condition_buffer[-1] = stop_condition
                print(f'stop conition = {stop_condition}')
                if all(entry == True for entry in stop_condition_buffer):
                    break 
            
            #time.sleep(3)
            """
            # slew the rotator
            self.do(f'rotator_goto_field {self.target_field_angle}')
            # self.do(f'rotator_goto_mech {self.target_mech_angle}')
            time.sleep(3)
            # if(tracking):
            #     self.do(f'mount_tracking_on')
            
            self.current_mech_angle = self.target_mech_angle
            
        except Exception as e:
            msg = f'roboOperator: could not set up {system} due to {e.__class__.__name__}, {e}'
            self.log(msg)
            err = roboError(context, self.lastcmd, system, msg)
            self.hardware_error.emit(err)
            self.target_ok = False
            return
        
        ### TURN DOME TRACKING BACK ON ###
        
        system = 'dome'
        try:
            # turn tracking back on
            self.do('dome_tracking_on')
            
        except Exception as e:
            msg = f'roboOperator: could not set up {system} due to {e.__class__.__name__}, {e}'
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
        system = 'ccd'
        self.logger.info(f'robo: telling ccd to take exposure!')
        """try:
            self.do(f'ccd_do_exposure')"""
        # pass the correct options to the ccd daemon
        obstype_dict = dict({'FLAT'     : '-f',
                             'BIAS'     : '-b',
                             'DARK'     : '-d',
                             'POINTING' : '-p',
                             'SCIENCE'  : '-s',
                             'TEST'     : '-t',
                             'FOCUS'    : '-foc'})
        
        obstype_option = obstype_dict.get(obstype, '')
        
        try:
            self.do(f'ccd_do_exposure {obstype_option}')
            
            
        except Exception as e:
            tb = traceback.format_exc()
            msg = f'roboOperator: could not set up {system} due to {e.__class__.__name__}, {e}'#', traceback: {tb}'
            self.log(msg)
            err = roboError(context, self.lastcmd, system, msg)
            self.hardware_error.emit(err)
            self.target_ok = False
            raise Exception(msg)
            return
        
        # if we get to here then we have successfully saved the image
        self.log(f'exposure complete!')
        
        # make a jpg of the last image and publish it to slack!
        postImage_process = subprocess.Popen(args = ['python','plotLastImg.py'])
        
        # the observation has been completed successfully :D
        self.observation_completed = True

    def remakePointingModel(self, append = False, firstpoint = 0):
        context = 'Pointing Model'
        self.alertHandler.slack_log('Setting Up a New Pointing Model!', group = None)
        if append:
            # if in append mode, don't clear the old points
            pass
        else:
            # clear the current pointing model
            self.do('mount_model_clear_points')
        
        time.sleep(2)
        
        # load up the points
        pointlist_filepath = os.path.join(os.getenv("HOME"), self.config['pointing_model']['default_pointlist'])
        self.pointingModelBuilder.load_point_list(pointlist_filepath)
        
        # now go through the list one by one, and observe each point!
        altaz_mapped = []
        radec_mapped = []
        # how many points are there to do?
        npoints = len(self.pointingModelBuilder.altaz_points)
        
        for i in np.arange(firstpoint-1, npoints, 1):
            altaz_point = self.pointingModelBuilder.altaz_points[i]
            target_alt = altaz_point[0]
            target_az  = altaz_point[1]
            

            self.alertHandler.slack_log(f'Target {i+1}/{npoints}:')
            
            
            system = 'Observe and Platesolve'
            try:
            
                # do the observation
                #self.do(f'robo_observe_altaz {target_alt} {target_az}')
                self.do(f'robo_observe altaz {target_alt} {target_az} --pointing')
                
                if self.target_ok:
                    
                    #time.sleep(10)
                    # ADD A CASE TO HANDLE SITUATIONS WHERE THE OBSERVATION DOESN'T WORK
                        
                    # platesolve the image
                    #TODO: fill this in from the config instead of hard coding
                    lastimagefile = os.readlink(os.path.join(os.getenv("HOME"), 'data', 'last_image.lnk'))
                    #lastimagefile = os.path.join(os.getenv("HOME"), 'data','images','20210730','SUMMER_20210730_043149_Camera0.fits')
                    
                    # check if file exists
                    imgpath = pathlib.Path(lastimagefile)
                    timeout = 20
                    dt = 0.5
                    t_elapsed = 0
                    self.log(f'waiting for image path {lastimagefile}')
                    while t_elapsed < timeout:
                        
                        file_exists = imgpath.is_file()
                        self.log(f'Last Image File Exists? {file_exists}')
                        if file_exists:
                            break
                        else:
                            time.sleep(dt) 
                            t_elapsed += dt
                    
                    
                    msg = f'running platesolve on image: {lastimagefile}'
                    self.log(msg)
                    print(msg)
                    solved = self.pointingModelBuilder.plateSolver.platesolve(lastimagefile, 0.47)
                    if solved:
                        ra_j2000_hours = self.pointingModelBuilder.plateSolver.results.get('ra_j2000_hours')
                        dec_j2000_degrees = self.pointingModelBuilder.plateSolver.results.get('dec_j2000_degrees')
                        platescale = self.pointingModelBuilder.plateSolver.results.get('arcsec_per_pixel')
                        field_angle = self.pointingModelBuilder.plateSolver.results.get('rot_angle_degs')
                        
                        ra_j2000 = astropy.coordinates.Angle(ra_j2000_hours * u.hour)
                        dec_j2000 = astropy.coordinates.Angle(dec_j2000_degrees * u.deg)
                        
                        ######################################################################
                        ### RUN IN SIMULATION MODE ###
                        # Get the nominal RA/DEC from the fits header. Could do this different ways.
                        #TODO: is this the approach we want? should it calculate it from the current position instead?
                        hdu_list = fits.open(lastimagefile,ignore_missing_end = True)
                        header = hdu_list[0].header
                        
                        ra_j2000_nom = astropy.coordinates.Angle(header["RA"], unit = 'deg')
                        dec_j2000_nom = astropy.coordinates.Angle(header["DEC"], unit = 'deg')
                        ######################################################################""
                        
                        self.log('RUNNING PLATESOLVE ON LAST IMAGE')
                        self.log(f'Platesolve Astrometry Solution: RA = {ra_j2000.to_string("hour")}, DEC = {dec_j2000.to_string("deg")}')
                        self.log(f'Nominal Position:               RA = {ra_j2000_nom.to_string("hour")}, DEC = {dec_j2000_nom.to_string("deg")}')
                        self.log(f'Platesolve:     Platescale = {platescale:.4f} arcsec/pix, Field Angle = {field_angle:.4f} deg')
                        """
                        #TODO: REMOVE THIS
                        # overwrite the solution with the nominal values so we can actually get a model
                        ra_j2000_hours = self.target_ra_j2000_hours
                        dec_j2000_degrees = self.target_dec_j2000_deg
                        """
                        msg = f'Adding model point (alt, az) = ({self.target_alt:0.1f}, {self.target_az:0.1f}) --> (ra, dec) = ({ra_j2000_hours:0.2f}, {dec_j2000_degrees:0.2f}), Nominal (ra, dec) = ({ra_j2000_nom.hour:0.2f}, {dec_j2000_nom.deg:0.2f})'
                        self.alertHandler.slack_log(msg, group = None)
                        # add the RA_hours and DEC_deg point to the telescope pointing model
                        self.doTry(f'mount_model_add_point {ra_j2000_hours} {dec_j2000_degrees}')
        
                        radec_mapped.append((ra_j2000_hours, dec_j2000_degrees))
                        altaz_mapped.append((self.target_alt, self.target_az))
                    else:
                        msg = f'> platesolve could not find a solution :( '
                        self.log(msg)
                        self.alertHandler.slack_log(msg)
                
            except Exception as e:
                msg = f'roboOperator: could not set up {system} due to {e.__class__.__name__}, {e}'
                self.log(msg)
                err = roboError(context, self.lastcmd, system, msg)
                self.hardware_error.emit(err)
                #return
        
        self.log(f'finished getting all the new points!')
        self.log(f'saving points')
        self.savePointingModePoints(altaz_tuple = altaz_mapped, radec_tuple = radec_mapped)
        
        
    def savePointingModePoints(self, altaz_tuple, radec_tuple, filename = ''):
        if filename == '':
            outfile = os.path.join(os.getenv("HOME"), 'data','current_pointing_model_points.txt')
        else:
            outfile = filename
        
        altlist, azlist = zip(*altaz_tuple)
        ralist, declist = zip(*radec_tuple)
        
        out = np.column_stack((altlist, azlist, ralist, declist))
        
        np.savetxt(outfile,out,
                   delimiter = '\t',
                   comments = '# ',
                   header = 'Alt (deg) Az (deg) RA (hour) DEC (deg)')
            
 
        
    def ephemInViewTarget_AltAz(self, target_alt, target_az, obstime = 'now', time_format = 'datetime'):
        # check if any of the ephemeris bodies are too close to the given target alt/az
        inview = list()
        for body in self.config['ephem']['min_target_separation']:
            mindist = self.config['ephem']['min_target_separation'][body]
            dist = ephem_utils.getTargetEphemDist_AltAz(target_alt = target_alt,
                                                        target_az = target_az,
                                                        body = body,
                                                        location = self.ephem.site,
                                                        obstime = obstime,
                                                        time_format = time_format)
            if dist < mindist:
                inview.append(True)
            else:
                inview.append(False)
    
        if any(inview):
            return True
        else:
            return False
    
    
