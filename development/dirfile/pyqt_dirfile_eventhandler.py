#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jun 16 12:30:12 2020

This is an attempt to recreate Barth's "dirfile_maker_simple.c" code in Python,
downloaded from here: https://sourceforge.net/p/getdata/mailman/message/29184811/
using timing methods from PyQt5

@author: nlourie
"""

import numpy as np
from datetime import datetime
import os
import time
import struct
from PyQt5 import uic, QtCore, QtGui, QtWidgets
import signal
import sys
import easygetdata as egd
import pygetdata as gd
import yaml
import copy

#%%

class slow_loop(QtCore.QThread):
    
    def __init__(self,config, state, curframe):
        QtCore.QThread.__init__(self)
        # loop execution number
        self.index = 0
        
        # pass the config to the thread
        self.config = config
        
        # give thread access to these methods to update the data as it comes in
        self.state = state
        self.curframe = curframe

        self.dt = self.config['daq_dt']['slow']
        
        
    def __del__(self):
        self.wait()
    
    def update(self):
        # Only print the even numbers
        self.index +=1
    
        # update the data
        # describe the mapping between variables and data
        self.map = dict({
            'scount' : self.index
            })
        
        # update the state and frame dictionaries
        for field in self.map.keys():
            curval = self.map[field]
            # update the state variables
            self.state.update({ field : curval })
        
            # update the vectors in the current frame
            # shift over the vector by one, then replace the last
            self.curframe[field] = np.append(self.curframe[field][1:], curval)
            
        print(f'slowloop: count = {self.index}, state = {self.state}')
 
        
    def run(self):
        print("slowloop: starting")
        

class fast_loop(QtCore.QThread):
    
    def __init__(self,config, state, curframe):
        QtCore.QThread.__init__(self)
        
        # loop execution number
        self.index = 0
        
        # pass the config to the thread
        self.config = config
        
        # give thread access to these methods to update the data as it comes in
        self.state = state
        self.curframe = curframe
        
        
        
        self.dt = self.config['daq_dt']['fast']
        
    def __del__(self):
        self.wait()
    
    def update(self):
        # Only print the even numbers
        self.index +=1
        print(f'fastloop: count = {self.index}')
        
        # update the data
        # describe the mapping between variables and data
        self.map = dict({
            'fcount' : self.index
            })
        
        # update the state and frame dictionaries
        for field in self.map.keys():
            curval = self.map[field]
            # update the state variables
            self.state.update({ field : curval })
        
            # update the vectors in the current frame
            # shift over the vector by one, then replace the last
            self.curframe[field] = np.append(self.curframe[field][1:], curval)
        
    def run(self):
        print("fastloop: starting")
        
        while True:
            self.update()
            time.sleep(self.dt)

        '''
        self.timer = QtCore.QTimer()
        self.timer.setInterval(self.dt)
        self.timer.timeout.connect(self.update)
        self.timer.start()
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
        
    def __del__(self):
        self.wait()
    
    def update(self):
        # Only print the even numbers
        #print(f'state = {self.state}')
        print('writethread: saving frame to dirfile')
        self.index +=1
        
        # write out all the fields in the current frame to the dirfile
        for field in self.curframe.keys():
            print(f'writethread: writing to {field}: {self.curframe[field]}')
            self.db.write_field(field, self.curframe[field], start_frame = 'last')
            
        
    def run(self):
        print("writethread: starting")
 
        while True:
            self.update()
            time.sleep(self.dt)
        ''' 
        self.timer = QtCore.QTimer()
        self.timer.setInterval(self.dt)
        self.timer.timeout.connect(self.update)
        self.timer.start()
        '''
    


class main(QtCore.QObject):                     
    def __init__(self, config, parent=None ):            
        super(main, self).__init__(parent)   
        
        # store the config
        self.config = config
        
        # create the dirfile directory
        now = datetime.utcnow() # or can use now for local time
        #now = str(int(now.timestamp())) # give the name the current ctime
        now_str = now.strftime('%Y%M%d_%H%M%S') # give the name a more readable date format
        self.dirname = now_str + '.dm'
        
        # define the housekeeping data dictionaries
        # samples per frame for each daq loop
        self.spf = dict()
        
        # current state values
        self.state = dict()
        
        # vectors holding all the samples in the current frame
        self.curframe = dict()
        
        # build the dictionaries for current data and fame
        self.build_dicts()
        
        # create the dirfile
        self.create_dirfile()
        
        # define the DAQ loops
        self.fastloop = fast_loop(config = config, state = self.state, curframe = self.curframe)
        self.slowloop = slow_loop(config = config, state = self.state, curframe = self.curframe)
        self.writethread = write_thread(config = config, dirfile = self.df, state = self.state, curframe = self.curframe)
        
        # start up the DAQ loops
        self.fastloop.timer = QtCore.QTimer()
        self.fastloop.timer.setInterval(self.fastloop.dt)
        self.fastloop.timer.timeout.connect(self.fastloop.update)
        self.fastloop.timer.start()
        
        self.slowloop.timer = QtCore.QTimer()
        self.slowloop.timer.setInterval(self.slowloop.dt)
        self.slowloop.timer.timeout.connect(self.slowloop.update)
        self.slowloop.timer.start()

        self.writethread.timer = QtCore.QTimer()
        self.writethread.timer.setInterval(self.writethread.dt)
        self.writethread.timer.timeout.connect(self.writethread.update)
        self.writethread.timer.start()
        '''
        self.fastloop.start()
        self.slowloop.start()
        self.writethread.start()
        '''
        
    def makeSymlink(self):
        #/* make a link to the current dirfile - kst can read this to make life easy... */
        try:
            os.symlink(self.dirname,'dm.lnk')
        except FileExistsError:
            print('deleting existing symbolic link')
            os.remove('dm.lnk')
            os.symlink(self.dirname,'dm.lnk')
                
    def create_dirfile(self):
        """
        Create the dirfile to hold the data from the DAQ loops
        All the fields from the config file will be added automatically
        """
        # create the dirfile database
        self.df = egd.EasyGetData(self.dirname, "w")
        
        #/* make a link to the current dirfile - kst can read this to make life easy... */
        try:
            os.symlink(self.dirname,'dm.lnk')
        except FileExistsError:
            print('deleting existing symbolic link')
            os.remove('dm.lnk')
            os.symlink(self.dirname,'dm.lnk')
        
        # add the fields from the config file to the dirfile
        for field in self.config['fields']:
            self.df.add_raw_entry(field = field, 
                                  spf = self.spf[self.config['fields'][field]['rate']],
                                  dtype = np.dtype(self.config['fields'][field]['dtype']),
                                  units = self.config['fields'][field]['units'],
                                  label = self.config['fields'][field]['label'])
        
        
        
    def build_dicts(self):
        """
        gets the fields and daq rates from the config file
        uses daq rates to calculate the samples per frame (spf) of each 
        field and build the vectors to hold the data for the current frame
        """
        
        # go through each daq loop in the config file and build the HK dictionaries
        for rate in self.config['daq_dt']:
            # calculate the spf for each daq loop
            spf = int(self.config['write_dt']/self.config['daq_dt'][rate])
            self.spf.update({rate : spf})
            print(f'{rate} daq loop: {spf} samples per frame')
            
        # go through all the fields
        for field in self.config['fields']:
            
            # add an item to the state dictionary, initialize with None
            self.state.update({field : None})
            print(f'adding field "{field}" to state dictionary')
            
            # add a numpy array item to the curframe dictionary
            spf = self.spf[self.config['fields'][field]['rate']]
            dtype = np.dtype(self.config['fields'][field]['dtype'])         
            self.curframe.update({field : np.full(spf, None, dtype = dtype)})
            print(f'adding vector with len = {spf} and type {dtype} to current frame dictionary')
# add the fields to the dirfile


#%%
#config_file = 'hk_config.yaml'
#config = yaml.load(open(config_file), Loader = yaml.FullLoader)
#%%

        

def sigint_handler(*args):
    """Handler for the SIGINT signal."""
    sys.stderr.write('\r')
    QtWidgets.QApplication.quit()

if __name__ == "__main__":
    signal.signal(signal.SIGINT, sigint_handler)
    app = QtWidgets.QApplication(sys.argv)

    config_file = 'hk_config.yaml'
    config = yaml.load(open(config_file), Loader = yaml.FullLoader)
    mainthread = main(config = config)

    sys.exit(app.exec_())
