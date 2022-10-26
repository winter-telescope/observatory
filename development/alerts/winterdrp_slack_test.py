#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Sep 28 12:09:16 2022

@author: nlourie
"""



import os
import yaml
import sys
import logging


# add the wsp directory to the PATH
code_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
wsp_path = code_path + '/wsp'
sys.path.insert(1, wsp_path)
print(f'wsp_path = {wsp_path}')

from alerts import alert_handler


# init a slack handler

auth_config_file = os.path.join(wsp_path, 'credentials', 'winterdrpbot_authentication.yaml')
auth_config  = yaml.load(open(auth_config_file) , Loader = yaml.FullLoader)


slacker = alert_handler.SlackDispatcher(auth_config)

# post to the #winterdrp channel
msg = 'this is a test of the new WINTER DRP Bot!'
channel = 'winter_drp'
slacker.post(channel, msg)

# post a picture
msg = 'i can post images too! :banana-dance:'
impath = os.path.join(wsp_path, 'alerts', 'summer_galaxy_pretty_cruz.gif')
slacker.postImage(channel, impath, msg, verbose = False)

