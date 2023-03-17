#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Mar 16 13:23:24 2023

@author: winter
"""

from datetime import datetime
import numpy as np
import matplotlib.pyplot as plt



varr = np.array([])


T = 30.0 # period in s
w = 2*np.pi/T

dtarr = np.arange(0, 60, 0.1)

for dt in dtarr:
    v = -50.0 + np.cos(w*dt) + 0.1*np.random.normal(0,1)
    
    varr = np.append(varr, v)
    
    
plt.figure()
plt.plot(dtarr, varr)

def getFakeTemp(timestamp, mean_temp, osc_period = 30.0, noise_amp = 0.1):
    
    # get the angular frequency: w = 2*pi/T
    w = 2*np.pi/osc_period
    
    T = mean_temp + np.cos(w*timestamp) + noise_amp*np.random.normal(0,1, len(timestamp))
    
    return T

t0 = 0*datetime.now().timestamp()

tarr = t0 + dtarr

Tarr = getFakeTemp(tarr, mean_temp = -50.0)

plt.figure()
plt.plot(tarr, Tarr)
plt.xlabel('timestamp')
plt.ylabel('T (C)')