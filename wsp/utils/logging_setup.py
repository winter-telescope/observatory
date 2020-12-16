#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Dec 15 19:07:33 2020

This file is part of wsp

# PURPOSE #

this is a module for setting up the winter logging

@author: nlourie
"""

# system packages
import sys
import os
import numpy as np
import time
from datetime import datetime
from PyQt5 import uic, QtCore, QtGui, QtWidgets
import pathlib
from labjack import ljm
import logging
import pathlib

# add the wsp directory to the PATH
wsp_path = os.path.dirname(os.getcwd())
sys.path.insert(1, wsp_path)

# winter modules
from utils import utils



def setup_logger(base_dir, config):
    """
    The names of the log file and path are specified in config.yaml:
        # where to put the log. base directory is home
        log_directory: 'data/log'
        log_link_directory: 'data'
        log_link_name: 'winter.log'
    
    
    Note that in the earlier version i had night computed with utils.night()
    in wsp, and then passed in "night" and logname (eg. 'testlog') also
    """
    ###
    ## create the log directory
    log_dir = os.getenv("HOME") + '/' + config['log_directory']
    
    night = utils.night()
    
    logname = night + '.log'
    logpath = log_dir + '/' + logname
    
    # create the directory and filenames for the data storage
    link_dir = os.getenv("HOME") + '/' + config['log_link_directory']
    link_name = config['log_link_name']
    linkpath = link_dir + '/' + link_name
    
    # create the data directory if it doesn't exist already
    pathlib.Path(log_dir).mkdir(parents = True, exist_ok = True)
    print(f'logger: making directory: {log_dir}')
            
    # create the data link directory if it doesn't exist already
    pathlib.Path(link_dir).mkdir(parents = True, exist_ok = True)
    print(f'logger: making directory: {link_dir}')
    

    #/* make a symbolic link so the log is easy to find
    print(f'logger: trying to create link at {linkpath}')
    
    try:
        os.symlink(logpath, linkpath)
    except FileExistsError:
        print('logger: deleting existing symbolic link')
        os.remove(linkpath)
        os.symlink(logpath, linkpath)
    
    ###
    fmt = "%(asctime)s.%(msecs).03d [%(filename)s:%(lineno)s - %(funcName)s()] %(levelname)s: %(threadName)s: %(message)s"
    datefmt = "%Y-%m-%d  %H:%M:%S"
    print(f'logger: setting up log at {logpath}')
    logger = logging.getLogger(logname)
    formatter = logging.Formatter(fmt,datefmt=datefmt)
    formatter.converter = time.gmtime

    fileHandler = logging.FileHandler(logpath, mode='a')
    fileHandler.setFormatter(formatter)

    #console = logging.StreamHandler()
    #console.setFormatter(formatter)
    #console.setLevel(logging.INFO)
    
    # add a separate logger for the terminal (don't display debug-level messages)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(fileHandler)
    #logger.addHandler(console)
    
    return logger


