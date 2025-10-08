"""camera_interface_daemon.py
This module provides the main interface for the camera daemon
"""

import getopt
import logging
import os
import shlex
import signal
import subprocess
import sys
import threading
import time
import traceback as tb
from abc import ABC, abstractmethod
from datetime import datetime, timedelta

import numpy as np
import ok
import Pyro5.core
import Pyro5.server
import pytz
import scipy.stats

# from photutils.datasets import make_random_gaussians_table, make_gaussian_sources_image
import yaml
from astropy.io import fits

# from ccdproc_convenience_functions import show_image
from PyQt5 import QtCore

# from utils import err_code
from wsp.daemon.daemon_utils import PyroDaemon
from wsp.utils.logging_setup import setup_logger
from wsp.utils.paths import CONFIG_PATH
from wsp.utils.paths import WSP_PATH as wsp_path


class BaseCameraInterface(QtCore.QObject, ABC):
    """
    Inteface for communications to the camera, either directly
    or through a TCP/IP or Pyro5 connection to a separarate
    camera daemon.
    """

    newReply = QtCore.pyqtSignal(int)
    newStatus = QtCore.pyqtSignal(object)
    newCommand = QtCore.pyqtSignal(str)
    updateStateSignal = QtCore.pyqtSignal(object)  # pass it a dict
    resetCommandPassSignal = QtCore.pyqtSignal(int)

    def __init__(
        self,
        name,
        config,
        mode="single",  # mode is likely camera specific, eg "single", "stack", "ndr", "iwr", etc
        logger=None,
        connection_timeout=0.5,
        verbose=False,
    ):
        super(BaseCameraInterface, self).__init__()

        self.config = config
        self.state = dict()
        self.name = name  # eg name: "summer", "winter-deep"
        self.logger = logger
        self.verbose = verbose
        self.mode = mode
        self.connected = False
        self.command_pass = 0
        print("initing sensor object")

        # self.reconnector = ReconnectHandler()

        self.setup_connection()

        # housekeeping attributes
        self.state = dict()

        # connect the update state signal
        self.updateStateSignal.connect(self.updateState)
        self.resetCommandPassSignal.connect(self.resetCommandPass)

        # local timezone for writing timestamps in local time
        self.local_timezone = pytz.timezone("America/Los_Angeles")

        # Load config-driven parameters:
        self.name = name
        self.config = config
        self.loadConfig(config)

        ## Startup:
        self.pollStatus()

    def loadConfig(self, config):
        """
        Load configuration parameters from the config dictionary.
        """
        self.startup_okay = True

    @abstractmethod
    def setup_connection(self):
        """
        Set up the connection to the camera.
        This can be a direct connection or a RPC (Pyro, TCP/IP) connection to a daemon.
        """
        # This is where you would set up the connection to the camera
        # For example, if using Pyro5:
        self.remote_object = None

    # General Methods
    def log(self, msg, level=logging.INFO):
        msg = f"WINTERsensor_{self.name}: {msg}"
        if self.logger is None:
            print(msg)
        else:
            self.logger.log(level=level, msg=msg)

    # Camera Interface Methods
    def updateState(self, dict_to_add):
        for key in dict_to_add:
            self.state.update({key: dict_to_add[key]})

    def resetCommandPass(self, val):
        # self.log(f'running resetCommandPass: {val}')
        # reset the command pass value to val (0 or 1), and update state
        self.command_pass = val
        self.state.update({"command_pass": val})

        # adding this because without it the state update gets missed by pollStatus sometimes
        # emit a signal and pass the new state dict out to the camera from the comm thread#
        self.newStatus.emit(self.state)

    def pollStatus(self):
        """
        Get housekeeping status. Will override this in the specific camera interface,
        but should call super().pollStatus() to ensure the base class
        updates the timestamp and emits the new status.
        This is called periodically to update the camera status.
        """
        # print('polling status...')
        self.timestamp = datetime.utcnow().timestamp()

        ##### Camera-specific polling code goes here #####

        """
        # Camera-specific polling code goes here, followed by the base class update
        # try:
            # print("trying  housekeeping")
            if self.startup_okay == True:
                raw_hk = {}  # replace with actual call to camera manufacturer API
                self.connected = True

            else:
                raw_hk = {}
        except Exception as e:
            print(e)
            print(tb.format_exc())
            raw_hk = {}
            self.connected = False"""
        #########

        # Update the state dictionary
        self.state.update(
            {
                "timestamp": self.timestamp,
                "connected": self.connected,
                "command_pass": self.command_pass,
                "startup_okay": self.startup_okay,
            }
        )
        # for now just dump in all the keys also
        for key in self.state.keys():
            print(f"{key}: type = {type(self.state[key])}")

        # emit a signal and pass the new state dict out to the camera from the comm thread
        self.newStatus.emit(self.state)

    def doCommand(self, cmd_obj):
        """
        This is connected to the newCommand signal. It parses the command and
        then executes the corresponding command from the list below

        using this as a reference: (source: https://stackoverflow.com/questions/6321940/how-to-launch-getattr-function-in-python-with-additional-parameters)

        """
        # print(f'dome: caught doCommand signal: {cmd_obj.cmd}')
        cmd = cmd_obj.cmd
        args = cmd_obj.args
        kwargs = cmd_obj.kwargs

        msg = f"(Thread {threading.get_ident()}: caught doCommand signal: {cmd_obj.cmd}, args = {args}, kwargs = {kwargs}"
        print(msg)
        try:
            getattr(self, cmd)(*args, **kwargs)
        except:
            pass

    # API methods for running camera
    # put all the req'd methods here:
    @abstractmethod
    def startup(self):
        """
        Start up the camera. This should set the camera state to READY.
        """
        pass

    @abstractmethod
    def shutdown(self):
        """
        Shut down the camera. This should set the camera state to OFF.
        """
        pass

    @abstractmethod
    def autoStartup(self, **kwargs):
        """
        Run auto startup for the camera.
        It sets the camera state to READY.
        """
        pass

    @abstractmethod
    def autoShutdown(self, **kwargs):
        """
        Run auto shutdown for the camera.
        It sets the camera state to OFF.
        """
        pass

    @abstractmethod
    def tecStart(self, coeffs=None, max_dacV=None, voffset=None):
        """
        Start the TEC (Thermoelectric Cooler) for the camera.
        """
        pass

    @abstractmethod
    def tecStop(self):
        """
        Stop the TEC (Thermoelectric Cooler) for the camera.
        """
        pass

    @abstractmethod
    def setSettings(self, settings):
        """
        Set the camera settings.
        This should update the camera configuration.
        """
        pass

    @abstractmethod
    def tecSetSetpoint(self, setpoint):
        """
        Set the TEC setpoint temperature.
        """
        pass

    @abstractmethod
    def tecGetSetpoint(self):
        """
        Get the current TEC setpoint temperature.
        """
        pass

    @abstractmethod
    def tecGetTemp(self):
        """
        Get the current TEC temperature.
        """
        pass

    @abstractmethod
    def setExposure(self, exptime):
        """
        Set the exposure time for the camera.
        """
        pass

    @abstractmethod
    def doExposure(self, filepath="", imtype="test", mode=None):
        """
        Take an exposure with the camera.

        filepath: str
            Directory for the file to be saved in.

        imtype: str
            A flag for the image type, e.g., "dark", "bias", "test", "light", etc.
        """
        pass


