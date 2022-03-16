#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Mar 16 14:38:01 2022

@author: winter
"""

import os
import sys
#import sqlalchemy as db
import logging
import glob
import shutil
import yaml
from datetime import datetime

# add the wsp directory to the PATH
code_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
wsp_path = code_path + '/wsp'
sys.path.insert(1, wsp_path)
print(f'wsp_path = {wsp_path}')
base_directory = wsp_path

from utils import utils
try:
    from schedule import schedule
except:
    import schedule
from alerts import alert_handler
from utils import logging_setup
logger = None
config = utils.loadconfig(os.path.join(wsp_path, 'config', 'config.yaml'))
#logger = logging_setup.setup_logger(base_directory, config)


# set up the alert system to post to slack
auth_config_file  = wsp_path + '/credentials/authentication.yaml'
user_config_file = wsp_path + '/credentials/alert_list.yaml'
alert_config_file = wsp_path + '/config/alert_config.yaml'

auth_config  = yaml.load(open(auth_config_file) , Loader = yaml.FullLoader)
user_config = yaml.load(open(user_config_file), Loader = yaml.FullLoader)
alert_config = yaml.load(open(alert_config_file), Loader = yaml.FullLoader)

alertHandler = alert_handler.AlertHandler(user_config, alert_config, auth_config)

msg = f"{datetime.now().strftime('%m/%d/%Y %H:%M')} archiving all TOO schedules with no more observable targets"

alertHandler.slack_log(msg, group = None)


def log( msg='', level = logging.INFO):
        if logger is None:
                print(msg)
        else:
            logger.log(level = level, msg = msg)

# get all the files in the ToO High Priority folder
highPriority_schedule_directory = os.path.join(os.getenv("HOME"), config['scheduleFile_ToO_HighPriority_directory'])
highPriority_schedules = glob.glob(os.path.join(highPriority_schedule_directory, '*.db'))
log(f'schedules in high priority folder: {highPriority_schedules}')
log()
ToOschedules = {}
# check if the schedule is already in self.ToOschedules
for sched_filepath in highPriority_schedules:
    sched_filename = sched_filepath.split('/')[-1]
    sched_filedirectory = highPriority_schedule_directory
    #log(f'need to add {sched_filename} to high priority schedules')
    sched_obj = schedule.Schedule(base_directory = base_directory,
                                  config = config,
                                  logger = logger,
                                  scheduleFile_directory = sched_filedirectory)
    
    # set up the ToO schedule
    sched_obj.loadSchedule(schedulefile_name  = sched_filepath)
    
    ToOschedules.update({sched_filename : {'filepath' : sched_filepath,
                                                'priority' : 'high',
                                                'schedule' : sched_obj}})

# now query if there are valid observations in any of the TOO schedule

# init a list of valid observations
validObs = []
validSchedules = []
validSchedule_filenames = []

#self.announce('querying all schedules in High Priority ToO folder...')
archived = 0
for schedname in ToOschedules:
    log(f'searching for valid observations in {schedname}...')
    TOOschedule = ToOschedules[schedname]['schedule']
    TOOschedule.gotoNextObs(obstime_mjd = 'now')
    remaining_valid_observations = TOOschedule.remaining_valid_observations
    log(f'> Remaining Observable Entries: {remaining_valid_observations}')
    
    # if the file has no remaining valid observations, move it to the completed folder
    if remaining_valid_observations == 0:
        log(f'>> MOVING TO COMPLETED FOLDER')
        destination = os.path.join(highPriority_schedule_directory, 'archived', schedname)
        source = os.path.join(highPriority_schedule_directory, schedname)
        shutil.move(source, destination)
        archived +=1
    log()

alertHandler.slack_log(f':sweep-4173: archived {archived} schedules, {len(ToOschedules) - archived} remain')