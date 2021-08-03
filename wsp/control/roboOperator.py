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
import json
import logging
import threading
import astropy.time
import astropy.coordinates
import astropy.units as u
from astropy.io import fits
import pathlib
import subprocess

# add the wsp directory to the PATH
wsp_path = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(1, wsp_path)

from utils import utils
from schedule import schedule
from schedule import ObsWriter
from ephem import ephem_utils
from telescope import pointingModelBuilder

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

class RoboOperatorThread(QtCore.QThread):
    """
    A dedicated thread to handle all the robotic operations!
    
    This is basically a thread to handle all the commands which get sent in 
    robotic mode
    """
    
    # this signal is connected to the RoboOperator's start_robo method
    restartRoboSignal = QtCore.pyqtSignal()
    
    # this signal is typically emitted by wintercmd, and is connected to the RoboOperators change_schedule method
    changeSchedule = QtCore.pyqtSignal(object)
    
    # this signal is typically emitted by wintercmd and is connected to the RoboOperator's do_currentObs method
    do_currentObs_Signal = QtCore.pyqtSignal()
    
    # this signal is typically emitted by wintercmd, it connected to RoboOperator's doExposure method.
    # this really just replicates calling ccd_do_exposure directly, but tests out all the connections between roboOperator and the ccd_daemon
    doExposureSignal = QtCore.pyqtSignal()
    
    # a generic do command signal for executing any command in robothread
    newCommand = QtCore.pyqtSignal(object)
    
    def __init__(self, base_directory, config, mode, state, wintercmd, logger, alertHandler, schedule, telescope, dome, chiller, ephem, viscam, ccd, mirror_cover):
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
                                     mirror_cover = self.mirror_cover
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

    

    def __init__(self, base_directory, config, mode, state, wintercmd, logger, alertHandler, schedule, telescope, dome, chiller, ephem, viscam, ccd, mirror_cover):
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
    
        
        ### SET UP THE WRITER ###
        # init the database writer
        writerpath = self.config['obslog_directory'] + '/' + self.config['obslog_database_name']
        #self.writer = ObsWriter.ObsWriter('WINTER_ObsLog', self.base_directory, config = self.config, logger = self.logger) #the ObsWriter initialization
        self.writer = ObsWriter.ObsWriter(writerpath, self.base_directory, config = self.config, logger = self.logger) #the ObsWriter initialization
        # create an empty dict that will hold the data that will get written out to the fits header and the log db
        self.data_to_log = dict()
        
        ### SCHEDULE ATTRIBUTES ###
        # load the dither list
        self.dither_alt, self.dither_az = np.loadtxt(self.schedule.base_directory + '/' + self.config['dither_file'], unpack = True)
        # convert from arcseconds to degrees
        self.dither_alt *= (1/3600.0)
        self.dither_az  *= (1/3600.0)
        
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

        
        ### CONNECT SIGNALS AND SLOTS ###
        self.startRoboSignal.connect(self.restart_robo)
        self.stopRoboSignal.connect(self.stop)
        #TODO: is this right (above)? NPL 4-30-21
        
        self.hardware_error.connect(self.broadcast_hardware_error)
        
        self.telescope.signals.wrapWarning.connect(self.handle_wrap_warning)
        # change schedule. for now commenting out bc i think its handled in the robo Thread def
        #self.changeSchedule.connect(self.change_schedule)
        
        ## overrides
        """ REMEMBER TO CHANGE BACK FOR NORMAL OPERATION """
        # override the dome.ok_to_open flag
        self.dome_override = False
        # override the sun altitude flag
        self.sun_override = False
        
        # some variables that hold the state of the sequences
        self.startup_complete = False
        self.calibration_complete = False
        
        ### SET UP THE SCHEDULE ###
        self.lastSeen = -1
        ## in robotic mode, the schedule file is the nightly schedule
        if self.mode == 'r':
            self.schedulefile_name = 'nightly'
        ## in manual mode, the schedule file is set to None
        else:
            self.schedulefile_name = None
            
        # set up the schedule
        ## after this point we should have something in self.schedule.currentObs
        self.setup_schedule()
        
        
        
        # start up the robotic observing!
        if self.mode == 'r':
            # start the robo?
            self.restart_robo()        # make a timer that will control the cadence of checking the conditions
        
        ### SET UP POINTING MODEL BUILDER ###
        self.pointingModelBuilder = pointingModelBuilder.PointingModelBuilder()
        
    def broadcast_hardware_error(self, error):
        msg = f':redsiren: *{error.system.upper()} ERROR* ocurred when attempting command: *_{error.cmd}_*, {error.msg}'
        group = 'sudo'
        self.alertHandler.slack_log(msg, group = group)
        
        # turn off tracking
        self.rotator_stop_and_reset()
        
    def announce(self, msg):
        self.logger.info(f'robo: {msg}')
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
    
    def rotator_stop_and_reset(self):
        self.log(f'stopping rotator and resetting to home position')
        # turn off tracking
        self.doTry('mount_tracking_off')
        self.doTry('rotator_home')
        
    def handle_wrap_warning(self, angle):
        
        # create a notification
        msg = f'*WRAP WARNING!!* rotator angle {angle} outside allowed range [{self.config["telescope"]["rotator_min_degs"]},{self.config["telescope"]["rotator_max_degs"]}])'       
        context = ''
        system = 'rotator'
        cmd = self.lastcmd
        err = roboError(context, cmd, system, msg)
        # directly broadcast the error rather than use an event to keep it all within this event
        self.broadcast_hardware_error(err)
        self.log(msg)
        
        # STOP THE ROTATOR
        self.rotator_stop_and_reset()
        
        # got to the next observation
        self.gotoNext()
    
    def restart_robo(self):
        # run through the whole routine. if something isn't ready, then it waits a short period and restarts
        
        # if we're in this loop, the robotic schedule operator is running:
        self.running = True
        
        while True:
            # EXECUTE THE FULL ROBOTIC SEQUENCE
            # return statements will exit and stop the robotic sequence
            # every time there's a return there needs to be an error emitted
            if not self.startup_complete:
                # Do the startup routine
                self.do_startup()
                # If that didn't work, then return
                if not self.startup_complete:
                    return
                    #break
            # if we're done with the startup, continue
            if not self.calibration_complete:
                # do the calibration:
                self.do_calibration()
                # If that didn't work, then return
                if not self.calibration_complete:
                    return
                    #break
            
            self.check_ok_to_observe()
            if self.ok_to_observe:
                break
            else:
                time.sleep(0.5)
            
        # we escaped the loop!
        # if it's okay to observe, then do the first observation!
        self.logger.info(f'finished startup, calibration, and it is okay to observe: doing current observation')
        self.do_currentObs()
        return
        
    def check_ok_to_observe(self, logcheck = False):
        """
        check if it's okay to observe/open the dome
        
        
        # logcheck flag indicates whether the result of the check should be written to the log
            we want the result logged if we're checking from within the do_observing loop,
            but if we're just loopin through restart_robo we can safely ignore the constant logging'
        """
        
        # if the sun is below the horizon, or if the sun_override is active, then we want to open the dome
        if self.ephem.sun_below_horizon or self.sun_override:
            
            # make a note of why we want to open the dome
            if self.ephem.sun_below_horizon:
                #self.logger.info(f'robo: the sun is below the horizon, I want to open the dome.')
                pass
            elif self.sun_override:
                if logcheck:
                    self.logger.warning(f"robo: the SUN IS ABOVE THE HORIZON, but sun_override is active so I want to open the dome")
            else:
                # shouldn't ever be here
                if logcheck:
                    self.logger.warning(f"robo: I shouldn't ever be here. something is wrong with sun handling")
                self.ok_to_observe = False
                #return
                #break
            
            # if we can open up the dome, then do it!
            if (self.dome.ok_to_open or self.dome_override):
                
                # make a note of why we're going ahead with opening the dome
                if self.dome.ok_to_open:
                    #self.logger.info(f'robo: the dome says it is okay to open.')# sending open command.')
                    pass
                elif self.dome_override:
                    if logcheck:
                        self.logger.warning(f"robo: the DOME IS NOT OKAY TO OPEN, but dome_override is active so I'm sending open command")
                else:
                    # shouldn't ever be here
                    self.logger.warning(f"robo: I shouldn't ever be here. something is wrong with dome handling")
                    self.ok_to_observe = False
                    #return
                    #break
                
               
                
                # Check if the dome is open:
                if self.dome.Shutter_Status == 'OPEN':
                    if logcheck:
                        self.logger.info(f'robo: okay to observe check passed')
                    
                    #####
                    # We're good to observe
                    self.ok_to_observe = True
                    #break
                    #####
                
                else:
                    # dome is closed.
                    """
                    #TODO: this is weird. This function should either be just a status poll
                    that is executed regularly, or it should be only run rarely.
                    having the open command in here makes it kind of a weird in-between
                    
                    """
                    msg = f'robo: shutter is closed. attempting to open...'
                    self.announce(msg)
                     # SEND THE DOME OPEN COMMAND
                    self.doTry('dome_open', context = 'startup', system = 'dome')
                    self.logger.info(f'robo: error opening dome.')
                    self.ok_to_observe = False
                    
            else:
                # there is an issue with the dome
                
                self.ok_to_observe = False
                    
            
        else:
            # the sun is up
            self.ok_to_observe = False
        
        
            
            
    
    def setup_schedule(self):
        
        if self.schedulefile_name is None:
            # NPL 9-21-20: put this in for now so that the while loop in run wouldn't go if the schedule is None
            self.schedule.currentObs = None

        else:
            #print(f'scheduleExecutor: loading schedule file [{self.schedulefile_name}]')
            # code that sets up the connections to the databases
            self.getSchedule(self.schedulefile_name)
            self.writer.setUpDatabase()
    
        
    
    def getSchedule(self, schedulefile_name):
        self.schedule.loadSchedule(schedulefile_name, self.lastSeen+1)

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

        print(f'scheduleExecutor: setting up new schedule from file >> {schedulefile_name}')

        if self.running:
            self.stop()

        self.schedulefile_name = schedulefile_name
        
        #NPL 4-29-21:
        self.setup_schedule()

    def get_data_to_log(self):
        data = {}
        # First, handle all the keys from self.schedule.currentObs.
        # THESE ARE SPECIAL KEYS WHICH ARE REQUIRED FOR THE SCHEDULER TO WORK PROPERLY
        
        keys_with_actual_vals = ["dist2Moon", "expMJD", "visitExpTime", "azimuth", "altitude"]
        
        for key in self.schedule.currentObs:
            # Some entries need the scheduled AND actuals recorded
                    
            if key in keys_with_actual_vals:
                data.update({f'{key}_scheduled': self.schedule.currentObs[key]})
            else:
                data.update({key: self.schedule.currentObs[key]})
        
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
    
    def waitForCondition(self, condition, timeout = 60):
        ## Wait until end condition is satisfied, or timeout ##
        
        # wait for the telescope to stop moving before returning
        # create a buffer list to hold several samples over which the stop condition must be true
        n_buffer_samples = self.config.get('cmd_satisfied_N_samples')
        stop_condition_buffer = [(not condition) for i in range(n_buffer_samples)]

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
            
            stop_condition = (self.state['mount_is_slewing'])
            # do this in 2 steps. first shift the buffer forward (up to the last one. you end up with the last element twice)
            stop_condition_buffer[:-1] = stop_condition_buffer[1:]
            # now replace the last element
            stop_condition_buffer[-1] = stop_condition
            
            if all(entry == True for entry in stop_condition_buffer):
                break 
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
            msg = f'roboOperator: could not execute function {cmd} due to {e.__class__.__name__}, {e}'
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

    def wait_for_dome_clearance(self):
        """
        This should just run a QTimer which waits until one of several 
        things happens:
            1. the dome is okay to open. then it will restart_robo()
            2. the sun will come up and we'll miss our window. in this case,
               initiate shutdown
        """
        pass
    
    def do_startup(self):
        # this is for passing to errors
        context = 'do_startup'
        
        ### DOME SET UP ###
        system = 'dome'
        msg = 'starting dome startup...'
        self.announce(msg)

        try:
            # take control of dome        
            self.do('dome_takecontrol')
            
            #self.do('dome_tracking_off')
    
            # home the dome
            self.do('dome_home')
            
            #self.do('dome_tracking_off')
            
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
            # connect the telescope
            self.do('mount_startup')
            
            # turn on the rotator
            self.do('rotator_enable')

            # TURN ON WRAP CHECK 
            # NPL 08-03-21 turning this off, it's causing an error.
            #self.do('rotator_wrap_check_enable')
            
            
        
        except Exception as e:
            msg = f'roboOperator: could not set up {system} due to {e.__class__.__name__}, {e}'
            self.log(msg)
            self.alertHandler.slack_log(f'*ERROR:* {msg}', group = None)
            err = roboError(context, self.lastcmd, system, msg)
            self.hardware_error.emit(err)
            return
        self.announce(':greentick: telescope startup complete!')
        
        # turn on 
        
        # if we made it all the way to the bottom, say the startup is complete!
        self.startup_complete = True
            
        self.announce(':greentick: startup complete!')
        
    def do_calibration(self):
        
        context = 'do_calibration'
        
        self.logger.info('robo: doing calibration routine. for now this does nothing.')
        ### Take darks ###
        # Nothing here yet
        
        
        self.calibration_complete = True
    
    def do_currentObs(self):
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
        self.check_ok_to_observe(logcheck = True)
        self.logger.info(f'self.running = {self.running}, self.ok_to_observe = {self.ok_to_observe}')
        if self.running & self.ok_to_observe:
            
            # grab some fields from the currentObs
            self.lastSeen = self.schedule.currentObs['obsHistID']
            #self.alt_scheduled = float(self.schedule.currentObs['altitude'])
            #self.az_scheduled = float(self.schedule.currentObs['azimuth'])
            
            self.ra_radians_scheduled = float(self.schedule.currentObs['fieldRA'])
            self.dec_radians_scheduled = float(self.schedule.currentObs['fieldDec'])
            
            
            
            
            # convert ra and dec from radians to astropy objects
            self.j2000_ra_scheduled = astropy.coordinates.Angle(self.ra_radians_scheduled * u.rad)
            self.j2000_dec_scheduled = astropy.coordinates.Angle(self.dec_radians_scheduled * u.rad)
            
            # get the target RA (hours) and DEC (degs) in units we can pass to the telescope
            self.target_ra_j2000_hours = self.j2000_ra_scheduled.hour
            self.target_dec_j2000_deg  = self.j2000_dec_scheduled.deg
            
            # calculate the current Alt and Az of the target 
            obstime_utc = astropy.time.Time(datetime.utcnow(), format = 'datetime')
            frame = astropy.coordinates.AltAz(obstime = obstime_utc, location = self.ephem.site)
            j2000_coords = astropy.coordinates.SkyCoord(ra = self.j2000_ra_scheduled, dec = self.j2000_dec_scheduled, frame = 'icrs')
            local_coords = j2000_coords.transform_to(frame)
            self.local_alt_deg = local_coords.alt.deg
            self.local_az_deg = local_coords.az.deg
            
            #msg = f'executing observation of obsHistID = {self.lastSeen} at (alt, az) = ({self.alt_scheduled:0.2f}, {self.az_scheduled:0.2f})'
            msg = f'executing observation of obsHistID = {self.lastSeen}'
            self.announce(msg)
            
            self.announce(f'>> Target (RA, DEC) = ({self.ra_radians_scheduled:0.2f} rad, {self.dec_radians_scheduled:0.2f} rad)')
            
            self.announce(f'>> Target (RA, DEC) = ({self.j2000_ra_scheduled.hour} h, {self.j2000_dec_scheduled.deg} deg)')
            
            self.announce(f'>> Target Current (ALT, AZ) = ({self.local_alt_deg} deg, {self.local_az_deg} deg)')
            
            
            # Do the observation
            
            context = 'do_currentObs'
            system = 'observation'
            try:
                
                # 3: trigger image acquisition
                self.exptime = float(self.schedule.currentObs['visitExpTime'])#/len(self.dither_alt)
                self.logger.info(f'robo: making sure exposure time on ccd to is set to {self.exptime}')
                
                # changing the exposure can take a little time, so only do it if the exposure is DIFFERENT than the current
                if self.exptime == self.state['ccd_exptime']:
                    self.log('requested exposure time matches current setting, no further action taken')
                    pass
                else:
                    self.log(f'current exptime = {self.state["ccd_exptime"]}, changing to {self.exptime}')
                    self.do(f'ccd_set_exposure {self.exptime}')
                    
                time.sleep(0.5)
                
                
                
                self.do(f'robo_observe_radec {self.target_ra_j2000_hours} {self.target_dec_j2000_deg}')
                
                # it is now okay to trigger going to the next observation
                self.log_observation_and_gotoNext()
                return
                
            except Exception as e:
                msg = f'roboOperator: could not execute current observation due to {e.__class__.__name__}, {e}'
                self.log(msg)
                err = roboError(context, self.lastcmd, system, msg)
                self.hardware_error.emit(err)
            
            # if we got here the observation wasn't completed properly
            #return
            self.gotoNext()
            
            
            """
            
            # turn off dome tracking while slewing the telescope
            self.do('dome_tracking_off')
            
            # 1: point the telescope
            context = 'do_currentObs'
            system = 'telescope'
            try:
                
                
                
                # turn tracking back on
                self.do(f'rotator_enable')
                
                # TURN ON WRAP CHECK 
                self.do('rotator_wrap_check_enable')
                
                # don't turn the tracking on it will drift off. just leave the rotator enabled and tracking off and then do a goto RA/DEC
                #self.do(f'mount_tracking_on')
                
                # point the rotator to the home position
                self.do(f'rotator_home')
                
                
                
                # check if alt and az are in allowed ranges
                in_view = (self.local_alt_deg >= self.config['telescope']['min_alt']) & (self.local_alt_deg <= self.config['telescope']['max_alt'])
                if in_view:
                    pass
                else:
                    msg = f'>> target not within view! skipping...'
                    self.log(msg)
                    self.alertHandler.slack_log(msg, group = 'sudo')
                    self.gotoNext()
                    return
                
                # now check if the target alt and az are too near the tracked ephemeris bodies
                 # first check if any ephemeris bodies are near the target
                self.log('checking that target is not too close to ephemeris bodies')
                ephem_inview = self.ephemInViewTarget_AltAz(target_alt = self.local_alt_deg,
                                                            target_az = self.local_az_deg)
                
                if not ephem_inview:
                    self.log('ephem check okay: no ephemeris bodies in the field of view.')
                    
                    pass
                else:
                    msg = f'>> ephemeris body is too close to target! skipping...'
                    self.log(msg)
                    self.alertHandler.slack_log(msg, group = 'sudo')
                    self.gotoNext()
                    return
                
                
                '''
                # Launder the alt and az scheduled to RA/DEC
                self.lastcmd = 'convert_alt-az_to_ra-dec'
                #TODO: remove this! This is just a patch so that we can observe the schedule during the day
                az_angle = astropy.coordinates.Angle(self.az_scheduled * u.deg)
                alt_angle = astropy.coordinates.Angle(self.alt_scheduled * u.deg)
                obstime_utc = astropy.time.Time(datetime.utcnow(), format = 'datetime')
                
                
                altaz_coords = astropy.coordinates.SkyCoord(alt = alt_angle, az = az_angle,
                                                            obstime = obstime_utc,
                                                            location = self.ephem.site,
                                                            frame = 'altaz')
                j2000_coords = altaz_coords.transform_to('icrs')
                j2000_ra_hours = j2000_coords.ra.hour
                j2000_dec_deg = j2000_coords.dec.deg
                '''
                
                # slew the telscope
                #self.do(f'mount_goto_alt_az {self.alt_scheduled} {self.az_scheduled}')
                #self.do(f'mount_goto_ra_dec_j2000 {j2000_ra_hours} {j2000_dec_deg}')
                self.do(f'mount_goto_ra_dec_j2000 {self.j2000_ra_scheduled.hour} {self.j2000_dec_scheduled.deg}')
                
            except Exception as e:
                msg = f'roboOperator: could not set up {system} due to {e.__class__.__name__}, {e}'
                self.log(msg)
                err = roboError(context, self.lastcmd, system, msg)
                self.hardware_error.emit(err)
                return
            
            system = 'dome'
            try:
                self.do(f'dome_goto {self.local_az_deg}')
            except Exception as e:
                msg = f'roboOperator: could not set up {system} due to {e.__class__.__name__}, {e}'
                self.log(msg)
                err = roboError(context, self.lastcmd, system, msg)
                self.hardware_error.emit(err)
                return
            
            # now that the slew is finished, turn on the dome tracking
            # turn on dome tracking (of telescope)
            #self.do('dome_tracking_on')
            
            # 2: create the log dictionary & FITS header. save log dict to self.lastObs_record
            # for now this is happeningin the ccd_daemon, but we need to make this better
            # and get the info from the database, etc
            
            # 3: trigger image acquisition
            self.exptime = float(self.schedule.currentObs['visitExpTime'])#/len(self.dither_alt)
            self.logger.info(f'robo: setting exposure time on ccd to {self.exptime}')
            #self.ccd.setexposure(self.exptime)
            
            # changing the exposure can take a little time, so only do it if the exposure is DIFFERENT than the current
            if self.exptime == self.state['ccd_exptime']:
                self.log('requested exposure time matches current setting')
                pass
            else:
                self.do(f'ccd_set_exposure {self.exptime}')
                
            time.sleep(0.5)
            
            # do the exposure and wrap with appropriate error handling
            system = 'ccd'
            self.logger.info(f'robo: telling ccd to take exposure!')
            try:
                self.do(f'ccd_do_exposure')
            except Exception as e:
                msg = f'roboOperator: could not set up {system} due to {e.__class__.__name__}, {e}'
                self.log(msg)
                err = roboError(context, self.lastcmd, system, msg)
                self.hardware_error.emit(err)
                return
            
            # if we get to here then we have successfully saved the image
            self.log(f'exposure complete!')
            
            # it is now okay to trigger going to the next observation
            self.log_observation_and_gotoNext()
            """
            '''
            # 4: start exposure timer
            self.logger.info('robo: starting timer to wait for exposure to finish')
            self.waittime = float(self.schedule.currentObs['visitExpTime'])#/len(self.dither_alt)
            self.waittime_padding = 2.0 # pad the waittime a few seconds just to be sure it's done
            self.waiting_for_exposure = True
            self.exptimer.start((self.waittime + self.waittime_padding)*1000.0) # start the timer with waittime in ms as a timeout
            '''
            # 5: exit
            
            
            
        else:
            # if it's not okay to observe, then restart the robo loop to wait for conditions to change
            self.restart_robo()
    
    def gotoNext(self): 
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
            
            if not self.schedulefile_name is None:
                self.logger.info('robo: no more observations to execute. shutting down connection to schedule and logging databases')
                ## TODO: Code to close connections to the databases.
                self.schedule.closeConnection()
                self.writer.closeConnection()
                
                
    def log_observation_and_gotoNext(self):
        self.logger.info('robo: image timer finished, logging observation and then going to the next one')
        # first thing's first, stop and reset the rotator
        self.rotator_stop_and_reset()
        
        #TODO: NPL 4-30-21 not totally sure about this tree. needs testing
        self.check_ok_to_observe(logcheck = True)
        if not self.ok_to_observe:
            # if it's not okay to observe, then restart the robo loop to wait for conditions to change
            self.restart_robo()
            return
            
        if self.schedule.currentObs is not None and self.running:
            self.logger.info('robo: logging observation')
            
            
            if self.state["ok_to_observe"]:
                    image_filename = str(self.lastSeen)+'.FITS'
                    image_filepath = os.path.join(self.writer.base_directory, self.config['image_directory'], image_filename) 
                    # self.telescope_mount.virtualcamera_take_image_and_save(imagename)
                    header_data = self.get_data_to_log()
                    # self.state.update(currentData)
                    # data_to_write = {**self.state}
                    #data_to_write = {**self.state, **header_data} ## can add other dictionaries here
                    #self.writer.log_observation(data_to_write, imagename)
                    self.writer.log_observation(header_data, image_filepath)
            
            # get the next observation
            self.logger.info('robo: getting next observation from schedule database')
            self.schedule.gotoNextObs()
            
            # do the next observation and continue the cycle
            self.do_currentObs()
            
        else:  
            if self.schedule.currentObs is None:
                self.logger.info('robo: in log and goto next, but either there is no observation to log.')
            elif self.running == False:
                self.logger.info("robo: in log and goto next, but I caught a stop signal so I won't do anything")
            
            if not self.schedulefile_name is None:
                self.logger.info('robo: no more observations to execute. shutting down connection to schedule and logging databases')
                ## TODO: Code to close connections to the databases.
                self.schedule.closeConnection()
                self.writer.closeConnection()
    
    def log_timer_finished(self):
        self.logger.info('robo: exposure timer finished.')
        self.waiting_for_exposure = False
    
    
    def doExposure(self):
        # test method for making sure the roboOperator can communicate with the CCD daemon
        # 3: trigger image acquisition
        #self.exptime = float(self.schedule.currentObs['visitExpTime'])#/len(self.dither_alt)
        
        self.logger.info(f'robo: running ccd_do_exposure in thread {threading.get_ident()}')

        
        # first check if any ephemeris bodies are near the target
        self.log('checking that target is not too close to ephemeris bodies')
        ephem_inview = self.ephemInViewTarget_AltAz(target_alt = self.state['mount_alt_deg'],
                                                    target_az = self.state['mount_az_deg'])
        
        if not ephem_inview:
            self.log('ephem check okay: no ephemeris bodies in the field of view.')
            self.logger.info(f'robo: telling ccd to take exposure!')
            self.do(f'ccd_do_exposure')
            self.log(f'exposure complete!')
            pass
        else:
            msg = f'>> ephemeris body is too close to target! skipping...'
            self.log(msg)
            self.alertHandler.slack_log(msg, group = 'sudo')
            self.gotoNext()
            return
        
    def do_observation(self, obstype, target, tracking = 'auto', field_angle = 'auto'):
        """
        A GENERIC OBSERVATION FUNCTION
        
        INPUTS:
            obstype: description of the observation type. can be any ONE of:
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
        # tag the context for any error messages
        context = 'do_observation'
        
        self.log(f'doing observation: obstype = {obstype}, target = {target}, tracking = {tracking}, field_angle = {field_angle}')
        
        #### FIRST MAKE SURE IT'S OKAY TO OBSERVE ###
        self.check_ok_to_observe(logcheck = True)
        self.logger.info(f'self.running = {self.running}, self.ok_to_observe = {self.ok_to_observe}')
        
        #TODO Uncomment this, for now it's commented out so that we can test with the dome closed
        # NPL 7-28-21
        """
        if self.ok_to_observe:
            pass
        else:
            
            return
        """
        ### Validate the observation ###
        # just make it lowercase to avoid any case issues
        obstype = obstype.lower()
        
        # first do some quality checks on the request
        # observation type
        #allowed_obstypes = ['schedule', 'altaz', 'radec']
        # for now only allow altaz, and we'll add on more as we go
        allowed_obstypes = ['altaz', 'object', 'radec']
        
        # raise an exception is the type isn't allwed
        if not (obstype in allowed_obstypes):
            self.log(f'improper observation type {obstype}, must be one of {allowed_obstypes}')
            return
        else:
            self.log(f'initiating observation type {obstype}')
        self.log('checking tracking')
        # raise an exception if tracking isn't a bool or 'auto'
        assert ((not type(tracking) is bool) or (tracking.lower() != 'auto')), f'tracking option must be bool or "auto", got {tracking}'
        
        self.log('checking field_angle')
        # raise an exception if field_angle isn't a float or 'auto'
        assert ((not type(field_angle) is float) or (field_angle.lower() != 'auto')), f'field_angle option must be float or "auto", got {field_angle}'
        
        # now check that the target is appropriate to the observation type
        if obstype == 'altaz':
            # make sure it's a tuple
            assert (type(target) is tuple), f'for {obstype} observation, target must be a tuple. got type = {type(target)}'
            
            # make sure it's the right length
            assert (len(target) == 2), f'for {obstype} observation, target must have 2 coordinates. got len(target) = {len(target)}'
            
            # make sure they're floats
            assert ( (type(target[0]) is float) & (type(target[0]) is float) ), f'for {obstype} observation, target vars must be floats'
            
            # get the target alt and az
            self.target_alt = target[0]
            self.target_az  = target[1]
            msg = f'Observing Target @ (Alt, Az) = {self.target_alt:0.1f}, {self.target_az:0.1f}'
            self.alertHandler.slack_log(msg, group = None)

            self.log(f'target: (alt, az) = {self.target_alt:0.1f}, {self.target_az:0.1f}')
            try:
                # calculate the nominal target ra and dec
                alt_object = astropy.coordinates.Angle(self.target_alt*u.deg)
                az_object = astropy.coordinates.Angle(self.target_az*u.deg)
                obstime = astropy.time.Time(datetime.utcnow())
                
                altaz = astropy.coordinates.SkyCoord(alt = alt_object, az = az_object, 
                                                     location = self.ephem.site, 
                                                     obstime = obstime, 
                                                     frame = 'altaz')
                j2000 = altaz.transform_to('icrs')
                self.target_ra_j2000_hours = j2000.ra.hour
                self.target_dec_j2000_deg = j2000.dec.deg
                msg = f'target: (ra, dec) = {self.target_ra_j2000_hours:0.1f}, {self.target_dec_j2000_deg:0.1f}'
                self.log(msg)
            except Exception as e:
                self.log(f'badness getting target nominal ra/dec: {e}')
            
            if tracking.lower() == 'auto':
                tracking = True
            else:
                pass
        elif obstype == 'radec':
            # make sure it's a tuple
            assert (type(target) is tuple), f'for {obstype} observation, target must be a tuple. got type = {type(target)}'
            
            # make sure it's the right length
            assert (len(target) == 2), f'for {obstype} observation, target must have 2 coordinates. got len(target) = {len(target)}'
            
            # make sure they're floats
            assert ( (type(target[0]) is float) & (type(target[0]) is float) ), f'for {obstype} observation, target vars must be floats'
            
            # get the target RA (hours) and DEC (degs)
            self.target_ra_j2000_hours = target[0]
            self.target_dec_j2000_deg = target[1]
            
            #j2000_coords = astropy.coordinates.SkyCoord.from_name(obj, frame = 'icrs')
            j2000_ra = self.target_ra_j2000_hours * u.hour
            j2000_dec = self.target_dec_j2000_deg * u.deg
            j2000_coords = astropy.coordinates.SkyCoord(ra = j2000_ra, dec = j2000_dec, frame = 'icrs')
            
            obstime = astropy.time.Time(datetime.utcnow())
            
            #lat = astropy.coordinates.Angle(self.config['site']['lat'])
            #lon = astropy.coordinates.Angle(self.config['site']['lon'])
            #height = self.config['site']['height'] * u.Unit(self.config['site']['height_units'])
            #site = astropy.coordinates.EarthLocation(lat = lat, lon = lon, height = height)
            frame = astropy.coordinates.AltAz(obstime = obstime, location = self.ephem.site)
            local_coords = j2000_coords.transform_to(frame)
            self.target_alt = local_coords.alt.deg
            self.target_az = local_coords.az.deg
        
        elif obstype == 'object':
            # do some asserts
            # TODO
            self.log(f'handling object observations')
            # make sure it's a string
            if not (type(target[0]) is str):
                self.log(f'for object observation, target must be a string object name, got type = {type(target)}')
                return
            
            try:
                obj = target
                
                j2000_coords = astropy.coordinates.SkyCoord.from_name(obj, frame = 'icrs')
                self.target_ra_j2000_hours = j2000_coords.ra.hour
                self.target_dec_j2000_deg = j2000_coords.dec.deg
                
                obstime = astropy.time.Time(datetime.utcnow())
                lat = astropy.coordinates.Angle(self.config['site']['lat'])
                lon = astropy.coordinates.Angle(self.config['site']['lon'])
                height = self.config['site']['height'] * u.Unit(self.config['site']['height_units'])
                                                
                site = astropy.coordinates.EarthLocation(lat = lat, lon = lon, height = height)
                frame = astropy.coordinates.AltAz(obstime = obstime, location = site)
                local_coords = j2000_coords.transform_to(frame)
                self.target_alt = local_coords.alt.deg
                self.target_az = local_coords.az.deg
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
        
        
        #### Validate the observation ###
        # check if alt and az are in allowed ranges
        in_view = (self.target_alt >= self.config['telescope']['min_alt']) & (self.target_alt <= self.config['telescope']['max_alt'])
        if in_view:
            pass
        else:
            msg = f'>> target not within view! skipping...'
            self.log(msg)
            #self.alertHandler.slack_log(msg, group = None)
            self.target_ok = False
            raise TargetError(msg)
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
            self.do('dome_tracking_on')
            
        except Exception as e:
            msg = f'roboOperator: could not set up {system} due to {e.__class__.__name__}, {e}'
            self.log(msg)
            err = roboError(context, self.lastcmd, system, msg)
            self.hardware_error.emit(err)
            
            return
            
            
        ### SLEW THE TELESCOPE ###
        # start with the dome because it can take forever
        
        system = 'telescope'
        try:
            
            if obstype == 'altaz':
                # slew to the requested alt/az
                self.do(f'mount_goto_alt_az {self.target_alt} {self.target_az}')
            
            elif obstype in ['radec', 'object']:
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
            
            time.sleep(3)
                
        except Exception as e:
            msg = f'roboOperator: could not set up {system} due to {e.__class__.__name__}, {e}'
            self.log(msg)
            err = roboError(context, self.lastcmd, system, msg)
            self.hardware_error.emit(err)
            return
        
        
        
        
        
            
            
        ### DO THE EXPOSURE ###
        
        # 2: create the log dictionary & FITS header. save log dict to self.lastObs_record
        # for now this is happeningin the ccd_daemon, but we need to make this better
        # and get the info from the database, etc
        
        # 3: trigger image acquisition
        
        
        # do the exposure and wrap with appropriate error handling
        system = 'ccd'
        self.logger.info(f'robo: telling ccd to take exposure!')
        try:
            self.do(f'ccd_do_exposure')
            
            
        except Exception as e:
            msg = f'roboOperator: could not set up {system} due to {e.__class__.__name__}, {e}'
            self.log(msg)
            err = roboError(context, self.lastcmd, system, msg)
            self.hardware_error.emit(err)
            raise Exception(msg)
            return
        
        # if we get to here then we have successfully saved the image
        self.log(f'exposure complete!')
        
        # make a jpg of the last image and publish it to slack!
        postImage_process = subprocess.Popen(args = ['python','plotLastImg.py'])

    def remakePointingModel(self):
        context = 'Pointing Model'
        self.alertHandler.slack_log('Setting Up a New Pointing Model!', group = None)
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
        
        for i in range(npoints):
            altaz_point = self.pointingModelBuilder.altaz_points[i]
            target_alt = altaz_point[0]
            target_az  = altaz_point[1]
            

            self.alertHandler.slack_log(f'Target {i+1}/{npoints}:')
            
            
            system = 'Observe and Platesolve'
            try:
            
                # do the observation
                self.do(f'robo_observe_altaz {target_alt} {target_az}')
                
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
    
    def old_do_observing(self):
        '''
        This function must contain all of the database manipulation code to remain threadsafe and prevent
        exceptions from being raised during operation
        '''
        self.running = True
 

        while self.schedule.currentObs is not None and self.running:
            #print(f'scheduleExecutor: in the observing loop!')
            self.lastSeen = self.schedule.currentObs['obsHistID']
            self.current_field_alt = float(self.schedule.currentObs['altitude'])
            self.current_field_az = float(self.schedule.currentObs['azimuth'])

            for i in range(len(self.dither_alt)):
                # step through the prescribed dither sequence
                dither_alt = self.dither_alt[i]
                dither_az = self.dither_az[i]
                print(f'Dither Offset (alt, az) = ({dither_alt}, {dither_az})')
                self.alt_scheduled = self.current_field_alt + dither_alt
                self.az_scheduled = self.current_field_az + dither_az

                #self.newcmd.emit(f'mount_goto_alt_az {self.currentALT} {self.currentAZ}')
                if self.state["ok_to_observe"]:
                    print(f'Observing Dither Offset (alt, az) = ({dither_alt}, {dither_az})')
                    self.telescope.mount_goto_alt_az(alt_degs = self.alt_scheduled, az_degs = self.az_scheduled)
                    # wait for the telescope to stop moving before returning
                    while self.state['mount_is_slewing']:
                       time.sleep(self.config['cmd_status_dt'])
                else:
                    print(f'Skipping Dither Offset (alt, az) = ({dither_alt}, {dither_az})')
                self.waittime = int(self.schedule.currentObs['visitTime'])/len(self.dither_alt)
                ##TODO###
                ## Step through current obs dictionairy and update the state dictionary to include it
                ## append planned to the keys in the obs dictionary, to allow us to use the original names to record actual values.
                ## for now we want to add actual waittime, and actual time.
                #####
                self.logger.info(f'robo: Taking a {self.waittime} second exposure...')
                #time.sleep(self.waittime)
                
                if self.state["ok_to_observe"]:
                    imagename = self.writer.base_directory + '/data/testImage' + str(self.lastSeen)+'.FITS'
                    # self.telescope_mount.virtualcamera_take_image_and_save(imagename)
                    currentData = self.get_data_to_log()
                    # self.state.update(currentData)
                    # data_to_write = {**self.state}
                    data_to_write = {**self.state, **currentData} ## can add other dictionaries here
                    self.writer.log_observation(data_to_write, imagename)

            self.schedule.gotoNextObs()

        if not self.schedulefile_name is None:
            ## TODO: Code to close connections to the databases.
            self.schedule.closeConnection()
            self.writer.closeConnection()
