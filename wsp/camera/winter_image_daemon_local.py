#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Oct  3 13:51:24 2023

# winter_image_daemon_local.py

WINTER Image Daemon Handler

This file is part of WSP

@author: nlourie
"""


import os
#import numpy as np
import sys
import Pyro5.core
import Pyro5.server
import Pyro5.errors
#import traceback as tb
from datetime import datetime
from PyQt5 import QtCore
import logging
import time
import astropy.io.fits as fits
import json
# add the wsp directory to the PATH
wsp_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(1, wsp_path)
print(f'winter image daemon handler: wsp_path = {wsp_path}')
from utils import utils
from utils import logging_setup
#from housekeeping import data_handler
try:
    import fitsheader
except:
    from camera import fitsheader

class PyroCommunicationError(Exception):
    pass

class WINTERImageHandler(QtCore.QObject):    
    '''
    Using a QObject so that it can signals. The problem is that all the Pyro
    calls for a given proxy have to be handled in a single thread. To execute commands
    from outside this thread let's try using the signal/slot approach.
    '''
    newCommand = QtCore.pyqtSignal(object)
    
    imageSaved = QtCore.pyqtSignal()
    
    def __init__(self, base_directory, config, camname, daemon_pyro_name,
                 ns_host = None,
                 logger = None, verbose = False,
                 ):
        super(WINTERImageHandler, self).__init__()
        
        # Define attributes
        self.base_directory = base_directory
        self.config = config
        self.camname = camname
        self.daemonname = daemon_pyro_name # the name that the camera daemon is registered under
        self.ns_host = ns_host # the ip address of the pyro name server, eg `192.168.1.10`
        self.state = dict()
        self.hk_state = dict()
        self.remote_state = dict()
        self.connected = False
        self.logger = logger
        self.default = self.config['default_value']
        self.verbose = verbose
        
        self.reconnect_attempts = 3

        
        
        # connect the signals and slots
        self.newCommand.connect(self.doCommand)
                
        # Startup
        # setup connection to pyro ccd
        self.init_remote_object()
        self.update_state()
        
        
    def log(self, msg, level = logging.INFO):
        msg = f'{self.daemonname}_local: {msg}'
        if self.logger is None:
                print(msg)
        else:
            self.logger.log(level = level, msg = msg) 
    
    
    def AutoconnectFunction(func):
        """
        This is a simple wrapper to simplify the try/except statement
        when executing a function in the command list.
        """
        def connect_then_execute(self, *args, **kwargs):
            
            # make sure we're connected to the daemon
            for i in range(self.reconnect_attempts):
                if self.verbose:
                    self.log(f'checking connection to image daemon, attempt {i+1}/{self.reconnect_attempts}')
                self.update_state()
                if self.verbose:
                    self.log(f'self.connected = {self.connected}')
                if self.connected:
                    break
                
            if not self.connected:
                msg = f'command {func} not executed! could not connect to daemon after {self.reconnect_attempts} attempts'
                raise PyroCommunicationError(msg)
            else:
                # now excecute the function
                func(self, *args, **kwargs)
            # try:
            #     func(*args, **kwargs)
                
                
            # except Exception as e:
            #     '''
            #     Exceptions are already handled by the argument parser
            #     so do nothing here.
            #     '''
            #     msg = (f'Could not execute command {func.__name__}: {e}')
            #     raise Exception(e)
                
                
            #     pass
        return connect_then_execute
    
    
    ###    
    def doCommand(self, cmd_obj):
        """
        This is connected to the newCommand signal. It parses the command and
        then executes the corresponding command from the list below

        using this as a reference: (source: https://stackoverflow.com/questions/6321940/how-to-launch-getattr-function-in-python-with-additional-parameters)     
        
        """
        cmd = cmd_obj.cmd
        args = cmd_obj.args
        kwargs = cmd_obj.kwargs
        
        #print(f'ccd: caught doCommand signal: {cmd}, args = {args}, kwargs = {kwargs}')

        try:
            getattr(self, cmd)(*args, **kwargs)
        except:
            pass
        
    def init_remote_object(self):
        # init the remote object
        try:
            if self.verbose:
                self.log(f'init_remote_object: trying to connect to {self.daemonname}')
            ns = Pyro5.core.locate_ns(host = self.ns_host)
            uri = ns.lookup(self.daemonname)
            self.remote_object = Pyro5.client.Proxy(uri)
            # connect
            self.remote_object._pyroBind()
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
                    self.log(f'camera: could not update remote state: {e}')
                self.connected = False
                pass    
           
            try:
                self.parse_state()
                
                
            except Exception as e:
                if self.verbose:
                    self.log(f'camera: could not parse remote state: {e}')
                pass
    
            
    def parse_state(self):
        '''
        Do any conditioning we need to properly handle and parse the state dictionary
        '''
         
        
        # update the rest of the stuff
        for key in self.remote_state.keys():
            self.state.update({key : self.remote_state[key]})
    
        self.state.update({'camname' : self.camname,
                           'is_connected' : self.connected,
                           
                           })
        
 
    
    def print_state(self):
        self.update_state()
        print(f'state = {json.dumps(self.state, indent = 2)}')
        
    #### EXTERNAL METHODS ####
    @AutoconnectFunction
    def get_focus_from_imgpathlist(self, images, dirpath = None,
                                   board_ids_to_use = None, plot_all = False):
        
        self.remote_object.get_focus_from_imgpathlist(images = images, 
                                                      board_ids_to_use = board_ids_to_use,
                                                      plot_all = plot_all)
    @AutoconnectFunction
    def validate_bias(self, image_filepath):
        
        results = self.remote_object.validate_bias(image_filepath)
    
        return results
    
    @AutoconnectFunction
    def killImageDaemon(self):
        self.remote_object.killImageDaemon()
    

        
# Try it out
if __name__ == '__main__':


    config = utils.loadconfig(wsp_path + '/config/config.yaml')
        
    logger = logging_setup.setup_logger(wsp_path, config)        
    
    logger = None
    verbose = False
    
    """
    def __init__(self, base_directory, config, daemon_pyro_name,
                 pyro_ns_host = None,
                 logger = None, verbose = False,
                 ):
    """
    winter_image_handler = WINTERImageHandler(wsp_path, config, camname = 'winter',
                       daemon_pyro_name = 'WINTERImageDaemon',
                       ns_host = '192.168.1.10', logger = logger, verbose = verbose)
    
    winter_image_handler.print_state()
    print()
    print()
    winter_image_handler.killImageDaemon()
    """
    while True:
        try:
            #cam.update_state()
            cam.print_state()
            time.sleep(1)
            
        except KeyboardInterrupt:
            break
    """
