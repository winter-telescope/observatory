#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
wsp: the WINTER Supervisor Program

This file is part of wsp

# PURPOSE #
This program is the top-level control loop which runs operations for the
WINTER instrument. 



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
wsp_path = os.getcwd()
sys.path.insert(1, wsp_path)

# winter modules
from power import power
from telescope import pwi4
from telescope import telescope
from control import systemControl
from command import commandServer_multiClient
from housekeeping import easygetdata
from control import systemControl_threaded


def sigint_handler(*args):
    """Handler for the SIGINT signal."""
    sys.stderr.write('\r')
    QtCore.QCoreApplication.quit()

if __name__ == "__main__":
    signal.signal(signal.SIGINT, sigint_handler)
    app = QtCore.QCoreApplication(sys.argv)

    # load the config
    config_file = wsp_path + '/config/config.yaml'
    config = yaml.load(open(config_file), Loader = yaml.FullLoader)
    
    # get the mode flag
    opt = 1
    
    # instatiate the control (ie main) class
    #TODO port this to the real systemControl instead
    winter = systemControl_threaded.control(mode = int(opt), config = config, base_directory = wsp_path)

    # Run the interpreter every so often to catch SIGINT
    timer = QtCore.QTimer()
    timer.start(500) 
    timer.timeout.connect(lambda: None) 

    sys.exit(app.exec_())