class signalCmd(object):
    """
    this is an object which can pass commands and args via a signal/slot to
    other threads, ideally for daemons
    """

    def __init__(self, cmd, *args, **kwargs):
        self.cmd = cmd
        self.argdict = dict()
        self.args = args
        self.kwargs = kwargs


class CommThread(QtCore.QThread):
    """
    CommThread: Communication Thread for Talking to the Sensor

    All communications with the sensor happen through this thread.
    """

    newReply = QtCore.pyqtSignal(int)
    # newCommand = QtCore.pyqtSignal(str)
    newCmdRequest = QtCore.pyqtSignal(object)
    # doReconnect = QtCore.pyqtSignal()
    newStatus = QtCore.pyqtSignal(object)
    stopPollTimer = QtCore.pyqtSignal()

    def __init__(self, camera, config, logger=None, verbose=False):
        super(QtCore.QThread, self).__init__()
        self.camera = camera
        self.config = config
        self.logger = logger
        self.verbose = verbose
        print("initing camera comms thread")

    def HandleCommandRequest(self, cmdRequest):
        self.newCmdRequest.emit(cmdRequest)

    def DoReconnect(self):
        # print(f'(Thread {threading.get_ident()}) Main: caught reconnect signal')
        self.doReconnect.emit()

    def run(self):
        print("in the run method for the camera comms thread")

        def SignalNewReply(reply):
            self.newReply.emit(reply)

        def SignalNewStatus(newStatus):
            self.newStatus.emit(newStatus)

        def StopPollTimer():
            print("trying to stop poll timer?")
            self.pollTimer.stop()

        self.camera = self.camera  # pass the camera object to the thread

        # defining the camera here so it lives in the thread
        self.camera = CameraRPCInterface(
            self.addr,
            config=self.config,
            mode=self.mode,
            logger=self.logger,
            verbose=self.verbose,
        )

        # if the newReply signal is caught, execute the sendCommand function
        self.newCmdRequest.connect(self.camera.doCommand)
        self.camera.newReply.connect(SignalNewReply)

        self.camera.newStatus.connect(SignalNewStatus)
        self.stopPollTimer.connect(StopPollTimer)

        self.pollTimer = QtCore.QTimer()
        self.pollTimer.setSingleShot(False)
        self.pollTimer.timeout.connect(self.camera.pollStatus)
        self.pollTimer.start(100)

        self.exec_()


