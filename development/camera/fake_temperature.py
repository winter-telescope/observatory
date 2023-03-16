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

tarr = np.arange(0, 60, 0.1)

for t in tarr:
    v = -50.0 + np.cos(w*t) + 0.1*np.random.normal(0,1)
    
    varr = np.append(varr, v)
    
    
plt.figure()
plt.plot(tarr, varr)

