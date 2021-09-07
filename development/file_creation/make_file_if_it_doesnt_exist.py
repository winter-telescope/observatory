#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Sep  7 11:40:30 2021

@author: nlourie
"""

"""
# FOR REFERENCE: DIRFILE SETUP
# create the dirfile directory
hk_dir = os.getenv("HOME") + '/' + self.config['housekeeping_data_directory']

now = datetime.utcnow() # or can use now for local time
#now = str(int(now.timestamp())) # give the name the current ctime
now_str = now.strftime('%Y%m%d_%H%M%S') # give the name a more readable date format
self.dirname = now_str + '.dm'
self.dirpath = hk_dir + '/' + self.dirname

# create the directory and filenames for the data storage
hk_link_dir = os.getenv("HOME") + '/' + self.config['housekeeping_data_link_directory']
hk_link_name = self.config['housekeeping_data_link_name']
hk_linkpath = hk_link_dir + '/' + hk_link_name

# create the data directory if it doesn't exist already
pathlib.Path(hk_dir).mkdir(parents = True, exist_ok = True)
print(f'housekeeping: making directory: {hk_dir}')
        
# create the data link directory if it doesn't exist already
pathlib.Path(hk_link_dir).mkdir(parents = True, exist_ok = True)
print(f'housekeeping: making directory: {hk_link_dir}')

# create the dirfile database
self.df = egd.EasyGetData(self.dirpath, "w")
print(f'housekeeping; creating dirfile at {self.dirpath}')
#/* make a link to the current dirfile - kst can read this to make life easy... */
print(f'housekeeping: trying to create link at {hk_linkpath}')

try:
    os.symlink(self.dirpath, hk_linkpath)
except FileExistsError:
    print('housekeeping: deleting existing symbolic link')
    os.remove(hk_linkpath)
    os.symlink(self.dirpath, hk_linkpath)
"""

import os
import sys
import yaml

# add the wsp directory to the PATH
wsp_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),'wsp')
sys.path.insert(1, wsp_path)
print(f'wsp_path = {wsp_path}')

# winter modules
from utils import utils

class Test(object):
    
    def __init__(self):
        self.triggers = dict({'trig1' : False,
                             'trig2' : False,
                             'trig3' : False})
    
    def setupTrigLog(self):
        """
        set up a yaml log file which records whether the command for each trigger
        has already been sent tonight.
        
        checks to see if tonight's triglog already exists. if not it makes a new one.
        """
        # file
        self.triglogfilename = f'triglog_{utils.tonight()}.yaml'
    
        # check if the file exists
        
        
        """
        for trigname in self.triggers.keys():
            self.triglog.update({trigname : False})
        """  


if __name__ == '__main__':
    
    main = Test()
    
    