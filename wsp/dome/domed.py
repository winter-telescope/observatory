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

# add the wsp directory to the PATH
wsp_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(1, wsp_path)
print(f'wsp_path = {wsp_path}')


from housekeeping import data_handler
from daemon import daemon_utils
from utils import utils
from utils import logging_setup


class StatusMonitor(QtCore.QObject):
    
    newStatus = QtCore.pyqtSignal(object)
    def __init__(self, addr, port, connection_timeout = 0.5):
        super(StatusMonitor, self).__init__()
        
        self.status = dict()
        self.addr = addr # IP address
        self.port = port # port
        self.connection_timeout = connection_timeout # time to allow each connection attempt to take
        
        self.reconnect_timeouts = np.array([0.5, 1, 5, 10, 30, 60, 300, 600]) + self.connection_timeout #all the allowed timeouts between reconnection attempts CAN'T BE LESS THAN CONN TIMEOUT
        self.reconnect_timeout_level = 0 # the index of the currently active timeout
        self.reconnect_timeout = self.reconnect_timeouts[self.reconnect_timeout_level]
        
        self.timestamp = datetime.utcnow().timestamp()
        self.connected = False
        
        self.reset_last_recconnect_timestamp()
        self.setup_connection()
        
    def reset_last_recconnect_timestamp(self):
        self.last_reconnect_timestamp = datetime.utcnow().timestamp()
        self.reconnect_remaining_time = 0.0
    
    def setup_connection(self):
        self.create_socket()
    

        
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
        if self.reconnect_timeout_level >= len(self.reconnect_timeouts):
            pass
        else:
           self.reconnect_timeout_level += 1 
 
        # now update the timeout
        self.update_timeout()
    
    def create_socket(self):
        print('creating socket')
        self.sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        self.sock.settimeout(self.connection_timeout)
        
    
    def old_connect_socket(self):
        if self.connected == False:
            try:
                
                # try to reconnect the socket
                self.sock.connect((self.addr, self.port))
                
                #if this works, then set connected to True
                self.connected = True
                
                
            except:
                
                # the connection is broken. set connected to false
                self.connected = False
                
                print(f'connthread: connection unsuccessful. waiting {self.current_timeout} until next reconnection')
                
                #self.run_timer()
                
                # set up a counter to count time until the reconnection timeout
                conn_attempt_t0 = datetime.utcnow().timestamp()
                conn_attempt_dt = 0.0
                
                
                # now tick off time until we've hit the timeout, then loop back to attempt reconnection
                while conn_attempt_dt < self.current_timeout:
                    print(f'time remaining: {self.reconnection_timeout:.0f} s (thread = {threading.get_ident()}')
                    # wait a hot second
                    #QtCore.QThread.sleep(1)
                    self.sleep(1)
                    
                    # update the delta
                    conn_attempt_dt = datetime.utcnow().timestamp() - conn_attempt_t0
                    
                    # update the time until the next reconnection so it's visible outside
                    self.reconnection_timeout = self.current_timeout - conn_attempt_dt
                
                print('timeout complete. incrementing timeout:')
                # once we're out of the timeout loop, update the timeout and prepare to try connection again
                # increment the timeout
                self.increment_reconnect_timeout()
                print(f'after incrementing, timeout is now {self.current_timeout:.0f}')
            
            print(f'connthread: running in thread {threading.get_ident()}')
        
            
            # make an attribute to keep track of if the connection is connected
            self.connected = False
            self.waiting_for_reconnect = False
        """
                self.reconnect_timeouts = np.array([0.5, 1, 5, 10, 30, 60, 300, 600]) + self.connection_timeout #all the allowed timeouts between reconnection attempts CAN'T BE LESS THAN CONN TIMEOUT
        self.reconnect_timeout_level = 0 # the index of the currently active timeout
        self.reconnect_timeout = self.reconnect_timeouts[self.reconnect_timeout_level]
        
        self.timestamp = datetime.utcnow().timestamp()
        self.connected = False
        
        self.reset_last_recconnect_timestamp()
        self.setup_connection()
        
    def reset_last_recconnect_timestamp(self):
        self.last_reconnect_timestamp = datetime.utcnow().timestamp()
        self.reconnect_remaining_time = 0.0
        
        """
    def updateDomeState(self, domeState):
        '''
        When we receive a status update from the dome, add each element 
        to the state dictionary
        '''
        print(f'(Thread: {threading.get_ident()}): recvd dome state: {domeState}')
        if type(domeState) is dict:
            # make sure we don't get some garbage, and only attempt if this is actually a dictionary
            for key in domeState.keys():
                try:
                    self.state.update({key : domeState[key]})
                
                except:
                    pass
        
        
    def connect_socket(self):
        print(f'(Thread {threading.get_ident()}) Attempting to connect socket')
        # record the time of this connection attempt
        self.reset_last_recconnect_timestamp()
        try:
            
            # try to reconnect the socket
            self.sock.connect((self.addr, self.port))
            
            print(f'(Thread {threading.get_ident()}) Connection attempt successful!')
            
            #if this works, then set connected to True
            self.connected = True
            
            # since the connection is fine, reset all the timeouts
            self.reset_reconnect_timeout()
            
            
            
        except:
            
            # the connection is broken. set connected to false
            self.connected = False
            print(f'(Thread {threading.get_ident()}) connection unsuccessful. waiting {self.reconnect_timeout} until next reconnection')   
            
            # increment the reconnection timeout
            self.increment_reconnect_timeout()
        
    def pollStatus(self):
        print(f'StatusMonitor: Polling status from Thread {threading.get_ident()}')
        # record the time that this loop runs
        self.timestamp = datetime.utcnow().timestamp()
        
        # report back some useful stuff
        self.status.update({'timestamp' : self.timestamp})
        self.status.update({'reconnect_remaining_time' : self.reconnect_remaining_time})
        self.status.update({'reconnect_timeout' : self.reconnect_timeout})
        
        # if the connection is live, ask for the dome status
        if self.connected:
            self.time_since_last_connection = 0.0
            print(f'Connected! Querying Dome Status.')
            try:
                dome_state = utils.query_socket(self.sock,
                             'status?', 
                             end_char = '}',
                             timeout = 2)
                
                self.updateDomeState(dome_state)
            
            except:
                print(f'Query attempt failed.')
                self.connected = False
        else:
            print(f'Dome Status Not Connected. ')
            
            '''
            If we're not connected, then:
                If we've waited the full reconnection timeout, then try to reconnect
                If not, then just note the time and pass''
            '''
            self.time_since_last_connection = (self.timestamp - self.last_reconnect_timestamp)
            self.reconnect_remaining_time = self.reconnect_timeout - self.time_since_last_connection
            
            
            
            if self.reconnect_remaining_time <= 0.0:
                print('Do a reconnect')
                # we have waited the full reconnection timeout
                self.connect_socket()
            
            else:
                # we haven't waited long enough do nothing
                pass
        
        self.newStatus.emit(self.status)
    
    
    
    

