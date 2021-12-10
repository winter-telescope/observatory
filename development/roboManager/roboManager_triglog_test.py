#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Sep  7 11:40:30 2021

@author: nlourie
"""

"""
# FOR REFERENCE: DIRFILE SETUP
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
print(f'housekeeping: making directory: {hk_dir}')
        
# create the data link directory if it doesn't exist already
pathlib.Path(hk_link_dir).mkdir(parents = True, exist_ok = True)
print(f'housekeeping: making directory: {hk_link_dir}')

# create the dirfile database
self.df = egd.EasyGetData(self.dirpath, "w")
print(f'housekeeping; creating dirfile at {self.dirpath}')
#/* make a link to the current dirfile - kst can read this to make life easy... */
print(f'housekeeping: trying to create link at {hk_linkpath}')

try:
    os.symlink(self.dirpath, hk_linkpath)
except FileExistsError:
    print('housekeeping: deleting existing symbolic link')
    os.remove(hk_linkpath)
    os.symlink(self.dirpath, hk_linkpath)
"""

import os
import sys
import yaml
import pathlib
import json
# add the wsp directory to the PATH
wsp_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),'wsp')
sys.path.insert(1, wsp_path)
print(f'wsp_path = {wsp_path}')

# winter modules
from utils import utils


class RoboTrigger(object):
    
    def __init__(self, trigtype, val, cond, cmd):
        self.trigtype = trigtype
        self.val = val
        self.cond = cond
        self.cmd = cmd

class Test(object):
    
    def __init__(self, config):
        
        self.config = config
        self.triggers = dict()
        self.triglog = dict()
        """self.triggers = dict({'trig1' : False,
                             'trig2' : False,
                             'trig3' : False})"""
        
        self.setupTrigs()
    
    def log(self, msg):
        
        print(f'roboManager: {msg}')
    
    def setupTrigs(self):
        """
        creates a dictionary of triggers which are pulled from the main config.yaml file
        these triggers must be saved under robotic_manager_triggers in the format below:
            
            Example:
                robotic_manager_triggers:
                    timeformat: '%H%M%S.%f'
                    triggers:
                        startup:
                            type: 'sun'
                            val: 5.0
                            cond: '<'
                            cmd: 'total_startup'
        
        after creating this dictionary, the trigger log file is set up
        """
        # create local dictionary of triggers
        for trig in self.config['robotic_manager_triggers']['triggers']:
            
            #print(trig)
            
            trigtype = self.config['robotic_manager_triggers']['triggers'][trig]['type']
            trigcond = self.config['robotic_manager_triggers']['triggers'][trig]['cond']
            trigval  = self.config['robotic_manager_triggers']['triggers'][trig]['val']
            trigcmd  = self.config['robotic_manager_triggers']['triggers'][trig]['cmd']
            
            # create a trigger object
            trigObj = RoboTrigger(trigtype = trigtype, val = trigval, cond = trigcond, cmd = trigcmd)
            
            # add the trigger object to the trigger dictionary
            self.triggers.update({trig : trigObj})
        
        # set up the log file
        
        self.setupTrigLog()
    
    #@Pyro5.server.expose
    def resetTrigLog(self, updateFile = True):
        # make this exposed on the pyro server so we can externally reset the triglog
        
        # overwrites the triglog with all False, ie none of the commands have been sent
        for trigname in self.triggers.keys():
                self.triglog.update({trigname : False})
    
        if updateFile:
            self.updateTrigLogFile()
    
    def updateTrigLogFile(self):
        
        # saves the current value of the self.triglog to the self.triglog_filepath file
        # dump the yaml file
        with open(self.triglog_filepath, 'w+') as file:
            #yaml.dump(self.triglog, file)#, default_flow_style = False)
            json.dump(self.triglog, file, indent = 2)
        
    
    def setupTrigLog(self):
        """
        set up a yaml log file which records whether the command for each trigger
        has already been sent tonight.
        
        checks to see if tonight's triglog already exists. if not it makes a new one.
        """
        # file
        self.triglog_dir = os.path.join(os.getenv("HOME"),'data','triglogs')
        self.triglog_filename = f'triglog_{utils.tonight()}.json'
        self.triglog_filepath = os.path.join(self.triglog_dir, self.triglog_filename)

        self.triglog_linkdir = os.path.join(os.getenv("HOME"),'data')
        self.triglog_linkname = 'triglog_tonight.lnk'
        self.triglog_linkpath = os.path.join(self.triglog_linkdir, self.triglog_linkname)
        
        # create the data directory if it doesn't exist already
        pathlib.Path(self.triglog_dir).mkdir(parents = True, exist_ok = True)
        self.log(f'ensuring directory exists: {self.triglog_dir}')
                
        # create the data link directory if it doesn't exist already
        pathlib.Path(self.triglog_linkdir).mkdir(parents = True, exist_ok = True)
        self.log(f'ensuring directory exists: {self.triglog_linkdir}')
        
        # check if the file exists
        try:
            # assume file exists and try to load triglog from file
            self.log(f'loading triglog from file')
            self.triglog = json.load(open(self.triglog_filepath))
            

        except FileNotFoundError:
            # file does not exist: create it
            self.log('no triglog found: creating new one')
            
            # create the default triglog: no cmds have been sent
            self.resetTrigLog()
            
            
        # recreate a symlink to tonights trig log file
        self.log(f'trying to create link at {self.triglog_linkpath}')

        try:
            os.symlink(self.triglog_filepath, self.triglog_linkpath)
        except FileExistsError:
            self.log('deleting existing symbolic link')
            os.remove(self.triglog_linkpath)
            os.symlink(self.triglog_filepath, self.triglog_linkpath)
        
        print(f'\ntriglog = {json.dumps(self.triglog, indent = 2)}')


if __name__ == '__main__':
    # load the config
    config_file = wsp_path + '/config/config.yaml'
    config = utils.loadconfig(config_file)
    main = Test(config)
    
    