class CameraRPCInterface(QtCore.QObject):
    """
    Remote procedure call (RPC) Interface for the camera
    Allows for remote procedure calls to the camera daemon
    This is the interface that WSP will communicate with.
    Keeping this in a separate thread so that it can field continuous
    housekeeping requests from the WSP, while also allowing for
    long-running/blocking commands to run on the the camera
    CameraInterface object.
    """

    # Define any pyqt signals here
    # commandRequest = QtCore.pyqtSignal(str)
    newCmdRequest = QtCore.pyqtSignal(object)

    def __init__(self, config, addr, mode, logger=None, verbose=False):
        super(CameraRPCInterface, self).__init__()

        ## init things here
        self.config = config
        self.addr = addr
        self.mode = mode
        self.logger = logger
        self.verbose = verbose
        self.state = dict()

        ## some things to keep track of what is going on
        # doing an exposure?
        self.doing_exposure = False

        # set up the other threads
        self.commthread = CommThread(
            self.camera,
            self.config,
            self.mode,
            logger=self.logger,
            verbose=self.verbose,
        )

        # start up the other threads
        self.commthread.start()

        # set up the signal/slot connections for the other threads
        self.commthread.newStatus.connect(self.updateStatus)
        self.newCmdRequest.connect(self.commthread.HandleCommandRequest)

    def log(self, msg, level=logging.INFO):

        msg = f"WINTERCam {self.addr}: {msg}"

        if self.logger is None:
            print(msg)
        else:
            self.logger.log(level=level, msg=msg)

    def updateStatus(self, newStatus):
        """
        Takes in a new status dictionary (eg, from the status thread),
        and updates the local copy of status

        we don't want to overwrite the whole dictionary!

        So do this element by element using update
        """
        if type(newStatus) is dict:
            # make sure we don't get some garbage, and only attempt if this is actually a dictionary
            for key in newStatus.keys():
                try:
                    self.state.update({key: newStatus[key]})

                except:
                    pass

        # print(f'Dome (Thread {threading.get_ident()}): got new status. status = {self.state}')

    def updateCommandReply(self, reply):
        """
        when we get a new reply back from the command thread, add it to the status dictionary
        """
        try:
            self.state.update({"command_reply": reply})
        except:
            pass

    ###### PUBLIC FUNCTIONS THAT CAN BE CALLED USING PYRO SERVER #####

    # Return the Current Status (the status is updated on its own)
    @Pyro5.server.expose
    def getStatus(self):
        if self.verbose:
            self.log("got command to return state dict")

        try:
            # update some required state variables,
            # can be overridden by the camera-specific implementation
            self.tec_temp = self.commthread.camera.tec_temp
            self.tec_setpoint = self.commthread.camera.tec_setpoint

            self.timestamp = datetime.utcnow().timestamp()

            self.state.update(
                {
                    "timestamp": self.timestamp,
                    "tec_temp": self.tec_temp,
                    "tec_setpoint": self.tec_setpoint,
                    "command_pass": self.commthread.camera.command_pass,
                    "startup_okay": self.commthread.camera.startup_okay,
                    "connected": self.commthread.camera.connected,
                }
            )
        except Exception as e:
            # self.log(f'Could not run getStatus: {e}')
            pass
        # print(self.state)
        return self.state

    @Pyro5.server.expose
    def startup(self):
        # startup sequence for sensor
        sigcmd = signalCmd("startup")
        self.newCmdRequest.emit(sigcmd)

    @Pyro5.server.expose
    def shutdown(self):
        # startup sequence for sensor
        sigcmd = signalCmd("shutdown")
        self.newCmdRequest.emit(sigcmd)

    @Pyro5.server.expose
    def autoStartup(self, **kwargs):
        """
        Run auto startup for the camera.
        It sets the camera state to READY.
        """
        print("autoStartup called")
        sigcmd = signalCmd("autoStartup", **kwargs)
        self.newCmdRequest.emit(sigcmd)

    @Pyro5.server.expose
    def autoShutdown(self, **kwargs):
        """
        Run auto shutdown for the camera.
        It sets the camera state to OFF.
        """
        print("autoShutdown called")
        sigcmd = signalCmd("autoShutdown", **kwargs)
        self.newCmdRequest.emit(sigcmd)

    @Pyro5.server.expose
    def tecStart(self, coeffs=None, max_dacV=None, voffset=None):
        # start up the TEC

        sigcmd = signalCmd(
            "tecStart", coeffs=coeffs, max_dacV=max_dacV, voffset=voffset
        )
        self.newCmdRequest.emit(sigcmd)

    @Pyro5.server.expose
    def tecStop(self):
        # start up the TEC
        sigcmd = signalCmd("tecStop")
        self.newCmdRequest.emit(sigcmd)

    @Pyro5.server.expose
    def setSettings(self, settings):
        # reset Settings
        sigcmd = signalCmd("setSettings", settings)
        self.newCmdRequest.emit(sigcmd)

    @Pyro5.server.expose
    def tecSetSetpoint(self, setpoint):
        # start up the TEC
        sigcmd = signalCmd("tecSetSetpoint", setpoint)
        self.newCmdRequest.emit(sigcmd)

    @Pyro5.server.expose
    def tecGetSetpoint(self):
        # get the TEC setpoint
        sigcmd = signalCmd("tecGetSetpoint")
        self.newCmdRequest.emit(sigcmd)

    @Pyro5.server.expose
    def tecGetTemp(self):
        # get the TEC temperature
        sigcmd = signalCmd("tecGetTemp")
        self.newCmdRequest.emit(sigcmd)

    @Pyro5.server.expose
    def setExposure(self, exptime):
        # set the exposure time
        sigcmd = signalCmd("setExposure", exptime)
        self.newCmdRequest.emit(sigcmd)

    @Pyro5.server.expose
    def doExposure(self, filepath="", imtype="test", mode=None):
        """
        take an exposure

        filepath: str
            directorty for the file to be saved in

        imtype: str
            a flag for the image type, eg "dark", "bias", "test", "light", etc

        """
        self.log(f"doing exposure with mode = {self.mode}")
        sigcmd = signalCmd("doExposure", filepath, imtype=imtype, mode=mode)
        self.newCmdRequest.emit(sigcmd)

    '''
    @Pyro5.server.expose
    def gotExposure(self):
        """
        tell Daemon the exposure was received

        """
        self.log(f"got exposure")
        sigcmd = signalCmd("gotExposure")
        self.newCmdRequest.emit(sigcmd)
    '''


