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
from PyQt5 import uic, QtCore, QtGui, QtWidgets
from astropy.io import fits
import numpy as np
import sys
import signal
import queue
import socket
from datetime import datetime
import threading
import logging
import json
import io

# add the wsp directory to the PATH
wsp_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(1, wsp_path)
print(f'wsp_path = {wsp_path}')


#from housekeeping import data_handler
from daemon import daemon_utils
from utils import utils
from utils import logging_setup

# connection methods from planewave

def readline(sock):
    """
    Utility function for reading from a socket until a
    newline character is found
    """
    buf = io.StringIO()
    while True:
        data = sock.recv(1).decode("utf-8")
        buf.write(data)
        if data == '\n':
            return buf.getvalue()
def sendreceive(sock, command):
    """
    Send a command to the server, and read the response.
    The response will be split into an integer error code and an optional error text messsage.
    Returns a tuple (code, error_text)
    """
    sock.send(bytes(command + "\n","utf-8"))
    response = readline(sock)
    # The response should consist of a numeric code, optionally
    # followed by some text if the code is 255 (error). Parse this out.
    fields = response.split(" ")
    response_code = int(fields[0])
    error_text = ""
    if len(fields) > 1:
        error_text = fields[1]
    return (response_code, error_text)

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
    
    
    def __init__(self, addr, port, logger = None, connection_timeout = 0.5, verbose = False):
        super(StatusMonitor, self).__init__()
        
        self.state = dict()
        self.addr = addr # IP address
        self.port = port # port
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
        if self.logger is None:
                print(msg)
        else:
            self.logger.log(level = level, msg = msg)    
    
    def setup_connection(self):
        self.create_socket()
    
    def create_socket(self):
        if self.verbose:
            self.log('(Thread {threading.get_ident()}) StatusMonitor: socket')
        self.sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        self.sock.settimeout(self.connection_timeout)
        
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
            self.setup_connection()
            # try to reconnect the socket
            self.sock.connect((self.addr, self.port))
            
            if self.verbose:
                self.log(f'(Thread {threading.get_ident()}) Connection attempt successful!')
            
            (code, text) = sendreceive(self.sock, "connect")
            if code == 0:
                print ("Connection established")
                #if this works, then set connected to True
                self.connected = True
            else:
                print("ERROR:", code, text) 
                raise Exception 
            
            
            
            
            # since the connection is fine, reset all the timeouts
            self.reconnector.reset_reconnect_timeout()
            
            
        except Exception as e:
            
            # the connection is broken. set connected to false
            self.connected = False
            self.log(f'(Thread {threading.get_ident()}) StatusMonitor: connection unsuccessful: {e}, waiting {self.reconnector.reconnect_timeout} until next reconnection')   
            
            
    
    def updateDomeState(self, domeState):
        '''
        When we receive a status update from the dome, add each element 
        to the state dictionary
        '''
        #print(f'(Thread: {threading.get_ident()}): recvd dome state: {domeState}')
        if type(domeState) is dict:
            # make sure we don't get some garbage, and only attempt if this is actually a dictionary
            for key in domeState.keys():
                try:
                    self.state.update({key : domeState[key]})
                
                except:
                    pass
        
        
    def pollStatus(self):
        #print(f'StatusMonitor: Polling status from Thread {threading.get_ident()}')
        # record the time that this loop runs
        self.timestamp = datetime.utcnow().timestamp()
        
        # report back some useful stuff
        self.state.update({'timestamp' : self.timestamp})
        self.state.update({'reconnect_remaining_time' : self.reconnector.reconnect_remaining_time})
        self.state.update({'reconnect_timeout' : self.reconnector.reconnect_timeout})
        self.state.update({'is_connected' : self.connected})
        
        # if the connection is live, ask for the dome status
        if self.connected:
            #self.time_since_last_connection = 0.0
            self.reconnector.time_since_last_connection = 0.0
            #print(f'Connected! Querying Dome Status.')
            try:
                """
                open_status = utils.query_socket(self.sock,
                             'shutterstate', 
                             end_char = '\n',
                             timeout = 2,
                             singlevalue = True)
                """
                (code, text) = sendreceive(self.sock, "shutterstate")
                # try to convert to number
                #open_status_num = int(open_status.strip())
                #print(f'open_status = {open_status_num}')
                state = dict({"Open_Status" : code})
                #print(f'dome state = {json.dumps(state, indent = 2)}')
                self.updateDomeState(state)
            
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
        if self.logger is None:
                print(msg)
        else:
            self.logger.log(level = level, msg = msg)
    
    def setup_connection(self):
        self.create_socket()
    
    def create_socket(self):
        if self.verbose:
            self.log('(Thread {threading.get_ident()}) CommandHandler: Creating socket')
        self.sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        #self.sock.settimeout(self.connection_timeout)
        
        # give it a long timeout so it can wait for slow replies
        # palomar uses 100 s fora shutter open/close
        # a 360 deg homing cycle takes 360deg/(2.5 deg/s) = 144 s
        # so let's use 150 seconds just to be safe
        #TODO: make the timeout update dynamically based on realistic estimates of the return time!
        self.sock.settimeout(150)
        
    def connect_socket(self):
        #return
        if self.verbose:
            self.log(f'(Thread {threading.get_ident()}) CommandHandler: Attempting to connect socket')
        # record the time of this connection attempt
        #self.reset_last_recconnect_timestamp()
        #self.reconnector.reset_last_reconnect_timestamp()
        
        try:
            self.setup_connection()
            # try to reconnect the socket
            self.sock.connect((self.addr, self.port))
            
            if self.verbose:
                self.log(f'(Thread {threading.get_ident()}) Connection attempt successful!')
            
            (code, text) = sendreceive(self.sock, "connect")
            if code == 0:
                #print ("Connection established")
                #if this works, then set connected to True
                self.connected = True
            else:
                print("ERROR:", code, text) 
                raise Exception 
            
            
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
            self.log(f'CommandHandler: Received command: {cmd}, but dome was disconnected. Reply = {self.disconnectedReply}')

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
    
    def __init__(self, addr, port, logger = None, connection_timeout = 0.5, verbose = False):
        super(QtCore.QThread, self).__init__()
        self.addr = addr
        self.port = port
        self.logger = logger
        self.connection_timeout = connection_timeout
        self.verbose = verbose
        
    def run(self):    
        def SignalNewStatus(newStatus):
            self.newStatus.emit(newStatus)
        def SignalDoReconnect():
            self.doReconnect.emit()
        
        self.timer= QtCore.QTimer()
        self.statusMonitor = StatusMonitor(self.addr, self.port, logger = self.logger, connection_timeout = self.connection_timeout, verbose = self.verbose)
        
        self.statusMonitor.newStatus.connect(SignalNewStatus)
        self.statusMonitor.doReconnect.connect(SignalDoReconnect)
        
        self.timer.setSingleShot(False)
        self.timer.timeout.connect(self.statusMonitor.pollStatus)
        self.timer.start(500)
        self.exec_()
        
        

