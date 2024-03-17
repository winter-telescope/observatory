#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Feb 15 15:26:13 2024

@author: nlourie
"""


import os
import sys
#import sqlalchemy as db
import logging
import glob
import shutil
import yaml
from datetime import datetime
#import wintertoo.validate


# add the wsp directory to the PATH
code_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
wsp_path = code_path + '/wsp'
sys.path.insert(1, wsp_path)
print(f'wsp_path = {wsp_path}')
base_directory = wsp_path

from utils import utils
try:
    from schedule import schedule
except Exception as e:
    print(f'could not import schedule from schedule:')
    import schedule

logger = None
config = utils.loadconfig(os.path.join(wsp_path, 'config', 'config.yaml'))



def log( msg='', level = logging.INFO):
        if logger is None:
                print(msg)
        else:
            logger.log(level = level, msg = msg)

# get all the files in the ToO High Priority folder
scheduleFile_ToO_directory = os.path.join(os.getenv("HOME"), config['scheduleFile_ToO_directory'])
ToO_scheduleFilepaths = glob.glob(os.path.join(scheduleFile_ToO_directory, '*.db'))
log(f'schedules in high priority folder: {scheduleFile_ToO_directory}')
log()
ToOschedules = {}
# check if the schedule is already in self.ToOschedules
for sched_filepath in ToO_scheduleFilepaths:
    sched_filename = sched_filepath.split('/')[-1]
    #log(f'need to add {sched_filename} to high priority schedules')
    sched_obj = schedule.Schedule(base_directory = base_directory,
                                  config = config,
                                  logger = logger,
                                  scheduleFile_directory = scheduleFile_ToO_directory,
                                  verbose = True)
    
    # set up the ToO schedule
    sched_obj.loadSchedule(schedulefile_name  = sched_filepath)
    
    ToOschedules.update({sched_filename : {'filepath' : sched_filepath,
                                                'schedule' : sched_obj}})

# now query if there are valid observations in any of the TOO schedule

# init a list of valid observations
validObs = []
validSchedules = []
validSchedule_filenames = []

#self.announce('querying all schedules in High Priority ToO folder...')
archived = 0
for schedname in ToOschedules:
    log()
    log(f'searching for valid observations in {schedname}...')
    TOOschedule = ToOschedules[schedname]['schedule']
    TOOschedule.gotoNextObs(obstime_mjd = 'now')
    remaining_observable_entries = TOOschedule.remaining_observable_entries
    log(f'> Remaining Observable Entries: {remaining_observable_entries}')
    
