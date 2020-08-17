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
from command import wintercmd
from command import commandParser
from housekeeping import weather
from housekeeping import housekeeping
from dome import dome
from schedule import schedule
from schedule import ObsWriter
from utils import utils

# Create the control class -- it inherets from QObject
# this is basically the "main" for the console application
class control(QtCore.QObject):

    ## Initialize Class ##
    def __init__(self,mode,config,base_directory, logger, parent = None):
        super(control, self).__init__(parent)

        # pass in the config
        self.config = config

        # pass in the logger
        self.logger = logger

        # pass in the base directory
        self.base_directory = base_directory

        ### SET UP THE HARDWARE ###

        # init the telescope
        self.telescope = pwi4.PWI4(host = self.config['telescope']['host'], port = self.config['telescope']['port'])


        # init the weather
        try:
            print('control: trying to load weather')
            self.weather = weather.palomarWeather(self.base_directory,config = self.config, logger = self.logger)
        except Exception as e:
            self.weather = None
            print("control: could not load weather data: ", e)

        #init the scheduler
        self.schedule = schedule.Schedule(base_directory = self.base_directory, date = 'today')

        ## init the database writer
        self.writer = ObsWriter.ObsWriter('demoRelational', self.base_directory) #the ObsWriter initialization



        ### SET UP THE COMMAND LINE INTERFACE
        self.wintercmd = wintercmd.Wintercmd(self.config, self.telescope, self.logger, self.schedule, self.writer)

        #init the schedule executor
        self.scheduleExec = commandParser.schedule_executor(self.telescope, self.schedule, self.writer, self.logger)

        # init the cmd executor
        self.cmdexecutor = commandParser.cmd_executor(self.telescope, self.wintercmd, self.logger, self.scheduleExec)

        # init the cmd prompt
        self.cmdprompt = commandParser.cmd_prompt(self.telescope, self.wintercmd)

        #init the schedule executor
        self.scheduleExec = commandParser.schedule_executor(self.telescope, self.schedule, self.writer, self.logger)

        # connect the new command signal to the executors
        self.cmdprompt.newcmd.connect(self.cmdexecutor.add_to_queue)
        self.cmdprompt.newcmd.connect(self.scheduleExec.interrupt)


        if mode == 0:
            self.scheduleExec.start()

        ### SET UP THE HOUSEKEEPING ###

        if mode == 1:
        # init the housekeeping class (this starts the daq and dirfile write loops)
            self.hk = housekeeping.housekeeping(self.config,
                                                telescope = self.telescope,
                                                weather = self.weather)

        ### START UP THE OBSERVATION SEQUENCE ###
        """
        # Startup the Telescope
        try:
            print("control: trying to init telescope")
            self.telescope_connect()
            self.telescope_axes_enable()
            #self.telescope_home()
            random_alt = np.random.randint(16,89)
            random_az = np.random.randint(1,359)
            self.telescope_mount.mount_goto_alt_az(random_alt, random_az)
        except Exception as e:
            self.telescope_mount = None
            print("control: could not connect to telescope mount: ")

        """






    """
    # commands that are useful
    def telescope_startup(self):
        telescope.telescope_startup(self.telescope_mount)
    def telescope_home(self):
        telescope.home(self.telescope_mount)
    def telescope_axes_enable(self):
        telescope.axes_enable(self.telescope_mount)
    def telescope_connect(self):
        telescope.connect(self.telescope_mount)
    def telescope_disconnect(self):
        telescope.disconnect(self.telescope_mount)
    def telescope_axes_disable(self):
        telescope.axes_disable(self.telescope_mount)
    def telescope_shutdown(self):
        telescope.shutdown(self.telescope_mount)

    """
