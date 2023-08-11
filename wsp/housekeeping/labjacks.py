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
from datetime import datetime
import logging
import json

# add the wsp directory to the PATH
wsp_path = os.path.dirname(os.getcwd())
sys.path.insert(1, wsp_path)

from utils import utils

class labjack(object):

    def __init__(self,config_file, logger = None, verbose = False):
        self.config = utils.loadconfig(config_file)
        self.ljlocation = self.config.get('location', '')
        self.state = dict()
        
        self.verbose = verbose
        self.logger = logger
        
        
        
        self.dt_since_last_reconnect = 10000
        self.reinitialize()
    
    
    def log(self, msg, level = logging.INFO):
        
        msg = f'{self.ljlocation} labjack: {msg}'
        if self.logger is None:
                print(msg)
        else:
            self.logger.log(level = level, msg = msg)
    
    def setup_dio_attributes(self):
        ljtype = self.config['lj_type'].lower()
        
        fio_names = [f'FIO{n}' for n in range(8)]
        eio_names = [f'EIO{n}' for n in range(8)]
        cio_names = [f'CIO{n}' for n in range(4)]
        mio_names = [f'MIO{n}' for n in range(3)]
        self.dio_names = fio_names + eio_names + cio_names + mio_names
        
        self.n_dio = len(self.dio_names)
            
    def connect(self):
        self.last_connection_attempt_timestamp = datetime.utcnow().timestamp()
        self.dt_since_last_reconnect = datetime.utcnow().timestamp() - self.last_connection_attempt_timestamp
        self.lj_type = self.config['lj_type']
        self.conn_type = self.config['conn_type']
        self.address = self.config['address']
        try:
            self.handle = ljm.openS(self.lj_type, self.conn_type, self.address)
            self.connected = True
        except Exception as e:
            self.connected = False
            self.log(f'Could not connect to labjack [type = {self.lj_type}, conn_type = {self.conn_type}, addr = {self.address}] due to {type(e)}: {e}')
    
    def reinitialize(self):
        
        if self.dt_since_last_reconnect >= 1.0:
            self.connect()
        if self.connected:
            self.input_channels = []
            self.setup_channels()
            self.read_all()
    
    def setup_ain(self):
        """
        loop through all the AIN entries in the config file.
        for each AIN entry, add a key:value pair to the setup dictionary,
        then use eWriteNames to send the channel options to the labjack
        """
        opts = dict()
        self.log("SETTING UP ANALOG INPUTS:")
        channel_type = 'ANALOG_INPUTS'
        for channel_name in self.config[channel_type]:
            # add each channel to the input channel list
            self.input_channels.append(channel_name)

            # load in the options from the config file to write out to the labjack
            self.log(f'    > getting options for {channel_name}')
            for opt in self.config[channel_type][channel_name].keys():
                val = self.config[channel_type][channel_name][opt]
                opt_text = channel_name + '_' + opt
                self.log(f'      > {opt_text}: {val}')
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
        digital_inputs = self.config.get(channel_type, None)
        if digital_inputs is not None:
    
            # read in the digital inputs to set them as input channels on the labjack
            self.log("SETTING UP DIGITAL INPUTS:")
            for ch in digital_inputs:
                # NPL 8-8-23: now we always read all the dio all the time
                ## add the digital inputs to the input channel list
                #self.input_channels.append(ch)
                
                self.log(f'    > adding  {ch}')
            # send the options to the labjack to set the channels as inputs
            ljm.eReadNames(self.handle, len(digital_inputs), digital_inputs)


        # Set up the digital outputs
        """
        #TODO: this is sufficient for T7 labjacks, but NOT for T4.
        # T4 labjacks have the channels that can be configured as digital I/O OR
        # analog inputs. Just trying to set the digital output with a digital
        # write will NOT work if the channel is configured as analog in. My 
        # workaround was to set it as digital using the Kipling GUI, and then 
        # this works. But to do it all from code will need to implement a more
        # sophisticated bitmask handling with DIO_INHIBIT, and DIO_ANALOG_ENABLE
        # which will set the type. See here:
            # https://labjack.com/pages/support?doc=/datasheets/t-series-datasheet/131-flexible-io-t4-only-t-series-datasheet/
        """
        opts = dict()
        channel_type = 'DIGITAL_OUTPUTS'
        digital_outputs = self.config.get(channel_type, None)
        if digital_outputs is not None:
            self.log("SETTING UP DIGITAL OUTPUTS")
            for channel_name in self.config[channel_type]:
                self.log(f'    > getting options for {channel_name}')
                opt_text = channel_name
                val = self.config[channel_type][channel_name]['STARTUP_OUTPUT']
                self.log(f'      > STARTUP_OUTPUT: {val}')
                opts.update({opt_text : val})
    
            # send the options to the labjack to set the channels as outputs
            ljm.eWriteNames(self.handle, len(digital_outputs), opts.keys(), opts.values())
        
    def setup_counters(self):
        # set up channels to work as pulse counters, eg for the flowmeters
        channel_type = 'DIGITAL_COUNTERS'
        digital_counters = self.config.get(channel_type, None)
        if digital_counters is not None:
            """
            loop through all the DIGITAL_COUNTERS entries in the config file.
            each digital counter is an entry in the digital counter list. Set
            all of these channels to be digital counters 
            """
            self.log("SETTING UP DIGITAL COUNTERS:")
            #Enable clock0.  Default frequency is 80 MHz.
            ljm.eWriteName(self.handle, "DIO_EF_CLOCK0_ENABLE", 1)
            for ch in digital_counters:
                # add the digital counters to the counter channel list
                # note we're not just adding the channel name, we're adding the call to get the count!
                # this is unlike the AIN or DIO reads where we just want the voltage at the input
                self.input_channels.append(f'{ch}_EF_READ_A')
                self.log(f'    > adding  {ch}')
                ljm.eWriteName(self.handle, f"{ch}_EF_ENABLE", 0)
                ljm.eWriteName(self.handle, f"{ch}_EF_INDEX", 8) # use 8 for counter, 3 for freq
                ljm.eWriteName(self.handle, f"{ch}_EF_ENABLE",1)
                self.log(f'    > added  {ch}')

        
    def setup_dac(self):
        pass

    def setup_channels(self):
        try:
            self.setup_ain()
        except Exception as e:
            self.log(f'error setting up analog input channels: {e}')
            pass
        
        try:
            self.setup_counters()
        except Exception as e:
            self.log(f'error setting up digital counters: {e}')
        
        try:
            self.setup_dio_attributes()
            self.setup_dio()
        except Exception as e:
            self.log(f'error setting up digital I/O channels: {e}')
            pass

        try:
            self.setup_dac() 
        except Exception as e:
            self.log(f'error setting up DACs: {e}')

            pass

    def dio_on(self, chan):
        # turn on a dio channel, eg FIO4
        # send the options to the labjack
        chan = chan.upper()
        ljm.eWriteNames(self.handle, 1, [chan], [1])
        

    def dio_off(self, chan):
        # turn off a dio channel
        # send the options to the labjack
        chan = chan.upper()
        ljm.eWriteNames(self.handle, 1, [chan], [0])
    
    def int_to_bool_list(self, num, nbits, return_bools = False):
        bin_string = format(num, f'0{nbits}b')
        #print(f'{num} --> {bin_string}')
        if return_bools:
            # return a list of true false
            return [x=='1' for x in bin_string[::-1]]
        else:
            # return a list of 1 or 0
            return [int(x) for x in bin_string[::-1]]
    
    def get_dio_status_dict(self):
        
        # poll the status of all dio channels
        dio_state_bitmask = int(ljm.eReadName(self.handle, "DIO_STATE"))
        
        dio_status_list = self.int_to_bool_list(dio_state_bitmask, self.n_dio)
        dio_status_dict = dict(zip(self.dio_names, dio_status_list))
        return dio_status_dict
    

    
    def read_all(self):
        # read all of the analog inputs and counters
        inputvals = ljm.eReadNames(self.handle, len(self.input_channels), self.input_channels)
        inputvals_dict = dict(zip(self.input_channels,inputvals))
        
        self.state.update(inputvals_dict)
        
        # now read all the dio states in a way the doesn't change their directionality (input vs output)
        dio_status_dict = self.get_dio_status_dict()
        self.state.update(dio_status_dict)
        
        
    def print_state(self):
        print()
        print(f'LJ @ {self.address} CURRENT STATE:')
        print(json.dumps(self.state, indent = 3))

