#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Jan 24 16:04:53 2020

power.py
This file is part of wsp

# PURPOSE #
To parse the power distribution (PDU) unit config files, and build a structure
for each pdu which can command the power on and off for individual
subsystems

Some of this is modeled on the powerswitch.py module from the Minerva
code library from Jason Eastman.

@author: nlourie
"""
import time
import sys
import os
import numpy as np
#import requests
import traceback as tb
import Pyro5.core
import json
import Pyro5.server
import Pyro5.errors
from PyQt5 import QtCore
import logging
import traceback as tb

# add the wsp directory to the PATH
wsp_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(1, wsp_path)
print(f'wsp_path = {wsp_path}')

class local_PowerManager(QtCore.QObject):
        newCommand = QtCore.pyqtSignal(object)

        def __init__(self, base_directory, ns_host = None, logger = None, verbose = False):
            super(local_PowerManager, self).__init__()
            self.base_directory = base_directory
            self.ns_host = ns_host
            self.logger = logger
            self.verbose = verbose
            self.state = dict()
            
            self.init_remote_object()
            
            
        def log(self, msg, level = logging.INFO):
            msg = f'powerManager: {msg}'
            if self.logger is None:
                    print(msg)
            else:
                self.logger.log(level = level, msg = msg)  
            

        def init_remote_object(self):
            # init the remote object
            if self.verbose:
                self.log(f'trying to re-init conn with power daemon, ns_host = {self.ns_host}')
            try:
                ns = Pyro5.core.locate_ns(host = self.ns_host)
                uri = ns.lookup('power')
                self.remote_object = Pyro5.client.Proxy(uri)
                self.connected = True
            except Exception as e:
                self.connected = False
                if self.verbose:
                    self.log(f'connection with remote object failed: {e}')
                pass
            
        def update_state(self):
            try:

                self.remote_state = self.remote_object.getState()
                self.parse_state()  

            except Exception as e:
                if self.verbose:
                    self.log(f'Could not update remote status: {e}', level = logging.ERROR)
                self.init_remote_object()
        
        def parse_state(self):
            for key in self.remote_state:
                self.state.update({key : self.remote_state[key]})
        
        def pdu_off(self, pduname, outlet):
            try:
                self.log(f'sending OFF command to {pduname}, outlet {outlet}')
                self.remote_object.pdu_off(pduname, outlet)
                
            except Exception as e:
                self.log(f'could not send OFF command to {pduname}, outlet {outlet}: {e}')
                pass

        
        def pdu_on(self, pduname, outlet):
            try:
                self.log(f'sending ON command to {pduname}, outlet {outlet}')
                self.remote_object.pdu_off(pduname, outlet)
            except Exception as e:
                self.log(f'could not send OFF command to {pduname}, outlet {outlet}: {e}')
                pass
            
        def pdu_cycle(self, pduname, outlet):
            try:
                self.log(f'sending CYCLE command to {pduname}, outlet {outlet}')
                self.remote_object.pdu_cycle(pduname, outlet)
            except Exception as e:
                self.log(f'could not send CYCLE command to {pduname}, outlet {outlet}: {e}')
                pass
        
        
        def print_state(self):
            self.update_state()
            #print(f'Local Object: {self.msg}')
            print(f'state = {self.state}')
            
        def doCommand(self, cmd_obj):
            """
            This is connected to the newCommand signal. It parses the command and
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
    
        


if __name__ == '__main__': 
  
    power = local_PowerManager(wsp_path)
    
    try:
        while True:
            power.print_state()
            time.sleep(1)
    except KeyboardInterrupt:
        pass