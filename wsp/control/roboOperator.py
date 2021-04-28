#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Apr 27 22:56:08 2021

operator.py

@author: nlourie
"""


import os
import numpy as np
import sys
from datetime import datetime
from PyQt5 import QtCore
import time
import json
import logging
# add the wsp directory to the PATH
wsp_path = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(1, wsp_path)

from utils import utils
from command import wintercmd


class RoboOperatorThread(QtCore.QThread):
    """
    A dedicated thread to handle all the robotic operations!
    
    This is basically a thread to handle all the commands which get sent in 
    robotic mode
    """
    
    def __init__(self, base_directory, config, state, wintercmd, telescope, dome, chiller, logger):
        super(QtCore.QThread, self).__init__()
        
        self.base_directory = base_directory
        self.config = config
        self.state = state
        self.wintercmd = wintercmd
        self.telescope = telescope
        self.dome = dome
        self.chiller = chiller
        self.logger = logger
        
    
    def run(self):    
        
        
        self.operator = RoboOperator(base_directory = self.base_directory, 
                                     config = self.config, 
                                     state = self.state, 
                                     wintercmd = self.wintercmd,
                                     telescope = self.telescope, 
                                     dome = self.dome, 
                                     chiller = self.chiller, 
                                     logger = self.logger)
        
        # Put all the signal/slot connections here:
        
            
        # Start the event loop
        self.exec_()

class roboError(object):
    """
    This is a class used to broadcast errors as pyqtSignals.
    The idea is that this will be caught elsewhere by the system monitor
    which can try to reboot or otherwise handle these errors.
    
    cmd:    the command that the roboOperator was trying to execute, eg 'dome_home'
    system: the system that the command involves, eg 'chiller'. this is used for rebooting
    err:    whatever error message goes along with this error
    """
    
    def __init__(self, context, cmd, system, msg):
        self.context = context
        self.cmd = cmd
        self.system = system
        self.msg = msg
        
class RoboOperator(QtCore.QObject):

    hardware_error = QtCore.pyqtSignal(object)    

    def __init__(self, base_directory, config, state, wintercmd, telescope, dome, chiller, logger = None):
        super(RoboOperator, self).__init__()
        
        self.base_directory = base_directory
        self.config = config
        self.state = state
        self.wintercmd = wintercmd
        self.telescope = telescope
        self.dome = dome
        self.chiller = chiller
        self.logger = logger
        self.lastcmd = None
        
        # some variables that hold the state of the sequences
        self.startup_complete = False
        self.calibration_complete = False
        
        self.restart_robo()
        
    def restart_robo(self):
        if not self.startup_complete:
            # Do the startup routine
            self.do_startup()
            # If that didn't work, then return
            if not self.startup_complete:
                return
        
        # if we're done with the startup, continue
        if not self.calibration_complete:
            # do the calibration:
            self.do_calibration()
            # If that didn't work, then return
            if not self.calibration_complete:
                return
        
        # if we can open up the dome, then do it!
        if self.dome.ok_to_open:
            self.doTry('dome_open', context = 'startup', system = 'dome')
            
        else:
            self.wait_for_dome_clearance()
    
        # if the dome is open, then start the observing loop!
        
    
    def log(self, msg, level = logging.INFO):
        if self.logger is None:
                print(msg)
        else:
            self.logger.log(level = level, msg = msg)
    
    
    def doTry(self, cmd, context = None, system = None):
        """
        This does the command by calling wintercmd.parse.
        The command should be written the same way it would be from the command line
        The system is specified so that alert signals can be broadcast out to various 
        """
        

        self.lastcmd = cmd
        try:
            self.wintercmd.parse(cmd)
        
        except Exception as e:
            msg = f'roboOperator: could not execute function {cmd} due to {e.__class__.__name__}, {e}'
            self.log(msg)
            err = roboError(cmd, system, msg)
            self.hardware_error.emit(err)
        
    
    def do(self, cmd):
        """
        This does the command by calling wintercmd.parse.
        The command should be written the same way it would be from the command line
        The system is specified so that alert signals can be broadcast out to various 
        """
        self.lastcmd = cmd
        self.wintercmd.parse(cmd)

    def wait_for_dome_clearance(self):
        """
        This should just run a QTimer which waits until one of several 
        things happens:
            1. the dome is okay to open. then it will restart_robo()
            2. the sun will come up and we'll miss our window. in this case,
               initiate shutdown
        """
        pass
    
    def do_startup(self):
        # this is for passing to errors
        context = 'do_startup'
        
        ### DOME SET UP ###
        system = 'dome'
        try:
            # take control of dome        
            self.do('dome_takecontrol')
    
            # home the dome
            self.do('dome_home')
        
        except Exception as e:
            msg = f'roboOperator: could not set up {system} due to {e.__class__.__name__}, {e}'
            self.log(msg)
            err = roboError(context, self.lastcmd, system, msg)
            self.hardware_error.emit(err)
            return
        
        ### MOUNT SETUP ###
        system = 'telescope'
        try:
            # connect the telescope
            self.do('mount_startup')
        
        except Exception as e:
            msg = f'roboOperator: could not set up {system} due to {e.__class__.__name__}, {e}'
            self.log(msg)
            err = roboError(context, self.lastcmd, system, msg)
            self.hardware_error.emit(err)
            return
        
        
        # if we made it all the way to the bottom, say the startup is complete!
        self.startup_complete = True
            
        
        
    def do_calibration(self):
        
        context = 'do_calibration'
        
        ### Take darks ###
        # Nothing here yet
        
        
        self.calibration_complete = True
        