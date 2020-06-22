#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jan 27 16:13:17 2020

systemControl.py

This file is part of wsp

# PURPOSE #
This module is the interface for all observing modes to command the various
parts of the instrument including
    - telescope
    - power systems
    - stepper motors
    

@author: nlourie
"""
# system packages
import sys
import os
import numpy as np
import time
import signal
from PyQt5 import uic, QtCore, QtGui, QtWidgets

# add the wsp directory to the PATH
wsp_path = os.path.dirname(os.getcwd())
sys.path.insert(1, wsp_path)

# winter modules
from power import power
from telescope import pwi4
from telescope import telescope
from command import commandServer_multiClient
from housekeeping import weather
from housekeeping import housekeeping
from dome import dome
from schedule import schedule
from utils import utils

def sigint_handler(*args):
    """
    Make the thing die when you do ctl+c
    Source:
        https://stackoverflow.com/questions/19811141/make-qt-application-not-to-quit-when-last-window-is-closed
    """
    
    """Handler for the SIGINT signal."""
    sys.stderr.write('\r')
    qb = QtWidgets.QMessageBox()
    qb.raise_()
    """
    if qb.question(None, '', "Are you sure you want to quit?",
                            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                            QtWidgets.QMessageBox.No) == QtWidgets.QMessageBox.Yes:
        QtWidgets.QApplication.quit()
        print("Okay... quitting.")
    else:
        pass
    """
    ans = qb.question(None, '', "Are you sure you want to quit?",
                            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                            QtWidgets.QMessageBox.No)
    
    if ans== QtWidgets.QMessageBox.Yes:
        QtWidgets.QApplication.quit()
        print("Okay... quitting.")
    else:
        pass

# create the control class

class control(QtWidgets.QMainWindow):
    

    ## Initialize Class ##
    def __init__(self,mode,config_file,base_directory, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.config_file = config_file
        self.base_directory = base_directory
        self.oktoobserve = False # Start it out by saying you shouldn't be observing

        # Define the Dome Class
        self.dome = dome.dome()
        
        # Start the Housekeeping Loops
        self.hk_slow = housekeeping.slowLoop(dome = self.dome)
        self.hk_slow.start()
        
        # Start up the Command Server
        
        
if __name__ == '__main__':
    signal.signal(signal.SIGINT, sigint_handler)    
    print('Executing Program')
    opt = 0
    base_directory = wsp_path
    config_file = ''
    # Standard way to start up the event loop in GUI mode
    app = QtWidgets.QApplication([])
    app.setQuitOnLastWindowClosed(False) #<-- otherwise it will quit once all windows are closed
    
    winter = control(mode = int(opt), config_file = '',base_directory = wsp_path)
    app.exec_()
    
    #plt.show()
    