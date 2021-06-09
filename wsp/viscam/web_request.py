#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed May 12 13:11:16 2021

@author: frostig
"""

import requests
#import time

#URL = 'http://192.168.1.54:5001/'


class Viscam: 
    # initialize
    def __init__(self, URL):
        self.url = URL
    
    # check raspi/web server responsiveness
    def send_raspi_check(self):
        string = self.url + "check_raspi"
        try:
            res = requests.get(string, timeout=10)
            status = res.status_code
            if res.text == "Raspi is responding":
                print("Status: ", status, res.text)
                return 1
            else:
                print("Status: ", status, "Raspi is not responding")
                return 0
        except:
            print("Raspi is not responding")
            return 0
    
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
            return status
        except:
            print("Raspi is not responding")
            return 0
    
    # send a command to the shutter
    # 0 - close the shutter
    # 1 - open the shutter    
    def send_shutter_command(self, state):
        string = self.url + "shutter?open=" + str(state)
        try:
            res = requests.get(string, timeout=10)
            status = res.status_code
            print("Status", status, "Response: ", res.text)
            return status
        except:
            print("Raspi is not responding")
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
                print("Status: ", status, " Unknown shutter state")
                return 1
            else:
                print("Status: ", status, "Shutter state is ", res.text)
                return 0
            print("Status", status, "Response: ", res.text)
            return status
        except:
            print("Raspi is not responding")
            return 0


viscam = Viscam(URL = 'http://192.168.1.54:5001/')

print("Check raspi")
check = viscam.send_raspi_check()
print(check)

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
    
    

