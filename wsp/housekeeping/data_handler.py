#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jun 23 12:34:10 2020

data_handler.py

This file is part of wsp

# PURPOSE #
This module has dedicated QThread data acquisition (DAQ)loops that run at
various times and log system information. It is instatiated by the
housekeeping class.

A writer thread uses the pygetdata library to log the housekeeping data to
dirfile directories using the getdata standard. This data is stored
as binary files, one for each field to be monitored from the housekeeping
script. These binary files and the database key, stored in the format file,
can be read and visualized in real time using KST.

@author: nlourie
"""




# system packages
import sys
import time
import os
import numpy as np
#import time
from datetime import datetime
import Pyro5.core
import Pyro5.server
from PyQt5 import QtCore#, uic, QtGui, QtWidgets
#import functools
import traceback
import threading

# add the wsp directory to the PATH
wsp_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(1, wsp_path)
print(f'data_handler: wsp_path = {wsp_path}')



class hk_loop(QtCore.QThread):

    def __init__(self,config, state, curframe, schedule, telescope, mirror_cover, labjacks, 
                 counter, dome, chiller, powerManager, ephem, 
                 #viscam, ccd, summercamera, wintercamera, 
                 camdict, fwdict,
                 robostate, sunsim = False, verbose = False, ns_host = None, logger = None):
        QtCore.QThread.__init__(self)
        # loop execution number
        self.index = 0
        self.timestamp = datetime.utcnow().timestamp()

        # subclass the methods passed in (ie, the hardware systems)
        self.telescope = telescope
        self.schedule = schedule
        self.labjacks = labjacks
        self.counter = counter
        self.dome = dome
        self.chiller = chiller
        self.powerManager = powerManager
        self.ephem = ephem
        #self.viscam = viscam
        #self.ccd = ccd
        #self.summercamera = summercamera
        #self.wintercamera = wintercamera
        self.camdict = camdict
        self.fwdict = fwdict
        self.mirror_cover = mirror_cover
        self.robostate = robostate
        self.verbose = verbose
        self.sunsim = sunsim
        self.ns_host = ns_host
        self.logger = logger
        # pass the config to the thread
        self.config = config
        
        # give thread access to these methods to update the data as it comes in
        self.state = state
        self.curframe = curframe
        
        # describe the loop rate
        self.rate = 'hk'
        self.dt = int(np.round(self.config['daq_dt'][self.rate],0))
        
        # set up the connection to the pyro5 server to get the simulated time if we're in sunsim mode
        if self.sunsim:
            self.setup_sunsim_connection()
        
        self.timer = QtCore.QTimer()
        self.timer.setInterval(self.dt)
        self.timer.timeout.connect(self.update_status)
        self.timer.start()
        #self.exec()
        print(f'datahandler: running housekeeping update at dt = {self.dt} ms, in thread {self.currentThread()}')


    def __del__(self):
        self.wait()

    def get(self, varname, default_val = -999):
        try:
            return eval( 'self.' + varname)
        except Exception as e:
            #print('could not get thing: ',e)
            return default_val
        
    def setup_sunsim_connection(self):
        if self.verbose:
            self.log(f'(Thread {threading.get_ident()}) hk_loop: creating pyro connection to sun simulator')
        # init the remote object
        try:
            time.sleep(1)
            ns = Pyro5.core.locate_ns(host = self.ns_host)
            uri = ns.lookup('sunsim')
            self.remote_object = Pyro5.client.Proxy(uri)
            self.connected = True
        except Exception as e:
            self.connected = False
            msg = f'data_handler: connection with remote sunsim object failed: {e}'
            if self.logger is None:
                print(msg)
            else:
                self.logger.exception(msg)
            pass
        pass
    
    def get_sunsim_timestamp(self):
        if self.connected:
            #print('trying to get sunsim timestamp')
            try:
                remote_state = self.remote_object.GetStatus()
                
                return remote_state['timestamp']
                
            except Exception as e:
                self.connected = False
                self.logger.error(f'could not get sunsim timestamp: {e}')
                return -777

        
        else:
            self.setup_sunsim_connection()
            return -777
            
    def update_status(self, default_value = -999):
        self.index +=1
        
        # THIS IS USED TO ADD A TIMESTAMP TO THE STATE DICTIONARY
        """if self.sunsim:
            self.timestamp = self.get_sunsim_timestamp
            
            pass
        else:
            pass
        """
        if self.sunsim:
            try:
                sunsim_timestamp = self.get_sunsim_timestamp()
                self.timestamp = sunsim_timestamp
                
                #print(f'sunsim_timestamp = {sunsim_timestamp}')
            except Exception as e:
                self.timestamp = -888
                print(f'could not get sunsim timestamp: {e}')
        else:
            self.timestamp = datetime.utcnow().timestamp()
        self.state.update({'timestamp' : self.timestamp})
        
        
        # is it faster to put the labjack poll here?
        #self.labjacks.read_all_labjacks()


        for field in self.config['fields']:

            #TODO: NPL 3-8-21 making just a single housekeeping loop, so ignoring the rate
            try:
                # update the state and frame dictionaries
                curval = self.get(self.config['fields'][field]['var'])
                self.state.update({field : curval})
                
                
            except Exception as e:
                """
                we end up here if there's a problem either getting the field,
                or with the config for that field. either way log it and
                just keep moving
                """
                if self.verbose:
                    print(f'datahandler: could not update field [{field}] due to {e.__class__}: {e}')
                pass
            
        # add in the text fields
        for field in self.config['header_fields']:
            try:
                 # update the state and frame dictionaries
                 curval = self.get(self.config['header_fields'][field]['var'])
                 self.state.update({field : curval})
                 
            except Exception as e:
                 """
                 we end up here if there's a problem either getting the field,
                 or with the config for that field. either way log it and
                 just keep moving
                 """
                 if self.verbose:
                     print(f'datahandler: could not update field [{field}] due to {e.__class__}: {e}')
                 pass
     
        
        
class daq_loop(QtCore.QThread):
    """
    This version follows the approach here: https://stackoverflow.com/questions/52036021/qtimer-on-a-qthread
    This makes sure that the QTimer belongs to *this* thread, not the thread that instantiated this QThread.
    To do this it forces the update function and Qtimer to be in the namespace of the run function,
    so that the timer is instantiated by the run (eg start) command
    
    This is a generic QThread which will execute the specified function
    at the specified cadence.

    It is meant for polling different sensors or instruments or servers
    each in their own thread so they don't bog each other down.
    """
    def __init__(self, func, dt, name = '', print_thread_name_in_update = False, thread_numbering = 'PyQt', autostart = True, *args, **kwargs):
        QtCore.QThread.__init__(self)

        self.index = 0
        self.name = name
        
        # define the function and options that will be run in this daq loop
        self.func = func
        self.args = args
        self.kwargs = kwargs

        # describe the loop rate
        self.dt = int(np.round(dt,0))
        
        # keep this as an option to debug and print out the thread of each operation
        self._print_thread_name_in_update_ = print_thread_name_in_update
        # how do you want to display the thread? if either specify 'pyqt', or it will assume normal, eg threading.get_ident()
        self._thread_numbering_ = thread_numbering.lower()
        
        # start the thread itself
        if autostart:
            self.start()
    
    
    def run(self):
        def update():
            ### POLL THE DATA ###
            try:
                self.func(*self.args, **self.kwargs)
                
                if self._print_thread_name_in_update_:
                    if self._thread_numbering_ == 'pyqt':
                        print(f'{self.name}: running func: <{self.func.__name__}> in thread {self.currentThread()}')
                    else:
                        print(f'{self.name}: running func: <{self.func.__name__}> in thread {threading.get_ident()}')
            except Exception as e:
                '''
                do nothing, don't want to clog up the program with errors if there's
                a problem. let this get handled elsewhere.
                '''
                print(f'could not execute function <{self.func.__name__}> because of {type(e)}: {e}')
                print(f'FULL TRACEBACK: {traceback.format_exc()}')
                pass
    
            self.index += 1
        
        print(f'{self.name}: starting timed loop')
        self.timer = QtCore.QTimer()
        self.timer.setInterval(self.dt)
        self.timer.timeout.connect(update)
        self.timer.start()
        self.exec()
        
       
    def __del__(self):
        self.wait()
    
    
''' 
class write_thread(QtCore.QThread):

    def __init__(self,config, dirfile, state, curframe):
        QtCore.QThread.__init__(self)

        # pass the config to the thread
        self.config = config

        # give thread access to these methods to update the data as it comes in
        #self.state = state
        self.curframe = curframe
        self.db = dirfile

        self.index = 0
        self.dt = self.config['write_dt']

        self.timer = QtCore.QTimer()
        self.timer.setInterval(self.dt)
        self.timer.timeout.connect(self.update)
        self.timer.start()
        #self.exec()
        print(f'datahandler: running dirfile write in thread {self.currentThread()}')


    def __del__(self):
        self.wait()

    def update(self):
        # Only print the even numbers
        #print(f'state = {self.state}')
        #print('writethread: saving frame to dirfile')

        self.index +=1

        # write out all the fields in the current frame to the dirfile
        for field in self.curframe.keys():
            #print(f'writethread: writing to {field}: {self.curframe[field]}')
            self.db.write_field(field, self.curframe[field], start_frame = 'last')
'''

