#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jan 27 17:48:35 2020

telescope_initialize.py

This file is part of wsp

# PURPOSE #

This file has an initialization script which gets the telescope ready for 
observing.

@author: nlourie
"""
import time
import numpy as np
from telescope import telescope
from telescope import pwi4

def connect(mount):
    print("Initializing Telescope...")
    # Now try to connect to the telescope using the module
    try:
    
        while True:
            s = mount.status()
            time.sleep(2)
            if s.mount.is_connected:
                print("Mount is connected")
                break
            else:
                print("Mount is not connected")
                print("Connecting to Mount...")
                s = mount.mount_connect()
                time.sleep(2)
    except:
        print("The telescope is not online")    
        #TODO add a message to the log



def disconnect(mount):
    print("Disconnecting Telescope Mount...")
    # Now try to connect to the telescope using the module
    try:
    
        while True:
            time.sleep(5)
            print("Disconnecting from Telescope")
            mount.mount_disconnect()
            s = mount.status()
            print ("Mount Connected?:", s.mount.is_connected)
            if not s.mount.is_connected:
                print("Mount Disconnected")
                break
            else:
                print("Trying again to disconnect mount...")
                s = mount.mount_disconnect()
                time.sleep(2)
                print ("Mount Connected?:", s.mount.is_connected)
    except:
        print("The telescope could not be disconnected!")    
        #TODO add a message to the log


        
def axes_enable(mount):
    try:
        # Turn on the Axes
        time.sleep(2)
        axes = {'az':0, 'alt':1}
        print("Enabling the motor axes:")
        mount.mount_enable(axes['az'])
        mount.mount_enable(axes['alt'])
        time.sleep(2)
        s = mount.status()
        print("Is the altitude axis enabled? ", s.mount.axis0.is_enabled)
        print("Is the azimuth axis enabled? ", s.mount.axis1.is_enabled)
    except:
        print("Telescope axes could not be enabled")
        #TODO add a message to the log

def axes_disable(mount):
    try:
        # Turn on the Axes
        time.sleep(2)
        axes = {'az':0, 'alt':1}
        print("Enabling the motor axes:")
        mount.mount_disable(axes['az'])
        mount.mount_disable(axes['alt'])
        time.sleep(2)
        s = mount.status()
        print("Is the altitude axis enabled? ", s.mount.axis0.is_enabled)
        print("Is the azimuth axis enabled? ", s.mount.axis1.is_enabled)
    except:
        print("Telescope axes could not be disabled")
        #TODO add a message to the log
    
def home(mount):
    try:
        # Point towards the door and look pretty!
        home_alt = 16
        home_az = 290
        
        print ("Slewing to home: ALT/AZ = %0.4f, %0.4f" %(home_alt,home_az))
        mount.mount_goto_alt_az(home_alt, home_az )
        
        
        time.sleep(5)
        while True:
            s = mount.status()
        
            print ("ALT: %.4f deg;  Az: %.4f degs, Axis0 dist: %.1f arcsec, Axis1 dist: %.1f arcsec" % (
                s.mount.altitude_degs, 
                s.mount.azimuth_degs,
                s.mount.axis0.dist_to_target_arcsec,
                s.mount.axis1.dist_to_target_arcsec
            ))
        
        
            if not s.mount.is_slewing:
                break
            time.sleep(0.5)
        
        print ("Slew complete. Stopping...")
        mount.mount_stop()
    except:
        print("could not home the telescope")
        #TODO add a message to the log

def goto(mount,az,alt):
    try:
        
        print ("Slewing to: ALT/AZ = %0.4f, %0.4f" %(alt,az))
        mount.mount_goto_alt_az(alt, az )
        
        
        time.sleep(5)
        while True:
            s = mount.status()
        
            print ("ALT: %.4f deg;  Az: %.4f degs, Axis0 dist: %.1f arcsec, Axis1 dist: %.1f arcsec" % (
                s.mount.altitude_degs, 
                s.mount.azimuth_degs,
                s.mount.axis0.dist_to_target_arcsec,
                s.mount.axis1.dist_to_target_arcsec
            ))
        
        
            if not s.mount.is_slewing:
                break
            time.sleep(0.5)
        
        print ("Slew complete. Stopping...")
        mount.mount_stop()
    except:
        print("could not move the telescope")
        #TODO add a message to the log


def initialize(mount):
    try:
        connect(mount)
        axes_enable(mount)
        home(mount)
    except:
        #TODO add a message to the log
        print("could not initialize telescope mount")


def shutdown(mount):
    try:
        home(mount)
        axes_disable(mount)
        disconnect(mount)
    except:
        #TODO add a message to the log
        print("could not shut down telescope mount")
        








