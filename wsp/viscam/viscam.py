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

# add the wsp directory to the PATH
wsp_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(1, wsp_path)
print(f'wsp_path = {wsp_path}')

class local_viscam(object):
        newCommand = QtCore.pyqtSignal(object)

        def __init__(self, base_directory):
            self.base_directory = base_directory

            self.state = dict()
            
            self.init_remote_object()
            
            

            
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
                print(f'Could not update remote state: {e}')
                print(tb.format_exc())
                #print('PRYO TRACEBACK:')
                #for line in Pyro5.errors.get_pyro_traceback():
                #    print(line.strip('\n'))
                
        def command_filter_wheel(self, pos):
            
            self.remote_object.command_filter_wheel(pos)
        
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
    viscam = local_viscam(wsp_path)
