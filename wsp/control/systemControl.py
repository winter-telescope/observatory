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
import Pyro5.nameserver
import yaml

# add the wsp directory to the PATH
wsp_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(1, wsp_path)
print(f'control: wsp_path = {wsp_path}')

# winter modules
#from power import power
#from telescope import pwi4
from telescope import telescope
from telescope import mirror_cover 
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
from chiller import small_chiller
#from routines import schedule_executor
from control import roboOperator
from ephem import ephem
from alerts import alert_handler
#from viscam import web_request
from viscam import viscam
from viscam import ccd
from power import powerManager
from housekeeping import labjack_handler_local
from camera import camera


# Create the control class -- it inherets from QObject
# this is basically the "main" for the console application
class control(QtCore.QObject):
    
    newcmd = QtCore.pyqtSignal(object)
    newcmdRequest = QtCore.pyqtSignal(object)
    
    ## Initialize Class ##
    def __init__(self,mode,config,base_directory, logger, opts = None, parent = None):
        super(control, self).__init__(parent)
        
        print(f'control: base_directory = {base_directory}')
        print(f'MODE = {mode}')
        self.opts = opts
    
        # pass in the config
        self.config = config
        # pass in the logger
        self.logger = logger
        # pass in the base directory
        self.base_directory = base_directory
        
        print(f'\nsystemControl: running with opts = {opts}')
        
        
        
        ### ADD HARDWARE DAEMONS TO THE DAEMON LAUNCHER ###
        # init the list of hardware daemons
        
        # Cleanup (kill any!) existing instances of the daemons running
        daemons_to_kill = [#'ns_daemon', 
                           'ccd_daemon.py' ,
                           'viscamd.py',
                           'domed.py', 
                           'chillerd.py', 
                           'small_chillerd.py', 
                           'test_daemon.py',
                           'dome_simulator_gui.py',
                           'ephemd.py', 
                           'dirfiled.py',
                           'roboManagerd.py',
                           'sun_simulator.py',
                           'powerd.py',
                           'labjackd.py',
                           ]
        daemon_utils.cleanup(daemons_to_kill)
        
        # make the list that will hold all the daemon process we launch
        self.daemonlist = daemon_utils.daemon_list()

        
        # clean out any found entries if the nameserver is still running
        # ALL MODES
        
        ###### DAEMONS #####
        # start the name server using subprocess
        # Note: there are other ways to do this, but this enforces that the name server is a child process that will be killed if wsp dies
        # check if the nameserver is already running. if so, don't add to daemon_list. if not, add it and launch.
        
        # first, figure out what nameserver address to use
        for currentArgument, currentValue in opts:
            if currentArgument in ("-n", "--ns_host"):
                self.ns_host = currentValue
                print(f'ns_host = {self.ns_host}')
            else:
                self.ns_host = self.config['pyro5_ns_default_addr']
            
            if currentArgument in ("-v", "--verbose"):
                self.verbose = True
            else:
                self.verbose = False
            
        
        try:
            nameserverd = Pyro5.core.locate_ns(host = self.ns_host)
            '''
            # Don't think I need to do this...
            try:
                # unregister all the entries
                entrylist = list(nameserverd.list().keys())[1:]
                print(f'entries in pyro5 nameserver: {entrylist}')
                for name in entrylist:
                    print(f'removing {name}...')
                    nameserverd.remove(name)
                    
                entrylist = list(nameserverd.list().keys())[1:]
                print(f'entries in pyro5 nameserver: {entrylist}')
            except Exception as e:
                print(f'could not cleanup nameserver entries: {e}')
            '''
        except:
            # the nameserver is not running
            print('control: nameserver not already running. starting from wsp')
            nameserverd = daemon_utils.PyDaemon(name = 'ns_daemon', filepath = f"{wsp_path}/daemon/ns_launcherd.py",
                                                args = ['-n', self.ns_host], 
                                                python = True)
            # self.daemonlist.add_daemon(nameserverd)
            # We have to actually launch the nameserver!
            print(f'Launching Nameserver at ns_host = {self.ns_host}')
            nameserverd.launch()
            #Pyro5.nameserver.start_ns_loop(host = self.ns_host) # this will hang here.
        
        if mode in ['r', 'i', 'm']:
            # test daemon
            self.testd = daemon_utils.PyDaemon(name = 'test', filepath = f"{wsp_path}/daemon/test_daemon.py")
            self.daemonlist.add_daemon(self.testd)
                    
            # chiller daemon
            if '--smallchiller' in opts:
                self.chillerd = daemon_utils.PyDaemon(name = 'chiller', filepath = f"{wsp_path}/chiller/small_chillerd.py", args = ['-n', self.ns_host])
            else:
                self.chillerd = daemon_utils.PyDaemon(name = 'chiller', filepath = f"{wsp_path}/chiller/chillerd.py", args = ['-n', self.ns_host])
            self.daemonlist.add_daemon(self.chillerd)
            pass
        
            # housekeeping data logging daemon (hkd = housekeeping daemon)
            self.hkd = daemon_utils.PyDaemon(name = 'hkd', filepath = f"{wsp_path}/housekeeping/pydirfiled.py", 
                                             args = ['-n', self.ns_host]) #change to dirfiled.py if you want to use the version that uses easygetdata
            self.daemonlist.add_daemon(self.hkd)
        
        if mode in ['i']:
            # labjack daemon
            self.labjackd = daemon_utils.PyDaemon(name = 'labjacks', filepath = f"{wsp_path}/housekeeping/labjackd.py", args = ['-n', self.ns_host])
            self.daemonlist.add_daemon(self.labjackd)
            
            
            
            
        if mode in ['r','m']:
            
            
            
            # SUMMER accesories (eg viscam)
            self.viscamd = daemon_utils.PyDaemon(name = 'viscam', filepath = f"{wsp_path}/viscam/viscamd.py")
            self.daemonlist.add_daemon(self.viscamd)
            
            # ccd daemon
            self.ccdd= daemon_utils.PyDaemon(name = 'ccd', filepath = f"{wsp_path}/viscam/ccd_daemon.py")#, args = ['-v'])
            self.daemonlist.add_daemon(self.ccdd)
            
            
            
            # power (PDU/NPS) daemon
            self.powerd = daemon_utils.PyDaemon(name = 'power', filepath = f"{wsp_path}/power/powerd.py")
            self.daemonlist.add_daemon(self.powerd)
        
        if '--sunsim' in opts:              
            self.sunsim = True
        else:
            self.sunsim = False
            
        # option to ignore whether the shutter is open, which let you test with the dome closed
        if '--dometest' in opts:
            self.dometest = True
        else:
            self.dometest = False
        
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
                
            if self.sunsim:
                # start up the fake sun_simulator
                self.sunsimd = daemon_utils.PyDaemon(name = 'sun_simulator', filepath = f"{wsp_path}/ephem/sun_simulator_gui.py")
                self.daemonlist.add_daemon(self.sunsimd)
                
        
            # ephemeris daemon
            #TODO: pass opts? ignore for now. don't need it running in verbose mode
            self.ephemd = daemon_utils.PyDaemon(name = 'ephem', filepath = f"{wsp_path}/ephem/ephemd.py", args = opts)
            self.daemonlist.add_daemon(self.ephemd)
        
        if mode in ['r']:
            # ROBOTIC OPERATION MODE!
            # ROBO MANAGER DAEMON
            self.roboManagerd = daemon_utils.PyDaemon(name = 'robomanager', filepath = f"{wsp_path}/control/roboManagerd.py", args = opts)
            self.daemonlist.add_daemon(self.roboManagerd)
            
            
                
        # Launch all hardware daemons
        self.daemonlist.launch_all()
        # now add the nameserver. we already started it, so we'll add it only 
        # after starting the rest. this will still let us shut them all down together?
        # might want to nix this altogether. 
        #self.daemonlist.add_daemon(nameserverd)

                
        
        
        ### SET UP THE HARDWARE ###
        # note we always want to set this all up. we just won't try to update the state later on if we're not running certain daemons
        # we'll run into trouble down the line if some of these attributes don't exist
        
        ### CREATE A VARIABLE TO HOLD THE ROBO OPERATOR STATE THAT BOTH ROBO AND HOUSEKEEPING CAN ACCESS
        self.robostate = dict()
        
        
        # init the network power supply
        """
        try:
            self.pdu1 = power.PDU('pdu1.ini',base_directory = self.base_directory)

        except Exception as e:
            self.logger.warning(f"control: could not init NPS at pdu1, {type(e)}: {e}")
        """
        self.powerManager = powerManager.local_PowerManager(self.base_directory)
        
        # init the test object (goes with the test_daemon)
        self.counter =  test_daemon_local.local_counter(wsp_path, ns_host = self.ns_host)

        # init the telescope
        self.telescope = telescope.Telescope(config = self.config, 
                                             host = self.config['telescope']['host'], 
                                             port = self.config['telescope']['port'],
                                             logger = logger)

        # init the mirror cover 
        self.mirror_cover = mirror_cover.MirrorCovers(addr = self.config['telescope_shutter']['addr'],
                                                      port = self.config['telescope_shutter']['port'],
                                                      config = self.config, logger = self.logger)
        
        # init the dome
        self.dome = dome.local_dome(base_directory = self.base_directory, config = self.config, telescope = self.telescope, logger = self.logger)
        
        # init the ephemeris
        self.ephem = ephem.local_ephem(base_directory = self.base_directory, config = self.config, ns_host = self.ns_host, logger = self.logger)
        
        # init the schedule. put it here so it can be passed into housekeeping
        self.schedule = schedule.Schedule(base_directory = self.base_directory, config = self.config, logger = self.logger)
        
        
        # init the viscam shutter, filter wheel, and raspberry pi
        #self.viscam = web_request.Viscam(URL = self.config['viscam_url'], logger = self.logger)
        self.viscam = viscam.local_viscam(base_directory = self.base_directory)
        
        #TODO: deprecate this
        # init the viscam ccd
        self.ccd = ccd.local_ccd(base_directory = self.base_directory, config = self.config, logger = self.logger)
        
        
        # init the sumnmer camera interface
        self.summercamera = camera.local_camera(base_directory = self.base_directory, config = self.config, 
                                          daemon_pyro_name = 'SUMMERcamera', ns_host = self.ns_host,
                                          logger = self.logger, verbose = self.verbose)
        
        # init the winter camera interface
        self.wintercamera = camera.local_camera(base_directory = self.base_directory, config = self.config, 
                                          daemon_pyro_name = 'WINTERcamera', ns_host = self.ns_host,
                                          logger = self.logger, verbose = self.verbose)

        # init the alert handler
        auth_config  = yaml.load(open(os.path.join(wsp_path,self.config['alert_handler']['auth_config_file'] )) , Loader = yaml.FullLoader)
        user_config  = yaml.load(open(os.path.join(wsp_path,self.config['alert_handler']['user_config_file'] )) , Loader = yaml.FullLoader)
        alert_config = yaml.load(open(os.path.join(wsp_path,self.config['alert_handler']['alert_config_file'])) , Loader = yaml.FullLoader)

        self.alertHandler = alert_handler.AlertHandler(user_config, alert_config, auth_config)
        if mode == 'r':        

            # send a signal that we've started up wsp!
            self.alertHandler.slack_log(f':futurama-bender-robot::telescope: *Starting WSP in Robotic Mode!*')
        
        # init the chiller
        if '--smallchiller' in opts:
            self.chiller = small_chiller.local_chiller(base_directory = self.base_directory, config = self.config, alertHandler = self.alertHandler)
        else:
            self.chiller = chiller.local_chiller(base_directory = self.base_directory, config = self.config, ns_host = self.ns_host)

        # init the labjacks        
        self.labjacks = labjack_handler_local.local_labjackHandler(self.base_directory, self.config, self.ns_host, self.logger)
        
        
        ### SET UP THE HOUSEKEEPING ###
            
            
            
        # if mode == 1:
        # init the housekeeping class (this starts the daq and dirfile write loops)
        self.hk = housekeeping.housekeeping(self.config,
                                                base_directory = self.base_directory,
                                                mode = mode,
                                                schedule = self.schedule,
                                                telescope = self.telescope,
                                                dome = self.dome,
                                                chiller = self.chiller,
                                                labjacks = self.labjacks,
                                                powerManager = self.powerManager,
                                                counter = self.counter,
                                                ephem = self.ephem,
                                                viscam = self.viscam, 
                                                ccd = self.ccd, 
                                                summercamera = self.summercamera,
                                                wintercamera = self.wintercamera,
                                                mirror_cover = self.mirror_cover,
                                                robostate = self.robostate,
                                                sunsim = self.sunsim,
                                                logger = self.logger
                                                )
        
        
        self.pyro_thread = daemon_utils.PyroDaemon(obj = self.hk, name = 'state', ns_host = self.ns_host)
        self.pyro_thread.start()
        
        """
        In this section we set up the appropriate command interface and executors for the chosen mode
        """
        ### SET UP THE COMMAND LINE INTERFACE
        self.wintercmd = wintercmd.Wintercmd(self.base_directory, 
                                             self.config, 
                                             state = self.hk.state, 
                                             alertHandler = self.alertHandler,
                                             daemonlist = self.daemonlist, 
                                             telescope = self.telescope, 
                                             dome = self.dome, 
                                             chiller = self.chiller, 
                                             powerManager = self.powerManager, 
                                             logger = self.logger, 
                                             viscam = self.viscam, 
                                             ccd = self.ccd, 
                                             summercamera = self.summercamera,
                                             wintercamera = self.wintercamera,
                                             mirror_cover = self.mirror_cover,
                                             ephem = self.ephem)
        
        if mode in ['r','m']:
            #init the schedule executor
            #self.scheduleExec = schedule_executor.schedule_executor(self.config, self.hk.state, self.telescope, self.wintercmd, self.schedule, self.writer, self.logger)
            pass

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
            self.roboThread = roboOperator.RoboOperatorThread(self.base_directory, 
                                                              self.config, 
                                                              mode = mode, 
                                                              state = self.hk.state, 
                                                              wintercmd = self.wintercmd, 
                                                              logger = self.logger, 
                                                              alertHandler = self.alertHandler, 
                                                              schedule = self.schedule, 
                                                              telescope = self.telescope, 
                                                              dome = self.dome, 
                                                              chiller = self.chiller, 
                                                              ephem = self.ephem, 
                                                              viscam=self.viscam, 
                                                              ccd = self.ccd, 
                                                              mirror_cover = self.mirror_cover,
                                                              robostate = self.robostate,
                                                              sunsim = self.sunsim,
                                                              dometest = self.dometest,
                                                              )
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





