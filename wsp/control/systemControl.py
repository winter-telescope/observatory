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
import os

import yaml
from PyQt5 import QtCore

# add the wsp directory to the PATH
# sys.path.insert(1, wsp_path)
# print(f"control: wsp_path = {wsp_path}")
# winter modules
from wsp.alerts import alert_handler
from wsp.camera import camera, winter_image_daemon_local
from wsp.camera.implementations.spring_camera import SpringCamera
from wsp.camera.implementations.winter_camera import local_camera
from wsp.chiller import chiller, small_chiller
from wsp.command import commandParser, commandServer, wintercmd
from wsp.control import roboOperator
from wsp.daemon import daemon_utils, test_daemon_local
from wsp.dome import dome
from wsp.ephem import ephem
from wsp.filterwheel import filterwheel
from wsp.housekeeping import housekeeping, labjack_handler_local
from wsp.power import powerManager
from wsp.schedule import schedule
from wsp.telescope import mirror_cover, telescope
from wsp.utils.paths import WSP_PATH
from wsp.watchdog import local_watchdog

wsp_path = WSP_PATH


# Create the control class -- it inherets from QObject
# this is basically the "main" for the console application
class control(QtCore.QObject):

    newcmd = QtCore.pyqtSignal(object)
    newcmdRequest = QtCore.pyqtSignal(object)

    ## Initialize Class ##
    def __init__(
        self, mode, config, hk_config, base_directory, logger, opts=None, parent=None
    ):
        super(control, self).__init__(parent)

        print(f"control: base_directory = {base_directory}")
        print(f"MODE = {mode}")
        self.opts = opts

        # pass in the config
        self.config = config
        self.hk_config = hk_config
        # pass in the logger
        self.logger = logger
        # pass in the base directory
        self.base_directory = base_directory

        print(f"\nsystemControl: running with opts = {opts}")

        # init the alert handler
        auth_config = yaml.load(
            open(
                os.path.join(wsp_path, self.config["alert_handler"]["auth_config_file"])
            ),
            Loader=yaml.FullLoader,
        )
        user_config = yaml.load(
            open(
                os.path.join(wsp_path, self.config["alert_handler"]["user_config_file"])
            ),
            Loader=yaml.FullLoader,
        )
        alert_config = yaml.load(
            open(
                os.path.join(
                    wsp_path, self.config["alert_handler"]["alert_config_file"]
                )
            ),
            Loader=yaml.FullLoader,
        )

        self.alertHandler = alert_handler.AlertHandler(
            user_config, alert_config, auth_config
        )

        ### ADD HARDWARE DAEMONS TO THE DAEMON LAUNCHER ###
        # init the list of hardware daemons

        # Cleanup (kill any!) existing instances of the daemons running
        daemons_to_kill = [  #'ns_daemon',
            "domed.py",
            "chillerd.py",
            "small_chillerd.py",
            "test_daemon.py",
            "dome_simulator_gui.py",
            "ephemd.py",
            "dirfiled.py",
            "roboManagerd.py",
            "sun_simulator.py",
            "powerd.py",
            "labjackd.py",
            "watchdogd.py",
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

        # set defaults:
        self.ns_host = self.config["pyro5_ns_default_addr"]
        self.verbose = False
        self.domesim = False
        self.sunsim = False
        self.dometest = False
        self.mountsim = False
        self.nochiller = False
        self.interactive_mode = False
        self.disable_watchdog = False

        print("sysControl: Parsing opts...")
        for currentArgument, currentValue in opts:
            print(
                f"sysControl: currentArgument, currentValue = ({currentArgument}, {currentValue})"
            )

            if currentArgument in ["-n", "--ns_host"]:
                self.ns_host = currentValue

            if currentArgument in ["-v", "--verbose"]:
                self.verbose = True

            if currentArgument in ["--domesim"]:
                self.domesim = True

            if currentArgument in ["--sunsim"]:
                self.sunsim = True

            # option to ignore whether the shutter is open, which let you test with the dome closed
            if currentArgument in ["--dometest"]:
                self.dometest = True

            # option to use the simulated telescope mount
            if currentArgument in ["--mountsim"]:
                self.mountsim = True

            # option to use the simulated telescope mount
            if currentArgument in ["--nochiller"]:
                self.nochiller = True

            # start in interactive mode with command line interface shell started
            if currentArgument in ["-s", "--shell"]:
                self.interactive_mode = True

            # disable the watchdog monitor which shuts down the system if the temps/flow look like failures
            if currentArgument in ["--disablewatchdog"]:
                self.disable_watchdog = True

        print(f"sysControl: ns_host = {self.ns_host}")
        print(f"sysControl: verbose = {self.verbose}")
        print(f"sysControl: sunsim = {self.sunsim}")
        print(f"sysControl: domesim = {self.domesim}")
        print(f"sysControl: dometest = {self.dometest}")
        print(f"sysControl: mountsim = {self.mountsim}")
        print(f"sysControl: nochiller = {self.nochiller}")
        print(f"sysControl: disable_watchdog = {self.disable_watchdog}")

        try:
            nameserverd = Pyro5.core.locate_ns(host=self.ns_host)

        except:
            # the nameserver is not running
            print("control: nameserver not already running. starting from wsp")
            nameserverd = daemon_utils.PyDaemon(
                name="ns_daemon",
                filepath=f"{wsp_path}/daemon/ns_launcherd.py",
                args=["-n", self.ns_host],
                python=True,
            )
            # self.daemonlist.add_daemon(nameserverd)
            # We have to actually launch the nameserver!
            print(f"Launching Nameserver at ns_host = {self.ns_host}")
            nameserverd.launch()
            # Pyro5.nameserver.start_ns_loop(host = self.ns_host) # this will hang here.

        if mode in ["r", "i", "m"]:
            # test daemon
            self.testd = daemon_utils.PyDaemon(
                name="test", filepath=f"{wsp_path}/daemon/test_daemon.py"
            )
            self.daemonlist.add_daemon(self.testd)

            # chiller daemon
            if not self.nochiller:
                if "--smallchiller" in opts:
                    self.chillerd = daemon_utils.PyDaemon(
                        name="chiller",
                        filepath=f"{wsp_path}/chiller/small_chillerd.py",
                        args=["-n", self.ns_host],
                    )
                else:
                    self.chillerd = daemon_utils.PyDaemon(
                        name="chiller",
                        filepath=f"{wsp_path}/chiller/chillerd.py",
                        args=["-n", self.ns_host],
                    )
                self.daemonlist.add_daemon(self.chillerd)
            else:
                pass

            # housekeeping data logging daemon (hkd = housekeeping daemon)
            self.hkd = daemon_utils.PyDaemon(
                name="hkd",
                filepath=f"{wsp_path}/housekeeping/pydirfiled.py",
                args=["-n", self.ns_host],
            )  # change to dirfiled.py if you want to use the version that uses easygetdata
            self.daemonlist.add_daemon(self.hkd)

            # power (PDU/NPS) daemon
            self.powerd = daemon_utils.PyDaemon(
                name="power",
                filepath=f"{wsp_path}/power/powerd.py",
                args=["-n", self.ns_host],
            )
            self.daemonlist.add_daemon(self.powerd)

            # labjack daemon
            self.labjackd = daemon_utils.PyDaemon(
                name="labjacks",
                filepath=f"{wsp_path}/housekeeping/labjackd.py",
                args=["-n", self.ns_host],
            )
            self.daemonlist.add_daemon(self.labjackd)

        if mode in ["i"]:

            pass

        if mode in ["r", "m"]:

            """
            # SUMMER accesories (eg viscam)
            self.viscamd = daemon_utils.PyDaemon(name = 'viscam', filepath = f"{wsp_path}/viscam/viscamd.py")
            self.daemonlist.add_daemon(self.viscamd)

            # ccd daemon
            self.ccdd= daemon_utils.PyDaemon(name = 'ccd', filepath = f"{wsp_path}/viscam/ccd_daemon.py")#, args = ['-v'])
            self.daemonlist.add_daemon(self.ccdd)
            """
            pass

        if mode in ["r", "m"]:
            # OBSERVATORY MODES (eg all but instrument)

            ###### DAEMONS #####
            # Dome Daemon
            domeargs = ["-n", self.ns_host]
            if self.domesim:
                domeargs.append("--domesim")
            self.domed = daemon_utils.PyDaemon(
                name="dome", filepath=f"{wsp_path}/dome/domed.py", args=domeargs
            )

            self.daemonlist.add_daemon(self.domed)

            if self.domesim:
                # start up the fake dome as a daemon
                self.domesimd = daemon_utils.PyDaemon(
                    name="dome_simulator",
                    filepath=f"{wsp_path}/dome/dome_simulator_gui.py",
                )
                self.daemonlist.add_daemon(self.domesimd)

            if self.sunsim:
                # start up the fake sun_simulator
                self.sunsimd = daemon_utils.PyDaemon(
                    name="sun_simulator",
                    filepath=f"{wsp_path}/ephem/sun_simulator_gui.py",
                )
                self.daemonlist.add_daemon(self.sunsimd)

            # ephemeris daemon
            # TODO: pass opts? ignore for now. don't need it running in verbose mode
            ephemargs = ["-n", self.ns_host]
            if self.sunsim:
                ephemargs.append("--sunsim")
            self.ephemd = daemon_utils.PyDaemon(
                name="ephem", filepath=f"{wsp_path}/ephem/ephemd.py", args=ephemargs
            )
            self.daemonlist.add_daemon(self.ephemd)

            # set up filter wheels
            winterfwargs = ["-n", self.ns_host]
            self.winterfwd = daemon_utils.PyDaemon(
                name="winterfw",
                filepath=f"{wsp_path}/filterwheel/winterFilterd.py",
                args=winterfwargs,
            )
            self.daemonlist.add_daemon(self.winterfwd)

            # watchdog monitor daemon
            if self.disable_watchdog:
                self.alertHandler.slack_log(
                    f":rediren: *WARNING* :redsiren: *Safety watchdog disabled!*",
                    group="operator",
                )
                self.alertHandler.slack_log(
                    f"somebody is running WSP with the safety watchdog disabled. This is a deliberate choice, but could have severe consequences if not properly monitored"
                )
            else:
                self.watchdog = daemon_utils.PyDaemon(
                    name="watchdog",
                    filepath=f"{wsp_path}/watchdog/watchdogd.py",
                    args=["-n", self.ns_host],
                )
                self.daemonlist.add_daemon(self.watchdog)

        if mode in ["r"]:
            # ROBOTIC OPERATION MODE!
            # ROBO MANAGER DAEMON
            roboargs = ["-n", self.ns_host]
            if self.sunsim:
                roboargs.append("--sunsim")
            self.roboManagerd = daemon_utils.PyDaemon(
                name="robomanager",
                filepath=f"{wsp_path}/control/roboManagerd.py",
                args=roboargs,
            )
            self.daemonlist.add_daemon(self.roboManagerd)

        # Launch all hardware daemons
        self.daemonlist.launch_all()
        # now add the nameserver. we already started it, so we'll add it only
        # after starting the rest. this will still let us shut them all down together?
        # might want to nix this altogether.
        # self.daemonlist.add_daemon(nameserverd)

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
        self.powerManager = powerManager.local_PowerManager(
            self.base_directory,
            ns_host=self.ns_host,
            logger=logger,
            verbose=self.verbose,
        )

        # init the test object (goes with the test_daemon)
        self.counter = test_daemon_local.local_counter(wsp_path, ns_host=self.ns_host)

        # init the telescope
        if self.mountsim:
            host = self.config["telescope"]["simhost"]
        else:
            host = self.config["telescope"]["host"]
        self.telescope = telescope.Telescope(
            config=self.config,
            host=host,
            port=self.config["telescope"]["comm_port"],
            mountsim=self.mountsim,
            logger=logger,
        )

        # init the mirror cover
        if self.mountsim:
            self.mirror_cover = None
        else:
            self.mirror_cover = mirror_cover.MirrorCovers(
                addr=self.config["telescope_shutter"]["addr"],
                port=self.config["telescope_shutter"]["port"],
                config=self.config,
                logger=self.logger,
            )

        # init the dome
        self.dome = dome.local_dome(
            base_directory=self.base_directory,
            config=self.config,
            telescope=self.telescope,
            ns_host=self.ns_host,
            logger=self.logger,
        )

        # init the ephemeris
        self.ephem = ephem.local_ephem(
            base_directory=self.base_directory,
            config=self.config,
            ns_host=self.ns_host,
            logger=self.logger,
        )

        # init the schedule. put it here so it can be passed into housekeeping
        self.schedule = schedule.Schedule(
            base_directory=self.base_directory, config=self.config, logger=self.logger
        )

        # init the summer camera interface
        self.springcamera = SpringCamera(
            base_directory=self.base_directory,
            config=self.config,
            camname="spring",
            daemon_pyro_name="SPRINGCamera",
            ns_host_camera=self.ns_host,
            ns_host_hk=self.ns_host,
            logger=None,
            verbose=False,
        )

        # init the winter camera interface
        self.wintercamera = local_camera(
            base_directory=self.base_directory,
            config=self.config,
            camname="winter",
            daemon_pyro_name="WINTERcamera",
            ns_host=self.ns_host,
            logger=self.logger,
            verbose=self.verbose,
        )

        # init the winter filterwheel interface
        self.winterfw = filterwheel.local_filterwheel(
            base_directory=self.base_directory,
            config=self.config,
            daemon_pyro_name="WINTERfw",
            ns_host=self.ns_host,
            logger=self.logger,
            verbose=self.verbose,
        )

        self.winter_image_handler = winter_image_daemon_local.WINTERImageHandler(
            wsp_path,
            config=self.config,
            camname="winter",
            daemon_pyro_name="WINTERImageDaemon",
            ns_host=self.ns_host,
            logger=self.logger,
            verbose=self.verbose,
        )

        # init the camera dictionary to hold all the cameras we have access to
        self.camdict = dict(
            {
                "winter": self.wintercamera,
                "spring": self.springcamera,
                #'summer' : self.summercamera,
            }
        )

        # init the filter wheels and the fwdict filter wheel dictionary
        self.fwdict = dict(
            {
                "winter": self.winterfw,
                #'summer' : self.summerfw,
            }
        )

        # init the image daemon handler dictionary
        self.imghandlerdict = dict(
            {
                "winter": self.winter_image_handler,
            }
        )

        if mode == "r":

            # send a signal that we've started up wsp!
            self.alertHandler.slack_log(
                f":futurama-bender-robot::telescope: *Starting WSP in Robotic Mode!*"
            )

        # init the chiller
        if "--smallchiller" in opts:
            self.chiller = small_chiller.local_chiller(
                base_directory=self.base_directory,
                config=self.config,
                alertHandler=self.alertHandler,
            )
        else:
            self.chiller = chiller.local_chiller(
                base_directory=self.base_directory,
                config=self.config,
                ns_host=self.ns_host,
            )

        # init the labjacks
        self.labjacks = labjack_handler_local.local_labjackHandler(
            base_directory=self.base_directory,
            config=self.config,
            ns_host=self.ns_host,
            logger=self.logger,
        )

        self.watchdog = local_watchdog.local_watchdog(
            self.base_directory, self.config, ns_host=self.ns_host, logger=self.logger
        )
        ### SET UP THE HOUSEKEEPING ###
        # init the housekeeping class (this starts the daq and dirfile write loops)
        self.hk = housekeeping.housekeeping(
            config=self.config,
            hk_config=self.hk_config,
            base_directory=self.base_directory,
            mode=mode,
            watchdog=self.watchdog,
            schedule=self.schedule,
            telescope=self.telescope,
            dome=self.dome,
            chiller=self.chiller,
            labjacks=self.labjacks,
            powerManager=self.powerManager,
            counter=self.counter,
            ephem=self.ephem,
            camdict=self.camdict,
            fwdict=self.fwdict,
            imghandlerdict=self.imghandlerdict,
            mirror_cover=self.mirror_cover,
            robostate=self.robostate,
            sunsim=self.sunsim,
            ns_host=self.ns_host,
            logger=self.logger,
        )

        self.pyro_thread = daemon_utils.PyroDaemon(
            obj=self.hk, name="state", ns_host=self.ns_host
        )
        self.pyro_thread.start()

        """
        In this section we set up the appropriate command interface and executors for the chosen mode
        """
        ### SET UP THE COMMAND LINE INTERFACE
        self.wintercmd = wintercmd.Wintercmd(
            self.base_directory,
            self.config,
            state=self.hk.state,
            alertHandler=self.alertHandler,
            daemonlist=self.daemonlist,
            telescope=self.telescope,
            dome=self.dome,
            chiller=self.chiller,
            labjacks=self.labjacks,
            powerManager=self.powerManager,
            logger=self.logger,
            camdict=self.camdict,
            fwdict=self.fwdict,
            imghandlerdict=self.imghandlerdict,
            mirror_cover=self.mirror_cover,
            ephem=self.ephem,
        )

        # init the command executor
        self.cmdexecutor = commandParser.cmd_executor(
            telescope=self.telescope, wintercmd=self.wintercmd, logger=self.logger
        )  # , listener = listener)

        if self.interactive_mode:
            # init the command prompt
            self.cmdprompt = commandParser.cmd_prompt(self.telescope, self.wintercmd)

            # connect the new command signal to the command executor
            self.cmdprompt.newcmd.connect(self.cmdexecutor.add_cmd_request_to_queue)
        # signal for if main wants to execute a raw cmd (same format as terminal).
        self.newcmd.connect(self.cmdexecutor.add_cmd_to_queue)
        # signal for if main wants to execute a command request
        self.newcmdRequest.connect(self.cmdexecutor.add_cmd_request_to_queue)

        # connect the new schedule command to the command executor
        if mode in ["r", "m"]:
            # self.scheduleExec.newcmd.connect(self.cmdexecutor.add_cmd_request_to_queue)
            self.roboThread = roboOperator.RoboOperatorThread(
                self.base_directory,
                self.config,
                mode=mode,
                state=self.hk.state,
                wintercmd=self.wintercmd,
                logger=self.logger,
                alertHandler=self.alertHandler,
                watchdog=self.watchdog,
                schedule=self.schedule,
                telescope=self.telescope,
                dome=self.dome,
                chiller=self.chiller,
                ephem=self.ephem,
                camdict=self.camdict,
                fwdict=self.fwdict,
                imghandlerdict=self.imghandlerdict,
                mirror_cover=self.mirror_cover,
                robostate=self.robostate,
                sunsim=self.sunsim,
                dometest=self.dometest,
                mountsim=self.mountsim,
            )
        # set up the command server which listens for command requests of the network
        self.commandServer = commandServer.server_thread(
            self.config["wintercmd_server_addr"],
            self.config["wintercmd_server_port"],
            self.logger,
            self.config,
        )
        # connect the command server to the command executor
        self.commandServer.newcmd.connect(self.cmdexecutor.add_cmd_request_to_queue)
        # connect the wintercmd newRequest signal to the cmd executor
        self.wintercmd.newCmdRequest.connect(self.cmdexecutor.add_cmd_request_to_queue)

        ##### START SCHEDULE EXECUTOR #####
        if mode in ["r", "m"]:
            self.roboThread.start()
