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
import Pyro5.server
import Pyro5.errors
from PyQt5 import QtCore
import traceback as tb

# add the wsp directory to the PATH
wsp_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(1, wsp_path)
print(f'wsp_path = {wsp_path}')

class local_PowerManager(object):
        newCommand = QtCore.pyqtSignal(object)

        def __init__(self, base_directory):
            self.base_directory = base_directory

            self.state = dict()
            
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
                print(f'Could not update remote state: {e}')
                print(tb.format_exc())
                #print('PRYO TRACEBACK:')
                #for line in Pyro5.errors.get_pyro_traceback():
                #    print(line.strip('\n'))
                
        def pdu_off(self, pduname, outlet):
            try:
                self.remote_object.pdu_off(pduname, outlet)
            except:
                pass

        
        def pdu_on(self, pduname, outlet):
            try:
                self.remote_object.pdu_off(pduname, outlet)
            except:
                pass
        
        
        
        def Home(self):
            #print(f'dome: trying to HOME dome')
            try:
                self.remote_object.Home()
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
            #print(f'dome: caught doCommand signal: {cmd_obj.cmd}')
            cmd = cmd_obj.cmd
            args = cmd_obj.args
            kwargs = cmd_obj.kwargs
            
            try:
                getattr(self, cmd)(*args, **kwargs)
            except:
                pass
        
        





# PDU Properties
class PDU(object):
    def __init__(self,pdu_config_file,base_directory,brand = 'digital loggers', autostart = True):
        
        self.base_directory = base_directory
        self.config_file = pdu_config_file
        self.load_config(autostart = autostart)
    
    def load_config(self, autostart = True):

        configObj = ConfigObj(self.base_directory + '/config/' + self.config_file)
        self.ip = configObj['Setup']['IP']
        self.num_outlets = int(configObj['Setup']['NUM_OUTLETS'])
        self.outlet_nums = np.arange(int(self.num_outlets))+1
        self.outlet_names = configObj['Setup']['OUTLETS']
        self.outlet_dict = dict(zip(self.outlet_names,self.outlet_nums))
        self.logname = configObj['Setup']['LOGNAME']
        self.name = configObj['Setup']['NAME']
        self.brand = configObj['Setup']['BRAND']
        self.status = self.getStatus()
        startup_config = list(configObj['Setup']['STARTUP'])
        self.startup_config = [int(state) for state in startup_config]
        if autostart:
            self.sendStatus(self.startup_config)
        
        
    def send(self,command):
        # This is adapted from Minerva as a better way to get the login credentials
        credential_obj = ConfigObj(self.base_directory + '/credentials/authentication.ini')
        username = credential_obj[self.logname]['USERNAME']
        password = credential_obj[self.logname]['PASSWORD']
        url = 'http://' + self.ip + '/' + command
        try:
            response = requests.get(url, auth = (username,password),timeout = 10)
            # added timeout so that if there's nothing to connect to it moves on
        except:
            print("Error communicating with PDU via http")
        return response
    
    def getStatus(self,verbose = False):
        if self.brand.lower() == 'digital loggers':
            try:
                response = self.send('status')
                # Find the place in the garbled html return that says "state">,
                # the next two characters are the status code
                status_key = '"state">'
                status_key_index = response.text.index(status_key)
                status_code = response.text[status_key_index + len(status_key): status_key_index + len(status_key) + 2]
                #convert the status character (which is a hex number) as a 4-bit binary number
                    # using this method: https://www.geeksforgeeks.org/python-ways-to-convert-hex-into-binary/
                status_a_bin = "{0:04b}".format(int(status_code[1],16))
                status_b_bin = "{0:04b}".format(int(status_code[0],16))
                
                # now need to flip the status codes around to make it make sense, and stick them together
                # This is because they're dumb. ie "1110" corresponds to 0,1,1,1] in status
                
                status_str = np.append(np.flip(list(status_a_bin)),np.flip(list(status_b_bin)))
                status = [int(state) for state in status_str]
                if verbose:
                    print(self.logname , " Outlet Status: " , self.status)
                    #TODO send something to the log
                #status has form:
                # status = [outlet1,outlet2,outlet3,outlet4,outlet5,outlet6,outlet7,outlet8]
            except Exception as e:
                    print('ERROR getting PDU status')
                    #print(tb.format_exc())
                    #TODO add an entry to the log
                    #sys.exit()
                    status = []

            self.status = status

            return status 
        
        
    def cycle(self,outlet,verbose = False):
        if self.brand.lower() == 'digital loggers':
            command  = 'outlet?' + str(outlet) + '=CCL'
            #TODO add this to the log
            if verbose:
                print("Sending CYCLE Command to " + self.logname + " Outlet # " + np.str(outlet))
            self.send(command)
            self.getStatus()
            
    def on(self,outlet,verbose = False):
        if self.brand.lower() == 'digital loggers':
            command  = 'outlet?' + str(outlet) + '=ON'
            #TODO add this to the log
            if verbose:
                print("Sending ON Command to " + self.logname + " Outlet # " + np.str(outlet))
            self.send(command)
            self.getStatus()
            
    def off(self,outlet,verbose = False):
        if self.brand.lower() == 'digital loggers':
            command  = 'outlet?' + str(outlet) + '=OFF'
            #TODO add this to the log
            if verbose:
                print("Sending OFF Command to " + self.logname + " Outlet # " + np.str(outlet))
            self.send(command)
            self.getStatus()
            
    def sendStatus(self,status_arr,verbose = False,message = ''):
        # Send the PDU status as an boolean array/list
        # the number of elements must match the number of outlets
        #TODO add this to the log
        print(message, ' PDU Command: Sending outlet config to ', self.logname, ': ',status_arr)
        
        if len(status_arr) != self.num_outlets:
            raise IOError( "The number of status bits in your command do not match the number of outlets")
        
        # check to make sure all the states are acceptable values
        for state in status_arr:
            if state not in [1,0]:
                raise IOError("Outlet States must be 1 or 0!")
        
        # now toggle all the states NOTE THIS HAPPENS SEQUENTIALLY
        for i in range(len(status_arr)):
            # check if the correct status is already achieved, then do nothing:
            if status_arr[i] != self.status[i]:
                if status_arr[i] == 0:
                    # if it's supposed to be off, turn it off!
                    self.off(i + 1)
                elif status_arr[i] == 1:
                    # if it's supposed to be on, turn it on!
                    self.on(i + 1)
        # Wait a few seconds and then query the status again
        #   if you don't wait long enough the status doesn't update properly
        time.sleep(5)
        self.getStatus(verbose = verbose)
        
       
if __name__ == '__main__': 
    """
    # Usage Example
    # Import the PDU properties
    try:
        pdu1 = PDU('pdu1.ini',os.path.dirname(os.getcwd()), autostart = False)
        
        print(f'initial status = {pdu1.getStatus()}')
        
        #print('initial status = ',pdu1.status)
        #new_status = [1,1,1,1,1,1,1,1]
        #pdu1.sendStatus(new_status)
        
        #print('final status = ',pdu1.status)
    
    except:
        pass

    """
    power = local_PowerManager(wsp_path)
    
    try:
        while True:
            power.print_state()
            time.sleep(1)
    except KeyboardInterrupt:
        pass