import os
import sys
import yaml
from datetime import datetime
import subprocess

# add the wsp directory to the PATH
wsp_path = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(1, wsp_path)
print(os.path.abspath(__file__))

# import the alert handler
from alerts import alert_handler
from utils import utils

# get the path for the scheduler
code_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
daily_scheduler_path = os.path.join(code_path, 'scheduler','daily_summer_scheduler')

# create the arguments
filepath = os.path.join(daily_scheduler_path,'run_winter_sim.py')
sky_config = os.path.join(daily_scheduler_path, 'sims', 'summer_1_night.json')
night_config = os.path.join(daily_scheduler_path, 'config', 'tonight.cfg')
#print(f'Setting up to run schedule for night of {utils.tonight()}')
print(f'Setting up to run schedule for night of {utils.tonight_local()}')
print(f'### RUNNING DAILY WINTER SCHEDULER ###')


