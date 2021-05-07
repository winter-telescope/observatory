#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri May  7 08:34:19 2021

@author: nlourie
"""
import os
import sys
import pygetdata as getdata
from datetime import datetime

# add the wsp directory to the PATH
wsp_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),'wsp')
sys.path.insert(1, wsp_path)
print(f'data_handler: wsp_path = {wsp_path}')

# winter modules
from housekeeping import easygetdata as egd
"""
# Read and print dirfile field
print ('== 1st pass == ')
d = getdata.dirfile(dirfile_path)
print ('dirfile nframe', d.nframes)
read_data = d.getdata('data')
print ('data read:')
print( read_data)
d.close()"""


dirfile_path = os.path.join(os.getenv("HOME"),'data','dm.lnk')
df = egd.EasyGetData(dirfile_path, "r")

#data = df.read_data((-2,-1),['timestamp'])
#print(f'last timestamp = {data}')

# Read and print dirfile field
print ('== 1st pass == ')
d = getdata.dirfile(dirfile_path)
print ('dirfile nframe', d.nframes)

last_timestamp = d.getdata('timestamp',first_frame = d.nframes, num_frames = 1)[0]
print(f'last_timestamp = {last_timestamp}')
print(f'now_timestamp  = {datetime.utcnow().timestamp()}')

"""read_data = d.getdata('timestamp')
print ('data read:')
print( read_data)"""
d.close()
