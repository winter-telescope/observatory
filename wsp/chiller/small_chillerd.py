#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Mar 22 11:33:37 2021

small_chillerd.py

This is part of wsp

# Purpose #

This is a standalone daemon for handling communications with the temporary chiller for the visible-wavelegnth camera. It uses a PyQt5 for managing threading and event handling, and uses Pyro5 for  hosting a remote object which wraps a TCP/IP interface and allows communication between WSP and the daemon.

Not sure if the RTU serial connection will let us do multithreading, so may 
need to move everything to the main event loop.

@author: nlourie, frostig
"""


import os
import Pyro5.core
import Pyro5.server
import time
from PyQt5 import uic, QtCore, QtGui, QtWidgets
import numpy as np
import sys
import signal
from datetime import datetime
import threading
import logging
#from pymodbus.client.sync import ModbusSerialClient
import time
from datetime import datetime
import json
import serial # pip install pyserial
import yaml



# add the wsp directory to the PATH
wsp_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(1, wsp_path)
print(f'wsp_path = {wsp_path}')


#from housekeeping import data_handler
from daemon import daemon_utils
from utils import utils
from utils import logging_setup
# import the alert handler
from alerts import alert_handler



class ReconnectHandler(object):
    '''
    This is a object to handle reconnections, keep track of how often we should
    reconnect, track if we are connected, and reconnect if we need to.
    '''
    def __init__(self, connection_timeout = 0):
        self.connection_timeout = connection_timeout
        # Note that the first one gets skipped
        self.reconnect_timeouts = np.array([0, 0.5, 1, 5, 10, 30, 60, 300, 600]) + self.connection_timeout #all the allowed timeouts between reconnection attempts CAN'T BE LESS THAN CONN TIMEOUT
        
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



# class CommandHandler(QtCore.QObject):
    
#     newReply = QtCore.pyqtSignal(str)
#     #newCommand = QtCore.pyqtSignal(object)
#     newRequest = QtCore.pyqtSignal(object)
    
#     def __init__(self, config, logger = None, verbose = False):
#         super(CommandHandler, self).__init__()
        
#         self.config = config
        
#         self.logger = logger
#         self.connection_timeout = self.config['serial_params']['timeout'] # time to allow each connection attempt to take
#         self.verbose = verbose
#         self.connected = False
        
#         self.setup_connection()
        
#     def log(self, msg, level = logging.INFO):
#         if self.logger is None:
#                 print(msg)
#         else:
#             self.logger.log(level = level, msg = msg)    
    
#     def setup_connection(self):
#         self.create_socket()
    
#     def create_socket(self):
#         if self.verbose:
#             self.log(f'(Thread {threading.get_ident()}) CommandHandler: creating socket')

#         self.sock = serial.Serial()
#         self.sock.port        = self.config['serial_params']['port']
#         self.sock.baudrate    = self.config['serial_params']['baudrate']
#         self.sock.timeout     = self.config['serial_params']['timeout']
#         self.sock.parity      = self.config['serial_params']['parity']
#         # breaks the code, use default anyway
#         #self.sock.stopbits    = self.config['serial_params']['stopbits']
#         self.sock.xonxoff     = self.config['serial_params']['xonxoff']
#         self.sock.bytesize    = self.config['serial_params']['bytesize']

        
#     def connect_socket(self):
#         if self.verbose:
#             self.log(f'(Thread {threading.get_ident()}) CommandHandler: Attempting to connect socket')
        
        
#         try:
            
#             #disconnect first
#             #self.sock.close()
#             # try to reconnect the socket
#             self.sock.open()
            
#             #print(f'(Thread {threading.get_ident()}) Connection attempt successful!')
            
#             #if this works, then set connected to True
#             if self.sock.is_open:
#                 self.connected = True
                

#             else:
#                 # the connection is broken. set connected to false
#                 self.connected = False
#                 self.log(f'(Thread {threading.get_ident()}) CommandHandler: connection unsuccessful.')#' waiting {self.reconnector.reconnect_timeout} until next reconnection')   
#                 #self.log(f'(Thread {threading.get_ident()}) StatusMonitor: connection unsuccessful. waiting {self.reconnector.reconnect_timeout} until next reconnection')   
            
            
#         except:
            
#             # the connection is broken. set connected to false
#             self.connected = False
#             self.log(f'(Thread {threading.get_ident()}) CommandHandler: connection unsuccessful.')#' waiting {self.reconnector.reconnect_timeout} until next reconnection')   
#             #self.log(f'(Thread {threading.get_ident()}) StatusMonitor: connection unsuccessful. waiting {self.reconnector.reconnect_timeout} until next reconnection')   
            
            
#     def sendCommand(self, register_request):
#         '''
#         This takes the command string and sends it directly to the dome.
#         It takes any received reply and triggers a new reply event
#         '''
#         command_ascii = register_request.command
#         com = command_ascii.decode()
        
#         #print(f'CommandHandler: caught newRequest signal to set {addr} to {value}')
        
#         if self.connected:
#             #self.time_since_last_connection = 0.0
#             #self.reconnector.time_since_last_connection = 0.0
#             #print(f'Connected! Querying Dome Status.')
            
            

#             try:
#                 # SEND THE COMMAND
                
#                 self.sock.write(command_ascii)
                
#                 # read response
#                 reply = self.sock.read(self.sock.inWaiting())
#                 # fifth character deams error
#                 err_char = chr(reply[5])
#                 self.log(f'CommandHandler: Command sent reply = {reply}')
#                 if err_char == '0':
#                         self.log(f'CommandHandler: Command sent successfully! reply = {reply}')
                
#                 # possible errors
#                 elif err_char == '1':
#                     self.log(f'chiller: checksum error, please check if valid command')
                    
#                 elif err_char == '2':
#                     self.log(f'chiller: Bad Command Number (Command Not used)')
                    
#                 elif err_char == '3':
#                     self.log(f'chiller: Parameter/Data Out of Bound')
                    
#                 else:
#                     if self.verbose:
#                         self.log(f'chiller: could not get {com}: {reply}')
#                     pass
            
#             except Exception as e:
#                 #print(f'Query attempt failed.')
#                 self.log(f'CommandHandler: Tried to write {com} : {e}')
#                 self.connected = False
#         else:
#             self.log(f'CommandHandler: Received command to write {com} but chiller was disconnected. ')

#             # the dome is not connected. set the reply to something that represents this state
#             #self.newReply.emit(self.disconnectedReply)
#             pass 
        
        
        
        
class StatusMonitor(QtCore.QObject):
    
    newStatus = QtCore.pyqtSignal(object)
    doReconnect = QtCore.pyqtSignal()
    newReply = QtCore.pyqtSignal(str)
    #newCommand = QtCore.pyqtSignal(object)
    newRequest = QtCore.pyqtSignal(object)
    alert_error = QtCore.pyqtSignal(object)  
    
    
    def __init__(self, config, logger = None, verbose = False, alertHandler  = None):
        super(StatusMonitor, self).__init__()
        
        self.config = config
        # general attributes
        #self.modbus_offset = self.config['modbus_register_offset']
        self.serial_query_dt = self.config['serial_query_dt']

        # dictionary that holds all the registers to query
        self.com_dict = self.config['commands']
        

        self.logger = logger
        self.connection_timeout = self.config['serial_params']['timeout'] # time to allow each connection attempt to take
        self.verbose = verbose
        self.timestamp = datetime.utcnow().timestamp()
        self.connected = False
        
        # set up alerts
        self.alertHandler = alertHandler
        self.alert_error.connect(self.broadcast_alert)
        
        # set up the state dictionary
        self.setup_state_dict()
        
        # have the doReconnect signal reattempt the connection
        #self.doReconnect.connect(self.connect_socket)
        
        self.reconnector = ReconnectHandler()
        
        self.setup_connection()
    
    def setup_state_dict(self):
        
        # state dictionary holds the parsed 
        self.state = dict()
        
        # nested dictionary that holds the timestamps of the last time and dt since each field was successfully polled
        self.state.update({'last_poll_time' : dict() })
        self.state.update({'last_poll_dt'   : dict() })

        
        init_timestamp = datetime.utcnow().timestamp()
        
        for key in self.com_dict.keys():
            self.state.update({key :  -888})
            self.state['last_poll_time'].update({key : init_timestamp})
            self.state['last_poll_dt'].update({key : 0.0})
    
    def log(self, msg, level = logging.INFO):
        if self.logger is None:
                print(msg)
        else:
            self.logger.log(level = level, msg = msg)    
    
    def broadcast_alert(self, name, content):
        # create a notification
        print(f'Broadcasting error: Chiller has encountered {name} : {content}' )
        msg = f':redsiren: *Alert!!*  Chiller has encountered {name} : {content}'       
        group = 'sudo'
        self.alertHandler.slack_log(msg, group = group)
    
    def setup_connection(self):
        self.create_socket()
    
    def create_socket(self):
        if self.verbose:
            self.log(f'(Thread {threading.get_ident()}) StatusMonitor: creating socket')
            

        self.sock = serial.Serial()
        self.sock.port        = self.config['serial_params']['port']
        self.sock.baudrate    = self.config['serial_params']['baudrate']
        self.sock.timeout     = self.config['serial_params']['timeout']
        self.sock.parity      = self.config['serial_params']['parity']
        # use default
        #self.sock.stopbits    = self.config['serial_params']['stopbits']
        self.sock.xonxoff     = self.config['serial_params']['xonxoff']
        self.sock.bytesize    = self.config['serial_params']['bytesize']
        
            
        
    def connect_socket(self):
        if self.verbose:
            self.log(f'(Thread {threading.get_ident()}) StatusMonitor: Attempting to connect socket')
        # record the time of this connection attempt
        #self.reset_last_recconnect_timestamp()
        self.reconnector.reset_last_reconnect_timestamp()
        
        # increment the reconnection timeout
        self.reconnector.increment_reconnect_timeout()
        
        try:
            # disconnect first
            #self.sock.close()
            # try to reconnect the socket
            self.sock.open()
            
            #print(f'(Thread {threading.get_ident()}) Connection attempt successful!')
            
            #if this works, then set connected to True
            if self.sock.is_open:
                self.connected = True
                
                # since the connection is fine, reset all the timeouts
                self.reconnector.reset_reconnect_timeout()
            else:
                # the connection is broken. set connected to false
                self.connected = False
                self.log(f'(Thread {threading.get_ident()}) StatusMonitor: connection unsuccessful. waiting {self.reconnector.reconnect_timeout} until next reconnection')   
            
            
        except:
            
            # the connection is broken. set connected to false
            self.connected = False
            self.log(f'(Thread {threading.get_ident()}) StatusMonitor: connection unsuccessful. waiting {self.reconnector.reconnect_timeout} until next reconnection')   
            
            
    
    def updateState(self, state):
        '''
        When we receive a status update, add each element 
        to the state dictionary
        '''
        #print(f'(Thread: {threading.get_ident()}): recvd dome state: {domeState}')
        print("STATE", state)
        if type(state) is dict:
            # make sure we don't get some garbage, and only attempt if this is actually a dictionary
            for key in state.keys():
                try:
                    self.state.update({key : state[key]})
                
                except:
                    pass
        
    def update_all_last_poll_dt(self):
        """
        Loops through all the state variables, and updates the dt since they
        were last updated. The state last_poll_time is updated only in self.pollStatus,
        but this can be used to more regularly update how long its been since each
        field was updated with fresh information from the chiller
        """
        for reg in self.config['commands']:
            try:
                # Update all the dt times
                # calculate the time since the last successfull pol
                timestamp = datetime.utcnow().timestamp()
                time_since_last_poll = timestamp - self.state['last_poll_time'][reg]
                self.state['last_poll_dt'].update({reg : time_since_last_poll})
            except Exception as e:
                print(f'Could not update dt for {reg}, error: {e}')
                pass
        
    def pollStatus(self):
        """
        if self.verbose:
            self.log(f'StatusMonitor: Polling status from Thread {threading.get_ident()}')
        """
        # record the time that this loop runs
        self.timestamp = datetime.utcnow().timestamp()
        
        # report back some useful stuff
        self.state.update({'poll_timestamp' : self.timestamp})
        self.state.update({'reconnect_remaining_time' : self.reconnector.reconnect_remaining_time})
        self.state.update({'reconnect_timeout' : self.reconnector.reconnect_timeout})
        self.state.update({'is_connected' : self.connected})
        
        # if the connection is live, ask for the chiller status
        if self.sock.is_open:
            self.connected = True
            #self.time_since_last_connection = 0.0
            self.reconnector.time_since_last_connection = 0.0
            #print(f'Connected! Querying Status.')
            try:
                # Do the query!
                
                # Read the registers one by one
                for com in self.config['commands']:
                    
                    
                    # read the register if its mode is 'r' or 'rw'
                    if 'r' in self.config['commands'][com]['mode']:
                        #print(f'chiller: querying {reg}')
                        try:
                            
                            # get command
                            command_string = self.config['commands'][com]['command']
                            # add checksum
                            check_sum = hex(sum(command_string.encode('ascii')) % 256)[2:]
                            if len(check_sum) == 1:
                                check_sum = '0' + check_sum
                            command_ascii = command_string.encode('ascii') + check_sum.encode('ascii') + b'\r'
                            self.sock.write(command_ascii)
                            time.sleep(1)                            
                            # read response
                            reply = self.sock.read(self.sock.inWaiting())
                            # fifth character deams error
                            err_char = chr(reply[5])
                            
                            # calculate the time since the last successfull pol
                            timestamp = datetime.utcnow().timestamp()
                            
                            
                            if err_char == '0':
                                if com == 'readWatchDog':
                                    val = reply[14:18]
                                    val = val.decode()
                                    self.state.update({'ControlStatusMode' : int(val[0])})
                                    self.state.update({'PumpStatusFlag' : int(val[1])})
                                    self.state.update({'AlarmStatusFlag' : int(val[2])})
                                    self.state.update({'WarningStatusFlag' : int(val[3])})
                                    self.state['last_poll_time'].update({'ControlStatusMode' : timestamp})
                                    self.state['last_poll_time'].update({'PumpStatusFlag': timestamp})
                                    self.state['last_poll_time'].update({'AlarmStatusFlag'  : timestamp})
                                    self.state['last_poll_time'].update({'WarningStatusFlag' : timestamp})
                                    if int(val[3]) == 1: #NPL 7-12-21 updated with the recast since val is a string
                                    #if val[3] == 1:
                                        print(f"Chiller alarm!: val[3] = {val[3]}, type(val[3]) = {type(val[3])}")
                                        command_string = '.0166rAlrmBit'
                                        check_sum = hex(sum(command_string.encode('ascii')) % 256)[2:]
                                        if len(check_sum) == 1:
                                            check_sum = '0' + check_sum
                                        command_ascii = command_string.encode('ascii') + check_sum.encode('ascii') + b'\r'
                                        self.sock.write(command_ascii)
                                        time.sleep(1)
                                        reply = self.sock.read(self.sock.inWaiting())
                                        print("alarm says: ", reply)
                                        err_name = 'Chiller alarm triggered'
                                        err_content = reply
                                        self.broadcast_alert(err_name, err_content)
                                else:
                                    val = reply[14:19]
                                    #print('temp_val', val)
                                    val = val.decode()
                                    val = int(val)*0.1
                                    self.state.update({com : val})
                                    self.state['last_poll_time'].update({com : timestamp})                                     # TODO - finish
                                    # update the state with the register value
                                    #self.state.update({com : val})
                                    
                                    
                                
                                    
                                    # log the timestamp of this poll for THIS REGISTER ONLY for future calculation of dt
                                    # self.state['last_poll_time'].update({com : timestamp})
                            
                            # possible errors
                            elif err_char == '1':
                                self.log(f'chiller: checksum error, please check if valid command')
                                
                            elif err_char == '2':
                                self.log(f'chiller: Bad Command Number (Command Not used)')
                                
                            elif err_char == '3':
                                self.log(f'chiller: Parameter/Data Out of Bound')
                             
                            elif err_char == '4':
                                self.log(f'chiller: Message length error')
                                
                            elif err_char == '5':
                                self.log(f'chiller: Sensor/Feature not Configured or Used')
                                            
                            else:
                                if self.verbose:
                                    self.log(f'chiller: could not get {com}: {reply}')
                                pass
                            
                            # update the dt since last update for ALL fields
                            #self.update_all_last_poll_dt()
                            
                            
                        
                        except Exception as e:
                            print(f'Poll chiller status error: {e}')
                            pass
                        
                        
                        time.sleep(self.serial_query_dt)
                        
                    else:
                        # the register is not specified to be read
                        pass
                
            
            except Exception as e:
                print(f'Query attempt failed: {e}')
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
 
    def sendCommand(self, register_request):
        '''
        This takes the command string and sends it directly to the dome.
        It takes any received reply and triggers a new reply event
        '''
        command_ascii = register_request.command
        com = command_ascii.decode()
        
        #print(f'CommandHandler: caught newRequest signal to set {addr} to {value}')
        
        if self.sock.is_open:
            #self.time_since_last_connection = 0.0
            #self.reconnector.time_since_last_connection = 0.0
            #print(f'Connected! Querying Dome Status.')
            
            

            try:
                # SEND THE COMMAND
                self.sock.write(command_ascii)
                time.sleep(1)
                
                # read response
                reply = self.sock.read(self.sock.inWaiting())

                # # send test error
                # err_name = 'Chiller test error, no need to be alarmed :)'
                # err_content = reply
                # print('Sending test error')
                # self.broadcast_alert(err_name, err_content)
                
                # fifth character deams error
                err_char = chr(reply[5])
                self.log(f'CommandHandler: Command sent reply = {reply}')
                if err_char == '0':
                        self.log(f'CommandHandler: Command sent successfully! reply = {reply}')
                
                # possible errors
                elif err_char == '1':
                    self.log(f'chiller: checksum error, please check if valid command')
                    
                elif err_char == '2':
                    self.log(f'chiller: Bad Command Number (Command Not used)')
                    
                elif err_char == '3':
                    self.log(f'chiller: Parameter/Data Out of Bound')
                    
                elif err_char == '4':
                    self.log(f'chiller: Message length error')
                    
                elif err_char == '5':
                    self.log(f'chiller: Sensor/Feature not Configured or Used')
                    
                else:
                    if self.verbose:
                        self.log(f'chiller: could not get {com}: {reply}')
                    pass
            
            except Exception as e:
                #print(f'Query attempt failed.')
                self.log(f'CommandHandler: Tried to write {com} : {e}')
                self.connected = False
        else:
            self.log(f'CommandHandler: Received command to write {com} but chiller was disconnected. ')

            # the dome is not connected. set the reply to something that represents this state
            #self.newReply.emit(self.disconnectedReply)
            pass 
        

class StatusThread(QtCore.QThread):
    """ I'm just going to setup the event loop and do
        nothing else..."""
    newStatus = QtCore.pyqtSignal(object)
    doReconnect = QtCore.pyqtSignal()
    newReply = QtCore.pyqtSignal(int)
    #newCommand = QtCore.pyqtSignal(str)
    newRequest = QtCore.pyqtSignal(object)
    #doReconnect = QtCore.pyqtSignal()
    
    
    def __init__(self, config, logger = None, verbose = False, alertHandler = None):
        super(QtCore.QThread, self).__init__()
        self.config = config
        self.logger = logger
        self.verbose = verbose
        self.alertHandler = alertHandler
        
        
        # check the update time is okay! will be bad if the loop time takes longer than the total poll time
        self.min_poll_time = len(self.config['commands']) * (self.config['serial_query_dt'] + self.config['serial_params']['timeout'])
        
        if self.config['status_poll_dt_seconds'] <= self.min_poll_time:
            print(f"specified poll dt ({self.config['status_poll_dt_seconds']}) less than minimum dt ({self.min_poll_time}).")
            self.update_dt = 1.2 * (self.min_poll_time * 1000)

            print(f"setting poll dt to 1.2 * min = {self.update_dt/1000}")
        
        else:
            self.update_dt = self.config['status_poll_dt_seconds']*1000.0


    def HandleRequest(self, request_object):
        self.newRequest.emit(request_object)
            
    def run(self):    
        def SignalNewStatus(newStatus):
            self.newStatus.emit(newStatus)
        def SignalDoReconnect():
            self.doReconnect.emit()
            
        def SignalNewReply(reply):
            self.newReply.emit(reply)
        
        self.timer= QtCore.QTimer()
        self.statusMonitor = StatusMonitor(self.config, logger = self.logger, verbose = self.verbose, alertHandler= self.alertHandler)
        
        self.statusMonitor.newStatus.connect(SignalNewStatus)
        self.statusMonitor.doReconnect.connect(SignalDoReconnect)
        
        self.newRequest.connect(self.statusMonitor.sendCommand)
        self.statusMonitor.newReply.connect(SignalNewReply) # fix
        
        self.timer.setSingleShot(False)
        self.timer.timeout.connect(self.statusMonitor.pollStatus)
        self.timer.start(self.update_dt)
        self.exec_()


# class CommandThread(QtCore.QThread):
#     newReply = QtCore.pyqtSignal(int)
#     #newCommand = QtCore.pyqtSignal(str)
#     newRequest = QtCore.pyqtSignal(object)
#     doReconnect = QtCore.pyqtSignal()
    
#     def __init__(self, config, logger = None,  verbose = False):
#         super(QtCore.QThread, self).__init__()
        
#         self.config = config
#         self.logger = logger
#         self.verbose = verbose
    
#     def HandleRequest(self, request_object):
#         self.newRequest.emit(request_object)
    
#     def DoReconnect(self):
#         #print(f'(Thread {threading.get_ident()}) Main: caught reconnect signal')
#         self.doReconnect.emit()
    
#     def run(self):    
#         def SignalNewReply(reply):
#             self.newReply.emit(reply)
        
#         self.commandHandler = CommandHandler(config = config, logger = self.logger, verbose = self.verbose)
#         # if the newReply signal is caught, execute the sendCommand function
#         self.newRequest.connect(self.commandHandler.sendCommand)
#         self.commandHandler.newReply.connect(SignalNewReply)
        
#         # if we recieve a doReconnect signal, trigger a reconnection
#         self.doReconnect.connect(self.commandHandler.connect_socket)
        
#         self.exec_()

       
class RegisterRequest(object):
    def __init__(self, addr, value):
        self.addr = addr
        self.value = value
        
class SerialCommandRequest(object):
    def __init__(self, command):
        self.command = command

#class Dome(object):        
class Chiller(QtCore.QObject):
    """
    This is the pyro object that handles connections and communication with
    the chiller.
    
    NOTE: config is a dictionary that contains the necessary chiller configuration
    parameters
    
    This object has several threads within it for handling connection,
    communication, and commanding.
    
    NOTE:
        This inherets from QObject, which allows it to have custom signals
        which can communicate with the communication threads
    """
    
    #statusRequest = QtCore.pyqtSignal(object)
    commandRequest = QtCore.pyqtSignal(object)
    
    def __init__(self, config, logger = None, verbose = False, alertHandler=None):
        super(Chiller, self).__init__()
        # attributes describing the internet address of the dome server
        self.config = config
        self.logger = logger
        self.state = dict()
        self.verbose = verbose
        self.alertHandler = alertHandler
        
        self.statusThread = StatusThread(  config = self.config, logger = self.logger, verbose = self.verbose, alertHandler = self.alertHandler )
        # self.commandThread = CommandThread(config = self.config, logger = self.logger, verbose = self.verbose)
        # connect the signals and slots
        
        self.statusThread.start()
        # self.commandThread.start()
        
        # if the status thread is request a reconnection, trigger the reconnection in the command thread too
        # self.statusThread.doReconnect.connect(self.commandThread.DoReconnect)
        
        self.statusThread.newStatus.connect(self.updateStatus)
        self.commandRequest.connect(self.statusThread.HandleRequest)
        # self.commandThread.newReply.connect(self.updateCommandReply)
        self.log(f'chiller: running in thread {threading.get_ident()}')
    
    
    
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
    def update_all_last_poll_dt(self):
        """
        Loops through all the state variables, and updates the dt since they
        were last updated. The state last_poll_time is updated only in self.pollStatus,
        but this can be used to more regularly update how long its been since each
        field was updated with fresh information from the chiller
        """
        for reg in self.config['commands']:
            try:
                # Update all the dt times
                # calculate the time since the last successfull pol
                timestamp = datetime.utcnow().timestamp()
                time_since_last_poll = timestamp - self.state['last_poll_time'][reg]
                self.state['last_poll_dt'].update({reg : time_since_last_poll})
            except Exception as e:
                if self.verbose:
                    print(f'Could not update dt for {reg}, error: {e}')
                pass
            
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
        # make a note of the time that the status was requested
        self.state.update({'request_timestamp' : datetime.utcnow().timestamp()})
        
        # update all the dt since last updated
        self.update_all_last_poll_dt()
        
        return self.state
    
    @Pyro5.server.expose
    def WriteCommand(self, command, value):
        self.log(f'chiller: got request to set {command} to {value}')
        # make sure the register is in the list
        com = command

        if com in self.config['commands']:
            if 'w' in self.config['commands'][com]['mode']:
                
                try:
                
                    #self.log(f'chiller: register request is on write-approved list')
                    # get command
                    command_string = self.config['commands'][com]['command']
                    #scale = self.config['registers'][register]['scale']
                    
                    
                    # make input ascii to add to command string
                    command_string = command_string + value
                    
                    # add checksum
                    check_sum = hex(sum(command_string.encode('ascii')) % 256)[2:]
                    if len(check_sum) == 1:
                                check_sum = '0' + check_sum
                    command_ascii = command_string.encode('ascii') + check_sum.encode('ascii') + b'\r'
                    
                    # write the value to the specified command register
                    request = SerialCommandRequest(command = command_ascii)
                    self.commandRequest.emit(request)
                    
                      # TODO - finish
                    # update the state with the register value
                    self.state.update({com : value})
                    
                    
                    # calculate the time since the last successfull pol
                    timestamp = datetime.utcnow().timestamp()
                    
                    # log the timestamp of this poll for THIS REGISTER ONLY for future calculation of dt
                    self.state['last_poll_time'].update({com : timestamp})
                
                except Exception as e:
                    #print(f'Query attempt failed.')
                    self.log(f'Chiller write command: Tried to write {com} but unfortunately: {e}')
              
                
                
                
            else:
                # the register is not on the write-allowed list
                self.log(f'chiller: ignored request for {command} which is set to read-only in config file')
                return
        
        else:
            # the register is not on the list
            self.log(f'chiller: ignored request to {command} which is not included in the config file')

            return
        
    @Pyro5.server.expose
    def setSetpoint(self, temperature):
        # change the setpoint
        self.log(f'got request to set chiller temperature to {temperature} C')
        temperature_string = int(temperature / 0.1)
        temperature_string = '0'+ str(temperature_string)
        self.WriteCommand('setCtrlT', temperature_string)
        
    @Pyro5.server.expose
    def TurnOn(self):
        # TURN THE CHILLER ON
        self.log('got request set chiller to RUN')
        self.WriteCommand('setStatus', '1')
    
    @Pyro5.server.expose
    def TurnOff(self):
        # TURN THE CHILLER OFF
        self.log('got request to set chiller to STANDBY')
        self.WriteCommand('setStatus', '0')
    
    """# Commands which make the dome do things
    @Pyro5.server.expose
    def Home(self):
        cmd = 'home'
        self.commandRequest.emit(cmd)"""
    
    
        
        
class PyroGUI(QtCore.QObject):   
    """
    This is the main class for the daemon. It is a QObject, which means that
    it can be initialized with it's own event loop. This runs the whole daemon,
    and has a dedicated QThread which handles all the Pyro stuff (the PyroDaemon object)
    """
                  
    def __init__(self, config, logger = None, verbose = False, alertHandler = None, parent=None ):            
        super(PyroGUI, self).__init__(parent)   

        self.config = config
        self.logger = logger
        self.verbose = verbose
        self.alertHandler = alertHandler
        
        msg = f'(Thread {threading.get_ident()}: Starting up Chiller Daemon '
        if logger is None:
            print(msg)
        else:
            logger.info(msg)

        
        # set up the dome
        self.chiller = Chiller(config = self.config,
                               logger = self.logger,
                               verbose = self.verbose,
                               alertHandler = self.alertHandler)
        
              
        self.pyro_thread = daemon_utils.PyroDaemon(obj = self.chiller, name = 'chiller')
        self.pyro_thread.start()
        


            
        
def sigint_handler( *args):
    """Handler for the SIGINT signal."""
    sys.stderr.write('\r')
    
    print('CAUGHT SIGINT, KILLING PROGRAM')
    
    # explicitly kill each thread, otherwise sometimes they live on
    main.chiller.statusThread.quit()
    #main.dome.commandThread.quit()
    
    QtCore.QCoreApplication.quit()

if __name__ == "__main__":
    
    #### GET ANY COMMAND LINE ARGUMENTS #####
    
    args = sys.argv[1:]
    
    
    modes = dict()
    modes.update({'-v' : "Running in VERBOSE mode"})
    modes.update({'-p' : "Running in PRINT mode (instead of log mode)."})
    
    # set the defaults
    verbose = False
    doLogging = True
    
    # Debugging mode
    #verbose = True
    #doLogging = False
    
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
                
                
            else:
                print(f'Invalid mode {arg}')
    


    
    
    
    
    ##### RUN THE APP #####
    app = QtCore.QCoreApplication(sys.argv)

    # set the wsp path as the base directory
    base_directory = wsp_path

    # load the config
    #config_file = base_directory + '/config/config.yaml'
    config_file = base_directory + '/config/small_chiller_config.yaml'
    config = utils.loadconfig(config_file)
    
    # set up the logger
    if doLogging:
        logger = logging_setup.setup_logger(base_directory, config)    
    else:
        logger = None
    
    # set up alerts locally
    # set up the alert system to post to slack
    auth_config_file  = wsp_path + '/credentials/authentication.yaml'
    user_config_file = wsp_path + '/credentials/alert_list.yaml'
    alert_config_file = wsp_path + '/config/alert_config.yaml'
    
    auth_config  = yaml.load(open(auth_config_file) , Loader = yaml.FullLoader)
    user_config = yaml.load(open(user_config_file), Loader = yaml.FullLoader)
    alert_config = yaml.load(open(alert_config_file), Loader = yaml.FullLoader)
    
    alertHandler = alert_handler.AlertHandler(user_config, alert_config, auth_config)
    print("alert handler", alertHandler, type(alertHandler))
    
    # set up the main app. note that verbose is set above
    main = PyroGUI(config = config, logger = logger, verbose = verbose, alertHandler = alertHandler)

    # handle the sigint with above code
    signal.signal(signal.SIGINT, sigint_handler)
    # Murder the application (reference: https://stackoverflow.com/questions/4938723/what-is-the-correct-way-to-make-my-pyqt-application-quit-when-killed-from-the-co)
    #signal.signal(signal.SIGINT, signal.SIG_DFL)

    # daemon = Pyro5.server.Daemon()
    # ns = Pyro5.core.locate_ns()
    # uri = daemon.register(Chiller)
    # ns.register("small_chiller", uri)
    # print("small chiller daemon running")


    # Run the interpreter every so often to catch SIGINT
    timer = QtCore.QTimer()
    timer.start(100) 
    timer.timeout.connect(lambda: None) 

    sys.exit(app.exec_())

