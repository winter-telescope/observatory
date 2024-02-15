#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Feb 15 15:18:42 2024

@author: nlourie
"""

import os
import sys
#import pathlib
import json
import yaml
import logging
import traceback
from datetime import datetime, timedelta
import pytz
import random

# add the wsp directory to the PATH
wsp_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),'wsp')
# switch to this when ported to wsp
#wsp_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

sys.path.insert(1, wsp_path)
print(f'CalTracker: wsp_path = {wsp_path}')

from utils import utils

class CalTracker(object):
    def __init__(self, config, logger = None):
        """
        This is an object which will help keep track of whether various
        calibration sequences have been executed.
        
        It creates and monitors a json log like this:
        
            {
                "winter": {
                    "darks" : {
                        "dark_times" : [60, 120]
                        "last_darkseq_timestamp_utc": null,
                        "last_darkseq_time_local": null,
                        }
                    }
            }
        """
        self.config = config
        self.logger = logger
        
        self.cal_log = dict()
        
        self.active_filters = dict()
        
        self.setupFocusLog()
    
    def log(self, msg, level = logging.INFO):
        if self.logger is None:
                print(msg)
        else:
            self.logger.log(level = level, msg = msg)
    