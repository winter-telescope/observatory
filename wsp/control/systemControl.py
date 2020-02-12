#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jan 27 16:13:17 2020

systemControl.py

This file is part of wsp

# PURPOSE #
This module is the interface for all observing modes to command the various
parts of the instrument including
    - telescope
    - power systems
    - stepper motors
    

@author: nlourie
"""
# system packages
import sys
import os
import numpy as np
import time

# add the wsp directory to the PATH
wsp_path = os.path.dirname(os.getcwd())
sys.path.insert(1, wsp_path)

# winter modules
from power import power
from telescope import pwi4
from telescope import telescope
from command import commandServer_multiClient
from housekeeping import weather
from dome import dome
from schedule import schedule
from utils import utils



# Create the control class  
class control(object):
    
    ## Initialize Class ##
    def __init__(self,mode,config_file,base_directory):
        self.config_file = config_file
        self.base_directory = base_directory
        self.oktoobserve = False # Start it out by saying you shouldn't be observing
        
        if mode not in [0,1,2]:
            raise IOError("'" + str(mode) + "' is note a valid operation mode")
    
        if mode == 2:
            #Start up the command server
            #commandServer_multiClient.start_commandServer(addr = '192.168.1.11',port = 7075)
            pass
        if mode in [0,1,2]:
            self.telescope_mount = pwi4.PWI4(host = "thor", port = 8220)
        
        if mode in [0,1]:
            # Startup the Power Systems
            self.pdu1 = power.PDU('pdu1.ini', base_directory)
            self.pdu1.getStatus()
            
            
            # Define the Dome Class
            self.dome = dome.dome()
            
            # Startup the Telescope
            self.telescope_connect()
            self.telescope_axes_enable()
            self.telescope_home()
            
            # Get the Site Weather Conditions
            self.weather = weather.palomarWeather(self.base_directory,'palomarWeather.ini','weather_limits.ini')
            if not self.weather.oktoopen:
                # if the weather is bad, ask if you want to force the dome open
                self.dome_forceOpen()
                

        if mode in [0]:
            # Robotic Observing Mode
            try:
            
                self.schedule = schedule.Schedule(base_directory = self.base_directory, date = 'today')
                while True:
                    try:
                        
                        # Check if it is okay to observe
                        self.weather.getWeather()
                        if self.caniobserve():
                           
                           if self.schedule.currentScheduleLine == -1:
                               print(f' Nothing left to observe tonight. Shutting down telescope...')
                               self.telescope_shutdown()
                               
                               break
                           
                           AZ = self.schedule.currentObs['azimuth']
                           ALT = self.schedule.currentObs['altitude']
                           waittime = self.schedule.currentObs['visitTime']
                           
                           if not self.dome.isopen:
                               self.dome.openDome()
                           self.dome.goto(az = AZ)
                           telescope.goto(self.telescope_mount,az = AZ, alt = ALT)
                           print(f' Taking a {waittime} second exposure...')
                           time.sleep(waittime)
                           imagename = base_directory + '/data/' + str(self.schedule.observed_timestamp)+'.FITS'
                           self.telescope_mount.virtualcamera_take_image_and_save(imagename)
                           self.schedule.logCurrentObs()
                           utils.plotFITS(imagename)
                           
                           self.schedule.gotoNextObs()
                            
                        else:
                            waittime = 15
                            print(" WSP says it's not okay to observe right now")
                            print(f" WSP will try again in {waittime} minutes")
                            # wait and try again in 15 minutes
                            time.sleep(waittime*60)
                    except KeyboardInterrupt:
                        break
            except KeyboardInterrupt:
                pass

    
    def caniobserve(self):
        #this function queries all the relevant things and decides whether it is appropriate to observe
        ok = []
        # Check if the weather is happy
        ok.append(self.weather.caniopen())
        
        # Check if the dome is online
        #ok.append(self.dome.ok)
        
        # Check if the times of day are appropriate
        # something about the sun height in ephem.py
        self.oktoobserve = all(ok)
        return self.oktoobserve
        
    
    # commands that are useful
    def telescope_initialize(self):
        telescope.telescope_initialize(self.telescope_mount)
    def telescope_home(self):
        telescope.home(self.telescope_mount)
    def telescope_axes_enable(self):
        telescope.axes_enable(self.telescope_mount)
    def telescope_connect(self):
        telescope.connect(self.telescope_mount)
    def telescope_disconnect(self):
        telescope.disconnect(self.telescope_mount)
    def telescope_axes_disable(self):
        telescope.axes_disable(self.telescope_mount)
    def telescope_shutdown(self):
        telescope.shutdown(self.telescope_mount)
    def dome_forceOpen(self):
        cmd = input(' OVERRIDE WEATHER AND FORCE DOME OPEN?? (y/n)')
        if cmd == 'y':
            cmd2 = input(' Are you sure you should be doing this?? I will tell on you. (y/n)')
            if cmd2 == 'y':
                self.weather.override = True
                self.dome.openDome()
            else:
                return
        else:
            return
        
if __name__ == '__main__':
    opt = 0
    base_directory = wsp_path
    config_file = ''
    
    winter = control(mode = int(opt), config_file = '',base_directory = wsp_path)
    #plt.show()
    


