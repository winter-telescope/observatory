#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Sep 23 17:54:52 2020
labjack.py

This file is part of wsp

# PURPOSE #
The purpose of this module is to 


@author: nlourie
"""
# system packages
import sys
import os
import numpy as np
import time
import signal
from labjack import ljm
import matplotlib.pyplot as plt

# add the wsp directory to the PATH
wsp_path = os.path.dirname(os.getcwd())
sys.path.insert(1, wsp_path)

from utils import utils

class labjack(object):
    
    def __init__(self,config_file):
        self.config = utils.loadconfig(config_file)
        self.connect()
        self.input_channels = []
        self.setup_channels()
        self.read_all()
    
    def connect(self):
        self.lj_type = self.config['lj_type']
        self.conn_type = self.config['conn_type']
        self.address = self.config['address']
        try:
            self.handle = ljm.openS(self.lj_type, self.conn_type, self.address)
        except Exception as e:
            print(f'Could not connect to labjack [type = {self.lj_type}, conn_type = {self.conn_type}, addr = {self.address}] due to {type(e)}: {e}')
    def setup_ain(self):
        """
        loop through all the AIN entries in the config file.
        for each AIN entry, add a key:value pair to the setup dictionary,
        then use eWriteNames to send the channel options to the labjack
        """
        opts = dict()
        print("SETTING UP ANALOG INPUTS:")
        channel_type = 'ANALOG_INPUTS'
        for channel_name in self.config[channel_type]:
            # add each channel to the input channel list
            self.input_channels.append(channel_name)
            
            # load in the options from the config file to write out to the labjack
            print(f'    > getting options for {channel_name}')
            for opt in self.config[channel_type][channel_name].keys():
                val = self.config[channel_type][channel_name][opt]
                opt_text = channel_name + '_' + opt
                print(f'      > {opt_text}: {val}')
                opts.update({opt_text : val})
        
        # send the options to the labjack
        ljm.eWriteNames(self.handle, len(opts), opts.keys(), opts.values())
    
    def setup_dio(self):
        """
        loop through all the DIGITAL_INPUT entries in the config file.
        each digital input is an entry in the digital input list. Set 
        all of these channels to input by reading them with eReadNames
        
        loop through all the DIGITAL_OUTPUT entries, and add them and their
        initial OUTPUT values to an options dictionary, then write them all
        to the labjack with eWriteNames
        """
        
        channel_type = 'DIGITAL_INPUTS'
        digital_inputs = self.config[channel_type]
        
        
        # read in the digital inputs to set them as input channels on the labjack
        print("SETTING UP DIGITAL INPUTS:")
        for ch in digital_inputs:
            # add the digital inputs to the input channel list
            self.input_channels.append(ch)
            print(f'    > adding  {ch}')
        # send the options to the labjack
        ljm.eReadNames(self.handle, len(digital_inputs), digital_inputs)
        
        opts = dict()
        channel_type = 'DIGITAL_OUTPUTS'
        print("SETTING UP DIGITAL OUTPUTS")
        for channel_name in self.config[channel_type]:
            print(f'    > getting options for {channel_name}')
            opt_text = channel_name
            val = self.config[channel_type][channel_name]['OUTPUT']
            print(f'      > OUTPUT: {val}')
            opts.update({opt_text : val})
            
        # send the options to the labjack
        ljm.eWriteNames(self.handle, len(opts), opts.keys(), opts.values())
    
    def setup_dac(self):
        pass
    
    def setup_channels(self):
        try:
            self.setup_ain()
        except Exception as e:
            pass
        
        try:
            self.setup_dio()
        except Exception as e:
            pass
        
        try:
            self.setup_dac()
        except Exception as e:
            pass
    
    def dio_on(self):
        # turn on a dio channel
        pass

    def dio_off(self):
        # turn off a dio channel
        pass
    
    def read_all(self):
        # read all of the inputs
        #print(f'reading labjack at {self.address}')
        vals = ljm.eReadNames(self.handle, len(self.input_channels), self.input_channels)

        self.state = dict(zip(self.input_channels,vals))
        #self.print_state()
    def print_state(self):
        print()
        print(f'LJ @ {self.address} CURRENT STATE:')
        for key in self.state.keys():
            print(f'\t{key}: {self.state[key]}')

class labjack_set(object):
    
    """
    the idea here is to create on object which holds a dictionary of labjack instance
    objects, one for each one in the system.
    
    it can be used to read the state of all the labjacks with one function
    """
    def __init__(self, config, base_directory):
        
        self.labjacks = dict() # a dictionary of labjack objects
        self.config = config
        self.base_directory = base_directory
        self.setup_labjacks()
    
    def setup_labjacks(self):
        """
        takes in the winter configuration and the base directory,
        and returns an object which holds a dictionary of labjack objects, one for each labjack specified
        in the winter configuration
        """
        for lj_name in self.config['labjacks']:
                try:
                    # create a new labjack object by loading the config for each labjack
                    labjack_config_file = self.base_directory + '/config/' + self.config['labjacks'][lj_name]['config']
                    print(f'labjacks: trying to create new labjack object for labjack [{lj_name}] using config from {labjack_config_file}')
                    lj = labjack(labjack_config_file)
                    
                    # add the new labjack object to the dictionary of labjack objects
                    self.labjacks.update({lj_name : lj})
                    
                    # announce that the labjack has been added properly
                    print(f'labjacks: added labjack [{lj_name}] to housekeeping labjack dictionary')
                    
                except Exception as e:
                    print(f'labjacks: could not set up labjack [{lj_name}], due to {type(e)}: {e}')

    
    def read_all_labjacks(self):
        """
        updates the status of all the labjacks by reading in all of the 
        input_channels for each labjack
        """
        for lj_name in self.labjacks.keys():
            self.labjacks[lj_name].read_all()
            
        
    def print_all_labjack_states(self):
        for lj_name in self.labjacks.keys():
            self.labjacks[lj_name].print_state()
   
if __name__ == '__main__':
    """
    config_file = wsp_path + '/config/labjack0_config.yaml'
    
    lj = labjack(config_file)
    
    lj.read_all()
    lj.print_state()
    """
    
    config = utils.loadconfig(wsp_path + '/config/config.yaml')
    
    lj = labjack_set(config, wsp_path)
    
    ch = []
    
    for i in range(10):
        lj.read_all_labjacks()
        v = lj.labjacks['lj0'].state['AIN1']
        ch.append(v )
        print(f'lj0: AIN1 = {v}')
        time.sleep(0.5)
        
    plt.figure()
    plt.plot(ch)
    #%%
    """
    fioState = 1
    aValues = [fioState]
    aNames = ["FIO3"]
    ljm.eWriteNames(lj.handle, len(aNames), aNames, aValues)
    """