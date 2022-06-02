#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed May 12 13:11:16 2021

@author: frostig
"""

import requests
from datetime import datetime
import time
from math import fmod
import numpy as np

#URL = 'http://192.168.1.54:5001/'

class Viscam: 
    # initialize
    def __init__(self, URL, logger):
        self.url = URL
        self.state = dict()
        self.logger = logger
        
        # home the filter wheel
        self.fw_pos = self.send_filter_wheel_command(-1)
        time.sleep(10)
               
    def log(self, msg):
        if self.logger is None:
            print(f'Viscam Client: {msg}')
        else:
            self.logger.info(msg)
    
    # check raspi/web server responsiveness
    def send_raspi_check(self):
        string = self.url + "check_raspi"
        try:
            res = requests.get(string, timeout=10)
            status = res.status_code
            if res.text == "Raspi is responding":
                #print("Status: ", status, res.text)
                #self.logger.debug(f'Raspi status {status}, {res.text}')
                return 1
            else:
                #print("Status: ", status, "Raspi is not responding")
                #self.logger.debug(f'Raspi status {status}, Raspi is not responding')
                return 0
        except:
            #print("Raspi is not responding")
            self.log(f'Raspi is not responding')
            return 0
            
    def update_state(self):
        # poll the state, if we're not connected try to reconnect
        # this should reconnect down the line if we get disconnected
        
        connected = self.send_raspi_check()
        
        if not connected:
            self.state.update({'pi_status' : 1})
            self.state.update({'pi_status_last_timestamp'  : datetime.utcnow().timestamp()})
            
        else:
            self.state.update({'pi_status' : 1})
            self.state.update({'pi_status_last_timestamp'  : datetime.utcnow().timestamp()})
            
            """
            pos = self.send_filter_wheel_command(8)
            try:
                pos = int(pos[22]) + 1 # get position in int
            except:
                pos = -1 # invalid filter position
            """
            self.state.update({'filter_wheel_position' : self.fw_pos})
            self.state.update({'filter_wheel_position_last_timestamp'  : datetime.utcnow().timestamp()})
            
            
            shut = self.check_shutter_state()
            self.state.update({'shutter_state' : shut})
            self.state.update({'shutter_state_last_timestamp'  : datetime.utcnow().timestamp()})
            
 
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


#viscam = Viscam(URL = 'http://192.168.1.54:5001/')

#print("Check raspi")
#check = viscam.send_raspi_check()
#print(check)

# print("Check shutter")
# check = check_shutter_state()

# print("Sending shutter request")
# check = send_shutter_command(0)

# print("Check shutter")
# check = check_shutter_state()

# print("Sending shutter request")
# check = send_shutter_command(1)

# print("Check shutter")
# check = check_shutter_state()

# check = send_filter_wheel_command(10)

# print("Sending filter wheel request")
# check = send_filter_wheel_command(1)
# print(check)

# check = send_filter_wheel_command(10)
# print(check)

# send_filter_wheel_command(11)

# try:
#     print("Check raspi")
#     check = send_raspi_check()
    
#     print(check)
    
#     print("Sending shutter request")
#     send_shutter_command(0)

#     print("Sending filter wheel request")
#     send_filter_wheel_command(1)

#     send_filter_wheel_command(11)

    
# except:
#     print("Didn't work")
    
    
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
    
    