class labjack_set(object):

    """
    the idea here is to create on object which holds a dictionary of labjack instance
    objects, one for each one in the system.

    it can be used to read the state of all the labjacks with one function
    """
    def __init__(self, config, base_directory, logger = None, verbose = True):
        self.config = config
        self.base_directory = base_directory
        self.verbose = verbose
        self.logger = logger
        self.labjacks = dict() # a dictionary of labjack objects
        self.setup_labjacks()
    
    def log(self, msg, level = logging.INFO):
        if self.logger is None:
                print(msg)
        else:
            self.logger.log(level = level, msg = msg)
    
    def setup_labjacks(self):
        """
        takes in the winter configuration and the base directory,
        and returns an object which holds a dictionary of labjack objects, one for each labjack specified
        in the winter configuration
        """
        for lj_name in self.config['labjacks']:
                try:
                    # create a new labjack object by loading the config for each labjack
                    labjack_config_file = os.path.join(self.base_directory, 'config', self.config['labjacks'][lj_name]['config'])
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
            try:
                if self.labjacks[lj_name].connected:    
                    self.labjacks[lj_name].read_all()
                else:
                    self.labjacks[lj_name].reinitialize()
            except Exception as e:
                if self.verbose:
                    self.log(f'could not read labjack {lj_name}: {e}, attempting to reinitialize...')
                self.labjacks[lj_name].reinitialize()
                

    def print_all_labjack_states(self):
        for lj_name in self.labjacks.keys():
            self.labjacks[lj_name].print_state()
            
    def lookup_dio_channel(self, chanargs):
        """ takes in args that should define channel. outputs the labjack
        address used in the labjacks dictionary, and the dio outlet name as a
        tuple, eg: ('LJ0', 'EIO5')
        
       If there's one arg, it will try to treat it
        as a string and do a lookup by outlet label.
        
        if there are two args it will treat them as ints and do a lookup
        by args = [LJ_ADDR, DIO_CHAN]
                   
        if there are more than two args it will log an error and return
        """
        try:
            if chanargs is None:
                raise ValueError('you gave me chanargs = None, cannot look that up')
            
            if type(chanargs) is list:
                if len(chanargs) == 1:
                    # if we only got one item in the list, assume it's the name
                    name_lookup = True
                    chan = chanargs[0]
                    
                elif len(chanargs) == 2:
                    ljaddr = chanargs[0]
                    outletnum = chanargs[1]
                    assert ljaddr in self.labjacks.keys(), f"labjack address {ljaddr} not found in labjacks dictionary"
                    assert outletnum in self.labjacks[ljaddr].config['DIGITAL_OUTPUTS'], f"outlet number {outletnum} not found in outlet list for labjack {ljaddr}"
                    
                    return ljaddr, outletnum
                else:
                    raise ValueError(f'unexpected number of channel arguments when looking up pdu outlet = {chanargs}')    
            
            else: # treat the input like a string
                # if we just got a single thing not a list, assume it's a name
                name_lookup = True
                chan = str(chanargs)
                
            if name_lookup == True:
                # init a list to hold the (ljaddr, chan_num) tuple that
                # corresponds to the chan specified
                chanaddr = []
                # now look up the str channel
                for ljaddr in self.labjacks:
                    for outletnum in self.labjacks[ljaddr].config['DIGITAL_OUTPUTS']:
                        outletname = self.labjacks[ljaddr].config['DIGITAL_OUTPUTS'][outletnum]['NAME']
                        # check if the outlet name is the same as the requested one
                        # note that this is being forced to be CASE INSENSITVE
                        if outletname.lower() == chan.lower():
                            chanaddr.append((ljaddr, outletnum))
                self.log(f'(ljaddr, outletnum) matching chan = {chan}: {chanaddr}')
                # what it there is degeneracy in outlet names?
                if len(chanaddr) > 1:
                    raise ValueError(f'there are {len(chanaddr)} outlets named {chan}, not sure which to use!')
                elif len(chanaddr) == 0:
                    raise ValueError(f'found no outlets named {chan}!')
                else:
                    ljaddr, outletnum = chanaddr[0]
                    return ljaddr, outletnum
                
            

                
        except Exception as e:
            self.log(f'error doing name lookup of LJ DIO channel: {e}')
            return None, None
        
    def dio_do(self, action, outlet_specifier):
        """
        execute a generic action on the power distribution units
        this will execute action (one of [on, off]) on the labjack
        on the specified outlet. the outlet specifier can either be a list
        descritbing the pdu number and the outlet number, eg ['LJ0', 'FIO5']
        or it can be a string which corresponds to the name given to
        the outlet number. it will use self.lookup_dio_channel to find the LJ
        address and outlet number and do nothing if the outlet name/specifier
        is invalid or not unique.
        """
        action = action.lower()
        
        
        if action not in ['on', 'off']:
            self.log(f"action {action} not in allowed actions of [on, off]")
            return
        
        # now get the pdu address (in the pdu_dict) and the outlet number
        ljaddr, outletnum = self.lookup_dio_channel(outlet_specifier)
        
        if any([item is None for item in [ljaddr, outletnum] ]):
            self.log('bad outlet lookup. no action executed.')
            return
        # now do the action
        func = getattr(self.labjacks[ljaddr], f'dio_{action}')
        func(outletnum)
        
        
if __name__ == '__main__':
    
    config = utils.loadconfig(wsp_path + '/config/config.yaml')

    lj = labjack_set(config, wsp_path)

    """
    while True:
    #for i in range(100):
        try:
            newtime = datetime.now().timestamp()
            lj.read_all_labjacks()
            lj.print_all_labjack_states()
            
            time.sleep(0.5)
            
        except KeyboardInterrupt:
            break
    """