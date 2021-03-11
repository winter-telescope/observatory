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
        """
        # set up the connection thread
        self.connthread = ConnectionThread(self.addr, self.port, self.connection_timeout)
        self.connthread.start()
        
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
        """
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
                #if not self.connthread.waiting_for_reconnect == True:
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
        
        # Set up a connection thread for the status thread
        #self.status_connThread = ConnectionThread(self.addr, port = self.port, connection_timeout = self.connection_timeout)
        #self.status_connThread.start()
        # Connect the signals and slots
        #self.statusThread.reconnect.connect(self.StatusReconnectBroker)
        
    # This can return the status over the pyro server
    @Pyro5.server.expose
    def getStatus(self):
        return self.status()
    
    def nullFunction(self):
        pass
    
    def StatusReconnectBroker(self):
        '''
        This is the slot which is connected to the disconnection signal from the 
        query thread, eg the status or command thread.
        
        It checks to see if the connection thread is already in the middle of a reconnection
        timeout. If it is, then it does nothing. If it is *not*, then it attemps to reconnect.
        '''
        
        if self.status_connThread.waiting_for_reconnect == False:
            self.status_connThread.connect_socket()
            
        else:
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
    #main.dome.status_connThread.quit()
    main.dome.status_connThread.terminate()
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
