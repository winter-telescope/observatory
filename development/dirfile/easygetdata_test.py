#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jun 18 16:54:27 2020


easygetdata test file

@author: nlourie
"""

import numpy as np
import pygetdata as gd
import easygetdata as egd

filename = 'dirfile_example'
df = egd.EasyGetData(filename, "w")

fieldname = 'data'
units = 'V'
label = 'Voltage'
spf = 20

df.add_raw_entry(field = fieldname, spf=spf, dtype = "float64", units = units, label = label)
df.add_raw_entry('poop', spf = 1, units = 'farts',label = 'fizzzarts')
# add data!
i = 0
try:
    while True:
        start = spf*i
        end = start+spf
        x = np.arange(start,end)*0.01
        data = np.cos(10*x)
        df.write_field(fieldname, data)
        df.write_field('poop', [i])
        i+=1
    
except KeyboardInterrupt:
    pass