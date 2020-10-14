#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Oct  6 15:09:10 2020

This is an example of a method to create a symbolic link to another file.

In this case, the idea is to create a nightly schedule file, which is saved
in /data/schedules. Then a symbolic link is created at /data/nightly_schedule.lnk,
which points to the nightly schedule.


@author: nlourie
"""

import os
from datetime import datetime
import pathlib
import numpy as np


    
home = os.path.expanduser("~")
parent_dir = home + '/data'

file_dir = parent_dir + '/schedules'

now = datetime.utcnow() # or can use now for local time
now_str = now.strftime('%Y%m%d') # give the name a more readable date format

file_path = file_dir + '/nightly_' + now_str + '.db'
file_link_path = parent_dir + '/nightly_schedule.lnk'

# create the data directory if it doesn't exist already
pathlib.Path(file_dir).mkdir(parents = True, exist_ok = True)
print(f'making directory: {parent_dir}')
        
# create the file (ie database or whatever). Replace this with the real code
header = f'THIS IS A SAMPLE FILE FOR THE NIGHT: {now_str}'
data = [1,2,3,4,5]
np.savetxt(file_path, data, header = header)

# make a symbolic link (symlink) to the file
print(f'trying to create link at {file_link_path} to {file_path}')

try:
    os.symlink(file_path, file_link_path)
except FileExistsError:
    print('deleting existing symbolic link')
    os.remove(file_link_path)
    os.symlink(file_path, file_link_path)