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
# add the wsp directory to the PATH
wsp_path = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(1, wsp_path)

from utils import utils
from schedule import schedule
from schedule import ObsWriter


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
    
    def __init__(self, base_directory, config, mode, state, wintercmd, logger, housekeeping, telescope, dome, chiller, ephem):
        super(QtCore.QThread, self).__init__()
        
        self.base_directory = base_directory
        self.config = config
        self.mode = mode
        self.state = state
        self.wintercmd = wintercmd
        self.wintercmd.roboThread = self
        self.housekeeping = housekeeping
        self.housekeeping.roboThread = self
        self.telescope = telescope
        self.dome = dome
        self.chiller = chiller
        self.logger = logger
        self.ephem = ephem
        
    
    def run(self):           
        self.robo = RoboOperator(base_directory = self.base_directory, 
                                     config = self.config, 
                                     mode = self.mode,
                                     state = self.state, 
                                     wintercmd = self.wintercmd,
                                     logger = self.logger,
                                     telescope = self.telescope, 
                                     dome = self.dome, 
                                     chiller = self.chiller, 
                                     ephem = self.ephem
                                     )
        
        # Put all the signal/slot connections here:
        ## if we get a signal to start the robotic operator, start it!
        self.restartRoboSignal.connect(self.robo.restart_robo)
        ## change schedule
        self.changeSchedule.connect(self.robo.change_schedule)
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
    
    

    

    def __init__(self, base_directory, config, mode, state, wintercmd, logger, telescope, dome, chiller, ephem):
        super(RoboOperator, self).__init__()
        
        self.base_directory = base_directory
        self.config = config
        self.mode = mode
        self.state = state
        self.wintercmd = wintercmd
        # assign self to wintercmd so that wintercmd has access to the signals
        self.wintercmd.roboOperator = self
        
        # set up the hardware systems
        self.telescope = telescope
        self.dome = dome
        self.chiller = chiller
        self.logger = logger
        self.ephem = ephem
        
        # keep track of the last command executed so it can be broadcast as an error if needed
        self.lastcmd = None
        
        # set attribute to indicate if robo operator is running
        self.running = True
        # set an attribute to indicate if we are okay to observe
        ## ie, if startup is complete, the calibration is complete, and the weather/dome is okay
        self.ok_to_observe = False
    
        # init the scheduler
        self.schedule = schedule.Schedule(base_directory = self.base_directory, config = self.config, logger = self.logger)
        # init the database writer
        self.writer = ObsWriter.ObsWriter('WINTER_ObsLog', self.base_directory, config = self.config, logger = self.logger) #the ObsWriter initialization
        
        
        # load the dither list
        self.dither_alt, self.dither_az = np.loadtxt(self.schedule.base_directory + '/' + self.config['dither_file'], unpack = True)
        # convert from arcseconds to degrees
        self.dither_alt *= (1/3600.0)
        self.dither_az  *= (1/3600.0)
        
        # create exposure timer to wait for exposure to finish
        self.exptimer = QtCore.QTimer()
        self.exptimer.setSingleShot(True)
        self.exptimer.timeout.connect(self.log_timer_finished)
        self.exptimer.timeout.connect(self.log_observation_and_gotoNext)
        

        
        ### CONNECT SIGNALS AND SLOTS ###
        self.startRoboSignal.connect(self.restart_robo)
        self.stopRoboSignal.connect(self.stop)
        #TODO: is this right (above)? NPL 4-30-21
        
        # change schedule. for now commenting out bc i think its handled in the robo Thread def
        #self.changeSchedule.connect(self.change_schedule)
        
        ## overrides
        # override the dome.ok_to_open flag
        self.dome_override = True
        # override the sun altitude flag
        self.sun_override = True
        
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

        
        
    def restart_robo(self):
        # run through the whole routine. if something isn't ready, then it waits a short period and restarts
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
        self.do_currentObs()
        return
        
    def check_ok_to_observe(self):
        # if the sun is below the horizon, or if the sun_override is active, then we want to open the dome
        if self.ephem.sun_below_horizon or self.sun_override:
            
            # make a note of why we want to open the dome
            if self.ephem.sun_below_horizon:
                #self.logger.info(f'robo: the sun is below the horizon, I want to open the dome.')
                pass
            elif self.sun_override:
                self.logger.warning(f"robo: the SUN IS ABOVE THE HORIZON, but sun_override is active so I want to open the dome")
            else:
                # shouldn't ever be here
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
                    self.logger.warning(f"robo: the DOME IS NOT OKAY TO OPEN, but dome_override is active so I'm sending open command")
                else:
                    # shouldn't ever be here
                    self.logger.warning(f"robo: I shouldn't ever be here. something is wrong with dome handling")
                    self.ok_to_observe = False
                    #return
                    #break
                
               
                
                # Check if the dome is open:
                if self.dome.Shutter_Status == 'OPEN':
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
                    self.logger.info(f'robo: shutter is closed. attempting to open...')
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
        for key in self.schedule.currentObs:
            if key in ("visitTime", "altitude", "azimuth"):
                data.update({f'{key}Scheduled': self.schedule.currentObs[key]})
            else:
                data.update({key: self.schedule.currentObs[key]})
        data.update({'visitTime': self.waittime, 'altitude': self.alt_scheduled, 'azimuth': self.az_scheduled})
        return data
    
    
    def log(self, msg, level = logging.INFO):
        if self.logger is None:
                print(msg)
        else:
            self.logger.log(level = level, msg = msg)
    
    
    def doTry(self, cmd, context = None, system = None):
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
            err = roboError(cmd, system, msg)
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
        self.logger.info('robo: starting dome startup...')
        try:
            # take control of dome        
            self.do('dome_takecontrol')
    
            # home the dome
            self.do('dome_home')
            
            # signal we're complete
            self.logger.info(f'robo: dome startup complete')
        except Exception as e:
            msg = f'roboOperator: could not set up {system} due to {e.__class__.__name__}, {e}'
            self.log(msg)
            err = roboError(context, self.lastcmd, system, msg)
            self.hardware_error.emit(err)
            return
        
        ### MOUNT SETUP ###
        system = 'telescope'
        self.logger.info('robo: starting telescope startup...')
        try:
            # connect the telescope
            self.do('mount_startup')
        
        except Exception as e:
            msg = f'roboOperator: could not set up {system} due to {e.__class__.__name__}, {e}'
            self.log(msg)
            err = roboError(context, self.lastcmd, system, msg)
            self.hardware_error.emit(err)
            return
        
        
        # if we made it all the way to the bottom, say the startup is complete!
        self.startup_complete = True
            
        
        
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
        self.check_ok_to_observe()
        if self.running & self.ok_to_observe:
            
            # grab some fields from the currentObs
            self.lastSeen = self.schedule.currentObs['obsHistID']
            self.alt_scheduled = float(self.schedule.currentObs['altitude'])
            self.az_scheduled = float(self.schedule.currentObs['azimuth'])
            
            self.logger.info(f'robo: executing observation of obsHistID = {self.lastSeen} at (alt, az) = ({self.alt_scheduled:0.2f}, {self.az_scheduled:0.2f})')
            
            # 1: point the telescope
            #TODO: change this to RA/DEC pointing instead of AZ/EL
            context = 'do_currentObs'
            system = 'telescope'
            try:
                
                # slew the telscope
                self.do(f'mount_goto_alt_az {self.alt_scheduled} {self.az_scheduled}')
            except Exception as e:
                msg = f'roboOperator: could not set up {system} due to {e.__class__.__name__}, {e}'
                self.log(msg)
                err = roboError(context, self.lastcmd, system, msg)
                self.hardware_error.emit(err)
                return
            
            system = 'dome'
            try:
                self.do(f'dome_goto {self.az_scheduled}')
            except Exception as e:
                msg = f'roboOperator: could not set up {system} due to {e.__class__.__name__}, {e}'
                self.log(msg)
                err = roboError(context, self.lastcmd, system, msg)
                self.hardware_error.emit(err)
                return
            # 2: create the log dictionary & FITS header. save log dict to self.lastObs_record
            # 3: trigger image acquisition
            # 4: start exposure timer
            self.logger.info('robo: starting timer to wait for exposure to finish')
            self.waittime = float(self.schedule.currentObs['visitTime'])#/len(self.dither_alt)
            self.waittime_padding = 2.0 # pad the waittime a few seconds just to be sure it's done
            self.exptimer.start((self.waittime + self.waittime_padding)*1000.0) # start the timer with waittime in ms as a timeout
            # 5: exit
        else:
            # if it's not okay to observe, then restart the robo loop to wait for conditions to change
            self.restart_robo()
        
    def log_observation_and_gotoNext(self):
        #TODO: NPL 4-30-21 not totally sure about this tree. needs testing
        self.check_ok_to_observe()
        if not self.ok_to_observe:
            # if it's not okay to observe, then restart the robo loop to wait for conditions to change
            self.restart_robo()
            return
            
        if self.schedule.currentObs is not None and self.running:
            self.logger.info('robo: logging observation')
            
            """
            if self.state["ok_to_observe"]:
                    imagename = self.writer.base_directory + '/data/testImage' + str(self.lastSeen)+'.FITS'
                    # self.telescope_mount.virtualcamera_take_image_and_save(imagename)
                    currentData = self.get_data_to_log()
                    # self.state.update(currentData)
                    # data_to_write = {**self.state}
                    data_to_write = {**self.state, **currentData} ## can add other dictionaries here
                    self.writer.log_observation(data_to_write, imagename)
            """
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
                self.logger.info(f'robo: Taking a {waittime} second exposure...')
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