class PyroGUI(QtCore.QObject):
    """
    This is the main class for the daemon. It is a QObject, which means that
    it can be initialized with it's own event loop. This runs the whole daemon,
    and has a dedicated QThread which handles all the Pyro stuff (the PyroDaemon object)
    """

    def __init__(
        self,
        pyroname,
        config,
        mode,
        ns_host=None,
        logger=None,
        verbose=False,
        parent=None,
    ):
        super(PyroGUI, self).__init__(parent)

        self.addr = addr
        self.config = config
        self.mode = mode
        self.ns_host = ns_host
        self.logger = logger
        self.verbose = verbose

        msg = f"(Thread {threading.get_ident()}: Starting up Sensor Daemon "
        if logger is None:
            print(msg)
        else:
            logger.info(msg)

        """
        # set up an alert handler so that the dome can send messages directly
        auth_config_file  = wsp_path + '/credentials/authentication.yaml'
        user_config_file = wsp_path + '/credentials/alert_list.yaml'
        alert_config_file = wsp_path + '/config/alert_config.yaml'
        
        auth_config  = yaml.load(open(auth_config_file) , Loader = yaml.FullLoader)
        user_config = yaml.load(open(user_config_file), Loader = yaml.FullLoader)
        alert_config = yaml.load(open(alert_config_file), Loader = yaml.FullLoader)
        
        self.alertHandler = alert_handler.AlertHandler(user_config, alert_config, auth_config)    
        
        """
        self.alertHandler = None

        # set up the dome
        self.servername = "command_server"  # this is the key it uses to set up the server from the conf file

        self.pyro_thread = PyroDaemon(
            obj=self.cam,
            name=f"{pyroname}",
            ns_host=self.ns_host,
        )
        self.pyro_thread.start()