#class Dome(object):        
class TelescopeShutter(QtCore.QObject):
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
    
    def __init__(self, addr, port, logger = None, connection_timeout = 1.5, verbose = False):
        super(TelescopeShutter, self).__init__()
        # attributes describing the internet address of the dome server
        self.addr = addr
        self.port = port
        self.logger = logger
        self.connection_timeout = connection_timeout
        self.state = dict()
        self.verbose = verbose
        
        self.statusThread = StatusThread(self.addr, self.port, logger = self.logger, connection_timeout = self.connection_timeout, verbose = self.verbose)
        self.commandThread = CommandThread(self.addr, self.port, logger = self.logger, connection_timeout = self.connection_timeout, verbose = self.verbose)
        # connect the signals and slots
        
        self.statusThread.start()
        self.commandThread.start()
        
        # if the status thread is request a reconnection, trigger the reconnection in the command thread too
        self.statusThread.doReconnect.connect(self.commandThread.DoReconnect)
        
        self.statusThread.newStatus.connect(self.updateStatus)
        self.commandRequest.connect(self.commandThread.HandleCommand)
        self.commandThread.newReply.connect(self.updateCommandReply)
        self.log(f'Dome: running in thread {threading.get_ident()}')
        
    def log(self, msg, level = logging.INFO):
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
                    
                    
        #print(f'Dome (Thread {threading.get_ident()}): got new status. status = {self.state}')
    def updateCommandReply(self, reply):
        '''
        when we get a new reply back from the command thread, add it to the status dictionary
        '''
        try:
            self.state.update({'command_reply' : reply})
        except:
            pass
        
    ###### PUBLIC FUNCTIONS THAT CAN BE CALLED USING PYRO SERVER #####
    
    # Return the Current Status (the status is updated on its own)
    @Pyro5.server.expose
    def GetStatus(self):
        return self.state
    
    # Commands which make the dome do things

    
    @Pyro5.server.expose
    def Close(self, wait = False):
        if not wait:
            cmd = 'beginclose'

        self.commandRequest.emit(cmd)
    

    
    @Pyro5.server.expose
    def Open(self, wait = False):
        if not wait:
            cmd = 'beginopen'
        
        self.commandRequest.emit(cmd)
    
    @Pyro5.server.expose
    def Stop(self):
        cmd = 'stop'
        self.commandRequest.emit(cmd)
        

        
    
        
        
