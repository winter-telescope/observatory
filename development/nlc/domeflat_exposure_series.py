#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed May  7 19:44:43 2025

@author: winter
"""

import os
import time
from datetime import datetime, timedelta
import numpy as np
import sys
from socket import socket, AF_INET, SOCK_STREAM

#%% init a tcp-ip connection to wsp

sock = socket(AF_INET, SOCK_STREAM)
wsp_cmd_server_address = ("localhost", 7000)
sock.connect(wsp_cmd_server_address)

def send(cmd):
    try:
        sock.sendall(bytes(cmd, "utf-8"))
        return 1
    except Exception as e:
        return 0, e
send("xyzzy")
#%% test out a tcp-ip cmd
send("setExposure 10")

send("doExposure")

#%% start up the observatory
send("do_startup")
#%% take control of the dome
send("dome_takecontrol")

#%% we want the robot OFF
send("robo_stop")

#%% set up the flat lamp

# turn on the lamp
send("pdu on callamp")
#%%
# make sure the filter is homed
send("fw_home")
#%%
# put the filter tray into the desired position
filterdict = {"dark" : 1,
              "J" : 2,
              "Y" : 3,
              "Hs" : 4}

filt = "J"
print(f"sending filter tray to {filt}-band: pos = {filterdict[filt]}")
send(f"fw_goto {filterdict[filt]}")

#%% slew the telescope 
default = False

if default:
    # the place we normally point for dome flats
    mount_alt = 30
    mount_az = 270
else:
    # point to a different place
    # for the prior NLC data we did this at 35, 270 in J-band
    mount_alt = 30
    mount_az = 270. - 80.



print(f"sending telescope to (alt, az) = ({mount_alt}, {mount_az})")
send(f"mount_goto_alt_az {mount_alt} {mount_az}")


dome_az = mount_az-90.
send(f"dome_goto {dome_az}")
print(f"sending dome to {dome_az} deg")
# slew the mount

#%% take a test exposure
e = 12.
send(f"setExposure {e}")
time.sleep(1)
dir_flat = "/home/winter/data/images/domeflats_nlc/20250507"
mode = "test"
buffer = 1.0
n_imgs = 1
for i in range(n_imgs):
    name = datetime.utcnow().strftime("%Y%m%d-%H%M%S-%f")[:-3] + '_exp_' + str(e) + '_lamp' + f"_{i}"
    send(f"doExposure --{mode} --imname {name} --imdir {dir_flat}")
    time.sleep(e+buffer)
print("done")


#%% let's make some dictionaries that define some approaches
image_buffer = 2.0
exptime_buffer = 0.5
datasets = {"fine"      : {"min_exptime" : 0.14,
                           "max_exptime" : 5.,
                           "n_exptimes"  : 50,
                           "n_ramps"     : 10,
                           "mode"        : "domeflat",
                           },
            "coarse"    : {"min_exptime" : 0.14,
                           "max_exptime" : 12.,
                           "n_exptimes"  : 50,
                           "n_ramps"     : 10,
                           "mode"        : "domeflat",
                                       },
            "2stage-1"    : {"min_exptime" : 0.14,
                           "mid_exptime" : 5.0,
                           "max_exptime" : 12.0,
                           "n_exptimes_lower" : 50,
                           "n_exptimes_upper" : 25,
                           "n_ramps"    : 10,
                           "mode" : "domeflat",
                           },
            "2stage-2"    : {"min_exptime" : 0.14,
                           "mid_exptime" : 5.0,
                           "max_exptime" : 12.0,
                           "n_exptimes_lower" : 50,
                           "n_exptimes_upper" : 10,
                           "n_ramps"    : 10,
                           "mode" : "domeflat",
                           },
            "test"      : {"min_exptime" : 0.14,
                           "max_exptime" : 5.0,
                           "n_exptimes"  : 5,
                           "n_ramps"     : 2,
                           "mode"        : "test",
                                       },
            }

for option in datasets:
    params = datasets[option]
    print()
    print(f"{option} dataset:")
    if "2stage" in option:
        exptimes_1 = np.linspace(params["min_exptime"], params["mid_exptime"], params["n_exptimes_lower"])
        exptimes_2 = np.linspace(params["mid_exptime"], params["max_exptime"], params["n_exptimes_upper"]+1)
        exptimes = np.append(exptimes_1, exptimes_2[1:]) # don't double count the mid exptime
        #print(exptimes)
    else:
        exptimes = np.linspace(params["min_exptime"], params["max_exptime"], params["n_exptimes"])
    n_ramps = params["n_ramps"]
    est_ramptime = np.sum(exptimes+(image_buffer+exptime_buffer))
    est_totaltime = n_ramps*est_ramptime
    print(f"{len(exptimes)} points from {min(exptimes)} - {max(exptimes)}, {n_ramps} ramps")
    print(f"estimated time per ramp = {est_ramptime} s")
    print(f"estimated total time = {est_totaltime/60.:.0f} m = {est_totaltime/3600.:.1f} h")

# previous approach
exptimes_old = np.linspace(0.14, 5, 70)
imgs_per_exptime = 10
buffer_old = 2.
est_ramptime_old = np.sum((exptimes_old+buffer_old)*imgs_per_exptime)
print()
print(f"old approach: \neach ramp (with {imgs_per_exptime} imgs per exptime) up to 5s took {est_ramptime_old/60:.1f} m")

#%% take the data
options = ["coarse", "fine"]
#options = ["test"]
options = ["2stage-2"]
for option in options:
    params = datasets[option]
    if "2stage" in option:
        exptimes_1 = np.linspace(params["min_exptime"], params["mid_exptime"], params["n_exptimes_lower"])
        exptimes_2 = np.linspace(params["mid_exptime"], params["max_exptime"], params["n_exptimes_upper"]+1)
        exptimes = np.append(exptimes_1, exptimes_2[1:]) # don't double count the mid exptime
        #print(exptimes)
    else:
        exptimes = np.linspace(params["min_exptime"], params["max_exptime"], params["n_exptimes"])
    
    n_ramps = params["n_ramps"]
    mode = params["mode"]
    est_ramptime = np.sum(exptimes+buffer)
    est_totaltime = n_ramps*est_ramptime
    
    starttime = datetime.now()
    est_endtime = starttime + timedelta(minutes=est_totaltime/60.0)
    timefmt = "%H:%M"
    print(f"start time: {starttime.strftime(timefmt)}")
    print(f"end time:   {est_endtime.strftime(timefmt)}")
    print(f"time to complete: {est_totaltime/60.:.0f} m")
    print()
    
    top_level_dir = f"/home/winter/data/images/domeflats_nlc/{starttime.strftime('%Y%m%d')}"
    
    
    # take the specified number of ramps
    for ramp_number in range(n_ramps):
        
        imdir = top_level_dir + f"/{option}-" + starttime.strftime("%Y%m%d_%H%M%S") + f"/ramp_{ramp_number}"
        #print(imdir)
        
        for ind, exptime in enumerate(exptimes):
            exptime = np.round(exptime,2)
            print(f"{option}: ramp [{ramp_number+1}/{n_ramps}]: Exptime [{ind+1}/{len(exptimes)}]: {exptime} s")
            send(f"setExposure {exptime}")
            time.sleep(exptime_buffer)
            
            imname = datetime.utcnow().strftime("%Y%m%d-%H%M%S-%f")[:-3] + f'_exp_{exptime}' + '_lamp' + f"_ramp_{ramp_number}"
            send(f"doExposure --{mode} --imname {imname} --imdir {imdir}")
            time.sleep(exptime+image_buffer)

print("DONE!")