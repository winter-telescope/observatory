#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jan 13 12:59:33 2020

@author: winter
"""


import time
import numpy as np
from pwi4_client_py3 import PWI4


print ("Connecting to PWI4...")

pwi4 = PWI4(host = "thor",port = 8220)



s = pwi4.status()
time.sleep(2)
print ("Mount connected:", s.mount.is_connected)

if not s.mount.is_connected:
    print ("Connecting to mount...")
    s = pwi4.mount_connect()
    time.sleep(2)
    print ("Mount connected:", s.mount.is_connected)

time.sleep(2)
axes = {'az':0, 'alt':1}
print("Enabling the motor axes:")
pwi4.mount_enable(axes['az'])
pwi4.mount_enable(axes['alt'])
time.sleep(2)
s = pwi4.status()
print("Is the altitude axis enabled? ", s.mount.axis0.is_enabled)
print("Is the azimuth axis enabled? ", s.mount.axis1.is_enabled)

time.sleep(2)
#print ("  RA/Dec: %.4f, %.4f" % (s.mount.ra_j2000_hours, s.mount.dec_j2000_degs))
print("Current ALT/AZ: %0.4f, %0.4f" %(s.mount.altitude_degs,s.mount.azimuth_degs))

random_alt = np.random.randint(16,89)
random_az = np.random.randint(1,359)
#pwi4.mount_goto_ra_dec_j2000(10, 70)

#random_alt = 0
#random_az = 120

print ("Slewing to ALT/AZ = %0.4f, %0.4f" %(random_alt,random_az))

pwi4.mount_goto_alt_az(random_alt, random_az )


time.sleep(5)
while True:
    s = pwi4.status()

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
pwi4.mount_stop()

pwi4.virtualcamera_take_image_and_save("Test_Image.FITS")

time.sleep(5)
print("Disabling Alt and Az Axes")
pwi4.mount_disable(axes['alt'])
pwi4.mount_disable(axes['az'])
time.sleep(2)
s = pwi4.status()
print("Is the altitude axis enabled? ", s.mount.axis0.is_enabled)
print("Is the azimuth axis enabled? ", s.mount.axis1.is_enabled)

time.sleep(5)
print("Disconnecting from Telescope")
pwi4.mount_disconnect()
s = pwi4.status()
print ("Mount Connected?:", s.mount.is_connected)
if s.mount.is_connected:
    print("Trying again to disconnect mount...")
    s = pwi4.mount_disconnect()
    time.sleep(2)
    print ("Mount Connected?:", s.mount.is_connected)
