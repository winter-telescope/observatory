#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Sep 22 18:15:55 2020

Labjack Test


@author: winter
"""


from labjack import ljm
import numpy as np
import matplotlib.pyplot as plt


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