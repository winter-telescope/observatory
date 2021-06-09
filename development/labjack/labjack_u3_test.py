#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jun  2 13:33:41 2021

@author: nlourie
"""



#from labjack import ljm
import numpy as np
import matplotlib.pyplot as plt
import u3
import os
import sys
from scipy import interpolate

code_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
wsp_path = os.path.join(code_path, 'wsp')
print(f'wsp_path = {wsp_path}')
"""

handle = ljm.openS("T7", "ETHERNET", '192.168.1.110')



info = ljm.getHandleInfo(handle)

print(f"Opened a LabJack with \n\
      Device type{info[0]}, \n\
      Connection Type: {info[1]}, \n\
      Serial Number: {info[2]}, \n\
      IP addr: {ljm.numberToIP(info[3])}, port: {info[4]}, \n\
      max bytes per MB: {info[5]}\n")

channels = ['AIN0', 'AIN1','AIN2', 'FIO2']
vals = ljm.eReadNames(handle, len(channels), channels)

val_dict = dict(zip(channels,vals))
for key in val_dict.keys():
    print(f'{key}: {val_dict[key]}')
    
"""

#u3dict = u3.openAllU3()

#%%
#lj1 = u3.U3(firstFound = False, devNumber = 320099049)
#lj1 = u3dict['320099049']

lj1 = u3.U3(autoOpen = False)
lj1.open(handleOnly = True, serial = 320099049)
#%%
lut_path = os.path.join(wsp_path, 'config','Thermistor_10k_2p5v_beta3984_V_to_T.LUT')
V_LUT, T_LUT = np.loadtxt(lut_path, unpack = True)

f = interpolate.interp1d(V_LUT, T_LUT, kind = 'linear')

V0 = lj1.getAIN(0)
V1 = lj1.getAIN(1)

T0 = f(V0)
T1 = f(V1)

print(f'T0 = {T0:0.3f} C')
print(f'T1 = {T1:0.3f} C')

