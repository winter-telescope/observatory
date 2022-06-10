#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jun  1 11:33:34 2022

A daemon for communicating with the SUMMER accesories. Keeping the viscam
name to keep consistent with the nomenclature within wsp.

This daemon connects and communicates with the flask web server on the SUMMER
raspberry pi to control the summer filter wheel, summer shutter, and other
(future) hardware.

@author: winterpi
"""

import requests
import os
import Pyro5.core
import Pyro5.server
from PyQt5 import QtCore
import numpy as np
import sys
import signal
import threading
import time
import logging
import json
import yaml
from datetime import datetime

# add the wsp directory to the PATH
wsp_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(1, wsp_path)
print(f'wsp_path = {wsp_path}')

from daemon import daemon_utils
#from utils import logging_setup

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

class CommandHandler(QtCore.QObject):
    
    newReply = QtCore.pyqtSignal(str)
    #newCommand = QtCore.pyqtSignal(object)
    newRequest = QtCore.pyqtSignal(object)
    newStatus = QtCore.pyqtSignal(object)
    
    def __init__(self, config, logger = None, verbose = False):
        super(CommandHandler, self).__init__()
        
        self.config = config
        self.url = self.config['viscam_url']
        
    def doCommand(self, cmd_obj):
            """
            This is connected to the newRequest signal. It parses the command and
            then executes the corresponding command from the list below

            using this as a reference: (source: https://stackoverflow.com/questions/6321940/how-to-launch-getattr-function-in-python-with-additional-parameters)     
            
            """
            print(f'viscamd cmd handler: caught doCommand signal: {cmd_obj.cmd}')
            cmd = cmd_obj.cmd
            args = cmd_obj.args
            kwargs = cmd_obj.kwargs
            
            try:
                getattr(self, cmd)(*args, **kwargs)
            except:
                pass
    
    # send a command to the filter wheel
    # -1: home the filter wheel (sends to pos 0)
    # 1-6 - set filter wheel to position 1-6
    # 8 - get current position
    
    def send_filter_wheel_command(self, position):
        print(f'going to try to execute the filter wheel move')
        string = self.url + "filter_wheel?n=" + str(position)   
        print(string)
        try:
            res = requests.get(string, timeout=10)
            print("Status", res.status_code, "Response: ", res.text)

            remote_state = json.loads(res.text)
            
            if res.status_code != 200:
                raise Exception

            #self.parse_state(remote_state)
            self.newStatus.emit(remote_state)
            return 1
        except:
            self.log(f'Filter wheel is not responding')
            return 0             
                 
                
   
    # send a command to the shutter
    # 0 - close the shutter
    # 1 - open the shutter    
    def send_shutter_command(self, state):
        string = self.url + "shutter?open=" + str(state)
        try:
            res = requests.get(string, timeout=10)
            status = res.status_code
            #print("Status", status, "Response: ", res.text)
            self.log(f'Shutter status {status}, {res.text}')
            return status
        except:
            #print("Raspi is not responding")
            self.log(f'Shutter is not responding')
            return 0
    
    # check what state the shutter is in
    # CAUTION: this is a global variable in the web server,
    # we cannot pull the actual shutter state
    # do not trust this variable
    # 0 - shutter is closed
    # 1 - shutter is open
    # 3 - unknown shutter state
    """
    def check_shutter_state(self):
        string = self.url  + "shutter_state"
        try:
            res = requests.get(string, timeout=10)
            status = res.status_code
            if res.text[0] == "3":
                #print("Status: ", status, " Unknown shutter state")
                return -1
            elif res.text[0] == "1":
                #print("Status: ", status, "Shutter state is ", res.text)
                return 1
            elif res.text[0] == "0":
                #print("Status: ", status, "Shutter state is ", res.text)
                return 0
            else:
                #print("Status", status, "Response: ", res.text)
                #return status
                return -1
        except:
            #print("Raspi is not responding")
            return -1
    """
    
        

class CommandThread(QtCore.QThread):
    newReply = QtCore.pyqtSignal(int)
    newStatus = QtCore.pyqtSignal(object)
    newRequest = QtCore.pyqtSignal(object)
    
    def __init__(self, config, logger = None,  verbose = False):
        super(QtCore.QThread, self).__init__()
        
        self.config = config
        self.logger = logger
        self.verbose = verbose
    
    def HandleRequest(self, request_object):
        self.newRequest.emit(request_object)
    
    def DoReconnect(self):
        #print(f'(Thread {threading.get_ident()}) Main: caught reconnect signal')
        self.doReconnect.emit()
    
    def run(self):    
        def SignalNewReply(reply):
            self.newReply.emit(reply)
        def SignalNewStatus(status):
            self.newStatus.emit(status)
        
        self.commandHandler = CommandHandler(config = self.config, logger = self.logger, verbose = self.verbose)
        # if the newReply signal is caught, execute the sendCommand function
        self.newRequest.connect(self.commandHandler.doCommand)
        self.commandHandler.newReply.connect(SignalNewReply)
        self.commandHandler.newStatus.connect(SignalNewStatus)
        
        self.exec_()



class Viscam(QtCore.QObject):
    
    
    commandRequest = QtCore.pyqtSignal(object)

    
    def __init__(self,  config, logger = None, verbose = False):
        
        super(Viscam, self).__init__()   
        
        self.config = config
        self.url = self.config['viscam_url']
        self.state = dict()
        self.logger = logger
        self.verbose = verbose
        
        self.commandThread = CommandThread(config = self.config, logger = self.logger, verbose = self.verbose)
        # connect the signals and slots
        
        self.commandThread.start()
        
        self.commandThread.newStatus.connect(self.parse_state)
        self.commandRequest.connect(self.commandThread.HandleRequest)
        #self.commandThread.newReply.connect(self.updateCommandReply)
        self.log(f'viscamd: running in thread {threading.get_ident()}')
        """
        self.dt = dt
        self.timer = QtCore.QTimer()
        self.timer.setInterval(self.dt)
        self.timer.timeout.connect(self.update)
        self.timer.start()
        """
        
    def update(self):

        for pduname in self.pdu_dict:
            
            # query the pdu status
            pdustate = self.pdu_dict[pduname].getState()
            self.state.update({pduname : pdustate})
            #print(pdustate['status'][7])


    def log(self, msg):
        if self.logger is None:
            print(f'Viscam: {msg}')
        else:
            self.logger.info(msg)
    
    def parse_state(self, remote_state):
        """
        run this whenever we get a new state reply from the server
        adds all key:value pairs (or rather updates) their values to the self.state
        dictionary
        """
        for key in remote_state.keys():
            try:
                self.state.update({key : remote_state[key]})
            except:
                pass
            
    def update_state(self):
        # poll the state, if we're not connected try to reconnect
        # this should reconnect down the line if we get disconnected
        """        
        connected = self.send_raspi_check()
        
        if not connected:
            self.state.update({'pi_status' : 1})
            self.state.update({'pi_status_last_timestamp'  : datetime.utcnow().timestamp()})
            
        else:
            self.state.update({'pi_status' : 1})
            self.state.update({'pi_status_last_timestamp'  : datetime.utcnow().timestamp()})
            

            self.state.update({'filter_wheel_position' : self.fw_pos})
            self.state.update({'filter_wheel_position_last_timestamp'  : datetime.utcnow().timestamp()})
            
            
            shut = self.check_shutter_state()
            self.state.update({'shutter_state' : shut})
            self.state.update({'shutter_state_last_timestamp'  : datetime.utcnow().timestamp()})
        """
        pass
        
    @Pyro5.server.expose
    def command_filter_wheel(self, pos):
        print(f'got ssignal  to move filter wheel to pos = {pos}')
        sigcmd = signalCmd('send_filter_wheel_command', pos)
        self.commandRequest.emit(sigcmd)
    
    @Pyro5.server.expose
    def getState(self):
        #print(self.state)
        return self.state 
    
class PyroGUI(QtCore.QObject):   

                  
    def __init__(self, config, logger, verbose, parent=None ):            
        super(PyroGUI, self).__init__(parent)   
        print(f'main: running in thread {threading.get_ident()}')
        
        self.config = config
        self.logger = logger
        self.verbose = verbose

        self.viscam = Viscam(config = self.config, logger = self.logger, verbose = self.verbose)
                
        self.pyro_thread = daemon_utils.PyroDaemon(obj = self.viscam, name = 'viscam')
        self.pyro_thread.start()
        
        """
        self.timer = QtCore.QTimer()
        self.timer.setInterval(500)
        self.timer.timeout.connect(self.check_pyro_queue)
        self.timer.start()
        """


            
        
def sigint_handler( *args):
    """Handler for the SIGINT signal."""
    sys.stderr.write('\r')
    
    #main.powerManager.daqloop.quit()
    
    QtCore.QCoreApplication.quit()

if __name__ == "__main__":
    
    
    app = QtCore.QCoreApplication(sys.argv)
    
    args = sys.argv[1:]
    
    
    modes = dict()
    modes.update({'-v' : "Running in VERBOSE mode"})
    
    # set the defaults
    verbose = False
    doLogging = True
    #print(f'args = {args}')
    
    if len(args)<1:
        pass
    
    else:
        for arg in args:
            
            if arg in modes.keys():
                
                # remove the dash when passing the option
                opt = arg.replace('-','')
                if opt == 'v':
                    print(f'viscamd: {modes[arg]}')
                    verbose = True
                elif opt == 'p':
                    print(f'viscamd: {modes[arg]}')
                    doLogging = False


            else:
                print(f'viscamd: Invalid mode {arg}')
    
    
    
    # set the wsp path as the base directory
    base_directory = wsp_path

    # load the config
    config_file = base_directory + '/config/config.yaml'
    config = yaml.load(open(config_file), Loader = yaml.FullLoader)
    #config.update({'viscam_url' : 'http://127.0.0.1:5001/'})
    # set up the logger
    if doLogging:
        #logger = logging_setup.setup_logger(base_directory, config)    
        logger = None
    else:
        logger = None
    
    
   
    
    
    main = PyroGUI(config, logger, verbose)


    
    signal.signal(signal.SIGINT, sigint_handler)

    # Run the interpreter every so often to catch SIGINT
    timer = QtCore.QTimer()
    timer.start(500) 
    timer.timeout.connect(lambda: None) 

    sys.exit(app.exec_())