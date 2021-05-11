#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Apr  8 10:19:30 2021

App to simulate the Dome

Uses the dome_simulator.ui file


@author: nlourie
"""

from PyQt5 import uic, QtCore, QtGui, QtWidgets
import sys
import json
from datetime import datetime
import os
import threading
import shlex
import time
import numpy as np
import traceback
import yaml
import logging

# add the wsp directory to the PATH
wsp_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(1, wsp_path)
print(f'dome_simulator: wsp_path = {wsp_path}')

import dome_simulator_commandServer
from utils import logging_setup
#from utils import utils


class WorkerSignals(QtCore.QObject):
    '''
    Defines the signals available from a running worker thread.

    In this example we've defined 5 custom signals:
        finished signal, with no data to indicate when the task is complete.
        error signal which receives a tuple of Exception type, Exception value and formatted traceback.
        result signal receiving any object type from the executed function.
    
    Supported signals are:

    finished
        No data
    
    error
        `tuple` (exctype, value, traceback.format_exc() )
    
    result
        `object` data returned from processing, anything

    progress
        `int` indicating % progress 
    '''
    finished = QtCore.pyqtSignal()
    error    = QtCore.pyqtSignal(tuple)
    result   = QtCore.pyqtSignal(object)
    progress = QtCore.pyqtSignal(float)

class Worker(QtCore.QRunnable):
    '''
    Worker thread

    Inherits from QRunnable to handler worker thread setup, signals and wrap-up.

    :param callback: The function callback to run on this worker thread. Supplied args and 
                     kwargs will be passed through to the runner.
    :type callback: function
    :param args: Arguments to pass to the callback function
    :param kwargs: Keywords to pass to the callback function

    '''

    def __init__(self, fn, *args, **kwargs): # Now the init takes any function and its args
        #super(Worker, self).__init__() # <-- this is what the tutorial suggest
        super().__init__() # <-- This seems to work the same. Not sure what the difference is???
        # Store constructor arguments (re-used for processing)
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        
        # This is a new bit: subclass an instance of the WorkerSignals class:
        self.signals = WorkerSignals()
        
        # A new bit since ex7: Add the callback to our kwargs
        self.kwargs['progress_callback'] = self.signals.progress 
        
        

    @QtCore.pyqtSlot()
    def run(self):
        '''
        Initialise the runner function with passed args, kwargs.
        
        Did some new stuff here since ex6.
        Now it returns an exception if the try/except doesn't work
        by emitting the instances of the self.signals QObject
        
        '''

        # Retrieve args/kwargs here; and fire processing using them
        try:
            result = self.fn(
                *self.args, **self.kwargs
            )
        except:
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.signals.error.emit((exctype, value, traceback.format_exc()))
        else:
            self.signals.result.emit(result)  # Return the result of the processing
        finally:
            self.signals.finished.emit()  # Done

class MainWindow(QtWidgets.QMainWindow):

    """
    The class taking care for the main window.
    It is top-level with respect to other panes, menus, plots and
    monitors.
    """
    
    newState = QtCore.pyqtSignal(str)
    
    def __init__(self, logger = None, *args, **kwargs):

        """
        Initializes the main window
        """

        super(MainWindow, self).__init__(*args, **kwargs)
        uic.loadUi(wsp_path + '/dome/' + 'dome_simulator.ui', self)  # Load the .ui file
        
        self.threadpool = QtCore.QThreadPool()
        
        self.logger = logger
        
        self.log(f'main thread {threading.get_ident()}: setting up simulated dome')
        
        # Set up the dome state dictionary
        
        self.state = dict()
        self.init_state()
        
        #self.logger = logger
        
        # NEED TO SET UP A TEST LOGGER AND CONFIG OTHERWISE THIS WON'T RUN
        self.config = yaml.load(open(wsp_path + '/config/config.yaml'), Loader = yaml.FullLoader)

       
        
        # Set up the status box
        self.statusbox = self.findChild(QtWidgets.QTextBrowser, "current_status_box")
        
        
        
        # get the update button
        self.update_button = self.findChild(QtWidgets.QPushButton, "update_button")
        self.update_button.pressed.connect(self.update_state)
        
        
        # get the rest of the buttons
        self.dome_status_button = self.findChild(QtWidgets.QComboBox, "dome_status_button")
        self.home_status_button = self.findChild(QtWidgets.QComboBox, "home_status_button")
        self.shutter_status_button = self.findChild(QtWidgets.QComboBox, "shutter_status_button")
        self.control_status_button = self.findChild(QtWidgets.QComboBox, "control_status_button")
        self.close_status_button = self.findChild(QtWidgets.QComboBox, "close_status_button")
        self.weather_status_button = self.findChild(QtWidgets.QComboBox, "weather_status_button")
        self.sunlight_status_button = self.findChild(QtWidgets.QComboBox, "sunlight_status_button")
        self.wetness_status_button = self.findChild(QtWidgets.QComboBox, "wetness_status_button")
        
        # update the display with the default values
        self.update_state()
        
        
        # create the server thread
        self.server_thread = dome_simulator_commandServer.server_thread('localhost', 62000, logger = self.logger, config = self.config, state = self.state_json)
        self.newState.connect(self.server_thread.updateStateSignal)
        #self.newState.connect(self.update_state)
        
        # connect the command server to the command executor
        self.server_thread.newcmd.connect(self.handle_cmd_request)
        self.server_thread.start()
        
        # Dome Characteristics
        self.az_speed = 23.5 #360/180 # speed in deg/sec #3.5 nominal
        self.open_time = 5 #90 # time to open the shutter #90 nominal
        self.close_time = 5 #90 # time to close the shutter #90 nominal
        self.allowed_error = 0.1
        self.movedir = 1.0 # is either +1 or -1 depending on which direction its going to move
        self.ok = False
        
    def log(self, msg, level = logging.INFO):
        if self.logger is None:
                print(msg)
        else:
            self.logger.log(level = level, msg = msg)
        
    def init_state(self):
        utc = datetime.utcnow()
        utc_datetime_str = datetime.strftime(utc, '%Y-%m-%d %H:%M:%S.%f')        # last query time string
        self.state.update({'UTC' : utc_datetime_str})
        self.state.update({'Telescope_Power'                : True,
                           'Dome_Azimuth'                   : 0.0,
                           'Dome_Status'                    : 'STOPPED',
                           'Home_Status'                    : 'READY',
                           'Shutter_Status'                 : 'OPEN',
                           'Control_Status'                 : 'REMOTE',
                           'Close_Status'                   : 'READY',
                           'Weather_Status'                 : 'READY',
                           'Sunlight_Status'                : 'READY',
                           'Wetness'                        : 'READY',
                           "Outside_Dewpoint_Threshold"     :2.0,
                           "Average_Wind_Speed_Threshold"   :11.2,
                           "Outside_Temp"                   :13.3,
                           "Outside_RH"                     :36.0,
                           "Outside_Dewpoint"               :-1.1,
                           "Pressure"                       :831.0,
                           "Wind_Direction"                 :261,
                           "Average_Wind_Speed"             :2.2,
                           "Weather_Hold_time"              :0,
                           "Faults"                         :0}
                          )
   
    
    
    def update_state(self):
        utc = datetime.utcnow()
        utc_datetime_str = datetime.strftime(utc, '%Y-%m-%d %H:%M:%S.%f')        # last query time string
        self.state.update({'UTC' : utc_datetime_str})
        self.state.update({'Dome_Status'    : self.dome_status_button.currentText()})
        self.state.update({'Home_Status'    : self.home_status_button.currentText()})
        self.state.update({'Shutter_Status' : self.shutter_status_button.currentText()})
        self.state.update({'Control_Status' : self.control_status_button.currentText()})
        self.state.update({'Close_Status'   : self.close_status_button.currentText()})
        self.state.update({'Weather_Status' : self.weather_status_button.currentText()})
        self.state.update({'Sunlight_Status': self.sunlight_status_button.currentText()})
        self.state.update({'Wetness'        : self.wetness_status_button.currentText()})
        
        self.state_json = json.dumps(self.state)
        
        
        
        self.update_display()
    
        self.newState.emit(self.state_json)
        
        
    def update_display(self):
        #print(self.state)
        text = json.dumps(self.state, indent = 2)
        
        self.statusbox.setText(text)
    
    
    # Commands that the dome does
    
    def takecontrol(self):
        if self.state['Control_Status'] in ['AVAILABLE']:
            self.state.update({'Control_Status' : 'REMOTE'})
            
            # set the dropdown to match the new value
            index = self.control_status_button.findText("REMOTE", QtCore.Qt.MatchFixedString)
            self.control_status_button.setCurrentIndex(index)
            
            # update the displayed status
            self.update_state()
    
    def givecontrol(self):
        if self.state['Control_Status'] in ['REMOTE']:
            self.state.update({'Control_Status' : 'AVAILABLE'})
            
            # set the dropdown to match the new value
            index = self.control_status_button.findText("AVAILABLE", QtCore.Qt.MatchFixedString)
            self.control_status_button.setCurrentIndex(index)
            
            # update the displayed status
            #self.newState.emit(self.state_json)
            self.update_state()
            
    def home(self):
        self.log('domesim: homing dome')
        if self.state['Control_Status'] in ['REMOTE']:
            
            # set the home status to not ready
            self.state.update({'Home_Status' : 'NOT_READY'})
            # set the dropdown to match the new value
            index = self.home_status_button.findText("NOT_READY", QtCore.Qt.MatchFixedString)
            self.home_status_button.setCurrentIndex(index)
            # update the state
            self.update_state()
            
            self.state.update({'Dome_Status' : 'HOMING'})
            # set the dropdown to match the new value
            index = self.dome_status_button.findText("HOMING", QtCore.Qt.MatchFixedString)
            self.dome_status_button.setCurrentIndex(index)
            # update the state
            self.update_state()
            
            
            # do some big moves
            # Now start the fake "move" in a separate thread which keeps track of time
            #worker1 = Worker(self.move_fake_az, az_goal = 180)
            worker2 = Worker(self.move_fake_az, az_goal = 180.0)
            self.threadpool.start(worker2)
            # Connect the signals to slots
            #worker1.signals.finished.connect(self.thread_complete)
            #worker1.signals.finished.connect(worker1.start)
            #worker1.signals.finished.connect(self.report_dome_move_complete)
            #worker1.signals.progress.connect(self.update_az_state)
            
            worker2.signals.progress.connect(self.update_az_state)
            worker2.signals.finished.connect(self.report_dome_move_complete)
            worker2.signals.finished.connect(self.show_home_complete)
            
    def show_home_complete(self):
            self.state.update({'Home_Status' : 'READY'})
            # set the dropdown to match the new value
            index = self.home_status_button.findText("READY", QtCore.Qt.MatchFixedString)
            self.home_status_button.setCurrentIndex(index)
            # update the displayed status
            #self.newState.emit(self.state_json)
            self.update_state()
            
            self.state.update({'Dome_Status' : 'STOPPED'})
            # set the dropdown to match the new value
            index = self.dome_status_button.findText("STOPPED", QtCore.Qt.MatchFixedString)
            self.dome_status_button.setCurrentIndex(index)
            # update the state
            self.update_state()
            
    
    def open_shutter(self):
        if (self.state['Control_Status'] in ['REMOTE']) & (self.state['Shutter_Status'] == 'CLOSED'):
            
            # set the shutter state to opening
            self.state.update({'Shutter_Status' : 'OPENING'})
            # set the dropdown to match the new value
            index = self.shutter_status_button.findText("OPENING", QtCore.Qt.MatchFixedString)
            self.shutter_status_button.setCurrentIndex(index)
            # update the state
            self.update_state()
            
            # start a timer in a worker thread (note just like the dome we don't get progress feedback)
            worker = Worker(self.wait_for_shutter, seconds = self.open_time)
            self.threadpool.start(worker)
        
            worker.signals.finished.connect(self.change_shutter_to_open)
   
    def close_shutter(self):
        if (self.state['Control_Status'] in ['REMOTE']) & (self.state['Shutter_Status'] == 'OPEN'):
            
            # set the shutter state to opening
            self.state.update({'Shutter_Status' : 'CLOSING'})
            # set the dropdown to match the new value
            index = self.shutter_status_button.findText("CLOSING", QtCore.Qt.MatchFixedString)
            self.shutter_status_button.setCurrentIndex(index)
            # update the state
            self.update_state()
            
            # start a timer in a worker thread (note just like the dome we don't get progress feedback)
            worker = Worker(self.wait_for_shutter, seconds = self.open_time)
            self.threadpool.start(worker)
        
            worker.signals.finished.connect(self.change_shutter_to_open)
            
    
    def change_shutter_to_open(self):
        # set the shutter state to open
        self.state.update({'Shutter_Status' : 'OPEN'})
        # set the dropdown to match the new value
        index = self.shutter_status_button.findText("OPEN", QtCore.Qt.MatchFixedString)
        self.shutter_status_button.setCurrentIndex(index)
        # update the state
        self.update_state()
    
    def change_shutter_to_closed(self):
        # set the shutter state to open
        self.state.update({'Shutter_Status' : 'CLOSED'})
        # set the dropdown to match the new value
        index = self.shutter_status_button.findText("CLOSED", QtCore.Qt.MatchFixedString)
        self.shutter_status_button.setCurrentIndex(index)
        # update the state
        self.update_state()
    
    def wait_for_shutter(self, seconds, progress_callback):
        dt = 5
        t_elapsed = 0
        
        while t_elapsed < seconds:
            time.sleep(dt)
            t_elapsed += dt
            t_remaining = seconds - t_elapsed
            progress_callback.emit(t_remaining)
            self.log(f'Shutter Move Remaining Time: {t_remaining}')
            
    
    def godome(self, az, homing = False):
        self.log(f'domesim: moving fake dome to az = {az} deg')
        if self.state['Control_Status'] in ['REMOTE']:
            if homing != True:
                # First indicate that the dome is moving
                self.state.update({'Dome_Status' : 'MOVING'})
                # set the dropdown to match the new value
                index = self.dome_status_button.findText("MOVING", QtCore.Qt.MatchFixedString)
                self.dome_status_button.setCurrentIndex(index)
                self.update_state()
            
            # Now start the fake "move" in a separate thread which keeps track of time
            worker = Worker(self.move_fake_az, az_goal = az)
            self.threadpool.start(worker)
            # Connect the signals to slots
            worker.signals.finished.connect(self.thread_complete)
            worker.signals.finished.connect(self.report_dome_move_complete)
            worker.signals.progress.connect(self.update_az_state)
    
    def report_dome_move_complete(self):
        # Now that the move is done, indicate that the dome has stopped moving
        self.state.update({'Dome_Status' : 'STOPPED'})
        # set the dropdown to match the new value
        index = self.dome_status_button.findText("STOPPED", QtCore.Qt.MatchFixedString)
        self.dome_status_button.setCurrentIndex(index)
        
        self.update_state()
    
            
    
    def update_az_state(self, az):
        
        # round the az to one decimal place
        az = np.round(az, 1)
        
        #self.log(f'Updating dome Az to {az}')
        self.state.update({'Dome_Azimuth' : az})
        self.update_state()
        
        """ 
        def move_fake_az(self, az, progress_callback):
        
            
        az_cur = 0
        while az_cur<az:
            print('Az Cur = ',az_cur)
            time.sleep(0.5)
            az_cur = az_cur+1.
            progress_callback.emit(az_cur)
        """
    
    
    
    def move_fake_az(self, az_goal, progress_callback, numsteps = 25, verbose = False):
        # put the requested azimuth on a 0-360 range
        az = self.state['Dome_Azimuth']
        
        # tell the dome to move over the server
        az_goal = np.mod(az_goal,360.0)
        # standin function to simulate movement
        self.log(f" Requested dome move from Az = {az} to {az_goal}")

        try:
            if np.abs(az_goal - az)>=self.allowed_error:
                # calculate the angular distance in the pos direction
                # want to drive dome shortest distance

                delta = az_goal - az
                
                if np.abs(delta) >= 180.0:
                    #print(f'delta = |{delta}| > 180')
                    dist_to_go = 360-np.abs(delta)
                    movedir = -1*np.sign(delta)
                    #print(f'new delta = {delta}')
                else:
                    #print(f'delta = |{delta}| < 180')
                    dist_to_go = np.abs(delta)
                    movedir = np.sign(delta)
                    
                drivetime = np.abs(dist_to_go)/self.az_speed # total time to move
                # now start "moving the dome" it stays moving for an amount of time
                    # based on the dome speed and distance to move
                self.log(f' Estimated Drivetime = {drivetime} s')
                dt = drivetime/numsteps #0.1 #increment time for updating position
                #N_steps = drivetime/dt
                #daz = delta/N_steps
                if verbose:
                    if movedir < 0:
                        dirtxt = '[-]'
                    else:
                        dirtxt = '[+]'
                    self.log(f"Rotating Dome {dist_to_go} deg in {dirtxt} direction from Az = {az} to Az = {az_goal}")
                
                while np.abs(az_goal - az) > self.allowed_error:
                    self.ismoving = True
                    # keep "moving" the dome until it gets close enough
                    time.sleep(dt)
                    # MAKE SURE THAT AZ ALWAYS STAYS IN 0-360 RANGE
                    az = np.mod(az + movedir*self.az_speed*dt,360.0)
                    if verbose:
                        self.log(f"Dome Az = {az}, Dist to Go = {np.abs(az_goal-az)} deg")# %(az, np.abs(az_goal-az)))
                        #print(f" Still Moving? {self.ismoving}")
                    # report back the azimuth as we go
                    progress_callback.emit(az)
                        
                self.ismoving = False
                if verbose:
                    if not self.ismoving:
                        self.log(f" Completed Dome Move.")
                    else:
                        self.log(" Moving error... move not complete?")
                
                # For now the error isn't interesting. Just force the postion to be the goal
                progress_callback.emit(az_goal)
                
            else:
                self.log(f" Not moving. Dome Az within allowed error: {self.allowed_error} deg")
        except KeyboardInterrupt:
            print(f" User interrupted dome move. Stopping!")
            return
    
    
    
        
    
    
    
    
    def thread_complete(self):
        # this is triggered when the worker emits the finished signal
        self.log("domesim: WORKER THREAD COMPLETE!")
        
    def handle_cmd_request(self, cmd_request):
        
        cmdstr = cmd_request.cmd
        try:
            parsed_string = shlex.split(cmdstr)
            cmd = parsed_string[0]
            if len(parsed_string) > 0:
                args = parsed_string[1:]
            else:
                args = []
        except:
            cmd = cmdstr
            args = []
        
        msg = f'domesim: Got new command request: {cmd}, args = {args} from user at {cmd_request.request_addr} | {cmd_request.request_port}'
        
        # try to do the command
        try:
            if cmd == 'takecontrol':
                #print(msg)
                self.takecontrol()
            
            elif cmd == 'givecontrol':
                #print(msg)
                self.givecontrol()
            
            elif cmd == 'home':
                #print(msg)
                self.home()
            
            elif cmd == 'godome':
                #print(msg)
                az = float(args[0])
                self.godome(az = az)
            
            elif cmd == 'status?':
                self.update_state()
            
            elif cmd == 'open':
                #print(msg)
                self.open_shutter()
            
            elif cmd == 'close':
                #print(msg)
                self.close_shutter()
            
            else:
                #print(f'SimDome: Did not recognize command {cmd}, args = {args} from user at {cmd_request.request_addr} | {cmd_request.request_port}')
                pass
        
        except Exception as e:
            #print(f'SimDome: Could not execute command {cmd}, args = {args}, error: {e}')
            pass
        
        
if __name__ == '__main__':
    
    doLogging = True
    config = yaml.load(open(wsp_path + '/config/config.yaml'), Loader = yaml.FullLoader)
    # set up the logger
    if doLogging:
        logger = logging_setup.setup_logger(wsp_path, config)    
    else:
        logger = None
    
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow(logger = logger)

    window.show()
    app.exec_()
