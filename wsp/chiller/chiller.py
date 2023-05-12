#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Mar 22 13:55:48 2021

chiller.py

This is part of wsp

# Purpose #

This program contains the software interface for the WINTER chiller,
including a class that contains the necessary commands to communicate
with the chiller


@author: nlourie
"""



import os
import numpy as np
import sys
import Pyro5.core
import Pyro5.server
from datetime import datetime
from PyQt5 import QtCore
import time
import json
# add the wsp directory to the PATH
wsp_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(1, wsp_path)
print(f'chiller: wsp_path = {wsp_path}')
from utils import utils




#class local_dome(object):
class local_chiller(QtCore.QObject):    
    '''
    Using a QObject so that it can signals. The problem is that all the Pyro
    calls for a given proxy have to be handled in a single thread. To execute commands
    from outside this thread let's try using the signal/slot approach.
    '''
    newCommand = QtCore.pyqtSignal(object)
    
    def __init__(self, base_directory, config, ns_host = None):
        super(local_chiller, self).__init__()
        
        # Define attributes
        self.base_directory = base_directory
        self.config = config
        self.ns_host = ns_host
        self.state = dict()
        self.remote_state = dict()
        self.connected = False
        self.default = self.config['default_value']
        
        # connect the signals and slots
        self.newCommand.connect(self.doCommand)
        
        # Startup
        self.init_remote_object()
        self.update_state()
        
    def doCommand(self, cmd_obj):
        """
        This is connected to the newCommand signal. It parses the command and
        then executes the corresponding command from the list below

        using this as a reference: (source: https://stackoverflow.com/questions/6321940/how-to-launch-getattr-function-in-python-with-additional-parameters)     
        
        """
        cmd = cmd_obj.cmd
        args = cmd_obj.args
        kwargs = cmd_obj.kwargs
        
        #print(f'chiller: caught doCommand signal: {cmd}, args = {args}, kwargs = {kwargs}')

        try:
            getattr(self, cmd)(*args, **kwargs)
        except:
            pass
        
    def init_remote_object(self):
        # init the remote object
        try:
            ns = Pyro5.core.locate_ns(host = self.ns_host)
            uri = ns.lookup('chiller')
            self.remote_object = Pyro5.client.Proxy(uri)
            self.connected = True
        except:
            self.connected = False
            pass
        '''
        except Exception:
            self.logger.error('connection with remote object failed', exc_info = True)
        '''
    def update_state(self):
        # poll the state, if we're not connected try to reconnect
        # this should reconnect down the line if we get disconnected
        if not self.connected:
            self.init_remote_object()
            
        else:
            try:
                self.remote_state = self.remote_object.GetStatus()
                
                
                self.parse_state()
                
                
            except Exception as e:
                #print(f'chiller: could not update remote state: {e}')
                pass
    
    def parse_state(self):
        '''
        Do any conditioning we need to properly handle and parse the state dictionary
        '''
        """ # things that have to do with querying server
        self.state.update({'last_command_reply'             :   self.remote_state.get('command_reply', self.default)})
        self.state.update({'query_timestamp'                :   self.remote_state.get('timestamp', self.default)})
        self.state.update({'reconnect_remaining_time'       :   self.remote_state.get('reconnect_remaining_time', self.default)})
        self.state.update({'reconnect_timeout'              :   self.remote_state.get('reconnect_timeout', self.default)})
        """
        # update the rest of the stuff
        for key in self.remote_state.keys():
            self.state.update({key : self.remote_state[key]})
        
        self.state.update({'is_connected'                   :   bool(self.remote_state.get('is_connected', self.default))})
        
        
            
    def print_state(self):
        print(f'state = {json.dumps(chiller.state, indent = 2)}')

    def setSetpoint(self, temperature):
        #print(f'chiller: trying to set the set point to {temperature}')
        self.remote_object.setSetpoint(temperature)
    
    def TurnOn(self):
        self.remote_object.TurnOn()
    
    def TurnOff(self):
        self.remote_object.TurnOff()
    
    def WriteRegister(self, register, value):
        self.remote_object.WriteRegister(register, value)
        
        
# Try it out
if __name__ == '__main__':

    config = utils.loadconfig(wsp_path + '/config/config.yaml')
    chiller = local_chiller(wsp_path, config)
    
    '''
    while True:
        try:
            chiller.update_state()
            chiller.print_state()
            time.sleep(0.5)
            
        except KeyboardInterrupt:
            break
    
    '''
    #%%
    chiller.update_state()
    #chiller.print_state()
    print(f'Chiller On = {bool(chiller.state["UserRemoteStartStop"])}')
    print(f"Current  T = {chiller.state['SystemDisplayValueStatus']}")
    print(f"Setpoint T = {chiller.state['UserSetpoint']}")
    
    #%%
    #chiller.WriteRegister('UserSetpoint', 18.1)
    chiller.setSetpoint(17.9)
    
    