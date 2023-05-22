#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Feb 24 15:58:21 2023

@author: winter
"""

import os
import sys
import numpy as np
#from ccdproc_convenience_functions import show_image
from PyQt5 import QtCore
import threading
import Pyro5.core
import Pyro5.server
import logging
from datetime import datetime, timedelta
import pytz
import getopt
from astropy.io import fits 
import signal
import scipy.stats
import time
#from photutils.datasets import make_random_gaussians_table, make_gaussian_sources_image
import yaml


# add the wsp directory to the PATH
wsp_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(1, wsp_path)
print(f'WINTERfilterd: wsp_path = {wsp_path}')


from daemon import daemon_utils
from utils import logging_setup

class EZStepper(QtCore.QObject):
    newReply = QtCore.pyqtSignal(int)
    newStatus = QtCore.pyqtSignal(object)
    newCommand = QtCore.pyqtSignal(str)
    updateStateSignal = QtCore.pyqtSignal(object) # pass it a dict
    resetCommandPassSignal = QtCore.pyqtSignal(int) 
    
    def __init__(self, config, logger = None, verbose = False):
        super(EZStepper, self).__init__()
        
        self.config = config
        self.state = dict()
        self.verbose = verbose
        self.logger = logger
        self.connected = False
        self.command_pass = 0
        self.timestamp = datetime.utcnow().timestamp()
        print('initing EZStepper object')
                
        # housekeeping attributes
        self.state = dict()
        
        
        # connect the update state signal
        self.updateStateSignal.connect(self.updateState)
        self.resetCommandPassSignal.connect(self.resetCommandPass)
        
        # startupvalues
        self.pos = -1.0
        self.pos_goal = -1.0
        self.is_moving = 1
        self.homed = 0
        self.encoder_pos = -1.0
        self.is_homing = 0
        
        
 

        ## Startup:
        
        self.home()
        
        self.pollStatus()
        
        

            
            
    
    # General Methods
    def log(self, msg, level = logging.INFO):
        msg = f'EZStepper: {msg}'
        if self.logger is None:
                print(msg)
        else:
            self.logger.log(level = level, msg = msg)
    
    # Sensor Methods    
    def updateState(self, dict_to_add):
        for key in dict_to_add:
            self.state.update({key : dict_to_add[key]})
    
    def resetCommandPass(self, val):
        self.log(f'running resetCommandPass: {val}')
        # reset the command pass value to val (0 or 1), and update state
        self.command_pass = val
        self.state.update({'command_pass' : val})
    
    def pollStatus(self):
        """
        Get housekeeping status

        """
        # put in the stuff to poll the ez steppers here
        
        # now update the state dictionary
        self.update_state()
        
    def update_state(self):
        self.state.update({ 'timestamp' : self.timestamp,
                            'is_moving' : self.is_moving,
                            'position'  : self.pos,
                            'pos_goal'  : self.pos_goal,
                            'encoder_pos' : self.encoder_pos,
                            'homed'     : self.homed,
                            'is_homing' : self.is_homing,
                            })

                            
        #emit a signal and pass the new state dict out to the camera from the comm thread
        self.newStatus.emit(self.state)
            
    def doCommand(self, cmd_obj):
        """
        This is connected to the newCommand signal. It parses the command and
        then executes the corresponding command from the list below

        using this as a reference: (source: https://stackoverflow.com/questions/6321940/how-to-launch-getattr-function-in-python-with-additional-parameters)     
        
        """
        #print(f'dome: caught doCommand signal: {cmd_obj.cmd}')
        cmd = cmd_obj.cmd
        args = cmd_obj.args
        kwargs = cmd_obj.kwargs
        
        msg = f'(Thread {threading.get_ident()}: caught doCommand signal: {cmd_obj.cmd}, args = {args}, kwargs = {kwargs}'
        print(msg)
        try:
            getattr(self, cmd)(*args, **kwargs)
        except:
            pass

    

    
    # API methods 
    def home(self, pos):
        self.encoder_pos = 0.0
        self.is_moving = 0
        self.pos_goal = 0.0
        self.homed = 1
        self.update_state()
        
    
    
    def goto(self, pos):
        try:
            print('in goto method')
            self.pos_goal = pos
            self.log(f'moving position: {self.pos} --> {self.pos_goal}')
            self.is_moving = 1
            self.update_state()
            
            # do the simulated move
            dt_total_move = 30.0 # how long will the move take?
            dt_update = 1.0
            dt = 0.0
            n_steps = int(dt_total_move/dt_update)
            for i in range(n_steps):
                time.sleep(dt_update)
                dt += dt_update
                self.pos = pos = -1
                self.is_moving = 1
                self.update_state()
            
            self.pos = pos
            self.is_moving = 0
            self.update_state()
            self.log(f'move complete!')
        except Exception as e:
            self.log(f'could not move ')


        
        
class signalCmd(object):
    '''
    this is an object which can pass commands and args via a signal/slot to
    other threads, ideally for daemons
    '''
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
    #newCommand = QtCore.pyqtSignal(str) 
    newCmdRequest = QtCore.pyqtSignal(object)
    #doReconnect = QtCore.pyqtSignal()
    newStatus = QtCore.pyqtSignal(object)
    stopPollTimer = QtCore.pyqtSignal()
    
    def __init__(self, config, logger = None, verbose = False):
        super(QtCore.QThread, self).__init__()
        self.config = config
        self.logger = logger
        self.verbose = verbose
        print('initing comm thread')
    
    def HandleCommandRequest(self, cmdRequest):
        self.newCmdRequest.emit(cmdRequest)
    
    def DoReconnect(self):
        #print(f'(Thread {threading.get_ident()}) Main: caught reconnect signal')
        self.doReconnect.emit()
    
    def run(self):    
        print('in the run method for the comm thread')
        def SignalNewReply(reply):
            self.newReply.emit(reply)
        def SignalNewStatus(newStatus):
            self.newStatus.emit(newStatus)
        
        def StopPollTimer():
            print('trying to stop poll timer?')
            self.pollTimer.stop()

        self.ezstep = EZStepper(config = self.config, logger = self.logger, verbose = self.verbose)
        
        # if the newReply signal is caught, execute the sendCommand function
        #self.newCommand.connect(self.sensor.doCommand)
        self.newCmdRequest.connect(self.ezstep.doCommand)
        self.ezstep.newReply.connect(SignalNewReply)
        
        # if we recieve a doReconnect signal, trigger a reconnection
        self.ezstep.newStatus.connect(SignalNewStatus)
        self.stopPollTimer.connect(StopPollTimer)
        
        self.pollTimer = QtCore.QTimer()
        self.pollTimer.setSingleShot(False)
        self.pollTimer.timeout.connect(self.ezstep.pollStatus)
        
        # How often can you realistically poll the stepper bus?
        stepper_time_between_polls_ms = 1000
        self.pollTimer.start(stepper_time_between_polls_ms)
        
        
        self.exec_()


class WINTERfw(QtCore.QObject):
    
    # Define any pyqt signals here
    #commandRequest = QtCore.pyqtSignal(str)
    newCmdRequest = QtCore.pyqtSignal(object)
    
    def __init__(self, config, logger = None, verbose = False ):
        super(WINTERfw, self).__init__()
        
        ## init things here
        self.config = config
        self.logger = logger
        self.verbose = verbose
        self.state = dict()
        
        ## some things to keep track of what is going on
        # doing an exposure?        
        # set up the other threads
        self.commthread = CommThread(self.config, logger = self.logger, verbose = self.verbose)
        
        # start up the other threads        
        self.commthread.start()
        
        # set up the signal/slot connections for the other threads
        self.commthread.newStatus.connect(self.updateStatus)
        self.newCmdRequest.connect(self.commthread.HandleCommandRequest)
        
    def log(self, msg, level = logging.INFO):
            
        msg = f'WINTERfw {self.addr}: {msg}'
        
        if self.logger is None:
            print(msg)
        else:
            self.logger.log(level = level, msg = msg)

            
    def updateStatus(self, newStatus):
        '''
        Takes in a new status dictionary (eg, from the status thread),
        and updates the local copy of status
        
        we don't want to overwrite the whole dictionary!
        
        So do this element by element using update
        '''
        if type(newStatus) is dict:
            # make sure we don't get some garbage, and only attempt if this is actually a dictionary
            for key in newStatus.keys():
                try:
                    self.state.update({key : newStatus[key]})
                
                except:
                    pass
                    
                    

    ###### PUBLIC FUNCTIONS THAT CAN BE CALLED USING PYRO SERVER #####
    
    # Return the Current Status (the status is updated on its own)
    @Pyro5.server.expose
    def getStatus(self):
        if self.verbose:
            self.log('got command to return state dict')
            
        try:
            self.timestamp = datetime.utcnow().timestamp()
            
            
            self.state.update({ 'timestamp' : self.timestamp,
                            
                            })
        except Exception as e:
            #self.log(f'Could not run getStatus: {e}')
            pass
        #print(self.state)
        return self.state
    
    @Pyro5.server.expose
    def goto(self, pos):
        sigcmd = signalCmd('goto', pos)
        self.newCmdRequest.emit(sigcmd)
        
    @Pyro5.server.expose
    def home(self):
        sigcmd = signalCmd('home')
        self.newCmdRequest.emit(sigcmd)

    
class PyroGUI(QtCore.QObject):   
    """
    This is the main class for the daemon. It is a QObject, which means that
    it can be initialized with it's own event loop. This runs the whole daemon,
    and has a dedicated QThread which handles all the Pyro stuff (the PyroDaemon object)
    """
                  
    def __init__(self, config, ns_host = None, logger = None, verbose = False, parent=None):            
        super(PyroGUI, self).__init__(parent)   
        
        self.config = config
        self.ns_host = ns_host
        self.logger = logger
        self.verbose = verbose
        
        msg = f'(Thread {threading.get_ident()}: Starting up Sensor Daemon '
        if logger is None:
            print(msg)
        else:
            logger.info(msg)

        
        self.alertHandler = None
        
        
        self.fw = WINTERfw( 
                                config = self.config,
                                logger = self.logger, 
                                verbose = self.verbose,
                                )        
        
        self.pyro_thread = daemon_utils.PyroDaemon(obj = self.fw, 
                                                   name = 'WINTERfw',
                                                   ns_host = self.ns_host,
                                                   )
        self.pyro_thread.start()
        


            
        
def sigint_handler( *args):
    """Handler for the SIGINT signal."""
    sys.stderr.write('\r')
    
    print('CAUGHT SIGINT, KILLING PROGRAM')
    
    # explicitly kill each thread, otherwise sometimes they live on
    main.fw.commthread.stopPollTimer.emit()
    time.sleep(0.5)
    
    main.fw.commthread.quit() #terminate is also a more rough option?
    
    print('KILLING APPLICATION')
    QtCore.QCoreApplication.quit()
    
    
if __name__ == '__main__':
    
    argumentList = sys.argv[1:]
    
    verbose = False
    doLogging = False
    ns_host = None
    # Options
    options = "vpn:a:"
     
    # Long options
    long_options = ["verbose", "print", "ns_host ="]
    
    
     
    try:
        # Parsing argument
        print(f'argumentList = {argumentList}')
        arguments, values = getopt.getopt(argumentList, options, long_options)
        print(f'arguments: {arguments}')
        print(f'values: {values}')
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
        
    print(f'verbose = {verbose}')
    print(f'logging mode = {doLogging}')
        
    # load the config
    config_file = 'winter_config.yaml'
    config = yaml.load(open(config_file), Loader = yaml.FullLoader)
        
    app = QtCore.QCoreApplication(sys.argv)
    
    if doLogging:
        logger = logging_setup.setup_logger(os.getenv("HOME"), config)    
    else:
        logger = None   
    
    
    main = PyroGUI(config = config, ns_host = ns_host, logger = logger, verbose = verbose)
    
    signal.signal(signal.SIGINT, sigint_handler)

    # Run the interpreter every so often to catch SIGINT
    timer = QtCore.QTimer()
    timer.start(500) 
    timer.timeout.connect(lambda: None) 

    sys.exit(app.exec_())
    