class StatusThread(QtCore.QThread):
    """ I'm just going to setup the event loop and do
        nothing else..."""
    newStatus = QtCore.pyqtSignal(object)

    def __init__(self, addr, port):
        super(QtCore.QThread, self).__init__()
        self.addr = addr
        self.port = port
        
    def run(self):    
        def SignalNewStatus(newStatus):
            self.newStatus.emit(newStatus)
        
        self.timer= QtCore.QTimer()
        self.statusMonitor = StatusMonitor(self.addr, self.port)
        
        self.statusMonitor.newStatus.connect(SignalNewStatus)
        
        self.timer.setSingleShot(False)
        self.timer.timeout.connect(self.statusMonitor.pollStatus)
        self.timer.start(1000)
        self.exec_()
        
        

#class Dome(object):        
class Dome(QtCore.QObject):
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
    #commandRequest = QtCore.pyqtSignal(object)
    
    def __init__(self, addr, port, connection_timeout = 1.5):
        super(Dome, self).__init__()
        # attributes describing the internet address of the dome server
        self.addr = addr
        self.port = port
        self.connection_timeout = connection_timeout
        self.status = dict()
        
        self.statusThread = StatusThread(self.addr, self.port)
        # connect the signals and slots
        
        self.statusThread.start()
        
        self.statusThread.newStatus.connect(self.updateStatus)
        
        print(f'Dome: running in thread {threading.get_ident()}')
        
        
    def updateStatus(self, newStatus):
        '''
        Takes in a new status dictionary (eg, from the status thread),
        and updates the local copy of status
        '''
        
        self.status = newStatus
        
        print(f'Dome (Thread {threading.get_ident()}): got new status. status = {self.status}')
        
        
        
    @Pyro5.server.expose
    def getStatus(self):
        return self.status
    
    
    

        
class PyroGUI(QtCore.QObject):   
    """
    This is the main class for the daemon. It is a QObject, which means that
    it can be initialized with it's own event loop. This runs the whole daemon,
    and has a dedicated QThread which handles all the Pyro stuff (the PyroDaemon object)
    """
                  
    def __init__(self, parent=None ):            
        super(PyroGUI, self).__init__(parent)   
        
        # set the wsp path as the base directory
        self.base_directory = wsp_path

        # load the config
        config_file = self.base_directory + '/config/config.yaml'
        self.config = utils.loadconfig(config_file)

        # set up the logger
        self.logger = logging_setup.setup_logger(self.base_directory, self.config)
        
        # set up the dome
        self.servername = 'command_server' # this is the key it uses to set up the server from the conf file
        self.dome_addr                  = self.config[self.servername]['addr']
        self.dome_port                  = self.config[self.servername]['port']
        self.dome_connection_timeout    = self.config[self.servername]['timeout']
        
        self.dome = Dome(addr = self.dome_addr, port = self.dome_port, connection_timeout = self.dome_connection_timeout)        
        
        self.pyro_thread = daemon_utils.PyroDaemon(obj = self.dome, name = 'dome')
        self.pyro_thread.start()
        


            
        
def sigint_handler( *args):
    """Handler for the SIGINT signal."""
    sys.stderr.write('\r')
    
    print('CAUGHT SIGINT, KILLING PROGRAM')
    
    # explicitly kill each thread, otherwise sometimes they live on
    #print('KILLING STATUS THREAD CONNECTION THREAD')
    #main.dome.status_connThread.quit()
    #main.dome.status_connThread.terminate()
    print('KILLING STATUS THREAD')
    #main.dome.statusThread.quit()
    main.dome.statusThread.terminate()
    print('KILLING APPLICATION')
    
    QtCore.QCoreApplication.quit()

if __name__ == "__main__":
    app = QtCore.QCoreApplication(sys.argv)

    
    main = PyroGUI()

    
    signal.signal(signal.SIGINT, sigint_handler)

    # Run the interpreter every so often to catch SIGINT
    timer = QtCore.QTimer()
    timer.start(100) 
    timer.timeout.connect(lambda: None) 

    sys.exit(app.exec_())
