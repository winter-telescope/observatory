#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jul 14 18:56:47 2021

@author: nlourie
"""



import os
import Pyro5.core
import Pyro5.server
import sys
from PyQt5 import QtCore
import json



# add the wsp directory to the PATH
wsp_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(1, wsp_path)
print(f'StateGetter: wsp_path = {wsp_path}') # make sure this actually prints out the correct path to the main wsp directory

# winter modules





class StateGetter(QtCore.QObject):
    
    """
    This is the pyro object that handles polling the published state from the 
    Pyro nameserver
    
    NOTE:
        This inherets from QObject, which allows it to have custom signals
        which can communicate with the communication threads
    """
    
    
    def __init__(self, verbose = False):
        super(StateGetter, self).__init__()
        
        # init the housekeeping state
        self.state = dict()
        
        # set up the link to the pyro server and make the local object        
        self.init_remote_object()
        


    def init_remote_object(self):
        # init the remote object: set up the link to the housekeeping state on the Pyro5 server
        try:
            self.remote_object = Pyro5.client.Proxy("PYRONAME:state")
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

        if not self.connected:
            self.init_remote_object()
            
        else:
            try:
                # get the state from the remote state object and make a local copy
                self.state = self.remote_object.GetStatus()
                                
            except Exception as e:
                print(f'StateGetter: could not update remote state: {e}')
                pass
        
        
    def print_state(self):
        # print out the state in a pretty format
        print(json.dumps(self.state, indent = 2))
        

        
if __name__ == '__main__':
    
    
    # init the state getter
    monitor = StateGetter()
    
    # get the current housekeeping state
    monitor.update_state()
    
    # print out the current state
    monitor.print_state()
    
    
    