#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Apr  5 15:18:46 2021

@author: nlourie
"""

import json
import requests
import os
import sys
import yaml

class SlackObj(object):
    def __init__(self, authentication_config):
        self.config = authentication_config
        
        
    
    def post(self, msg, channel):
        try:
            slack_data = dict({'text': msg})
            webhook_url = self.config['slackbot_webhooks'][channel]
            
            response = requests.post(
            webhook_url, 
            data = json.dumps(slack_data), 
            headers = {'Content-Type': 'application/json'}
            )
        
            status_code = response.status_code
            reply_text = response.text
        
        except Exception as e:
            status_code = -999
            reply_text = e
        
        return status_code, reply_text


# add the wsp directory to the PATH
code_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
wsp_path = code_path + '/wsp'
sys.path.insert(1, wsp_path)
print(f'wsp_path = {wsp_path}')

authentication_config_file = wsp_path + '/credentials/authentication.yaml'

config = yaml.load(open(authentication_config_file), Loader = yaml.FullLoader)


slack = SlackObj(config)
#msg = ":banana-dance:"


user_to_tag = 'frostig'

#msg = f":redsiren:If there's a scheduling error, we might need <@{user_to_tag}> to do something. But for now all is good :slightly_smiling_face:"

#msg = f"Hi Danielle, do you get tagged when I do <@frostig>?"
msg = "This is a scary message"

#channel = 'winter_observatory'
channel = 'nlourie'

prefix = dict({'info' : 'WINTERbot: ',
               'warning' : 'WINTERbot WARNING: '})


level = 'warning'
code, reply = slack.post(prefix[level] + msg, channel)
print(f'request returned code {code}: {reply}')