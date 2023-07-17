#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jul 17 06:34:48 2023

Data Purger

@author: nlourie
"""

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
import subprocess
from functools import partial
import shutil

actually_delete = True


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
#logger = logging_setup.setup_logger(wsp_path, config)


# set up the alert system to post to slack
auth_config_file  = wsp_path + '/credentials/authentication.yaml'
user_config_file = wsp_path + '/credentials/alert_list.yaml'
alert_config_file = wsp_path + '/config/alert_config.yaml'

auth_config  = yaml.load(open(auth_config_file) , Loader = yaml.FullLoader)
user_config = yaml.load(open(user_config_file), Loader = yaml.FullLoader)
alert_config = yaml.load(open(alert_config_file), Loader = yaml.FullLoader)

alertHandler = alert_handler.AlertHandler(user_config, alert_config, auth_config)

nweeks = 1
ndays = nweeks*7

commissioning_date = datetime(2023,6,1,0,0)

if nweeks >1:
    suffix = ''
else:
    suffix = 's'

msg = f"{datetime.now().strftime('%m/%d/%Y %H:%M')} deleting nightly data older than {nweeks} week{suffix}:"

alertHandler.slack_log(msg, group = None)


def log( msg='', level = logging.INFO):
    if logger is None:
        print(msg)
    else:
        logger.log(level = level, msg = msg)

def getFolderSize(p):
    # from here: https://stackoverflow.com/a/18763675
    prepend = partial(os.path.join, p)
    return sum([(os.path.getsize(f) if os.path.isfile(f) else getFolderSize(f)) for f in map(prepend, os.listdir(p))])

# get all the files in the ToO High Priority folder
nightly_data_dir = os.path.join(os.getenv("HOME"), config['image_directory'])
imagedirpaths = glob.glob(os.path.join(nightly_data_dir,'*'))
#log(f'directories in nightly image directory: {imagedirpaths}')

skippeddirs = []
purgepaths = []
purgedirs = []
preshipdirs = []
est_purgesize = 0
# get today's data: just use simple now to do in current cpu time/timezone
today = datetime.now()

# now go through each directory:
for dirpath in imagedirpaths:
    
    dirname = os.path.basename(dirpath)
    #print(dirname)

    # try to make a date out of the path
    try:
        dirdate = datetime.strptime(dirname, '%Y%m%d')
        
        # only purge data taken after commissioning:
        if dirdate > commissioning_date:
            dt = today - dirdate
            
            # if enough days have passed since the folder's date
            if dt.days > ndays:
                purgedirs.append(dirname)
                purgepaths.append(dirpath)
                est_purgesize += getFolderSize(dirpath)
        else:
            preshipdirs.append(dirname)
    except:
        skippeddirs.append(dirname)

est_purgesize_gb = est_purgesize/1e9

# NOW ACTUALLY DELETE THE DIRECTORIES!!!!!
if actually_delete:
    for dirpath in purgepaths:
        try:
            shutil.rmtree(dirpath)
        except Exception as e:
            msg = f'could not purge directory at {dirpath} due to error: {e}'
            log(msg)
            alertHandler.slack_log(f'{msg}')

log(f'skipped these directories bc they could not be turned into dates: {skippeddirs}')
log()
log(f'skipped these directories bc they were from before commissioning: {preshipdirs}')
log()
if len(purgedirs)==0:
    purgemsg = f'No directories to delete.'
else:
    purgemsg = f'Purging these directories to free up {est_purgesize_gb:.1f}G of disk space on Freya: {purgedirs}'
log(purgemsg)

    
alertHandler.slack_log(f':sweep-4173: {purgemsg}')