class PyroGUI(QtCore.QObject):   
    """
    This is the main class for the daemon. It is a QObject, which means that
    it can be initialized with it's own event loop. This runs the whole daemon,
    and has a dedicated QThread which handles all the Pyro stuff (the PyroDaemon object)
    """
                  
    def __init__(self, config, logger = None, verbose = False, parent=None, sim = False):            
        super(PyroGUI, self).__init__(parent)   

        self.config = config
        self.logger = logger
        self.verbose = verbose
        
        msg = f'(Thread {threading.get_ident()}: Starting up Shutter Daemon '
        if logger is None:
            print(msg)
        else:
            logger.info(msg)

        
        # set up the dome
        self.servername = 'telescope_shutter' # this is the key it uses to set up the server from the conf file
        if sim == True:
            self.addr = 'localhost'
        else:
            self.addr                  = self.config[self.servername]['addr']
        self.port                  = self.config[self.servername]['port']
        self.connection_timeout    = self.config[self.servername]['timeout']
        #print(f'addr = {self.addr}, port = {self.port}')
        self.shutter = TelescopeShutter(addr = self.addr, 
                         port = self.port, 
                         logger = self.logger, 
                         connection_timeout = self.connection_timeout,
                         verbose = self.verbose)        
        
        self.pyro_thread = daemon_utils.PyroDaemon(obj = self.shutter, name = 'shutter')
        self.pyro_thread.start()
        


            
        
def sigint_handler( *args):
    """Handler for the SIGINT signal."""
    sys.stderr.write('\r')
    
    print('CAUGHT SIGINT, KILLING PROGRAM')
    
    # explicitly kill each thread, otherwise sometimes they live on
    main.shutter.statusThread.quit()
    main.shutter.commandThread.quit()
    #main.dome.statusThread.terminate()
    #print('KILLING APPLICATION')
    
    QtCore.QCoreApplication.quit()

if __name__ == "__main__":
    
    #### GET ANY COMMAND LINE ARGUMENTS #####
    
    args = sys.argv[1:]
    
    
    modes = dict()
    modes.update({'-v' : "Running in VERBOSE mode"})
    modes.update({'-p' : "Running in PRINT mode (instead of log mode)."})
    modes.update({'--sim' : "Running in SIMULATED mode" })
    
    # set the defaults
    verbose = True
    doLogging = True
    sim = False
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
                
                elif opt == 'sim':
                    print(modes[arg])
                    sim = True
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
    main = PyroGUI(config = config, logger = logger, verbose = verbose, sim = False)

    # handle the sigint with above code
    signal.signal(signal.SIGINT, sigint_handler)
    # Murder the application (reference: https://stackoverflow.com/questions/4938723/what-is-the-correct-way-to-make-my-pyqt-application-quit-when-killed-from-the-co)
    #signal.signal(signal.SIGINT, signal.SIG_DFL)


    # Run the interpreter every so often to catch SIGINT
    timer = QtCore.QTimer()
    timer.start(100) 
    timer.timeout.connect(lambda: None) 

    sys.exit(app.exec_())
