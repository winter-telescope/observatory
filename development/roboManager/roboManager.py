#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Mar  9 09:05:52 2021

domed.py

This is part of wsp

# Purpose #

This is a standalone daemon which communicates directly with the WINTER
Command Server. It has attributes which return state variables which can report
back the dome status using the Pyro name server. It also has wrappers around
all the allowed commands that can be sent to the dome. 

Replies to commands from the dome are logged.




@author: nlourie
"""



import os
import Pyro5.core
import Pyro5.server
import time
#from PyQt5 import uic, QtGui, QtWidgets
from PyQt5 import QtCore
#from astropy.io import fits
import numpy as np
import sys
import signal
#import queue
import socket
from datetime import datetime, timedelta
import threading
import logging
import yaml
import json
import pathlib
import traceback
import pytz

# add the wsp directory to the PATH
wsp_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),'wsp')
# switch to this when ported to wsp
#wsp_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

sys.path.insert(1, wsp_path)
print(f'roboManager: wsp_path = {wsp_path}')


#from housekeeping import data_handler
from daemon import daemon_utils
from utils import utils
from utils import logging_setup
#from watchdog import watchdog
from alerts import alert_handler


class ReconnectHandler(object):
    '''
    This is a object to handle reconnections, keep track of how often we should
    reconnect, track if we are connected, and reconnect if we need to.
    '''
    def __init__(self, connection_timeout = 0):
        self.connection_timeout = connection_timeout
        # Note that the first one gets skipped
        #self.reconnect_timeouts = np.array([0, 0.5, 1, 5, 10, 30, 60, 300, 600]) + self.connection_timeout #all the allowed timeouts between reconnection attempts CAN'T BE LESS THAN CONN TIMEOUT
        self.reconnect_timeouts = np.array([0, 0.5, 1, 5]) + self.connection_timeout #all the allowed timeouts between reconnection attempts CAN'T BE LESS THAN CONN TIMEOUT

        
        self.reconnect_timeout_level = 0 # the index of the currently active timeout
        self.reconnect_timeout = self.reconnect_timeouts[self.reconnect_timeout_level]
        
        self.reset_last_reconnect_timestamp()

        
        
    def reset_last_reconnect_timestamp(self):
        self.last_reconnect_timestamp = datetime.utcnow().timestamp()
        self.reconnect_remaining_time = 0.0
        self.time_since_last_connection = 0.0
        
    
    def update_timeout(self):
        '''Set the value of the current timeout'''
        self.reconnect_timeout = self.reconnect_timeouts[self.reconnect_timeout_level]
        #return current_timeout
    
    def reset_reconnect_timeout(self):
        self.reconnect_timeout_level = 0
        self.update_timeout()
    
    def increment_reconnect_timeout(self):
        ''' Increase the timeout level by one '''
        
        # if the current timeout level is greater than or equal to the number of levels, do nothing,
        # otherwise increment by one
        if self.reconnect_timeout_level >= (len(self.reconnect_timeouts) - 1):
            pass
        else:
           self.reconnect_timeout_level += 1 
 
        # now update the timeout
        self.update_timeout()
    
    def get_time_since_last_connection(self):
        timestamp = datetime.utcnow().timestamp()
        self.time_since_last_connection = (timestamp - self.last_reconnect_timestamp)
        self.reconnect_remaining_time = self.reconnect_timeout - self.time_since_last_connection





class StatusMonitor(QtCore.QObject):
    
    newStatus = QtCore.pyqtSignal(object)
    doReconnect = QtCore.pyqtSignal()
    handModeEnabled = QtCore.pyqtSignal()
    
    def __init__(self, proxyname, logger = None, connection_timeout = 0.5, verbose = False):
        super(StatusMonitor, self).__init__()
        
        self.state = dict()
        self.proxyname = proxyname # address (in this case proxyname)
        self.logger = logger
        self.connection_timeout = connection_timeout # time to allow each connection attempt to take
        self.verbose = verbose
        self.timestamp = datetime.utcnow().timestamp()
        self.connected = False
        
        # have the doReconnect signal reattempt the connection
        #self.doReconnect.connect(self.connect_socket)
        
        self.reconnector = ReconnectHandler()
        
        self.setup_connection()
    
    def log(self, msg, level = logging.INFO):
        tagged_msg = 'roboManager: ' + msg
        if self.logger is None:
                print(tagged_msg)
        else:
            self.logger.log(level = level, msg = tagged_msg)    
    
    def setup_connection(self):
        self.create_socket()
    
    def create_socket(self):
        if self.verbose:
            self.log(f'(Thread {threading.get_ident()}) StatusMonitor: creating socket')
        # init the remote object
        try:
            self.remote_object = Pyro5.client.Proxy(f"PYRONAME:{self.proxyname}")
            self.connected = True
        except Exception as e:
            self.connected = False
            self.logger.error(f'roboManager: connection with remote object failed: {e}', exc_info = True)
            pass
        
    def connect_socket(self):
        if self.verbose:
            self.log(f'(Thread {threading.get_ident()}) StatusMonitor: Attempting to connect socket')
        # record the time of this connection attempt
        #self.reset_last_recconnect_timestamp()
        self.reconnector.reset_last_reconnect_timestamp()
        
        # increment the reconnection timeout
        self.reconnector.increment_reconnect_timeout()
        
        try:
            
            self.log(f'(Thread {threading.get_ident()}) StatusMonitor: trying to connection to ({self.addr} | {self.port})')
            
            # try to reconnect the socket
            #self.sock.connect((self.addr, self.port))
            self.create_socket()
            
            #print(f'(Thread {threading.get_ident()}) Connection attempt successful!')
            
            #if this works, then set connected to True
            self.connected = True
            
            # since the connection is fine, reset all the timeouts
            self.reconnector.reset_reconnect_timeout()
            
            
        except Exception as e:
            
            # the connection is broken. set connected to false
            self.connected = False
            if self.verbose:
                self.log(f'(Thread {threading.get_ident()}) StatusMonitor: connection unsuccessful: {e}, waiting {self.reconnector.reconnect_timeout} until next reconnection')   
            
            
    
    def updateState(self, state):
        '''
        When we receive a status update from the dome, add each element 
        to the state dictionary
        '''
        #print(f'(Thread: {threading.get_ident()}): recvd dome state: {domeState}')
        if type(state) is dict:
            # make sure we don't get some garbage, and only attempt if this is actually a dictionary
            for key in state.keys():
                try:
                    self.state.update({key : state[key]})
                
                except:
                    pass
        
        # assign sun attributes
        self.sun_alt = self.state.get('sun_alt', -888)
        self.timestamp = self.state.get('timestamp', datetime.fromtimestamp(0))
        
        
    def pollStatus(self):
        #print(f'StatusMonitor: Polling status from Thread {threading.get_ident()}')
        # record the time that this loop runs
        self.polltimestamp = datetime.utcnow().timestamp()
        
        # report back some useful stuff
        self.state.update({'timestamp' : self.polltimestamp})
        self.state.update({'reconnect_remaining_time' : self.reconnector.reconnect_remaining_time})
        self.state.update({'reconnect_timeout' : self.reconnector.reconnect_timeout})
        self.state.update({'is_connected' : self.connected})
        
        # poll the state, if we're not connected try to reconnect
        # this should reconnect down the line if we get disconnected
        
        if self.connected:
            
            try:
                state = self.remote_object.GetStatus()
                
                self.updateState(state)
                
            except Exception as e:
                #print('WTF')
                #if self.verbose:
                #self.log(f'could not update observatory state: {e}')
                #exc_info = sys.exc_info()
                #traceback.print_exception(*exc_info)
                pass
        
        else:
            #print(f'Dome Status Not Connected. ')
            
            '''
            If we're not connected, then:
                If we've waited the full reconnection timeout, then try to reconnect
                If not, then just note the time and pass''
            '''
            self.reconnector.get_time_since_last_connection()
            
            
            #if self.reconnect_remaining_time <= 0.0:
            if self.reconnector.reconnect_remaining_time <= 0.0:
                if self.verbose:
                    self.log('StatusMonitor: Do a reconnect')
                # we have waited the full reconnection timeout
                self.doReconnect.emit()
                self.connect_socket()
                
            else:
                # we haven't waited long enough do nothing
                pass
            
        
        """
        
        if not self.connected:
            self.init_remote_object()
            
        else:
            try:
                self.observatoryState = self.remote_object.GetStatus()
                
                
            except Exception as e:
                if self.verbose:
                    print(f'ephemd: could not update observatory state: {e}')
                pass
        """
        """
        # if the connection is live, ask for the dome status
        if self.connected:
            #self.time_since_last_connection = 0.0
            self.reconnector.time_since_last_connection = 0.0
            #print(f'Connected! Querying Dome Status.')
            try:
                dome_state = utils.query_socket(self.sock,
                             'status?', 
                             end_char = '}',
                             timeout = 2)
                #print(f'dome state = {json.dumps(dome_state, indent = 2)}')
                self.updateDomeState(dome_state)
            
            except:
                #print(f'Query attempt failed.')
                self.connected = False
        else:
            #print(f'Dome Status Not Connected. ')
            
            '''
            If we're not connected, then:
                If we've waited the full reconnection timeout, then try to reconnect
                If not, then just note the time and pass''
            '''
            self.reconnector.get_time_since_last_connection()
            
            
            #if self.reconnect_remaining_time <= 0.0:
            if self.reconnector.reconnect_remaining_time <= 0.0:
                if self.verbose:
                    self.log('StatusMonitor: Do a reconnect')
                # we have waited the full reconnection timeout
                self.doReconnect.emit()
                self.connect_socket()
                
            else:
                # we haven't waited long enough do nothing
                pass
        """
        self.newStatus.emit(self.state)
    
class CommandHandler(QtCore.QObject):
    newReply = QtCore.pyqtSignal(int)
    newCommand = QtCore.pyqtSignal(str)
    
    def __init__(self, addr, port, logger = None, connection_timeout = 0.5, verbose = False):
        super(CommandHandler, self).__init__()
        
        self.state = dict()
        self.addr = addr # IP address
        self.port = port # port
        self.logger = logger
        self.connection_timeout = connection_timeout # time to allow each connection attempt to take
        self.verbose = verbose
        # this reply is updated in the dome state dictionary when the connection is dead
        self.disconnectedReply = -9
        
        #self.timestamp = datetime.utcnow().timestamp()
        self.connected = False
        
        #self.reconnector = ReconnectHandler()
        
        self.setup_connection()
    
    def log(self, msg, level = logging.INFO):
        msg = 'roboManager: ' + msg        
        if self.logger is None:
                print(msg)
        else:
            self.logger.log(level = level, msg = msg)
    
    def setup_connection(self):
        self.create_socket()
        
        self.connect_socket()
    
    def create_socket(self):
        if self.verbose:
            self.log(f'(Thread {threading.get_ident()}) CommandHandler: Creating socket')
        self.sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        #self.sock.settimeout(self.connection_timeout)
        
        # give it a long timeout so it can wait for slow replies
        # palomar uses 100 s fora shutter open/close
        # a 360 deg homing cycle takes 360deg/(2.5 deg/s) = 144 s
        # so let's use 150 seconds just to be safe
        #TODO: make the timeout update dynamically based on realistic estimates of the return time!
        self.sock.settimeout(150)
        
    def connect_socket(self):
        if self.verbose:
            self.log(f'(Thread {threading.get_ident()}) CommandHandler: Attempting to connect socket')
        # record the time of this connection attempt
        #self.reset_last_recconnect_timestamp()
        #self.reconnector.reset_last_reconnect_timestamp()
        
        try:
            
            # try to reconnect the socket
            self.sock.connect((self.addr, self.port))
            
            if self.verbose:
                self.log(f'(Thread {threading.get_ident()}) Connection attempt successful!')
            
            #if this works, then set connected to True
            self.connected = True
            
            # since the connection is fine, reset all the timeouts
            #self.reconnector.reset_reconnect_timeout()
            
            
        except:
            
            # the connection is broken. set connected to false
            self.connected = False
            
            if self.verbose:
                print(f'(Thread {threading.get_ident()}) CommandHandler: connection unsuccessful.')   
            
            self.newReply.emit(self.disconnectedReply)
            # increment the reconnection timeout
            #self.reconnector.increment_reconnect_timeout()
            
            
    def sendCommand(self, cmd):
        '''
        This takes the command string and sends it directly to the dome.
        It takes any received reply and triggers a new reply event
        '''
        
        
        if self.connected:
            #self.time_since_last_connection = 0.0
            #self.reconnector.time_since_last_connection = 0.0
            #print(f'Connected! Querying Dome Status.')
            
            

            try:
                reply = utils.query_socket(self.sock,
                             cmd, 
                             end_char = '\n')
                             #timeout = self.connection_timeout)
                             #timeout = 10000)
                
                self.log(f'CommandHandler: Sent command {cmd} to dome. Received reply: {reply}')
                self.newReply.emit(reply)
            
            except Exception as e:
                #print(f'Query attempt failed.')
                self.log(f'CommandHandler: Tried to send command {cmd} to dome, but rasied exception: {e}')
                self.connected = False
        else:
            self.log(f'CommandHandler: Received command: {cmd}, but WSP was disconnected. Reply = {self.disconnectedReply}')

            # the dome is not connected. set the reply to something that represents this state
            self.newReply.emit(self.disconnectedReply)
            #print(f'Dome Status Not Connected. ')
            pass

class CommandThread(QtCore.QThread):
    newReply = QtCore.pyqtSignal(int)
    newCommand = QtCore.pyqtSignal(str)
    doReconnect = QtCore.pyqtSignal()
    
    def __init__(self, addr, port, logger = None, connection_timeout = 0.5, verbose = False):
        super(QtCore.QThread, self).__init__()
        self.addr = addr
        self.port = port
        self.logger = logger
        self.connection_timeout = connection_timeout
        self.verbose = verbose
    
    def HandleCommand(self, cmd):
        self.newCommand.emit(cmd)
    
    def DoReconnect(self):
        #print(f'(Thread {threading.get_ident()}) Main: caught reconnect signal')
        self.doReconnect.emit()
    
    def run(self):    
        def SignalNewReply(reply):
            self.newReply.emit(reply)
        
        self.commandHandler = CommandHandler(self.addr, self.port, logger = self.logger, connection_timeout = self.connection_timeout, verbose = self.verbose)
        # if the newReply signal is caught, execute the sendCommand function
        self.newCommand.connect(self.commandHandler.sendCommand)
        self.commandHandler.newReply.connect(SignalNewReply)
        
        # if we recieve a doReconnect signal, trigger a reconnection
        self.doReconnect.connect(self.commandHandler.connect_socket)
        
        self.exec_()

class StatusThread(QtCore.QThread):
    """ I'm just going to setup the event loop and do
        nothing else..."""
    newStatus = QtCore.pyqtSignal(object)
    doReconnect = QtCore.pyqtSignal()
    enableHandMode = QtCore.pyqtSignal()
    
    def __init__(self, proxyname, logger = None, connection_timeout = 0.5, verbose = False):
        super(QtCore.QThread, self).__init__()
        self.proxyname = proxyname
        #self.port = port
        self.logger = logger
        self.connection_timeout = connection_timeout
        self.verbose = verbose
        
    def run(self):    
        def SignalNewStatus(newStatus):
            self.newStatus.emit(newStatus)
        def SignalDoReconnect():
            self.doReconnect.emit()
        def SignalHandModeEnabled():
            self.enableHandMode.emit()
        
        self.timer= QtCore.QTimer()
        self.statusMonitor = StatusMonitor(self.proxyname, logger = self.logger, connection_timeout = self.connection_timeout, verbose = self.verbose)
        
        self.statusMonitor.newStatus.connect(SignalNewStatus)
        self.statusMonitor.doReconnect.connect(SignalDoReconnect)
        self.statusMonitor.handModeEnabled.connect(SignalHandModeEnabled)
        
        self.timer.setSingleShot(False)
        self.timer.timeout.connect(self.statusMonitor.pollStatus)
        self.timer.start(100)
        self.exec_()
        
    
class RoboTrigger(object):
    
    def __init__(self, trigtype, val, cond, cmd, sundir):
        self.trigtype = trigtype
        self.val = val
        self.cond = cond
        self.cmd = cmd
        self.sundir = sundir
        


#class Dome(object):        
class RoboManager(QtCore.QObject):
    """
    This is the pyro object that handles connections and communication with t
    the dome.
    
    This object has several threads within it for handling connection,
    communication, and commanding.
    
    NOTE:
        This inherets from QObject, which allows it to have custom signals
        which can communicate with the communication threads
    """
    
    #statusRequest = QtCore.pyqtSignal(object)
    commandRequest = QtCore.pyqtSignal(str)
    
    def __init__(self, config, addr, port, status_proxyname, sunsim = False, logger = None, connection_timeout = 1.5, alertHandler = None, verbose = False):
        super(RoboManager, self).__init__()
        # attributes describing the internet address of the dome server
        self.config = config
        self.addr = addr
        self.port = port
        self.proxyname = status_proxyname
        self.logger = logger
        self.connection_timeout = connection_timeout
        self.state = dict()
        self.alertHandler = alertHandler
        self.verbose = verbose
        self.sunsim = sunsim
        
        # dictionaries for the triggered commands
        self.triggers = dict()
        self.triglog  = dict()
        # set up the trigger dictgionaries
        self.setupTrigs()
        
        self.tz = pytz.timezone('America/Los_Angeles')
        
        self.statusThread = StatusThread(self.proxyname, logger = self.logger, connection_timeout = self.connection_timeout, verbose = self.verbose)
        self.commandThread = CommandThread(self.addr, self.port, logger = self.logger, connection_timeout = self.connection_timeout, verbose = self.verbose)
        # connect the signals and slots
        
        self.statusThread.start()
        self.commandThread.start()
        
        # if the status thread is request a reconnection, trigger the reconnection in the command thread too
        # THE STATUS THREAD IS A PYRO CONN, THE COMMAND THREAD IS A SOCKET, SO DON'T CONNECT THEIR RECONNECTION ATTEMPTS
        #self.statusThread.doReconnect.connect(self.commandThread.DoReconnect)
        
        # if the status thread gets the signbal that we've entered hand mode then enter hand mode
        #self.statusThread.enableHandMode.connect(self.handleHandMode)
        
        self.statusThread.newStatus.connect(self.updateStatus)
        self.commandRequest.connect(self.commandThread.HandleCommand)
        self.commandThread.newReply.connect(self.updateCommandReply)
        self.log(f'running in thread {threading.get_ident()}')
        
    def log(self, msg, level = logging.INFO):
        msg = 'roboManager: ' + msg
        if self.logger is None:
                print(msg)
        else:
            self.logger.log(level = level, msg = msg)
            
    def updateStatus(self, newStatus):
        '''
        Takes in a new status dictionary (eg, from the status thread),
        and updates the local copy of status
        
        we don't want to overwrite the whole dictionary!
        
        So do this element by element using update
        '''
        if type(newStatus) is dict:
            # make sure we don't get some garbage, and only attempt if this is actually a dictionary
            for key in newStatus.keys():
                try:
                    self.state.update({key : newStatus[key]})
                
                except:
                    pass
        
        # check if we should be requesting any tasks
        self.checkWhatToDo()
                    
        #print(f'roboManager (Thread {threading.get_ident()}): got new status. status = {json.dumps(self.state, indent = 2)}')
        """
        print(f'roboManager (Thread {threading.get_ident()}): got new status:')
        print(f'            timestamp : {self.state.get("timestamp", -999)}')
        print(f'            sun_alt   : {self.state.get("sun_alt", -999)}')
        print(f'            sun_az    : {self.state.get("sun_az", -999)}')
        """
        
    def updateCommandReply(self, reply):
        '''
        when we get a new reply back from the command thread, add it to the status dictionary
        '''
        try:
            self.state.update({'command_reply' : reply})
        except:
            pass
    
    
    def setupTrigs(self):
        """
        creates a dictionary of triggers which are pulled from the main config.yaml file
        these triggers must be saved under robotic_manager_triggers in the format below:
            
            Example:
                robotic_manager_triggers:
                    timeformat: '%H%M%S.%f'
                    triggers:
                        startup:
                            type: 'sun'
                            val: 5.0
                            cond: '<'
                            cmd: 'total_startup'
        
        after creating this dictionary, the trigger log file is set up
        """
        
        # create local dictionary of triggers
        for trig in self.config['robotic_manager_triggers']['triggers']:
            
            print(trig)
            
            trigtype = self.config['robotic_manager_triggers']['triggers'][trig]['type']
            trigcond = self.config['robotic_manager_triggers']['triggers'][trig]['cond']
            trigval  = self.config['robotic_manager_triggers']['triggers'][trig]['val']
            trigcmd  = self.config['robotic_manager_triggers']['triggers'][trig]['cmd']
            trigsundir = self.config['robotic_manager_triggers']['triggers'][trig]['sundir']
            
            # create a trigger object
            trigObj = RoboTrigger(trigtype = trigtype, val = trigval, cond = trigcond, cmd = trigcmd, sundir = trigsundir)
            
            # add the trigger object to the trigger dictionary
            self.triggers.update({trig : trigObj})
        
        # set up the log file
        
        self.setupTrigLog()
        
    @Pyro5.server.expose
    def resetTrigLog(self, updateFile = True):
        # make this exposed on the pyro server so we can externally reset the triglog
        
        # overwrites the triglog with all False, ie none of the commands have been sent
        for trigname in self.triggers.keys():
                #self.triglog.update({trigname : False})
                self.triglog.update({trigname : {'sent' : False, 'sun_alt_sent' : '', 'time_sent' : ''}})
        if updateFile:
            self.updateTrigLogFile()
    
    def updateTrigLogFile(self):
        
        # saves the current value of the self.triglog to the self.triglog_filepath file
        # dump the yaml file
        with open(self.triglog_filepath, 'w+') as file:
            #yaml.dump(self.triglog, file)#, default_flow_style = False)
            json.dump(self.triglog, file, indent = 2)
        
    
    def setupTrigLog(self):
        """
        set up a yaml log file which records whether the command for each trigger
        has already been sent tonight.
        
        checks to see if tonight's triglog already exists. if not it makes a new one.
        """
        # file
        self.triglog_dir = os.path.join(os.getenv("HOME"),'data','triglogs')
        self.triglog_filename = f'triglog_{utils.tonight()}.json'
        self.triglog_filepath = os.path.join(self.triglog_dir, self.triglog_filename)

        self.triglog_linkdir = os.path.join(os.getenv("HOME"),'data')
        self.triglog_linkname = 'triglog_tonight.lnk'
        self.triglog_linkpath = os.path.join(self.triglog_linkdir, self.triglog_linkname)
        
        # create the data directory if it doesn't exist already
        pathlib.Path(self.triglog_dir).mkdir(parents = True, exist_ok = True)
        self.log(f'ensuring directory exists: {self.triglog_dir}')
                
        # create the data link directory if it doesn't exist already
        pathlib.Path(self.triglog_linkdir).mkdir(parents = True, exist_ok = True)
        self.log(f'ensuring directory exists: {self.triglog_linkdir}')
        
        # check if the file exists
        try:
            # assume file exists and try to load triglog from file
            self.log(f'loading triglog from file')
            self.triglog = json.load(open(self.triglog_filepath))
            

        except FileNotFoundError:
            # file does not exist: create it
            self.log('no triglog found: creating new one')
            
            # create the default triglog: no cmds have been sent
            self.resetTrigLog()
            
            
        # recreate a symlink to tonights trig log file
        self.log(f'trying to create link at {self.triglog_linkpath}')

        try:
            os.symlink(self.triglog_filepath, self.triglog_linkpath)
        except FileExistsError:
            self.log('deleting existing symbolic link')
            os.remove(self.triglog_linkpath)
            os.symlink(self.triglog_filepath, self.triglog_linkpath)
        
        print(f'\ntriglog = {json.dumps(self.triglog, indent = 2)}')
            
        
    
    def getTrigCurVals(self, trigname):
        """:
        get the trigger value (the value on which to trigger), and the current value of the given trigger
        trigger must be in self.config['robotic_manager_triggers']['triggers']
        
        this is trying to build a general framework where we can decide down the line that we want to trigger
        a command off of the sun altitude or a time.
        
        it may be too fussy and might not worth doing this way, but we shall see.
        """
        trigtype = self.config['robotic_manager_triggers']['triggers'][trigname]['type']
        
        if trigtype == 'sun':
            #print(f'handling sun trigger:')
            trigval = self.config['robotic_manager_triggers']['triggers'][trigname]['val']
            #curval = self.sun_alt
            curval = self.state['sun_alt']
            
        elif trigtype == 'time':
            #print(f'handling time trigger:')
            trig_datetime = datetime.strptime(self.config['robotic_manager_triggers']['triggers'][trigname]['val'], self.config['robotic_manager_triggers']['timeformat'])
            
            if self.sunsim:
                now_datetime = datetime.fromtimestamp(self.state['timestamp'])
            else:
                now_datetime = datetime.now()
                
            
            # now the issue is that the timestamp from trig_datetime has a real time but a nonsense date. so we can't subtract
            # to be able to subtract, let's make the two times on the same day, and use the now_datetime to get the day.
            
            now_year = now_datetime.year
            now_month = now_datetime.month
            now_day = now_datetime.day
            
            trig_hour = trig_datetime.hour
            trig_minute = trig_datetime.minute
            trig_second = trig_datetime.second
            trig_microsecond = trig_datetime.microsecond
            
            trig_datetime_today = datetime(year = now_year, 
                                           month = now_month, 
                                           day = now_day,
                                           hour = trig_hour,
                                           minute = trig_minute,
                                           second = trig_second,
                                           microsecond = trig_microsecond)
            
            # if the trigger time is between 0:00 and 8:00 then we need to shove it forward by a day
            if (trig_hour < 8.0) & (now_datetime.hour > 8) & (now_datetime.hour <= 24):
                trig_datetime_today += timedelta(days = 1)
            
            #NOW we have two times on the same day. subtract to get the 
            # for the trigval and the curval we will return the timestamps of each. these can be compared easily
            trigval = trig_datetime_today.timestamp()
            #curval = self.timestamp
            #curval = self.state['timestamp']
            curval = now_datetime.timestamp()
            #print(f'trig_datetime_today = {trig_datetime_today}, timestamp = {trig_datetime_today.timestamp()}')
            #print(f'now_datetime        = {now_datetime}, timestamp = {now_datetime.timestamp()}')
            #print()
            
        return trigval, curval
        
        
        
        
    def checkWhatToDo(self):
        """
        This is the main meat of this program. It checks the sun alt and time against a
        set of predefined tasks and then submits commands to the WSP wintercmd TCP/IP
        command interface.

        Returns
        -------
        None.

        """
        
        # startup #
        #for trigname in ['startup']:
        for trigname in self.triggers.keys():
            #print(f'evaluating trigger: {trigname}')
            # load up the trigger object
            trig = self.triggers[trigname]
            
            # check to see if the trigger has already been executed
            if self.triglog[trigname]['sent']:
                # the trigger cmd has already been sent. do nothing.
                pass
            else:
                # see if the trigger condition has been met
                trigval, curval = self.getTrigCurVals(trigname)
                #print(f'\ttrigval = {trigval}, curval = {curval}')
                
                trig_condition = f'{curval} {trig.cond} {trigval}'
                trig_condition_met = eval(trig_condition)
                
                # check the sun direction (ie rising/setting)
                if trig.sundir == 0:
                    trig_sun_ok = True
                elif trig.sundir <0:
                    # require sun to be setting
                    if self.state['sun_rising']:
                        trig_sun_ok = False
                    else:
                        trig_sun_ok = True
                else:
                    # require sun to be rising
                    if self.state['sun_rising']:
                        trig_sun_ok = True
                    else:
                        trig_sun_ok = False
                
                #print(f'\ttrig condition: {trig_condition} --> {trig_condition_met}')
                
                if trig_condition_met & trig_sun_ok:
                    # the trigger condition is met!
                    print()
                    print(f'Time to send the {trig.cmd} command!')
                    print(f'\ttrigval = {trigval}, curval = {curval}')
                    print(f'\ttrig condition: {trig_condition} --> {trig_condition_met}')
                    print()
                    # send the trigger command
                    self.do(trig.cmd)
                    
                    # log that we've sent the command
                    #self.triglog.update({trigname : True})
                    self.triglog.update({trigname : {'sent' : True, 'sun_alt_sent' : self.state['sun_alt'], 'time_sent' : datetime.fromtimestamp(self.state['timestamp']).isoformat(sep = ' ')}})

                    
                    # update the triglog file
                    self.updateTrigLogFile()
                    
                else:
                    # trigger condition not met
                    #print(f'\tNot yet time to send {trig.cmd} command')
                    pass
            
    
    
    ###### PUBLIC FUNCTIONS THAT CAN BE CALLED USING PYRO SERVER #####
    
    # Return the Current Status (the status is updated on its own)
    @Pyro5.server.expose
    def GetStatus(self):
        return self.state
    
    # Commands which make the dome do things
    @Pyro5.server.expose
    def xyxxy(self):
        cmd = 'xyzzy'
        self.commandRequest.emit(cmd)
        
    @Pyro5.server.expose
    def do(self, cmd):
        # send an arbitrary command to WSP
        
        print(f'roboManager: sending command >> {cmd}')
        
        self.commandRequest.emit(cmd)
        
    
        
        
class PyroGUI(QtCore.QObject):   
    """
    This is the main class for the daemon. It is a QObject, which means that
    it can be initialized with it's own event loop. This runs the whole daemon,
    and has a dedicated QThread which handles all the Pyro stuff (the PyroDaemon object)
    """
                  
    def __init__(self, config, logger = None, verbose = False, parent=None, sunsim = False):            
        super(PyroGUI, self).__init__(parent)   

        self.config = config
        self.logger = logger
        self.verbose = verbose
        
        msg = f'(Thread {threading.get_ident()}: Starting up roboManager Daemon '
        if logger is None:
            print(msg)
        else:
            logger.info(msg)

        
        # set up an alert handler so that the dome can send messages directly
        auth_config_file  = wsp_path + '/credentials/authentication.yaml'
        user_config_file = wsp_path + '/credentials/alert_list.yaml'
        alert_config_file = wsp_path + '/config/alert_config.yaml'
        
        auth_config  = yaml.load(open(auth_config_file) , Loader = yaml.FullLoader)
        user_config = yaml.load(open(user_config_file), Loader = yaml.FullLoader)
        alert_config = yaml.load(open(alert_config_file), Loader = yaml.FullLoader)
        
        self.alertHandler = alert_handler.AlertHandler(user_config, alert_config, auth_config)    
        
        if sunsim:
            self.proxyname = 'sunsim'
        else:
            self.proxyname = 'state'
        


        # set up the dome        
        self.addr                  = self.config['wintercmd_server_addr']
        self.port                  = self.config['wintercmd_server_port']
        self.connection_timeout    = self.config['wintercmd_server_timeout']
        
        self.roboManager = RoboManager(config = self.config,
                                       addr = self.addr, 
                                       port = self.port, 
                                       status_proxyname = self.proxyname,
                                       logger = self.logger, 
                                       connection_timeout = self.connection_timeout,
                                       alertHandler = self.alertHandler,
                                       verbose = self.verbose)        
        
        self.pyro_thread = daemon_utils.PyroDaemon(obj = self.roboManager, name = 'roboManager')
        self.pyro_thread.start()
        


            
        
def sigint_handler( *args):
    """Handler for the SIGINT signal."""
    sys.stderr.write('\r')
    
    print('CAUGHT SIGINT, KILLING PROGRAM')
    
    # close any dangling socket connections
    main.roboManager.commandThread.commandHandler.sock.close()
    
    # explicitly kill each thread, otherwise sometimes they live on
    main.roboManager.statusThread.quit()
    main.roboManager.commandThread.quit()
    
    #main.dome.statusThread.terminate()
    #print('KILLING APPLICATION')
    
    QtCore.QCoreApplication.quit()

if __name__ == "__main__":
    
    #### GET ANY COMMAND LINE ARGUMENTS #####
    
    args = sys.argv[1:]
    
    
    modes = dict()
    modes.update({'-v' : "Running in VERBOSE mode"})
    modes.update({'-p' : "Running in PRINT mode (instead of log mode)."})
    modes.update({'--sunsim' : "Running in SIMULATED SUN mode" })
    
    # set the defaults
    verbose = False
    doLogging = False
    sunsim = False
    #domesim = True
    
    #print(f'args = {args}')
    
    if len(args)<1:
        pass
    
    else:
        for arg in args:
            
            if arg in modes.keys():
                
                # remove the dash when passing the option
                opt = arg.replace('-','')
                if opt == 'v':
                    print(modes[arg])
                    verbose = True
                    
                elif opt == 'p':
                    print(modes[arg])
                    doLogging = False
                
                elif opt == 'domesim':
                    print(modes[arg])
                    domesim = True
            else:
                print(f'Invalid mode {arg}')
    

    
    
    
    
    
    
    ##### RUN THE APP #####
    app = QtCore.QCoreApplication(sys.argv)

    # set the wsp path as the base directory
    base_directory = wsp_path

    # load the config
    config_file = base_directory + '/config/config.yaml'
    config = utils.loadconfig(config_file)
    
    
    # set up the logger
    if doLogging:
        logger = logging_setup.setup_logger(base_directory, config)    
    else:
        logger = None
    
    # set up the main app. note that verbose is set above
    main = PyroGUI(config = config, logger = logger, verbose = verbose, sunsim = sunsim)

    # handle the sigint with above code
    signal.signal(signal.SIGINT, sigint_handler)
    # Murder the application (reference: https://stackoverflow.com/questions/4938723/what-is-the-correct-way-to-make-my-pyqt-application-quit-when-killed-from-the-co)
    #signal.signal(signal.SIGINT, signal.SIG_DFL)


    # Run the interpreter every so often to catch SIGINT
    timer = QtCore.QTimer()
    timer.start(100) 
    timer.timeout.connect(lambda: None) 

    sys.exit(app.exec_())
