#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jun  1 11:34:14 2022

@author: winterpi
"""

import sys
import os
import traceback as tb
import Pyro5.core
import Pyro5.server
import Pyro5.errors
from PyQt5 import QtCore
import json

# add the wsp directory to the PATH
wsp_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(1, wsp_path)
print(f'wsp_path = {wsp_path}')


class local_viscam(QtCore.QObject):
    '''
    Using a QObject so that it can signals. The problem is that all the Pyro
    calls for a given proxy have to be handled in a single thread. To execute commands
    from outside this thread let's try using the signal/slot approach.
    '''
    newCommand = QtCore.pyqtSignal(object)
    #def __init__(self, base_directory, config, logger):
    def __init__(self, base_directory):
        super(local_viscam, self).__init__()
        self.base_directory = base_directory

        self.state = dict()
                
        # connect the signals and slots
        self.newCommand.connect(self.doCommand) 
        
        # Startup
        # setup connection to pyro ccd
        self.init_remote_object()
        self.update_state()
        
    def init_remote_object(self):
        # init the remote object
        try:
            self.remote_object = Pyro5.client.Proxy("PYRONAME:viscam")
        
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
            # in wsp operation all these errors need to be muted otherwise they'll flood the zone, but know they're here
            pass
        
    def command_filter_wheel(self, pos):
        
        self.remote_object.command_filter_wheel(pos)
        
    def send_shutter_command(self, state):
        
        self.remote_object.send_shutter_command(state)
    
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
    def printState(self, update = True):
        
        if update:
            self.update_state()
        print(json.dumps(viscam.state, indent = 3))
if __name__ == '__main__':
    viscam = local_viscam(wsp_path)
