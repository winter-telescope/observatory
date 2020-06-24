#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jun 24 16:34:51 2020

@author: nlourie
"""

import json
import yaml

# load up the yaml config and make into a dict
d = yaml.load(open('test.yaml'), Loader = yaml.FullLoader)

# convert the dict to json
d_json = json.dumps(d,indent = 4)

# save the json to a file
with open('test.json', 'w') as json_file:
  json.dump(d, json_file,indent = 4)

# read in the json file to a dict
d_read_json = json.load(open('test.json'))

