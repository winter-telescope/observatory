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

#URL = 'http://192.168.1.54:5001/'

class Viscam: 
    # initialize
    def __init__(self, URL, logger):
        self.url = URL
        self.state = dict()
        self.logger = logger
    
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
            self.logger.info(f'Raspi is not responding')
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
            
            pos = self.send_filter_wheel_command(8)
            try:
                pos = int(pos[22]) + 1 # get position in int
            except:
                pos = -1 # invalid filter position

            self.state.update({'filter_wheel_position' : pos})
            self.state.update({'filter_wheel_position_last_timestamp'  : datetime.utcnow().timestamp()})
            
            shut = self.check_shutter_state()
            self.state.update({'shutter_state' : shut})
            self.state.update({'shutter_state_last_timestamp'  : datetime.utcnow().timestamp()})
            
 
    # send a command to the filter wheel
    # 1 - set filter wheel to position 1
    # 2-7 - set filter wheel to position 2-7
    # 8 - get current position
    # 9 - check number of available positions
    # 10 - get filter wheel firmware version
    def send_filter_wheel_command(self, position):
        string = self.url + "filter_wheel?n=" + str(position)     
        try:
            res = requests.get(string, timeout=10)
            status = res.status_code
            print("Status", status, "Response: ", res.text)
            #self.logger.info(f'Filter wheel status {status}, {res.text}')
            return res.text
        except:
            #print("Raspi is not responding")
            self.logger.info(f'Filter wheel is not responding')
            return 0            
                 
                
        
    # # send a command to the filter wheel
    # # 1 - set filter wheel to position 1
    # # 2-7 - set filter wheel to position 2-7
    # # 8 - get current position
    # # 9 - check number of available positions
    # # 10 - get filter wheel firmware version
    # def send_filter_wheel_command(self, position):
        
    #     # if moving filter wheel
    #     if position < 8:
    #         # check where it is now
    #         last_pos = self._send_filter_wheel_command(8)
    #         try:
    #             last_pos = int(last_pos[22]) + 1 # get position in int
    #             print("Position is currently ", last_pos)
    #         except:
    #             last_pos = -1 # invalid filter position
                
    #         if self.short_circ(position-1, last_pos-1) >= 0: # zero index 
    #             # if the shortest path for the filter wheel is the positive 
    #             # or zero, do normal command
    #             return self._send_filter_wheel_command(int(position))
    
    #         else:            
    #             # else, force it to go long way
    #             # the longest, short distance is 3, so start by adding  +3
    #             new_pos = fmod(last_pos + 3, 7) # modulo 7 positions
    #             print("intermediate new position: " , int(new_pos))
    #             ret = self._send_filter_wheel_command(int(new_pos))
    #             time.sleep(5) # wait for wheel to move 
    #             # if new_pos is the desired position, return
    #             if new_pos == position:
    #                 return ret
    #             # else go to final position
    #             else:
    #                 return self._send_filter_wheel_command(int(position))

    #     else:   
    #         # if not, query normally
    #         return self._send_filter_wheel_command(int(position))
   
    # send a command to the shutter
    # 0 - close the shutter
    # 1 - open the shutter    
    def send_shutter_command(self, state):
        string = self.url + "shutter?open=" + str(state)
        try:
            res = requests.get(string, timeout=10)
            status = res.status_code
            #print("Status", status, "Response: ", res.text)
            self.logger.info(f'Shutter status {status}, {res.text}')
            return status
        except:
            #print("Raspi is not responding")
            self.logger.info(f'Shutter is not responding')
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
    
    

