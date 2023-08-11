#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Feb 22 12:17:46 2023

@author: winter
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
import logging

# add the wsp directory to the PATH
wsp_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(1, wsp_path)
print(f'local labjack handler: wsp_path = {wsp_path}')
from utils import utils




#class local_dome(object):
class local_labjackHandler(QtCore.QObject):    
    '''
    Using a QObject so that it can signals. The problem is that all the Pyro
    calls for a given proxy have to be handled in a single thread. To execute commands
    from outside this thread let's try using the signal/slot approach.
    '''
    newCommand = QtCore.pyqtSignal(object)
    
    def __init__(self, base_directory, config, ns_host = None, logger = None, verbose = False):
        super(local_labjackHandler, self).__init__()
        
        # Define attributes
        self.base_directory = base_directory
        self.config = config
        self.ns_host = ns_host
        self.logger = logger
        self.verbose = verbose
        self.state = dict()
        self.remote_state = dict()
        self.connected = False
        self.default = self.config['default_value']
        
        # connect the signals and slots
        self.newCommand.connect(self.doCommand)
        
        # Startup
        self.init_remote_object()
        self.update_state()
    
    def log(self, msg, level = logging.INFO):
        if self.logger is None:
                print(msg)
        else:
            self.logger.log(level = level, msg = msg)
    
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
            uri = ns.lookup('labjacks')
            self.remote_object = Pyro5.client.Proxy(uri)
            self.connected = True
        except Exception as e:
            self.connected = False
            self.log(f'local labjackHandler: conn with remote object failed: {e}')
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
                self.remote_state = self.remote_object.getState()

            except Exception as e:
                #print(f'chiller: could not update remote state: {e}')
                self.connected = False
                pass
            
            try:
                self.parse_state()

            except Exception as e:
                #print(f'chiller: could not update remote state: {e}')
                pass
    
    def parse_state(self):
        '''
        Do any conditioning we need to properly handle and parse the state dictionary
        '''
        # update the rest of the stuff
        for key in self.remote_state.keys():
            self.state.update({key : self.remote_state[key]})
        
        #self.state.update({'is_connected'                   :   bool(self.remote_state.get('is_connected', self.default))})
      
    def dio_do(self, action, outlet_specifier):
        try:
            self.log(f'sending {action} command to labjack digital output specified by {outlet_specifier}')
            self.remote_object.dio_do(action, outlet_specifier)
            
        except Exception as e:
            self.log(f'could not send {action} command to labjack digital output specified by {outlet_specifier}: {e}')
            pass   
      
if __name__ == '__main__':
    # load the config
    config_file = wsp_path + '/config/config.yaml'
    config = utils.loadconfig(config_file)
    
    labjacks = local_labjackHandler(wsp_path, config, ns_host = '192.168.1.20')
    
    #%%
    labjacks.update_state()
    print(labjacks.state)
    #%%
    """
    #print(json.dumps(labjacks.state, indent = 3))
    field = "COUNT_LJ0_DIO0"
    print(f"{field} : {labjacks.state[field]}")
    #%%
    while True:
        try:
            labjacks.update_state()
            #print(json.dumps(labjacks.state, indent = 3))
            print(f"{field} : {labjacks.state[field]}")
            time.sleep(30)
        except KeyboardInterrupt:
            break
    
    """  
        
     