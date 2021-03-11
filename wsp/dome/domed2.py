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



#class ConnectionThread(object):
class ConnectionThread(QtCore.QThread):
    '''
    This is a dedicated thread which handles reconnections to the command server
    It opens a new connection and then does nothing unless a missed connection event
    occurs. A missed connection event will trigger a reconnection attempt. If the 
    reconnection is unsuccessful, it will wait an amount of time specified by the current
    timeout, and then try again. The timeouts get longer and longer, and then are reset
    when there is a successful connection
    '''
    def __init__(self, addr, port, connection_timeout = 1.5, *args, **kwargs):
        QtCore.QThread.__init__(self)
        self.addr = addr # IP address
        self.port = port # port
        self.connection_timeout = connection_timeout # time to allow each connection attempt to take
        
        self.reconnection_timeout = 0.0
        
    #def __init__(self):
        
        self.reconnect_timeouts = np.array([0.5, 1, 5, 10, 30, 60, 300, 600]) + self.connection_timeout #all the allowed timeouts between reconnection attempts CAN'T BE LESS THAN CONN TIMEOUT
        self.reconnect_timeout_level = 0 # the index of the currently active timeout
        self.current_timeout = self.reconnect_timeouts[self.reconnect_timeout_level]
        
        # start up the thread
        self.start()
        
    # I think i need a run method?
    def run(self):
        
        
        def reset_reconnect_timeout():
            self.timeout_level = 0
        
        def update_timeout():
            '''Set the value of the current timeout'''
            self.current_timeout = self.reconnect_timeouts[self.reconnect_timeout_level]
            #return current_timeout
        
        def increment_reconnect_timeout():
            ''' Increase the timeout level by one '''
            
            # if the current timeout level is greater than or equal to the number of levels, do nothing,
            # otherwise increment by one
            if self.reconnect_timeout_level >= len(self.reconnect_timeouts):
                pass
            else:
               self.reconnect_timeout_level += 1 
     
            # now update the timeout
            self.update_timeout()
        
        def create_socket():
            print('connthread: creating socket')
            self.sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
            self.sock.settimeout(self.connection_timeout)
        
        def connect_socket():
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
            # init the socket
            create_socket()
            
            # make an attribute to keep track of if the connection is connected
            self.connected = False
            self.waiting_for_reconnect = False
    
    """
    
    def run_timer(self):
        print('starting countdown timer!')
        self.conn_attempt_t0 = datetime.utcnow().timestamp()
        self.conn_attempt_dt = 0.0
        
        self.timer = QtCore.QTimer()
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.countdown_and_reconnect)
        self.timer.start()
   
    def countdown_and_reconnect(self):
        if self.conn_attempt_dt < self.current_timeout:
            # the connection is broken. set connected to false
            self.connected = False
            
            # we are starting to count down the timeout. set waiting_for_reconnect to True
            self.waiting_for_reconnect = True
            print(f'time remaining: {self.reconnection_timeout} s')
            
            # update the delta
            self.conn_attempt_dt = datetime.utcnow().timestamp() - self.conn_attempt_t0
            
            # update the time until the next reconnection so it's visible outside
            self.reconnection_timeout = self.current_timeout - self.conn_attempt_dt
        
        else:
            print('timeout finished')
            # we've finished the timeout. stop the wait timer and reattempt connection
            # now that the timeout is done, set self.waiting_for_reconnect to False
            self.waiting_for_reconnect = False
            #self.timer.terminate()
            self.connect_socket
    """
    
                
    

class StatusThread(QtCore.QThread):
    '''
    This is a dedicated QThread which handles the status monitoring of the
    dome. It's only job is to continuously ask the dome for it's status.
    
    This thread has it's own Connection thread which can be used to reoconnect
    the socket if there is an error each time the status is queried.
    '''
    reconnect = QtCore.pyqtSignal()

    def __init__(self, addr, port, connection_timeout = 1.5):
        QtCore.QThread.__init__(self)
        self.addr = addr
        self.port = port
        self.connection_timeout = connection_timeout
        self.dt = 500
        
        #is the connection open?
        self.connected = False
        
        # set up the connection thread
        self.connthread = ConnectionThread(self.addr, self.port, self.connection_timeout)
        
        # wait until the socket is created. sometimes this takes a finite but almost zero amount of time
        while True:
            try:
                self.sock = self.connthread.sock
                break
            except:
                pass
        
        # status
        self.status = dict()
        
        # connect signal to slot
        self.reconnect.connect(self.connthread.connect_socket)
        
        # START UP THE THREAD
        self.start()
    
    def run(self):
        def queryStatus():
            #print(f'statusthread: querying status (thread = {threading.get_ident()}')
            if self.connected == True:
                print(f'     statusthread (Thread {threading.get_ident()}): connected! ')
            else:
                print(f'     statusthread (Thread {threading.get_ident()}): not connected :(')
                
                # if the connection thread is NOT already waiting out a reconnection timeout, tell it to reconnect
                if not self.connthread.waiting_for_reconnect == True:
                    self.reconnect.emit()
                    # Note we don't want to continuously emit this signal, otherwise it will
                    # bog down the conn thread
        
        # Set up a timer to run the status thread loop
        print(f'statusthread: starting timed loop in Thread {threading.get_ident()}')
        self.timer = QtCore.QTimer()
        self.timer.setInterval(self.dt)
        self.timer.timeout.connect(queryStatus)
        self.timer.start()
        self.exec()
        
        print(f'statusthread: running in thread {threading.get_ident()}')
        
    
    


class Dome(object):        
#class Dome(QtCore.QObject):
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
        #super(Dome, self).__init__()
        # attributes describing the internet address of the dome server
        self.addr = addr
        self.port = port
        self.connection_timeout = connection_timeout
        self.status = dict()
        
        print(f'Dome: running in thread {threading.get_ident()}')
        
        # this is a dumb debug thing, run a daqloop that just prints the thread name to keep track of the threads
        #self.printloop = data_handler.daq_loop(self.nullFunction, 1000, print_thread_name_in_update = True, thread_numbering = 'norm')
        
        # Set up the status thread
        self.statusThread = StatusThread(addr = self.addr, port = self.port, connection_timeout = self.connection_timeout)
        
        
        # External methods
        
    # This can return the status over the pyro server
    @Pyro5.server.expose
    def getStatus(self):
        return self.status()
    
    def nullFunction(self):
        pass



        
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
    print('KILLING STATUS THREAD CONNECTION THREAD')
    #main.dome.statusThread.connthread.quit()
    main.dome.statusThread.connthread.terminate()
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
