#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Feb  5 17:16:23 2021


This is a module that contains the local weather attributes
It will set up a remote object from the weather daemon, check it,
and holds variables that can be accessed internally within wsp


@author: winter
"""


import os
import io
from configobj import ConfigObj
import urllib.request
import urllib.error
import urllib.parse
import numpy as np
from datetime import datetime,timedelta
import pytz
import sys
import traceback
import Pyro5.core
import Pyro5.server

# add the wsp directory to the PATH
wsp_path = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(1, wsp_path)

from utils import utils


class Weather(object):
    
    def __init__(self,base_directory, config, logger):
        
        self.base_directory = base_directory
        self.config = config
        self.logger = logger
        
        self.init_remote_weather()
        self.getWeather()
        
    def init_remote_weather(self):
        #init the weather
        try:
            self.remote_weather = Pyro5.client.Proxy("PYRONAME:weather")
            self.remote_weather.startWeather(base_directory = self.base_directory)
            self.logger.error('weather connect succesful')
        except Exception as e:
            self.logger.error('weather connect failed', exc_info=True )
            
    def getWeather(self):
        # this asks the remote weather object for the current weather (returned as a dict)
        self.state = self.remote_weather.getWeather()
        
        # now assign all the attributes that wsp is looking for
        self.assign_attributes()
        
    def assign_attributes(self):
        
        self.ok_to_observe = self.state['ok_to_observe']
        pass
        
# Try it out
if __name__ == '__main__':
    config = utils.loadconfig(wsp_path + '/config/config.yaml')
    night = utils.night()
    logger = utils.setup_logger(wsp_path, night, logger_name = 'logtest')

    weather = Weather(os.path.dirname(os.getcwd()),config = config, logger = logger)