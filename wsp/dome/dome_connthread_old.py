#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Mar 11 15:04:01 2021

just storing this here while i work on a version that works better
@author: winter
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
        # make an attribute to keep track of if the connection is connected
        self.connected = False
        self.waiting_for_reconnect = False
        
        
    #def __init__(self):
        
        self.reconnect_timeouts = np.array([0.5, 1, 5, 10, 30, 60, 300, 600]) + self.connection_timeout #all the allowed timeouts between reconnection attempts CAN'T BE LESS THAN CONN TIMEOUT
        self.reconnect_timeout_level = 0 # the index of the currently active timeout
        self.current_timeout = self.reconnect_timeouts[self.reconnect_timeout_level]
        
        # start up the thread
        #self.start()
        
    # I think i need a run method?
    def run(self):
        # without this exec it seems like the thread completes and never starts its event loop
        
        
        # set up the socket
        print(f'connthread: running in thread {threading.get_ident()}')
        # init the socket
        self.create_socket()
        self.exec()
        
        
        
        
    def reset_reconnect_timeout(self):
        self.timeout_level = 0
    
    def update_timeout(self):
        '''Set the value of the current timeout'''
        self.current_timeout = self.reconnect_timeouts[self.reconnect_timeout_level]
        #return current_timeout
    
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
        print(f'connthread (Thread {threading.get_ident()}): creating socket')
        self.sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        self.sock.settimeout(self.connection_timeout)
    
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
    def reconnection_broker(self):
        '''
        This is the slot which is connected to the disconnection signal from the 
        query thread, eg the status or command thread.
        
        It checks to see if the connection thread is already in the middle of a reconnection
        timeout. If it is, then it does nothing. If it is *not*, then it attemps to reconnect.
        '''
        
        if self.waiting_for_reconnect == False:
            self.connect_socket()
            
        else:
            pass
        
    
    def connect_socket(self):
        
        print(f'connthread (Thread {threading.get_ident()}): attempting to connect socket')
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
                
    
    
    