# fake_camera_daemon.py

"""
Fake camera daemon for testing purposes.

"""
import getopt
import os
import signal
import sys
import threading
import time

import Pyro5.core
import Pyro5.server
import yaml
from PyQt5 import QtCore

from wsp.camera.state import CameraState
from wsp.daemon import daemon_utils
from wsp.housekeeping import data_handler
from wsp.utils.paths import CONFIG_PATH
from wsp.utils.paths import WSP_PATH as wsp_path


class TimerThread(QtCore.QThread):
    """
    This is a thread that just counts up the timeout and then emits a
    timeout signal. It will be connected to the worker thread so that it can
    run a separate thread that times each worker thread's execution
    """

    timerTimeout = QtCore.pyqtSignal()

    def __init__(self, timeout, *args, **kwargs):
        super(TimerThread, self).__init__()
        print("created a timer thread")
        # Set up the timeout. Convert seconds to ms
        self.timeout = timeout * 1000.0

    def run(self):
        def printTimeoutMessage():
            print(f"timer thread: timeout happened")

        print(f"running timer in thread {threading.get_ident()}")
        # run a single shot QTimer that emits the timerTimeout signal when complete
        self.timer = QtCore.QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(printTimeoutMessage)
        self.timer.timeout.connect(self.timerTimeout.emit)
        self.timer.start(self.timeout)
        self.exec_()


# @Pyro5.server.expose
class FakeCamera(QtCore.QObject):
    def __init__(self, config, logger, verbose=False):

        super(FakeCamera, self).__init__()

        # Dedicated for fake exposure complete signal
        self.expTimer = QtCore.QTimer()
        self.expTimer.setSingleShot(True)
        self.expTimer.timeout.connect(self.exposure_complete)

        # Dedicated for fake auto start complete signal
        self.autoStartTimer = QtCore.QTimer()
        self.autoStartTimer.setSingleShot(True)
        self.autoStartTimer.timeout.connect(self.autoStartComplete.emit)

        # Initialize camera state
        self.camera_state = CameraState.OFF

    def exposure_complete(self):
        """
        This is called when the exposure is complete.
        It emits the exposureComplete signal.
        """
        print("exposure complete")
        self.exposureComplete.emit()

    ## API METHODS ##
    @Pyro5.expose
    def autoStartupCamera(self, **kwargs):
        """
        Run auto startup for the camera.
        It sets the camera state to READY.
        """
        print("autoStartupCamera called")
        self.camera_state = CameraState.READY
        self.autoStartComplete.emit()

    @Pyro5.expose
    def autoShutdownCamera(self, **kwargs):
        """
        Run auto shutdown for the camera.
        It sets the camera state to OFF.
        """
        print("autoShutdownCamera called")
        self.camera_state = CameraState.OFF
        self.autoShutdownComplete.emit()

    @Pyro5.expose
    def checkCamera(self, **kwargs):
        """
        Check the camera started up okay.
        This is a no-op for the fake camera.
        """
        print("checkCamera called")
        # In a real camera, this would check the camera state and return an error if not READY
        if self.camera_state != CameraState.READY:
            return False
        return True

    @Pyro5.expose
    def killCameraDaemon(self, **kwargs):
        """
        Kill the camera daemon.
        This is a no-op for the fake camera.
        """
        print("killCameraDaemon called")
        # In a real camera, this would stop the camera daemon process


class PyroGUI(QtCore.QObject):
    """
    This is the main class for the daemon. It is a QObject, which means that
    it can be initialized with it's own event loop. This runs the whole daemon,
    and has a dedicated QThread which handles all the Pyro stuff (the PyroDaemon object)
    """

    def __init__(self, config, ns_host=None, logger=None, verbose=False, parent=None):
        super(PyroGUI, self).__init__(parent)

        self.config = config
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

        self.cam = FakeCamera(
            config=self.config,
            logger=self.logger,
            verbose=self.verbose,
        )

        self.pyro_thread = daemon_utils.PyroDaemon(
            obj=self.cam,
            name="FakeCamera",
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

    verbose = False
    doLogging = True
    ns_host = "localhost"
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

            elif currentArgument in ("-n", "--ns_host"):
                ns_host = currentValue

            elif currentArgument in ("-p", "--print"):
                doLogging = False

    except getopt.error as err:
        # output error, and return with an error code
        print(str(err))

    print(f"verbose = {verbose}")
    print(f"logging mode = {doLogging}")
    print(f"ns_host = {ns_host}")

    # load the config
    config_file = CONFIG_PATH
    config = yaml.load(open(config_file), Loader=yaml.FullLoader)

    app = QtCore.QCoreApplication(sys.argv)

    if doLogging:
        logger = logging_setup.setup_logger(os.getenv("HOME"), config)
    else:
        logger = None

    # main = PyroGUI(sensor_name=name, verbose=verbose, logger=None)
    main = PyroGUI(
        config=config,
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
