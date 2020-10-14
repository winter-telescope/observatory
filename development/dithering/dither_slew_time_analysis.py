#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Sep 22 13:58:43 2020

Analyzing WINTER Telescope Slew Time

@author: nlourie
"""

import numpy as np
import matplotlib.pyplot as plt

ftime, index, mount_az_deg, mount_alt_deg, current_field_az, current_field_alt, az_scheduled, alt_scheduled, mount_is_slewing,az_dist, alt_dist = np.loadtxt('dither_slew_time.txt',
                                                                                                                                           unpack = True,
                                                                                                                                           comments = '#',
                                                                                                                                           dtype = float)



imin = 246#443#246
imax = 443#636#443                                                                                                                              

ftime = ftime - ftime[(index>imin) & (index<imax)][0]
az0 = np.mean(current_field_az[(index>imin) & (index<imax)])
alt0 = np.mean(current_field_alt[(index>imin) & (index<imax)])
imin = 243
plt.figure(figsize = (12,6))
plt.rcParams.update({'font.size': 22})
plt.subplot(1,2,1)
#plt.plot(index[(index>imin) & (index<imax)], ((mount_az_deg-az0)*3600)[(index>imin) & (index<imax)],'-o')
#plt.plot(index[(index>imin) & (index<imax)], ((current_field_az-az0)*3600)[(index>imin) & (index<imax)],'-o')
#plt.plot(index[(index>imin) & (index<imax)], ((az_scheduled-az0)*3600)[(index>imin) & (index<imax)],'-o')
#plt.axis([imin, imax,-60,60])
#plt.subplot(1,2,2)
x = ftime
symbol = '-'
plt.plot(x[(index>imin) & (index<imax)], ((mount_az_deg-az0)*3600)[(index>imin) & (index<imax)],symbol,label = 'Current')
plt.plot(x[(index>imin) & (index<imax)], ((current_field_az-az0)*3600)[(index>imin) & (index<imax)],symbol,label = 'Current Field')
plt.plot(x[(index>imin) & (index<imax)], ((az_scheduled-az0)*3600)[(index>imin) & (index<imax)],symbol,label = 'Scheduled')
plt.plot(x[(index>imin) & (index<imax)], (mount_is_slewing*10)[(index>imin) & (index<imax)],symbol, label = 'Slewing?')
plt.plot(x[(index>imin) & (index<imax)], (az_dist)[(index>imin) & (index<imax)],symbol,label = 'Dist to Target')
plt.ylabel('$\delta$ Az [as]',fontsize = 18)
plt.xlabel('Time [s]')
plt.axis([np.min(x[(index>imin) & (index<imax)]),np.max(x[(index>imin) & (index<imax)]),-60,60])
plt.legend(fontsize = 10, loc = 1)

plt.subplot(1,2,2)
plt.plot(x[(index>imin) & (index<imax)], ((mount_alt_deg-alt0)*3600)[(index>imin) & (index<imax)],symbol,label = 'Current')
plt.plot(x[(index>imin) & (index<imax)], ((current_field_alt-alt0)*3600)[(index>imin) & (index<imax)],symbol,label = 'Current Field')
plt.plot(x[(index>imin) & (index<imax)], ((alt_scheduled-alt0)*3600)[(index>imin) & (index<imax)],symbol,label = 'Scheduled')
plt.plot(x[(index>imin) & (index<imax)], (mount_is_slewing*10)[(index>imin) & (index<imax)],symbol, label = 'Slewing?')
plt.plot(x[(index>imin) & (index<imax)], (alt_dist)[(index>imin) & (index<imax)],symbol,label = 'Dist to Target')
plt.ylabel('$\delta$ Alt [as]',fontsize = 18)
plt.xlabel('Time [s]')
plt.axis([np.min(x[(index>imin) & (index<imax)]),np.max(x[(index>imin) & (index<imax)]),-60,60])
plt.legend(fontsize = 10, loc = 1)
plt.tight_layout()
#%%
"""
az_scaling = np.max((az_scheduled-az0)[(index>imin) & (index<imax)])
plt.figure(figsize = (8,6))

plt.plot(index[(index>imin) & (index<imax)], (mount_is_slewing-0.5)[(index>imin) & (index<imax)],'-o')