def sigint_handler(*args):
    """Handler for the SIGINT signal."""
    sys.stderr.write("\r")

    print("CAUGHT SIGINT, KILLING PROGRAM")

    # explicitly kill each thread, otherwise sometimes they live on
    main.cam.commthread.stopPollTimer.emit()
    time.sleep(0.5)

    main.cam.commthread.quit()  # terminate is also a more rough option?

    print("KILLING APPLICATION")
    QtCore.QCoreApplication.quit()


if __name__ == "__main__":

    argumentList = sys.argv[1:]

    addr = "sb"
    verbose = False
    doLogging = True
    ns_host = "192.168.1.10"
    mode = "ndr"
    # Options
    options = "vpn:a:m:"

    # Long options
    long_options = ["verbose", "print", "ns_host =", "addr =", "mode ="]

    try:
        # Parsing argument
        print(f"argumentList = {argumentList}")
        arguments, values = getopt.getopt(argumentList, options, long_options)
        print(f"arguments: {arguments}")
        print(f"values: {values}")
        # checking each argument
        for currentArgument, currentValue in arguments:

            if currentArgument in ("-v", "--verbose"):
                verbose = True

            elif currentArgument in ("-a", "--addr"):
                addr = currentValue
                # print('name given', name)

            elif currentArgument in ("-n", "--ns_host"):
                ns_host = currentValue

            elif currentArgument in ("-p", "--print"):
                doLogging = False

            elif currentArgument in ("-m", "--mode"):
                mode = currentValue

    except getopt.error as err:
        # output error, and return with an error code
        print(str(err))

    print(f"verbose = {verbose}")
    print(f"logging mode = {doLogging}")
    print(f"name = {addr}")
    print(f"sensor mode = {mode}")

    # load the config
    config_file = CONFIG_PATH
    config = yaml.load(open(config_file), Loader=yaml.FullLoader)

    app = QtCore.QCoreApplication(sys.argv)

    if doLogging:
        logger = setup_logger(os.getenv("HOME"), config)
    else:
        logger = None

    main = PyroGUI(
        addr=addr,
        config=config,
        mode=mode,
        ns_host=ns_host,
        logger=logger,
        verbose=verbose,
    )

    signal.signal(signal.SIGINT, sigint_handler)

    # Run the interpreter every so often to catch SIGINT
    timer = QtCore.QTimer()
    timer.start(500)
    timer.timeout.connect(lambda: None)

    sys.exit(app.exec_())
