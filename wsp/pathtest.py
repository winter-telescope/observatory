#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Feb  9 10:44:20 2021

this is a test script to figure out how to get the proper paths so that 
base_directory can be specified in a way that wsp can be run from any directory
by adding it to the $PATH variable


@author: winter
"""

# system packages
import sys
import os
import numpy as np
import time
from PyQt5 import uic, QtCore, QtGui, QtWidgets
import yaml
import signal
from pathlib import Path


# add the wsp directory to the PATH
#wsp_path = os.getcwd()
wsp_path = os.path.dirname(__file__)
sys.path.insert(1, wsp_path)

# winter modules
from power import power
from telescope import pwi4
#from telescope import telescope
from control import systemControl
from command import commandServer_multiClient
from housekeeping import easygetdata
from control import systemControl_threaded
from utils import utils
from utils import logging_setup

print(f'### Test Script for Evaluating if the WSP Base Directory Path is Set Up Correctly ###')
print()
print(f'This gets the location of the file that is actually being executed')
print(f'\t__file__ = {__file__}')
print(f'\tos.path.dirname(__file__) = {os.path.dirname(__file__)}')

print()

print(f'This method gets the directory of wherever the file has been asked to run')
print(f'\tos.getcwd() = {os.getcwd()}')

print()

print('Are we properly getting the wsp_path?')
print(f'\twsp_path = {wsp_path}')

d = dict()
d.update({True : 'Yes!'})
d.update({False : 'No! :-('})
correct_path = '/home/winter/WINTER_GIT/code/wsp'
correct = (wsp_path == correct_path)
print(f'\tCorrect Path = {correct_path}')
print(f'\tIs this the proper path? {d[correct]}')