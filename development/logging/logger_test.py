#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jul  8 12:06:47 2020

logger_test.py

This is a test script to test out how the python logger library works

Bit of this are stolen graciously from minerva: 
    https://github.com/MinervaCollaboration/minerva-control/blob/master/minerva_library/utils.py

@author: nlourie
"""
import time
import logging
import os
import datetime


def update_logger_path(logger, newpath):
    fmt = "%(asctime)s.%(msecs).03d [%(filename)s:%(lineno)s - %(funcName)s()] %(levelname)s: %(threadName)s: %(message)s"
    datefmt = "%Y-%m-%dT%H:%M:%S"
    formatter = logging.Formatter(fmt,datefmt=datefmt)
    formatter.converter = time.gmtime

    for fh in logger.handlers: logger.removeHandler(fh)
    fh = logging.FileHandler(newpath, mode='a')
    fh.setFormatter(formatter)
    logger.addHandler(fh)

def setup_logger(base_dir, night, logger_name):

    path = base_dir + '/log/' + night

    if os.path.exists(path) == False:
        # use makedirs instead of mkdir because it makes any needed intermediary directories
        os.makedirs(path)
        
    fmt = "%(asctime)s.%(msecs).03d [%(filename)s:%(lineno)s - %(funcName)s()] %(levelname)s: %(threadName)s: %(message)s"
    datefmt = "%Y-%m-%d  %H:%M:%S"

    logger = logging.getLogger(logger_name)
    formatter = logging.Formatter(fmt,datefmt=datefmt)
    formatter.converter = time.gmtime

    fileHandler = logging.FileHandler(path + '/' + logger_name + '.log', mode='a')
    fileHandler.setFormatter(formatter)

    console = logging.StreamHandler()
    console.setFormatter(formatter)
    console.setLevel(logging.INFO)
    
    # add a separate logger for the terminal (don't display debug-level messages)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(fileHandler)
    logger.addHandler(console)
    
    return logger


def night():
    today = datetime.datetime.utcnow()
    if datetime.datetime.now().hour >= 10 and datetime.datetime.now().hour <= 16:
        today = today + datetime.timedelta(days=1)
    return 'n' + today.strftime('%Y%m%d')

####

base_dir = os.getcwd()
night = night()
logger = setup_logger(base_dir, night, logger_name = 'logtest')

logger.info('info from program')
#%%
thing = 'fart'
logger.debug(f'debug from program thing = {thing}')
logger.warning('warning from program')