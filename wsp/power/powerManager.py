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
import requests
from configobj import ConfigObj
import traceback as tb
import Pyro5.core
import json
import Pyro5.server
import Pyro5.errors
from PyQt5 import QtCore
import traceback as tb

# add the wsp directory to the PATH
wsp_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(1, wsp_path)
print(f'wsp_path = {wsp_path}')

class local_PowerManager(QtCore.QObject):    
    '''
    Using a QObject so that it can signals. The problem is that all the Pyro
    calls for a given proxy have to be handled in a single thread. To execute commands
    from outside this thread let's try using the signal/slot approach.
    '''
    newCommand = QtCore.pyqtSignal(object)
        
    def __init__(self, base_directory, logger = None):
        super(local_PowerManager, self).__init__()

        self.base_directory = base_directory

        self.state = dict()
        
        # connect the signals and slots
        self.newCommand.connect(self.doCommand)
        
        self.init_remote_object()
        
        

        
    def init_remote_object(self):
        # init the remote object
        try:
            self.remote_object = Pyro5.client.Proxy("PYRONAME:power")
        
        except Exception as e:
            self.logger.error('connection with remote object failed', exc_info = True)
    
    def update_state(self):
        try:
            self.remote_state = self.remote_object.getState()
            
            for key in self.remote_state:
                self.state.update({key : self.remote_state[key]})

        except Exception as e:
            
            #print(f'Could not update remote state: {e}')
            #print(tb.format_exc())
            #print('PRYO TRACEBACK:')
            #for line in Pyro5.errors.get_pyro_traceback():
            #    print(line.strip('\n'))
            # don't want to spew errors in wsp
            pass
            
    def pdu_off(self, pduname, outlet):
        try:
            self.remote_object.pdu_off(pduname, outlet)
        except:
            pass

    
    def pdu_on(self, pduname, outlet):
        try:
            self.remote_object.pdu_on(pduname, outlet)
        except:
            pass
    
    def pdu_cycle(self, pduname, outlet):
        try:
            self.remote_object.pdu_cycle(pduname, outlet)
        except:
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
        #print(f'powerManager: caught doCommand signal: {cmd_obj.cmd}')
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