plt.plot(index[(index>imin) & (index<imax)], np.gradient(mount_is_slewing)[(index>imin) & (index<imax)],'-o')
plt.plot(index[(index>imin) & (index<imax)], ((az_scheduled-az0)/az_scaling)[(index>imin) & (index<imax)])
"""
#%%
dith_az, dith_alt = np.loadtxt('dither_list.conf', unpack = True)
print(f'dith_az = {dith_az}')
print(f'dith_alt = {dith_alt}')

#%%
plt.figure()
imin = 260
imax = 443

xrange = x[(index>imin) & (index<imax)]
azrange = ((az_scheduled - mount_az_deg)*3600)[(index>imin) & (index<imax)]
altrange = ((alt_scheduled - mount_alt_deg)*3600)[(index>imin) & (index<imax)]
azerr_range = az_dist[(index>imin) & (index<imax)]
alterr_range = alt_dist[(index>imin) & (index<imax)]

az_offset = np.median(azrange)
alt_offset = np.median(altrange)

plt.plot(xrange,azrange,'b-', label = 'Az: Measured Error')
plt.plot(xrange,azrange*0.0+az_offset,'b--', label = f'Az: Median Az Offset = %0.3f arcsec'%az_offset)
plt.plot(xrange,azerr_range,'g--',label = 'Az: PW Reported Error')
plt.plot(xrange,altrange,'r-', label = 'Alt: Measured Error')
plt.plot(xrange,altrange*0.0+alt_offset,'r--', label = f'Alt: Median Offset = %0.3f arcsec'%alt_offset)
plt.plot(xrange,alterr_range,'m--',label = 'Alt: PW Reported Err')
plt.legend(fontsize = 10, loc = 1)
plt.xlabel('Time [s]')
plt.ylabel('Angular Error [as]')
#plt.axis([np.min(xrange), np.max(xrange),-10,10])
plt.tight_layout()
#%%
move1_starts = [246,286,324,364,404]
move1_ends =   [259,290,330,370,408]


move2_starts = [443,482,520,559,599]
move2_ends =   [457,486,525,565,603]


move_starts = np.append(move1_starts, move2_starts)
move_ends = np.append(move1_ends, move2_ends)

dt = np.zeros(len(move_starts))
daz = np.zeros(len(move_starts))
dalt = np.zeros(len(move_starts))
for i in range(len(move_starts)):
    dt[i] = ftime[index == move_ends[i]] - ftime[index == move_starts[i]]
    #daz[i] = (az_scheduled[index == move_starts[i]] - az_scheduled[index == move_starts[i-1]])*3600
    daz[i] = ((az_scheduled-az0)*3600)[index == (move_starts[i]+5)] - ((az_scheduled-az0)*3600)[index == (move_starts[i]-5)]
    dalt[i] = ((alt_scheduled-alt0)*3600)[index == (move_starts[i]+5)] - ((alt_scheduled-alt0)*3600)[index == (move_starts[i]-5)]

dtheta = (daz**2 + dalt**2)**0.5

print(f'dt = {dt}')
print(f'daz = {daz}')
print(f'dalt = {dalt}')



plt.figure(figsize = (12,6))
plt.rcParams.update({'font.size': 12})

plt.subplot(3,2,1)
plt.plot(daz[dt<5], dt[dt<5],'o')
plt.xlabel('dt [s]')
plt.ylabel('daz [as]')
plt.subplot(3,2,2)
plt.plot(daz[dt<5]/dt[dt<5])
plt.xlabel('move number')
plt.ylabel('daz/dt [as/s]')

plt.subplot(3,2,3)
plt.plot(dalt[dt<5], dt[dt<5],'o')
plt.xlabel('dt [s]')
plt.ylabel('dalt [as]')
plt.subplot(3,2,4)
plt.plot(dalt[dt<5]/dt[dt<5])
plt.xlabel('move number')
plt.ylabel('dalt/dt [as/s]')

plt.subplot(3,2,5)
plt.plot(dtheta[dt<5], dt[dt<5],'o')
plt.xlabel('dt [s]')
plt.ylabel('dtheta [as]')
plt.subplot(3,2,6)
plt.plot(dtheta[dt<5]/dt[dt<5])
plt.xlabel('move number')
plt.ylabel('dtheta/dt [as/s]')
plt.tight_layout()

