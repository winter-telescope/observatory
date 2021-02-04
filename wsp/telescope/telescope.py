#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jan 27 17:48:35 2020

telescope.py

This file is part of wsp

# PURPOSE #

This is a wrapper for the pwi4_client.py program from planewave.

It is written mainly to add a current status object to the pwi4_client.PWI4 class

The goal is that this is written in such a way that we can update pwi4_client
when PlaneWave publishes updates without having to modify that code, but maintain
the extra functionality we need.




@author: nlourie
"""
import time
import numpy as np
import sys
import os
from datetime import datetime
# add the wsp directory to the PATH
wsp_path = os.path.dirname(os.getcwd())
sys.path.insert(1, wsp_path)

# winter modules
from telescope import pwi4_client


class Telescope(pwi4_client.PWI4):
    
    """
    This inherits from pwi4_client.PWI4
    """
    
    def __init__(self, host="localhost", port=8220):
    
        super(Telescope, self).__init__(host = host, port = port)
    
        # create an empty state dictionary that will be updated 
        self.state = dict()
        
    def status_text_to_dict_parse(self, response):
        """
        Given text with keyword=value pairs separated by newlines,
        return a dictionary with the equivalent contents.
        """

        # In Python 3, response is of type "bytes".
        # Convert it to a string for processing below
        if type(response) == bytes:
            response = response.decode('utf-8')

        response_dict = {}

        lines = response.split("\n")
        
        for line in lines:
            fields = line.split("=", 1)
            if len(fields) == 2:
                name = fields[0]
                value = fields[1]
                '''
                # NL: this is a departure from the planewave code.
                The idea is that instead of making a dictionary of just values
                directily it's a mixed type dictionary, so that if some value is False,
                the dictionary value is a python boolean False, not the string 'false'
                
                Note that all the entries in the dictionary by default are strings. 
                The PW code specifically says what type of entry each entry is,
                for now let's just try to force it to a float and pass if not.
                
                This should be okay, because floats will be floats, bools are parsed
                separately, and any ints will become floats, but can always
                be changed back to ints by data_handler. Strings that can't
                be turned into floats will stay strings, like the pwi4.version field. 
                '''
                
                if value.lower() == 'true':
                    value = True
                elif value.lower() == 'false':
                    value = False
                elif 'timestamp' in name:
                    # if timestampt is in the name the format is YYYY-MM-DD HH:MM:SS.S
                    datetime_obj = datetime.strptime(value,'%Y-%m-%d %H:%M:%S.%f')
                    value = datetime_obj.timestamp()
                else:
                    try:
                        value = np.float(value)
                    except:
                        pass
                # this is the normal thing:
                response_dict[name] = value
        
        return response_dict
    
    def update_state(self, verbose = False):
        # written by NPL
        # poll telescope status
        try:
            #self.state = self.status()
            self.state = self.status_text_to_dict_parse(self.request("/status"))
        except Exception as e:
            '''
            do nothing here. this avoids flooding the log with errors if
            the system is disconnected. Instead, this should be handled by the
            watchdog to signal/log when the system is offline at a reasonable 
            cadance.
            
            if desired, we could set self.state_dict back to an empty dictionary.
            This would make housekeeping get the default values back, but otherwise
            let's just set mount.is_connected to False.
            '''
            # for now if the state can't update, then set the connected key to false:
            self.state.update({'mount.is_connected' : False})
            
            if verbose:
                print(f'could not update telescope status: {type(e)}: {e}')
if __name__ == '__main__':
        

    telescope = Telescope('thor')
    print(f'Mount Is Connected: {telescope.state.get("mount.is_connected",-999)} ')
    
    print(f'Getting Updated State from Telescope:')
    telescope.update_state()
    print(f'Mount Is Connected: {telescope.state.get("mount.is_connected",-999)} ')

