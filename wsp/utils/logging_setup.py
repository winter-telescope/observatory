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
# from labjack import ljm
import logging
import os

# from datetime import datetime
# from PyQt5 import uic, QtCore, QtGui, QtWidgets
import pathlib
import sys

# import numpy as np
import time

# import pathlib
"""
# add the wsp directory to the PATH
wsp_path = os.path.dirname(os.getcwd())
sys.path.insert(1, wsp_path)
"""
# add the wsp directory to the PATH
wsp_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(1, wsp_path)
if __name__ == "__main__":
    print(f"wsp_path = {wsp_path}")


# winter modules
from utils import utils


def sayHello():
    return "Hello!"


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
    log_dir = os.path.join(os.path.expanduser("~"), config["log_directory"])

    # night = utils.tonight()
    night = utils.tonight()

    logname = night + ".log"
    logpath = log_dir + "/" + logname

    # create the directory and filenames for the data storage
    link_dir = os.path.join(os.path.expanduser("~"), config["log_link_directory"])
    link_name = config["log_link_name"]
    linkpath = link_dir + "/" + link_name

    # create the data directory if it doesn't exist already
    pathlib.Path(log_dir).mkdir(parents=True, exist_ok=True)
    print(f"logger: making directory: {log_dir}")

    # create the data link directory if it doesn't exist already
    pathlib.Path(link_dir).mkdir(parents=True, exist_ok=True)
    print(f"logger: making directory: {link_dir}")

    # /* make a symbolic link so the log is easy to find
    print(f"logger: trying to create link at {linkpath}")

    try:
        os.symlink(logpath, linkpath)
    except FileExistsError:
        print("logger: deleting existing symbolic link")
        os.remove(linkpath)
        os.symlink(logpath, linkpath)

    ###
    fmt = "%(asctime)s.%(msecs).03d [%(filename)s:%(lineno)s - %(funcName)s()] %(levelname)s: %(threadName)s: %(message)s"
    datefmt = "%Y-%m-%d  %H:%M:%S"
    print(f"logger: setting up log at {logpath}")

    logger = logging.getLogger(logname)

    # if there are no handlers, then add one, otherwise leave it alone!
    """
    creating tons of handlers will result in each one making a redundant log entry
    running this from different python consoles will result in new handlers for each consol.
    That is okay. Running multiple scripts from a single console (eg spyder) will result in finding
    the already created handlers and will skip making a new one. This is good!
    """
    print(f"Found {len(logger.handlers)} FileHandlers")
    print(f"FileHandlers = {logger.handlers}")
    if len(logger.handlers) == 0:
        print(f"No handlers. Adding one...")
        formatter = logging.Formatter(fmt, datefmt=datefmt)
        # Use UTC
        # formatter.converter = time.gmtime
        # Use local time
        formatter.converter = time.localtime

        fileHandler = logging.FileHandler(logpath, mode="a")
        fileHandler.setFormatter(formatter)
        fileHandler.setLevel(logging.DEBUG)
        # add a separate logger for the terminal (don't display debug-level messages)
        logger.setLevel(logging.DEBUG)
        logger.addHandler(fileHandler)

    return logger


if __name__ == "__main__":
    # test out the logger setup
    # load the config
    base_directory = wsp_path
    config_file = base_directory + "/config/config.yaml"
    config = utils.loadconfig(config_file)
    logger = setup_logger(base_directory, config)

    logger.info("Testing out the logger")
