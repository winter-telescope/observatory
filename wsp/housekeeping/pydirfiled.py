#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jun  1 16:24:36 2021

dirfiled.py

This file is part of wsp

# PURPOSE #
This daemon grabs the housekeeping state from WSP at a regular interval,
and fills and writes the data to the dirfile. This allows better timing,
keeps the dirfile filling and writing all in a single thread, and allows
the dirfile interface to be ignored if desired (ie if running WSP on a computer
without pygetdata)


@author: nlourie
"""

import os
import Pyro5.core
import Pyro5.server
#import time
#from PyQt5 import uic, QtGui, QtWidgets
from PyQt5 import QtCore
#from astropy.io import fits
import numpy as np
import sys
import signal
#import queue
#import threading
from datetime import datetime
import pathlib
import getopt



# add the wsp directory to the PATH
# add the wsp directory to the PATH
wsp_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(1, wsp_path)
print(f'dirfiled: wsp_path = {wsp_path}')

# winter modules

#from housekeeping import data_handler

try:
    from housekeeping import dirfile_python
except:
    import dirfile_python

#from daemon import daemon_utils

from utils import utils
from utils import logging_setup






class DirfileWriter(QtCore.QObject):
    
    """
    This is the pyro object that handles the creation of the dirfile,
    polling the published state from the Pyro nameserver, and updating the
    dirfile.
    
    NOTE:
        This inherets from QObject, which allows it to have custom signals
        which can communicate with the communication threads
    """
    
    
    def __init__(self, base_directory, config, logger, ns_host = None, verbose = False):
        super(DirfileWriter, self).__init__()
        
        self.base_directory = base_directory
        self.config = config
        self.logger = logger
        self.verbose = verbose
        self.ns_host = ns_host
        
        # define the housekeeping data dictionaries
        # samples per frame for each daq loop
        
        #dt = 0.25
        
        self.spf = self.config['dirfile_spf']#10
        self.dt = int(self.config['dirfile_write_dt']/self.spf)
        
        # current state values
        self.state = dict()
        
        # vectors holding all the samples in the current frame
        self.curframe = dict()
        self.samples_in_curframe = 0
        
        # build the dictionaries for current data and fame
        self.build_dicts()
        
        # create the dirfile
        self.create_dirfile()
        
        # connect the signals and slots
        
        # Startup
        self.init_remote_object()
        #self.update_state()
        
        # Start QTimer which updates state
        self.timer = QtCore.QTimer()
        self.timer.setSingleShot(False)
        self.timer.timeout.connect(self.update_state)
        self.timer.start(int(self.dt))
        
        
    def init_remote_object(self):
        # init the remote object
        try:
            ns = Pyro5.core.locate_ns(host = self.ns_host)
            uri = ns.lookup('state')
            self.remote_object = Pyro5.client.Proxy(uri)
            self.connected = True
        except Exception as e:
            if self.verbose:
                print(f'Could not init remote object: {e}')
            self.connected = False
            pass
        '''
        except Exception:
            self.logger.error('connection with remote object failed', exc_info = True)
        '''
    def update_state(self):
        # poll the state, if we're not connected try to reconnect
        # this should reconnect down the line if we get disconnected
        if self.verbose:
            print(f'pydirfiled: updating state')
        if not self.connected:
            self.init_remote_object()
            
        else:
            try:
                self.state = self.remote_object.GetStatus()
                
                #print(f'count = {self.state["count"]}')
                
                #self.parse_state()
                self.add_to_frame(self.state)
                
            except Exception as e:
                if self.verbose:
                    print(f'dirfiled: could not update remote state: {e}')
                pass
        
        self.samples_in_curframe += 1
        #print(f'samples in curframe = {self.samples_in_curframe}')
        if self.samples_in_curframe == self.spf:
            self.write_curframe()
        
        """
        if verbose:
            self.daqloop = data_handler.daq_loop(self.update, dt = self.dt, name = self.name, print_thread_name_in_update = True, thread_numbering = 'norm')
        else:
            self.daqloop = data_handler.daq_loop(self.update, dt = self.dt, name = self.name)
        """
    
    
    def add_to_frame(self, state):

        for field in self.config['fields']:

            #if self.config['fields'][field]['rate'] == self.rate:
            #TODO: NPL 3-8-21 making just a single housekeeping loop, so ignoring the rate
            try:
                curval = self.state.get(field, -999)
                self.curframe[field] = np.append(self.curframe[field], curval)
                
                
                
            except Exception as e:
                """
                we end up here if there's a problem either getting the field,
                or with the config for that field. either way log it and
                just keep moving
                """
                if self.verbose:
                    print(f'dirfiled: could not update field [{field}] due to {e.__class__}: {e}')
                pass
        
    def reset_curframe(self):
        self.samples_in_curframe = 0
        for field in self.config['fields']:
            self.curframe.update({field: np.array([])})
        
    def write_curframe(self):
        """
        for key in ['count']:
            print(f'curframe for {key} = {self.curframe[key]}')
        """
        for field in self.config['fields']:
            #print(f'writethread: writing to {field}: {self.curframe[field]}')
            self.df.write_field(field, self.curframe[field], start_frame = 'last')
            # now reset the curframe
        
        self.reset_curframe()
    
    def create_dirfile(self):
        """
        Create the dirfile to hold the data from the DAQ loops
        All the fields from the config file will be added automatically
        """
        # create the dirfile directory
        hk_dir = os.getenv("HOME") + '/' + self.config['housekeeping_data_directory']
        
        now = datetime.utcnow() # or can use now for local time
        #now = str(int(now.timestamp())) # give the name the current ctime
        now_str = now.strftime('%Y%m%d_%H%M%S') # give the name a more readable date format
        self.dirname = now_str + '.dm'
        self.dirpath = hk_dir + '/' + self.dirname
        
        # create the directory and filenames for the data storage
        hk_link_dir = os.getenv("HOME") + '/' + self.config['housekeeping_data_link_directory']
        hk_link_name = self.config['housekeeping_data_link_name']
        hk_linkpath = hk_link_dir + '/' + hk_link_name
        
        # create the data directory if it doesn't exist already
        pathlib.Path(hk_dir).mkdir(parents = True, exist_ok = True)
        print(f'dirfiled: making directory: {hk_dir}')
                
        # create the data link directory if it doesn't exist already
        pathlib.Path(hk_link_dir).mkdir(parents = True, exist_ok = True)
        print(f'dirfiled: making directory: {hk_link_dir}')
        
        # create the dirfile database
        #self.df = egd.EasyGetData(self.dirpath, "w")
        
        self.df = dirfile_python.Dirfile(self.dirpath)
        
        print(f'dirfiled: creating dirfile at {self.dirpath}')
        #/* make a link to the current dirfile - kst can read this to make life easy... */
        print(f'dirfiled: trying to create link at {hk_linkpath}')
        
        try:
            os.symlink(self.dirpath, hk_linkpath)
        except FileExistsError:
            print('dirfiled: deleting existing symbolic link')
            os.remove(hk_linkpath)
            os.symlink(self.dirpath, hk_linkpath)
        
        # add the fields from the config file to the dirfile
        if 'fields' in self.config:
            for field in self.config['fields']:
                # add handling for the various field types ('ftype') allowed by the dirfile standards as they come up
                
    
                self.df.add_raw_entry(field = field, 
                                      #spf = self.spf[self.config['fields'][field]['rate']],
                                      spf = self.spf,
                                      # now that we're not using easygetdata we don't need a dtype object, just a string name
                                      #dtype = np.dtype(self.config['fields'][field]['dtype']),
                                      dtype = self.config['fields'][field]['dtype'],
                                      units = self.config['fields'][field]['units'],
                                      label = self.config['fields'][field]['label'])
            
        # add in any derived fields
        if 'derived_fields' in self.config:
            for field in self.config['derived_fields']:
                ftype = self.config['derived_fields'][field]['ftype'].lower()
                if ftype == 'lincom':
                    self.df.add_lincom_entry(field = field, 
                                            input_field = self.config['derived_fields'][field]['input_field'], 
                                            slope = self.config['derived_fields'][field]['slope'], 
                                            intercept = self.config['derived_fields'][field]['intercept'],
                                            units = self.config['derived_fields'][field]['units'],
                                            label = self.config['derived_fields'][field]['label'])
                elif ftype == 'linterp':
                    self.df.add_linterp_entry(field, 
                                              input_field = self.config['derived_fields'][field]['input_field'], 
                                              LUT_file = self.base_directory + '/' + self.config['derived_fields'][field]['LUT_file'],
                                              units = self.config['derived_fields'][field]['units'],
                                              label = self.config['derived_fields'][field]['label'])
        
    
    
    
    def build_dicts(self):
        """
        gets the fields and daq rates from the config file
        uses daq rates to calculate the samples per frame (spf) of each 
        field and build the vectors to hold the data for the current frame
        """
        '''
        # go through each daq loop in the config file and build the HK dictionaries
        for rate in self.config['daq_dt']:
            # calculate the spf for each daq loop
            spf = int(self.config['write_dt']/self.config['daq_dt'][rate])
            self.spf.update({rate : spf})
            print(f'{rate} daq loop: {spf} samples per frame')
        '''    
        # go through all the fields
        for field in self.config['fields']:
            
            # add an item to the state dictionary, initialize with zeros
            self.state.update({field : None})
            if self.verbose:
                print(f'dirfiled: adding field "{field}"')
            
            # add a numpy array item to the curframe dictionary
            #spf = self.spf[self.config['fields'][field]['rate']]
            
            """
            # I don't think we need this?
            spf = self.spf
            dtype = np.dtype(self.config['fields'][field]['dtype'])         
            """
            
            # this is the old way where we had fixed length frames:
            #self.curframe.update({field : np.full(spf, 0, dtype = dtype)})
            #print(f'adding vector with len = {spf} and type {dtype} to current frame dictionary')
            
            self.curframe.update({field: np.array([])})
            
class Main(QtCore.QObject):
    ## Initialize Class ##
    def __init__(self, base_directory, config, logger, ns_host = None, opts = None,parent = None):
        super(Main, self).__init__(parent)

        self.dirfileWriter = DirfileWriter(base_directory, config, logger, ns_host)
        
    
            
        
def sigint_handler( *args):
    """Handler for the SIGINT signal."""
    sys.stderr.write('\r')
    
    #main.counter.daqloop.quit()
    
    QtCore.QCoreApplication.quit()

if __name__ == "__main__":
    
    ##### GET ANY COMMAND LINE ARGUMENTS #####
    
    args = sys.argv[1:]
    print(f'args = {args}')
    
    # set the defaults
    verbose = False
    doLogging = True
    ns_host = None
    #ns_host = '192.168.1.10'
    
    options = "vpn:"
    long_options = ["verbose", "print", "ns_host:"]
    arguments, values = getopt.getopt(args, options, long_options)
    # checking each argument
    print()
    print(f'Parsing sys.argv...')
    print(f'arguments = {arguments}')
    print(f'values = {values}')
    for currentArgument, currentValue in arguments:
        if currentArgument in ("-v", "--verbose"):
            verbose = True
            print("Running in VERBOSE mode")
        
        elif currentArgument in ("-p", "--print"):
            doLogging = False
            print("Running in PRINT mode (instead of log mode).")
        elif currentArgument in ("-n", "--ns_host"):
            ns_host = currentValue
    
    ##### RUN THE APP #####
    
    
    
    
    app = QtCore.QCoreApplication(sys.argv)
    
    # set the wsp path as the base directory
    base_directory = wsp_path

    # load the config
    config_file = base_directory + '/config/config.yaml'
    config = utils.loadconfig(config_file)
    

    
    # set up the logger
    if doLogging:
        logger = logging_setup.setup_logger(base_directory, config)    
    else:
        logger = None
    
    print(f'dirfiled: connecting with ns_host = {ns_host}')
    main = Main(base_directory = wsp_path, config = config, logger = logger, ns_host = ns_host)

    
    signal.signal(signal.SIGINT, sigint_handler)

    # Run the interpreter every so often to catch SIGINT
    timer = QtCore.QTimer()
    timer.start(500) 
    timer.timeout.connect(lambda: None) 

    sys.exit(app.exec_())
