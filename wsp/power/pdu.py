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
import traceback as tb
from bs4 import BeautifulSoup
import logging

# add the wsp directory to the PATH
wsp_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),'wsp')
# switch to this when ported to wsp
#wsp_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

sys.path.insert(1, wsp_path)
print(f'pdu: wsp_path = {wsp_path}')

from utils import logging_setup
from utils import utils

# PDU Properties
class PDU(object):
    def __init__(self, name, pdu_config, auth_config, autostart = True, logger = None):
        
        self.name = name
        self.logger = logger
        self.auth_config = auth_config
        self.config = pdu_config    
        
        self.brand = self.config['pdus'][self.name]['brand']
        self.ip = self.config['pdus'][self.name]['ip']
        self.startup_config = [int(state) for state in list(str(self.config['pdus']['pdu1']['startup']))]
        self.num_outlets = 8
        self.outletstate = dict()
        self.outletnames2nums = dict()
        self.outletnums2names = dict()
        self.state = dict()
        self.status = [-1, -1, -1, -1, -1, -1, -1, -1]
        
        # read what the current outlet names are
        try:
            self.getOutletNames()
        except Exception as e:
            self.log(f'could not get outlet names: {e}')
        # now set the outlet names to match the config file
        try:
            self.initOutletNames()
        except Exception as e:
            self.log(f'could not set outlet names: {e}')
        # get the current outlet status
        self.getStatus()
        
        # do you want to send the outlet status from the config file?
        if autostart:
            self.sendStatus(self.startup_config)
        
    
    def log(self, msg, level = logging.INFO):
        
        msg = f'PDU {self.name}: {msg}'
        
        if self.logger is None:
                print(msg)
        else:
            self.logger.log(level = level, msg = msg)
        
    def send(self,command):
        # This is adapted from Minerva as a better way to get the login credentials
        username = self.auth_config['pdu'][self.name]['USERNAME']
        password = self.auth_config['pdu'][self.name]['PASSWORD']
        url = 'http://' + self.ip + '/' + command
        try:
            #self.log(f'sending http request: {url}')
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
                status = [-1, -1, -1, -1, -1, -1, -1, -1]
                self.log(f'ERROR getting PDU status: {e}')
                    #print(tb.format_exc())
                    #TODO add an entry to the log
                    #sys.exit()
                    
                    
            self.status = status
            # now update the state
            for i in range(len(self.status)):
                self.outletstate.update({i+1 : self.status[i]})
              
    
    def getState(self):
        # this is a method to update the state dictionary with all the info
        
        self.getStatus()
        self.state.update({'status' : self.status})
        self.state.update({'outletnames2nums' : self.outletnames2nums})
        self.state.update({'outletnums2names' : self.outletnums2names})         
        
        return self.state
    
    def getOutletNames(self):   
        """
        This does a query of the full status page then scrapes the various fields
        It is adapted from the dlipower module by dwight hubbard
        
            dlipower.py : (adapted from dlipower.Outlet.statuslist)
                https://github.com/dwighthubbard/python-dlipower/blob/master/dlipower/dlipower.py
            linked from digital loggers website: https://www.digital-loggers.com/python.html
        
        It works reliably... but is *very* slow. So don't plan on doing it more often
        than absolutely necessary
        
        """
                
        res = self.send('index.htm')
        
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # Get the root of the table containing the port status info
        root = soup.findAll('td', text='1')[0].parent.parent.parent
        
        # Finding the root of the table with the outlet info failed
        # try again assuming we're seeing the table for a user
        # account insteaed of the admin account (tables are different)
        
        root = soup.findAll('th', text='#')[0].parent.parent.parent
        
        for temp in root.findAll('tr'):
            columns = temp.findAll('td')
            if len(columns) == 5:
                outlet_number = int(columns[0].string)
                outlet_name = str(columns[1].string)
                self.outletnums2names.update({outlet_number : outlet_name})
                self.outletnames2nums.update({outlet_name : outlet_number})
                
    def initOutletNames(self):
        
        outletnames_requested = self.config['pdus'][self.name]['outlets']
        
        # get the current outlet names
        self.getOutletNames()
        
        for num in outletnames_requested:
            if self.outletnums2names[num] == outletnames_requested[num]:
                pass
            else:
                self.renameOutlet(num, outletnames_requested[num])
        
        # now check if it worked
        self.getOutletNames()
        
        if self.outletnums2names == outletnames_requested:
            self.log('outlet names initialized successfully')
        else:
            self.log('could not initialize outlet names!!')
            
                
    def renameOutlet(self, outlet, name):

        res = self.send(f'unitnames.cgi?outname{outlet}={name}')
        
    def cycle(self,outlet):
        if self.brand.lower() == 'digital loggers':
            if type(outlet) is int:
                if outlet in np.arange(1, self.num_outlets+1, 1):
                    outletnum = outlet
                else:
                    outletnum = None
            elif type(outlet) is str:
                #if it's a name look it up in the reverse dict
                outletnum = self.outletnames2nums.get(outlet, None)
            else:
                outletnum = None
            if outletnum is None:
                self.log(f'bad outlet {outlet} specified. returning.')
                return
                
            command  = 'outlet?' + str(outletnum) + '=CCL'
            #TODO add this to the log
            self.log(f"Sending CYCLE Command to Outlet # {outletnum}")
            self.send(command)
            self.getStatus()
            
    def on(self,outlet):
        if self.brand.lower() == 'digital loggers':
            if type(outlet) is int:
                if outlet in np.arange(1, self.num_outlets+1, 1):
                    outletnum = outlet
                else:
                    outletnum = None
            elif type(outlet) is str:
                #if it's a name look it up in the reverse dict
                outletnum = self.outletnames2nums.get(outlet, None)
            else:
                outletnum = None
            if outletnum is None:
                self.log(f'bad outlet {outlet} specified. returning.')
                return
            command  = 'outlet?' + str(outletnum) + '=ON'
            #TODO add this to the log
            self.log(f"Sending ON Command to  Outlet # {outletnum}")
            self.send(command)
            self.getStatus()
            
    def off(self,outlet):
        if self.brand.lower() == 'digital loggers':
           if type(outlet) is int:
               if outlet in np.arange(1, self.num_outlets+1, 1):
                   outletnum = outlet
               else:
                   outletnum = None
           elif type(outlet) is str:
               #if it's a name look it up in the reverse dict
               outletnum = self.outletnames2nums.get(outlet, None)
           else:
               outletnum = None
           if outletnum is None:
               self.log(f'bad outlet {outlet} specified. returning.')
               return
           command  = 'outlet?' + str(outletnum) + '=OFF'
           #TODO add this to the log
           self.log(f"Sending OFF Command to Outlet # {outletnum}")
           self.send(command)
           self.getStatus()
            
    def sendStatus(self,status_arr):
        # Send the PDU status as an boolean array/list
        # the number of elements must match the number of outlets
        #TODO add this to the log
        self.log(f'Sending outlet config: {status_arr}')
        
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
                elif status_arr[i] == 2:
                    # if it's not 1 or 0, do nothing!
                    pass
                else:
                    pass
                    
        # Wait a few seconds and then query the status again
        #   if you don't wait long enough the status doesn't update properly
        time.sleep(5)
        self.getStatus()
        
       
if __name__ == '__main__': 
    # Usage Example
    # Import the PDU properties
    
    pdu_config = utils.loadconfig(os.path.join(wsp_path, 'config', 'powerconfig.yaml'))
    auth_config = utils.loadconfig(os.path.join(wsp_path, 'credentials', 'authentication.yaml'))
    
    pdu1 = PDU('pdu1', pdu_config, auth_config, autostart = False)
    pdu2 = PDU('pdu2', pdu_config, auth_config, autostart = False)
    print(f'pdu1 initial status = {pdu1.status}')
    print(f'pdu2 initial status = {pdu2.status}')    
        #print('initial status = ',pdu1.status)
        #new_status = [1,1,1,1,1,1,1,1]
        #pdu1.sendStatus(new_status)
        
        #print('final status = ',pdu1.status)

    