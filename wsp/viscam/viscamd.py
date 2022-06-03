#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jun  1 11:33:34 2022

A daemon for communicating with the SUMMER accesories. Keeping the viscam
name to keep consistent with the nomenclature within wsp.

This daemon connects and communicates with the flask web server on the SUMMER
raspberry pi to control the summer filter wheel, summer shutter, and other
(future) hardware.

@author: winterpi
"""

import requests
import os
import Pyro5.core
import Pyro5.server
from PyQt5 import QtCore
import numpy as np
import sys
import signal
import threading
import time
import logging
import json
from datetime import datetime

# add the wsp directory to the PATH
wsp_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(1, wsp_path)
print(f'wsp_path = {wsp_path}')



class CommandHandler(QtCore.QObject):
    
    newReply = QtCore.pyqtSignal(str)
    #newCommand = QtCore.pyqtSignal(object)
    newRequest = QtCore.pyqtSignal(object)
    
    def __init__(self, config, logger = None, verbose = False):
        super(CommandHandler, self).__init__()
        
    def doCommand(self, cmd_obj):
            """
            This is connected to the newRequest signal. It parses the command and
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
    
    # send a command to the filter wheel
    # -1: home the filter wheel (sends to pos 0)
    # 1-6 - set filter wheel to position 1-6
    # 8 - get current position
    
    def send_filter_wheel_command(self, position):
        string = self.url + "filter_wheel?n=" + str(position)   
        print(string)
        try:
            res = requests.get(string, timeout=10)
            pos = int(res.text)
            status = res.status_code
            #print("Status", status, "Response: ", res.text)
            #self.logger.info(f'Filter wheel status {status}, {res.text}')
            self.fw_pos = pos
            self.update_state()
            return pos
        except:
            #print("Raspi is not responding")
            self.log(f'Filter wheel is not responding')
            return -11            
                 
                
   
    # send a command to the shutter
    # 0 - close the shutter
    # 1 - open the shutter    
    def send_shutter_command(self, state):
        string = self.url + "shutter?open=" + str(state)
        try:
            res = requests.get(string, timeout=10)
            status = res.status_code
            #print("Status", status, "Response: ", res.text)
            self.log(f'Shutter status {status}, {res.text}')
            return status
        except:
            #print("Raspi is not responding")
            self.log(f'Shutter is not responding')
            return 0
    
    # check what state the shutter is in
    # CAUTION: this is a global variable in the web server,
    # we cannot pull the actual shutter state
    # do not trust this variable
    # 0 - shutter is closed
    # 1 - shutter is open
    def check_shutter_state(self):
        string = self.url  + "shutter_state"
        try:
            res = requests.get(string, timeout=10)
            status = res.status_code
            if res.text[0] == "3":
                #print("Status: ", status, " Unknown shutter state")
                return -1
            elif res.text[0] == "1":
                #print("Status: ", status, "Shutter state is ", res.text)
                return 1
            elif res.text[0] == "0":
                #print("Status: ", status, "Shutter state is ", res.text)
                return 0
            else:
                #print("Status", status, "Response: ", res.text)
                #return status
                return -1
        except:
            #print("Raspi is not responding")
            return -1
    
        

class CommandThread(QtCore.QThread):
    newReply = QtCore.pyqtSignal(int)
    newRequest = QtCore.pyqtSignal(object)
    
    def __init__(self, config, logger = None,  verbose = False):
        super(QtCore.QThread, self).__init__()
        
        self.config = config
        self.logger = logger
        self.verbose = verbose
    
    def HandleRequest(self, request_object):
        self.newRequest.emit(request_object)
    
    def DoReconnect(self):
        #print(f'(Thread {threading.get_ident()}) Main: caught reconnect signal')
        self.doReconnect.emit()
    
    def run(self):    
        def SignalNewReply(reply):
            self.newReply.emit(reply)
        
        self.commandHandler = CommandHandler(config = self.config, logger = self.logger, verbose = self.verbose)
        # if the newReply signal is caught, execute the sendCommand function
        self.newRequest.connect(self.commandHandler.doCommand)
        self.commandHandler.newReply.connect(SignalNewReply)
        
        self.exec_()



class Viscam(QtCore.QObject):
    
    
    commandRequest = QtCore.pyqtSignal(object)

    
    def __init__(self,  config, URL, name = 'viscam', dt = 100, logger = None, verbose = False):
        
        super(Viscam, self).__init__()   
        
        self.config = config
        self.url = URL
        self.state = dict()
        self.logger = logger
        self.verbose = verbose
        
        self.commandThread = CommandThread(config = self.config, logger = self.logger, verbose = self.verbose)
        # connect the signals and slots
        
        self.statusThread.start()
        self.commandThread.start()
        
        # if the status thread is request a reconnection, trigger the reconnection in the command thread too
        self.statusThread.doReconnect.connect(self.commandThread.DoReconnect)
        
        self.statusThread.newStatus.connect(self.updateStatus)
        self.commandRequest.connect(self.commandThread.HandleRequest)
        self.commandThread.newReply.connect(self.updateCommandReply)
        self.log(f'chiller: running in thread {threading.get_ident()}')
        
        self.timer = QtCore.QTimer()
        self.timer.setInterval(self.dt)
        self.timer.timeout.connect(self.update)
        self.timer.start()

    
    def setup_pdu_dict(self):
        
        # make a dictionary of all the pdus
        for pduname in pdu_config['pdus']:
            pduObj = pdu.PDU(pduname, self.pdu_config, self.auth_config, autostart = True, logger = logger)
            
            self.pdu_dict.update({pduname : pduObj})
            
        
    def update(self):

        for pduname in self.pdu_dict:
            
            # query the pdu status
            pdustate = self.pdu_dict[pduname].getState()
            self.state.update({pduname : pdustate})
            #print(pdustate['status'][7])


    def log(self, msg):
        if self.logger is None:
            print(f'Viscam: {msg}')
        else:
            self.logger.info(msg)
    
            
    def update_state(self):
        # poll the state, if we're not connected try to reconnect
        # this should reconnect down the line if we get disconnected
        """        
        connected = self.send_raspi_check()
        
        if not connected:
            self.state.update({'pi_status' : 1})
            self.state.update({'pi_status_last_timestamp'  : datetime.utcnow().timestamp()})
            
        else:
            self.state.update({'pi_status' : 1})
            self.state.update({'pi_status_last_timestamp'  : datetime.utcnow().timestamp()})
            

            self.state.update({'filter_wheel_position' : self.fw_pos})
            self.state.update({'filter_wheel_position_last_timestamp'  : datetime.utcnow().timestamp()})
            
            
            shut = self.check_shutter_state()
            self.state.update({'shutter_state' : shut})
            self.state.update({'shutter_state_last_timestamp'  : datetime.utcnow().timestamp()})
        """
        
    @Pyro5.server.expose
    def getState(self):
        #print(self.state)
        return self.state 
 
    
    
if __name__ == '__main__':
    url = 'http://127.0.0.1:5001/'
    viscam = Viscam(url, None)
    
    print()
    print(f'FW Pos = {viscam.state.get("filter_wheel_position", -999)}')
    print()
    for i in range(5):
        pos = np.random.randint(0,6)
        print(f'FW: Sending to Pos = {pos}')
        viscam.send_filter_wheel_command(pos)
        time.sleep(1)
        print(f'FW Pos = {viscam.state["filter_wheel_position"]}')
        print()
    