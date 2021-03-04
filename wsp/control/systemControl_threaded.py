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
import Pyro5.client

# add the wsp directory to the PATH
wsp_path = os.path.dirname(os.getcwd())
sys.path.insert(1, wsp_path)

# winter modules
from power import power
from telescope import pwi4
from telescope import telescope
#from command import commandServer_multiClient
from command import commandServer
from command import wintercmd
from command import commandParser
from housekeeping import housekeeping
from dome import dome
from schedule import schedule
from schedule import ObsWriter
from utils import utils
from power import power
from housekeeping import local_weather

# Create the control class -- it inherets from QObject
# this is basically the "main" for the console application
class control(QtCore.QObject):

    ## Initialize Class ##
    def __init__(self,mode,config,base_directory, logger, parent = None):
        super(control, self).__init__(parent)
        
        print(f'control: base_directory = {base_directory}')


        # pass in the config
        self.config = config
        # pass in the logger
        self.logger = logger
        # pass in the base directory
        self.base_directory = base_directory

        ### SET UP THE HARDWARE ###
        # init the network power supply
        try:
            self.pdu1 = power.PDU('pdu1.ini',base_directory = self.base_directory)

        except Exception as e:
            self.logger.warning(f"control: could not init NPS at pdu1, {type(e)}: {e}")


        # init the telescope
        self.telescope = telescope.Telescope(host = self.config['telescope']['host'], port = self.config['telescope']['port'])

        # # init the weather(Old way)
        # try:
        #     self.logger.info('control: trying to load weather')
        #     print('control: trying to load weather')
        #     self.weather = weather.palomarWeather(self.base_directory,config = self.config, logger = self.logger)
        # except Exception as e:
        #     self.weather = None
        #     self.logger.warning(f"control: could not load weather data: {e}")
        #     print(f"control: could not load weather data: {e}")

        """
        #init the weather
        try:
            self.weather = Pyro5.client.Proxy("PYRONAME:weather")
            self.weather.startWeather(base_directory = self.base_directory)
            self.logger.error('weather connect succesful')
        except Exception as e:
            self.logger.error('weather connect failed', exc_info=True )
        """
        
        # init the weather by creating a local object that interfaces with the remote object from the weather daemon
        
        self.weather = local_weather.Weather(self.base_directory, config = self.config, logger = self.logger)
        
        
        #init the scheduler
        self.schedule = schedule.Schedule(base_directory = self.base_directory, config = self.config, date = 'today')
        ## init the database writer
        self.writer = ObsWriter.ObsWriter('WINTER_ObsLog', self.base_directory) #the ObsWriter initialization


        ### SET UP THE HOUSEKEEPING ###

        # if mode == 1:
        # init the housekeeping class (this starts the daq and dirfile write loops)
        self.hk = housekeeping.housekeeping(self.config,
                                                base_directory = self.base_directory,
                                                mode = mode,
                                                telescope = self.telescope,
                                                weather = self.weather,
                                                schedule = self.schedule)
        
        print(f'control: is it okay to observe? val = {self.weather.ok_to_observe}')


        '''
        In this section we set up the appropriate command interface and executors for the chosen mode
        '''
        ### SET UP THE COMMAND LINE INTERFACE
        if mode in 's':
            #self.wintercmd = wintercmd.ScheduleCmd(self.config, self.hk.state, self.telescope, self.logger)
            self.wintercmd = wintercmd.Wintercmd(self.config, self.hk.state, self.telescope, self.logger)
            #init the schedule executor
            self.scheduleExec = commandParser.schedule_executor(self.config, self.hk.state, self.telescope, self.wintercmd, self.schedule, self.writer, self.logger)
            # init the cmd executor
            self.cmdexecutor = commandParser.cmd_executor(self.telescope, self.wintercmd, self.logger, self.scheduleExec)

            # init the cmd prompt
            self.cmdprompt = commandParser.cmd_prompt(self.telescope, self.wintercmd)


            # connect the new command signal to the executors
            self.cmdprompt.newcmd.connect(self.cmdexecutor.add_to_queue)
            self.scheduleExec.newcmd.connect(self.cmdexecutor.add_to_queue)
        else:
            self.wintercmd = wintercmd.Wintercmd(self.config, self.hk.state, self.telescope, self.logger)
            #self.wintercmd = wintercmd.ManualCmd(self.config, self.hk.state, self.telescope, self.logger)

            # init the cmd executor
            self.cmdexecutor = commandParser.cmd_executor(self.telescope, self.wintercmd, self.logger)

            # init the cmd prompt
            self.cmdprompt = commandParser.cmd_prompt(self.telescope, self.wintercmd)
            # connect the new command signal to the executors
            self.cmdprompt.newcmd.connect(self.cmdexecutor.add_to_queue)

            # set up the command server which listens for command requests of the network
            self.commandServer = commandServer.server_thread(self.config['wintercmd_server_addr'], self.config['wintercmd_server_port'], self.logger, self.config)
            # connect the command server to the command executor
            self.commandServer.newcmd.connect(self.cmdexecutor.add_to_queue)


        ## Not loving this approach at the moment, trying something else
        # if mode == 0:
        #     self.cmdprompt.newcmd.connect(self.scheduleExec.stop)



        if mode == 's':
            self.scheduleExec.start()














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
