#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jun  1 11:34:14 2022

@author: winterpi
"""

import sys
import os
import traceback as tb
import Pyro5.core
import Pyro5.client
import Pyro5.server
import Pyro5.errors
from PyQt5 import QtCore
import json
import time
import logging

# add the wsp directory to the PATH
wsp_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(1, wsp_path)
print(f'fw: wsp_path = {wsp_path}')
from utils import utils
from utils import logging_setup

class local_filterwheel(QtCore.QObject):
    '''
    Using a QObject so that it can signals. The problem is that all the Pyro
    calls for a given proxy have to be handled in a single thread. To execute commands
    from outside this thread let's try using the signal/slot approach.
    '''
    newCommand = QtCore.pyqtSignal(object)
    #def __init__(self, base_directory, config, logger):
    def __init__(self, base_directory, config, daemon_pyro_name,
                 ns_host = None,
                 logger = None, verbose = False,
                 ):
        super(local_filterwheel, self).__init__()

        # Define attributes
        self.base_directory = base_directory
        self.config = config
        self.daemonname = daemon_pyro_name # the name that the camera daemon is registered under
        self.ns_host = ns_host # the ip address of the pyro name server, eg `192.168.1.10`
        self.logger = logger
        self.verbose = verbose
        self.state = dict()

        self.defaultval = -888

        # connect the signals and slots
        self.newCommand.connect(self.doCommand)

        # Startup
        # setup connection to pyro ccd
        self.init_remote_object()
        self.update_state()

    def log(self, msg, level = logging.INFO):
        msg = f'{self.daemonname}: {msg}'
        if self.logger is None:
                print(msg)
        else:
            self.logger.info(level = level, msg = msg)

    def init_remote_object(self):
        # init the remote object
        try:
            if self.verbose:
                self.log(f'init_remote_object: trying to connect to {self.daemonname}')
            ns = Pyro5.core.locate_ns(host = self.ns_host)
            uri = ns.lookup(self.daemonname)
            self.remote_object = Pyro5.client.Proxy(uri)
            self.connected = True
        except Exception as e:
            self.connected = False
            if self.verbose:
                self.log(f'connection to remote object failed: {e}')
            pass

    def update_state(self):
        # poll the state, if we're not connected try to reconnect
        # this should reconnect down the line if we get disconnected
        #self.log(f'updating remote state: self.connected = {self.connected}')

        if not self.connected:
            if self.verbose:
                self.log(f'self.connected = {self.connected}: try to init_remote_object again')
            self.init_remote_object()


        else:
            try:
                #self.log(f'updating remote state')
                self.remote_state = self.remote_object.getStatus()
            except Exception as e:
                if self.verbose:
                    self.log(f'could not update remote state: {e}')
                self.connected = False
                pass

            try:
                self.parse_state()


            except Exception as e:
                if self.verbose:
                    self.log(f'could not parse remote state: {e}')
                #self.connected = False
                pass

    def parse_state(self):
        '''
        Do any conditioning we need to properly handle and parse the state dictionary
        '''


        # update the rest of the stuff
        for key in self.remote_state.keys():
            self.state.update({key : self.remote_state[key]})

        self.state.update({'is_connected'                   :   bool(self.remote_state.get('is_connected', self.defaultval))})

    def goto(self, pos):

        self.remote_object.goto(pos)

    def home(self):

        self.remote_object.home()


    def getEncoderLoc(self, verbose=False):
        self.remote_object.getEncoderLoc(verbose=verbose)


    def getMicrostepLoc(self, verbose=False):
        self.remote_object.getMicrostepLoc(verbose=verbose)


    def getInputStatus(self, verbose=False):
        self.remote_object.getInputStatus(verbose=verbose)


    def goToLocation(self, microstep_loc):
        self.remote_object.goToLocation(microstep_loc)

    def goToFilter(self, filter_num):
        self.remote_object.goToFilter(filter_num)


    def print_state(self):
        self.update_state()
        #print(f'Local Object: {self.msg}')
        print(f'state = {self.state}')

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

        try:
            getattr(self, cmd)(*args, **kwargs)
        except:
            pass
    def printState(self, update = True):

        if update:
            self.update_state()
        print()
        print(json.dumps(self.state, indent = 3))

# Try it out
if __name__ == '__main__':


    config = utils.loadconfig(wsp_path + '/config/config.yaml')

    logger = logging_setup.setup_logger(wsp_path, config)

    logger = None
    verbose = True

    fw = local_filterwheel(wsp_path, config, daemon_pyro_name = 'WINTERfw',
                       ns_host = 'localhost', logger = logger, verbose = verbose)

    fw.print_state()

    fw.goToFilter(3)

    fw.goToFilter(2)

    while True:
        try:
            #cam.update_state()
            fw.print_state()
            time.sleep(1)

        except KeyboardInterrupt:
            break
