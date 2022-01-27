import yaml
import sys
from datetime import datetime
from os.path import exists, getsize

wsp_path = '../wsp'
sys.path.insert(0, wsp_path)
from alerts import alert_handler
from utils import utils

schedulefile_name = f'nightly_{utils.tonight_local()}.db'
schedule_path = '/home/winter/data/schedules/'+schedulefile_name

file_exists = exists(schedule_path)

if file_exists == True:
    file_size = getsize(schedule_path)
    if file_size < 10**6: 
        msg = f"WARNING! Nightly schedule file exists at {schedule_path} but is only {file_size} bytes large"
    else:
        msg = f"Nightly schedule file exists at {schedule_path} and is {file_size} bytes large"
else:
     msg = f"ERROR! No nightly schedule file exist at {schedule_path}"

auth_config_file  = wsp_path + '/credentials/authentication.yaml'
user_config_file = wsp_path + '/credentials/alert_list.yaml'
alert_config_file = wsp_path + '/config/alert_config.yaml'

auth_config  = yaml.load(open(auth_config_file) , Loader = yaml.FullLoader)
user_config = yaml.load(open(user_config_file), Loader = yaml.FullLoader)
alert_config = yaml.load(open(alert_config_file), Loader = yaml.FullLoader)

alertHandler = alert_handler.AlertHandler(user_config, alert_config, auth_config)

print(msg)
  
#alertHandler.email_group('scheduler', 'subject', msg)

alertHandler.slack_message_group('scheduler', msg)


