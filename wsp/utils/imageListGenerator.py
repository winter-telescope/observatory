#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Mar 16 13:04:54 2022

@author: winter
"""
from datetime import datetime
import glob
import os
import sys
import numpy as np

# add the wsp directory to the PATH
code_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
wsp_path = code_path + '/wsp'
sys.path.insert(1, wsp_path)
print(f'wsp_path = {wsp_path}')

from utils import utils

for i in range(4):
    if i == 0:
        starttime = 59654.0208333333
        endtime = 59654.1041666667
        comment = 'timed_requests_03_15_2022_16_1647385494.db'
        savefile = 'TOO_20220315_1.txt'
    if i == 1:
        starttime = 59654.5
        endtime = 59654.5833333333
        comment = 'timed_requests_03_15_2022_15_1647383735.db'
        savefile = 'TOO_20220315_2.txt'
    if i == 2:
        starttime = 59654.2083333333
        endtime = 59654.2916550926
        comment = 'timed_requests_03_15_2022_15_1647383035.db'
        savefile = 'TOO_20220315_3.txt'
    if i == 3:
        starttime = 59654.125
        endtime = 59654.2118055556
        comment = 'timed_requests_03_15_2022_15_1647382777.db'
        savefile = 'TOO_20220315_4.txt'
    
    savepath = os.path.join(os.getenv("HOME"), 'data', 'imageLists', savefile)
    
    imglist = utils.getImages(starttime, endtime, fullpath = False)
    
    print(f'Found {len(imglist)} images between {starttime} and {endtime}:\n ',"\n  ".join(imglist))
    
    np.savetxt(savepath, np.array(imglist), delimiter='\t', fmt = '%s', header = f'TOO Schedule File = {comment}')
