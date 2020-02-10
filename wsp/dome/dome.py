#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Feb  6 16:41:04 2020

dome.py

This is part of wsp

# Purpose #

This program contains the software interface for the WINTER telescope dome,
including a dome class that contains the necessary commands to communicate
with the telescope dome


@author: nlourie
"""
# system modules
import numpy as np
import time
import sys
import os

# add the wsp directory to the PATH
wsp_path = os.path.dirname(os.getcwd())
sys.path.insert(1, wsp_path)

# winter modules

class dome(object):
    
    def __init__(self):
        """
        # This will set up the dome class.
        
        Eventually it should probably take in the IP address of the dome
        teletry server, and maybe read a config file with information about the
        location of the dome
        
        """
        print("Initializing  Dome")
        #TODO add a message to the log
        
        ## Characteristics ##
        self.az_speed = 360/180 # speed in deg/sec
        self.open_time = 20 # time to open the shutter
        self.close_time = 20 # time to close the shutter
        self.allowed_error = 0.1
        self.movedir = 1.0 # is either +1 or -1 depending on which direction its going to move
        self.ok = False
        
        ## Update Status ##
        self.getstatus()
        # THIS IS JUST FOR THE SIMULATION MODE
        self.ismoving = False
        self.isopening = False
        self.isclosing = False
        self.isopen = False
        self.az = 90
        
        
        self.az_goal = self.az
        
    def getstatus(self):
        # This will poll the telemetry server. For now its just nominal things
        self.ok = True # Is everything okay with the dome?
        #TODO will need to determine when the dome is okay!
        
        #self.ismoving = 
        #self.isopening = 
        #elf.isclosing = 
        #self.isopen = 
        #self.az = 
        pass
        
    def openDome(self,sim = True,verbose = True):
        if sim:
            self.isopening = True
            time.sleep(self.open_time)
            self.isopening = False
        else:
            print(" No code for commanding dome in non simulation mode")

    def closeDome(self,sim = True,verbose = True):
        if sim:
            self.isclosing = True
            time.wait(self.open_time)
            self.isclosing = False
        else:
            print(" No code for commanding dome in non simulation mode")
            
    def goto(self,az,sim = True,verbose = True):
        # tell the dome to move over the server
        self.az_goal = az
        # standin function to simulate movement
        print(f" Requested move from Az = {self.az} to {self.az_goal}")
        if sim:
            try:
                if (self.az_goal - self.az)>=self.allowed_error:
                    # calculate the angular distance in the pos direction
                    # want to drive dome shortest distance
                    """
                    delta_pos = (360.0-self.az) + self.az_goal
                    delta_neg = (self.az - self.az_goal)
                    if np.abs(delta_pos) <= np.abs(delta_neg):
                        delta = delta_pos
                        self.movedir = +1.0 # want to drive in the pos direction
                    else:
                        delta = delta_neg
                        self.movedir = -1.0 # want to drive in the neg direction
                    """
                    delta = self.az_goal - self.az
                    
                    if np.abs(delta) >= 180.0:
                        #print(f'delta = |{delta}| > 180')
                        dist_to_go = 360-np.abs(delta)
                        self.movedir = -1*np.sign(delta)
                        #print(f'new delta = {delta}')
                    else:
                        #print(f'delta = |{delta}| < 180')
                        dist_to_go = np.abs(delta)
                        self.movedir = np.sign(delta)
                        
                    drivetime = np.abs(dist_to_go)/self.az_speed # total time to move
                    # now start "moving the dome" it stays moving for an amount of time
                        # based on the dome speed and distance to move
                    print(' Estimated Drivetime = ',drivetime,' s')
                    dt = 0.1 #increment time for updating position
                    #N_steps = drivetime/dt
                    #daz = delta/N_steps
                    if verbose:
                        if self.movedir < 0:
                            dirtxt = '[-]'
                        else:
                            dirtxt = '[+]'
                        print(f" Rotating Dome {dist_to_go} deg in {dirtxt} direction from Az = {self.az} to Az = {self.az_goal}")
                    
                    while np.abs(self.az_goal - self.az) > self.allowed_error:
                        self.ismoving = True
                        # keep "moving" the dome until it gets close enough
                        time.sleep(dt)
                        self.az = self.az + self.movedir*self.az_speed*dt
                        if verbose:
                            print("     Dome Az = %0.3f, Dist to Go = %0.3f deg" %(self.az, self.az_goal-self.az))
                            #print(f" Still Moving? {self.ismoving}")
                    self.ismoving = False
                    if verbose:
                        if not self.ismoving:
                            print(f" Completed Dome Move.")
                        else:
                            print(" Moving error... move not complete?")
                    
                else:
                    print(f" Not moving. Dome Az within allowed error: {self.allowed_error} deg")
            except KeyboardInterrupt:
                print(f" User interrupted dome move. Stopping!")
                return
        else:
            print(" No code for commanding dome in non simulation mode")
if __name__ == '__main__':
    dome = dome()
    
    dome.az = 0
    dome.goto(50, verbose = True)
    
    
    
                

                
            
                
            
            
        