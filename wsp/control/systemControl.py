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
import yaml

# add the wsp directory to the PATH
wsp_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(1, wsp_path)
print(f'control: wsp_path = {wsp_path}')

# winter modules
from power import power
#from telescope import pwi4
from telescope import telescope
#from command import commandServer_multiClient
from command import commandServer
from command import wintercmd
from command import commandParser
from housekeeping import housekeeping
from dome import dome
from schedule import schedule
#from schedule import ObsWriter
#from utils import utils
#from power import power
#from housekeeping import local_weather
from daemon import daemon_utils
from daemon import test_daemon_local
#from dome import dome
from chiller import chiller
#from routines import schedule_executor
from control import roboOperator
from ephem import ephem
from alerts import alert_handler

# Create the control class -- it inherets from QObject
# this is basically the "main" for the console application
class control(QtCore.QObject):
    
    newcmd = QtCore.pyqtSignal(object)
    newcmdRequest = QtCore.pyqtSignal(object)
    
    ## Initialize Class ##
    def __init__(self,mode,config,base_directory, logger, opts = None, parent = None):
        super(control, self).__init__(parent)
        
        print(f'control: base_directory = {base_directory}')
        self.opts = opts
    
        # pass in the config
        self.config = config
        # pass in the logger
        self.logger = logger
        # pass in the base directory
        self.base_directory = base_directory
        
        
        
        ### ADD HARDWARE DAEMONS TO THE DAEMON LAUNCHER ###
        # init the list of hardware daemons
        
        # Cleanup (kill any!) existing instances of the daemons running
        daemons_to_kill = ['pyro5-ns', 'domed.py', 'chillerd.py', 'test_daemon.py','dome_simulator_gui.py','ephemd.py','dirfiled.py']
        daemon_utils.cleanup(daemons_to_kill)
        
        
        self.daemonlist = daemon_utils.daemon_list()
        
        if mode in ['r','i','m']:
            # ALL MODES
            
            ###### DAEMONS #####
            # start the name server using subprocess
            # Note: there are other ways to do this, but this enforces that the name server is a child process that will be killed if wsp dies
            # check if the nameserver is already running. if so, don't add to daemon_list. if not, add it and launch.
            try:
                nameserverd = Pyro5.core.locate_ns()
            
            except:
                # the nameserver is not running
                print(f'control: nameserver not already running. starting from wsp')
                nameserverd = daemon_utils.PyDaemon(name = 'pyro_ns', filepath = "pyro5-ns", python = False)
                self.daemonlist.add_daemon(nameserverd)
            
            # test daemon
            self.testd = daemon_utils.PyDaemon(name = 'test', filepath = f"{wsp_path}/daemon/test_daemon.py")
            self.daemonlist.add_daemon(self.testd)
            
            # chiller daemon
            self.chillerd = daemon_utils.PyDaemon(name = 'chiller', filepath = f"{wsp_path}/chiller/chillerd.py")#, args = ['-v'])
            self.daemonlist.add_daemon(self.chillerd)
            
            # housekeeping data logging daemon (hkd = housekeeping daemon)
            self.hkd = daemon_utils.PyDaemon(name = 'hkd', filepath = f"{wsp_path}/housekeeping/dirfiled.py")
            self.daemonlist.add_daemon(self.hkd)
            
        if mode in ['r','m']:
            # OBSERVATORY MODES (eg all but instrument)
            
            ###### DAEMONS #####
            # Dome Daemon
            self.domed = daemon_utils.PyDaemon(name = 'dome', filepath = f"{wsp_path}/dome/domed.py", args = opts)
            self.daemonlist.add_daemon(self.domed)
            
            if '--domesim' in opts:
                # start up the fake dome as a daemon
                self.domesim = daemon_utils.PyDaemon(name = 'dome_simulator', filepath = f"{wsp_path}/dome/dome_simulator_gui.py")
                self.daemonlist.add_daemon(self.domesim)
        
            # ephemeris daemon
            #TODO: pass opts? ignore for now. don't need it running in verbose mode
            self.ephemd = daemon_utils.PyDaemon(name = 'ephem', filepath = f"{wsp_path}/ephem/ephemd.py")
            self.daemonlist.add_daemon(self.ephemd)
            
            
            
        # Launch all hardware daemons
        self.daemonlist.launch_all()
        
        
        
        ### SET UP THE HARDWARE ###
        # note we always want to set this all up. we just won't try to update the state later on if we're not running certain daemons
        # we'll run into trouble down the line if some of these attributes don't exist
        
        # init the network power supply
        try:
            self.pdu1 = power.PDU('pdu1.ini',base_directory = self.base_directory)

        except Exception as e:
            self.logger.warning(f"control: could not init NPS at pdu1, {type(e)}: {e}")

        # init the test object (goes with the test_daemon)
        self.counter =  test_daemon_local.local_counter(wsp_path)     

        # init the telescope
        self.telescope = telescope.Telescope(config = self.config, host = self.config['telescope']['host'], port = self.config['telescope']['port'])

        
        # init the dome
        self.dome = dome.local_dome(base_directory = self.base_directory, config = self.config)

        # init the chiller
        self.chiller = chiller.local_chiller(base_directory = self.base_directory, config = self.config)
        
        # init the ephemeris
        self.ephem = ephem.local_ephem(base_directory = self.base_directory, config = self.config)
        
        # init the weather by creating a local object that interfaces with the remote object from the weather daemon
        
        #self.weather = local_weather.Weather(self.base_directory, config = self.config, logger = self.logger)
        self.weather = 'placeholder'
        
        # init the schedule. put it here so it can be passed into housekeeping
        self.schedule = schedule.Schedule(base_directory = self.base_directory, config = self.config, logger = self.logger)

        # init the alert handler
        auth_config  = yaml.load(open(os.path.join(wsp_path,self.config['alert_handler']['auth_config_file'] )) , Loader = yaml.FullLoader)
        user_config  = yaml.load(open(os.path.join(wsp_path,self.config['alert_handler']['user_config_file'] )) , Loader = yaml.FullLoader)
        alert_config = yaml.load(open(os.path.join(wsp_path,self.config['alert_handler']['alert_config_file'])) , Loader = yaml.FullLoader)

        self.alertHandler = alert_handler.AlertHandler(user_config, alert_config, auth_config)
        if mode == 'r':
            # send a signal that we've started up wsp!
            self.alertHandler.slack_log(f':futurama-bender-robot::telescope: *Starting WSP in Robotic Mode!*')
        """
        # NPL: 4-29-21: moving the schedule stuff over to the roboOperator.
        #init the scheduler
        self.schedule = schedule.Schedule(base_directory = self.base_directory, config = self.config, logger = self.logger, date = 'today')
        ## init the database writer
        self.writer = ObsWriter.ObsWriter('WINTER_ObsLog', self.base_directory, config = self.config, logger = self.logger) #the ObsWriter initialization
        """

        ### SET UP THE HOUSEKEEPING ###

        # if mode == 1:
        # init the housekeeping class (this starts the daq and dirfile write loops)
        self.hk = housekeeping.housekeeping(self.config,
                                                base_directory = self.base_directory,
                                                mode = mode,
                                                schedule = self.schedule,
                                                telescope = self.telescope,
                                                dome = self.dome,
                                                weather = self.weather,
                                                chiller = self.chiller,
                                                counter = self.counter,
                                                ephem = self.ephem)
        
        
        self.pyro_thread = daemon_utils.PyroDaemon(obj = self.hk, name = 'state')
        self.pyro_thread.start()
        
        '''
        In this section we set up the appropriate command interface and executors for the chosen mode
        '''
        ### SET UP THE COMMAND LINE INTERFACE
        self.wintercmd = wintercmd.Wintercmd(self.base_directory, self.config, state = self.hk.state, daemonlist = self.daemonlist, telescope = self.telescope, dome = self.dome, chiller = self.chiller, logger = self.logger)
        
        if mode in ['r','m']:
            #init the schedule executor
            #self.scheduleExec = schedule_executor.schedule_executor(self.config, self.hk.state, self.telescope, self.wintercmd, self.schedule, self.writer, self.logger)
            pass
        """
        #NPL 4-27-21: commenting out this listener stuff. I don't think it's used anymore
            listener = self.scheduleExec
        else:
            listener = None
        """
        # init the command executor
        self.cmdexecutor = commandParser.cmd_executor(telescope = self.telescope, wintercmd = self.wintercmd, logger = self.logger)#, listener = listener)
        
        # init the command prompt
        self.cmdprompt = commandParser.cmd_prompt(self.telescope, self.wintercmd)        
        
        # connect the new command signal to the command executor
        self.cmdprompt.newcmd.connect(self.cmdexecutor.add_cmd_request_to_queue)
        # signal for if main wants to execute a raw cmd (same format as terminal). 
        self.newcmd.connect(self.cmdexecutor.add_cmd_to_queue)
        # signal for if main wants to execute a command request
        self.newcmdRequest.connect(self.cmdexecutor.add_cmd_request_to_queue)
        
        
        # connect the new schedule command to the command executor
        if mode in ['r','m']:
            #self.scheduleExec.newcmd.connect(self.cmdexecutor.add_cmd_request_to_queue)
            self.roboThread = roboOperator.RoboOperatorThread(self.base_directory, self.config, mode = mode, state = self.hk.state, wintercmd = self.wintercmd, logger = self.logger, alertHandler = self.alertHandler, schedule = self.schedule, telescope = self.telescope, dome = self.dome, chiller = self.chiller, ephem = self.ephem)
        # set up the command server which listens for command requests of the network
        self.commandServer = commandServer.server_thread(self.config['wintercmd_server_addr'], self.config['wintercmd_server_port'], self.logger, self.config)
        # connect the command server to the command executor
        self.commandServer.newcmd.connect(self.cmdexecutor.add_cmd_request_to_queue)
        # connect the wintercmd newRequest signal to the cmd executor
        self.wintercmd.newCmdRequest.connect(self.cmdexecutor.add_cmd_request_to_queue)
        
        
        ##### START SCHEDULE EXECUTOR #####
        if mode in ['r','m']:
            #self.scheduleExec.start()
            self.roboThread.start()
            # Now execute a list of commands
            """cmdlist = ['mount_connect', 'mount_az_on', 'mount_alt_on', 'mount_home','mount_goto_alt_az 35 38.5']
            self.logger.info(f'control: trying to add a list of commands to the cmd executor')
            self.newcmd.emit(cmdlist)"""





        
        
        ### Old deprecated stuff staged for deletion:

        """
        if mode in 's':
            
            #init the schedule executor
            self.scheduleExec = commandParser.schedule_executor(self.config, self.hk.state, self.telescope, self.wintercmd, self.schedule, self.writer, self.logger)
            # init the cmd executor
            listener = self.scheduleExec
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
        """

        ## Not loving this approach at the moment, trying something else
        # if mode == 0:
        #     self.cmdprompt.newcmd.connect(self.scheduleExec.stop)





       






