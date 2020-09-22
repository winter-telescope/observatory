#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Sep 22 13:58:43 2020

Analyzing WINTER Telescope Slew Time

@author: nlourie
"""

import numpy as np
import matplotlib.pyplot as plt

ftime, index, mount_az_deg, mount_alt_deg, current_field_az, current_field_alt, az_scheduled, alt_scheduled, mount_is_slewing = np.loadtxt('dither_testing.txt',
                                                                                                                                           unpack = True,
                                                                                                                                           comments = '#',
                                                                                                                                           dtype = float)



imin = 245
imax = 442                                                                                                                                          

ftime = ftime - ftime[(index>imin) & (index<imax)][0]
az0 = np.mean(az_scheduled[(index>imin) & (index<imax)])

plt.figure(figsize = (12,6))
plt.rcParams.update({'font.size': 22})
plt.subplot(1,2,1)
plt.plot(index[(index>imin) & (index<imax)], ((mount_az_deg-az0)*3600)[(index>imin) & (index<imax)],'-o')
plt.plot(index[(index>imin) & (index<imax)], ((current_field_az-az0)*3600)[(index>imin) & (index<imax)],'-o')
plt.plot(index[(index>imin) & (index<imax)], ((az_scheduled-az0)*3600)[(index>imin) & (index<imax)],'-o')
plt.axis([imin, imax,-60,60])
plt.subplot(1,2,2)
plt.plot(ftime[(index>imin) & (index<imax)], ((mount_az_deg-az0)*3600)[(index>imin) & (index<imax)],'-o')
plt.plot(ftime[(index>imin) & (index<imax)], ((current_field_az-az0)*3600)[(index>imin) & (index<imax)],'-o')
plt.plot(ftime[(index>imin) & (index<imax)], ((az_scheduled-az0)*3600)[(index>imin) & (index<imax)],'-o')
plt.plot(ftime[(index>imin) & (index<imax)], (mount_is_slewing*10)[(index>imin) & (index<imax)],'-o')
plt.axis([0,np.max(ftime[(index>imin) & (index<imax)]),-60,60])
#%%
az_scaling = np.max((az_scheduled-az0)[(index>imin) & (index<imax)])
plt.figure(figsize = (8,6))

plt.plot(index[(index>imin) & (index<imax)], (mount_is_slewing-0.5)[(index>imin) & (index<imax)],'-o')

plt.plot(index[(index>imin) & (index<imax)], np.gradient(mount_is_slewing)[(index>imin) & (index<imax)],'-o')
plt.plot(index[(index>imin) & (index<imax)], ((az_scheduled-az0)/az_scaling)[(index>imin) & (index<imax)])