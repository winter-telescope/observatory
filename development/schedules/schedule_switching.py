#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jan 20 17:34:50 2022

Testing having multiple schedules, and switching between them,
and querying all of them


@author: nlourie
"""

import os
import sys
import yaml
import glob
import subprocess
import numpy as np

# add the wsp directory to the PATH
wsp_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),'wsp')
# switch to this when ported to wsp
#wsp_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

sys.path.insert(1, wsp_path)
print(f'schedule_switching: wsp_path = {wsp_path}')

from schedule import schedule
from utils import logging_setup
from utils import utils


class roboSim(object):
    
    def __init__(self, base_directory, config, logger):
        
        self.base_directory = base_directory
        self.config = config
        self.logger = logger
        
        # new things adding here
        self.ToOschedules = dict()
        
    def log(self, msg):
        print(msg)
    def announce(self, msg):
        print(msg)
    
    # these are for setting up the baseline survey schedule
    def setup_schedule(self):
        
        if self.schedulefile_name is None:
            # NPL 9-21-20: put this in for now so that the while loop in run wouldn't go if the schedule is None
            self.schedule.currentObs = None

        else:
            #print(f'scheduleExecutor: loading schedule file [{self.schedulefile_name}]')
            # code that sets up the connections to the databases
            # NPL: 09-13-21: added start_fresh = True so changing schedules will start at the first entry
            self.getSchedule(self.schedulefile_name, startFresh = True)

            # RAS - note that this is where we should send the
            # plot of tonight's observation footprint to Slack
            res = subprocess.Popen(args=['python','plotTonightSchedule.py'])

            self.writer.setUpDatabase()
    
        
    
    def getSchedule(self, schedulefile_name, startFresh = True):
        """
        #NPL 12-16-21 this is deprecated
        if startFresh:
            currentTime = 0
        else:
            currentTime = self.lastseen + 1
        """
        self.schedule.loadSchedule(schedulefile_name)
    
    def load_best_observing_target(self, obstime_mjd):
        """
        Checks to see what the best target to observe is right now. 
        
        Decision tree:
            1. check if there are any schedule files in the ToO High priority folder
                if yes:
                    load the most recent one.
                else:
                    pass
            2. check if there are
                if yes:
                    load the most recent one.
                else:
                    pass
            3. get the first valid entry from the current schedule
                this is either a TOO, the baseline schedule (last loaded. eg through load_target_schedule or nightly), or None
            4. run self.do_currentObs()
        """
        #TODO: handle what to do if another schedule is added during TOO observation
        #This isn't quite the right behavior in any case... we want to actually see if there are valid observations in the TOO schedules
        # if there are none, than we need to handle switching back to the normal operations. maybe we want to keep the baseline as nightly_tonight ALWAYS,
        # and then keep self.targeSchedule or something that can be handled. this would stil let us load the target schedule from the wintercmd 
        # interface, and also let WSP switch back and forth between them easily by changing schedules in here.
        
        # get all the files in the ToO High Priority folder
        highPriority_schedule_directory = os.path.join(os.getenv("HOME"), self.config['scheduleFile_ToO_HighPriority_directory'])
        self.highPriority_schedules = glob.glob(os.path.join(highPriority_schedule_directory, '*.db'))
        self.log(f'schedules in high priority folder: {self.highPriority_schedules}')
        
        self.log('')
        # check if the schedule is already in self.ToOschedules
        for sched_filepath in self.highPriority_schedules:
            sched_filename = sched_filepath.split('/')[-1]
            sched_filedirectory = highPriority_schedule_directory
            if sched_filename in self.ToOschedules:
                pass
            else:
                self.log(f'need to add {sched_filename} to high priority schedules')
                sched_obj = schedule.Schedule(base_directory = self.base_directory,
                                              config = self.config,
                                              logger = self.logger,
                                              scheduleFile_directory = sched_filedirectory)
                
                # set up the ToO schedule
                sched_obj.loadSchedule(schedulefile_name  = sched_filepath)
                
                self.ToOschedules.update({sched_filename : {'filepath' : sched_filepath,
                                                            'priority' : 'high',
                                                            'schedule' : sched_obj}})
        
        # now query if there are valid observations in any of the TOO schedule
        
        # init a list of valid observations
        validObs = []
        validSchedules = []
        validSchedule_filenames = []
                
        for schedname in self.ToOschedules:
            self.log('')
            self.announce(f'searching for valid observation in {schedname}')
            TOOschedule = self.ToOschedules[schedname]['schedule']
            TOOschedule.gotoNextObs(obstime_mjd = obstime_mjd)
            
            if TOOschedule.currentObs is None:
                self.announce(f'no valid observations at this time (MJD = {obstime_mjd}), standing by...')
            else:
                # add the observation to the list of valid observations
                validObs.append(TOOschedule.currentObs)
                validSchedules.append(TOOschedule)
                validSchedule_filenames.append(schedname)
        
        # check to make sure things loaded right
        self.log('')
        self.log('Current Observations Loaded Up:')
        for schedname in self.ToOschedules:
            TOOschedule = self.ToOschedules[schedname]['schedule']
            self.log(f' > {schedname}: currentObs obsHistID = {TOOschedule.currentObs["obsHistID"]}')
        
        #  now sort all the valid observations by smallest validStop time. eg rank by which will be not valid soonest
        self.log('')
        self.log('list all the obsHistIDs in the list of current valid observations')
        for obs in validObs:
            print(f'> obsHistID = {obs["obsHistID"]}, validStop = {obs["validStop"]}')
        # make a list of the validStop times
        validStopTimes = np.array([obs["validStop"] for obs in validObs])
        
        # get the indices that would sort by smallest validStop to largest
        # turn these into numpy arrays so we can use their handy argsort and indexing scheme
        sorted_indices = np.argsort(validStopTimes)
        #validSchedules_numpy = np.array(validSchedules)
        validObs_numpy = np.array(validObs)
        validSchedule_filenames_numpy = np.array(validSchedule_filenames)
        
        #self.log(f'sorted_indices = {sorted_indices}')
        #self.log(f'validObs_numpy[sorted_indices] = {validObs_numpy[sorted_indices]}')
        #self.log(f'validSchedule_filenames_numpy[sorted_indices] = {validSchedule_filenames_numpy[sorted_indices]}')
        # the first of the sorted validObs is the one we should observe
        bestObservation = validObs_numpy[sorted_indices][0]
        bestScheduleFilename = validSchedule_filenames_numpy[sorted_indices][0]
        self.log('')
        self.log(f'we should be observing from {bestScheduleFilename}, obsHistID = {bestObservation["obsHistID"]}')
        
if __name__ == '__main__':
    
    config = yaml.load(open(wsp_path + '/config/config.yaml'), Loader = yaml.FullLoader)
    doLogging = False
    base_directory = wsp_path
    # set up the logger
    if doLogging:
        logger = logging_setup.setup_logger(wsp_path, config)    
    else:
        logger = None
        
        
    robo = roboSim(base_directory, config, logger)
    
    obstime_mjd = 59557.0705373745
    
    robo.load_best_observing_target(obstime_mjd = obstime_mjd)
#schedule = schedule.Schedule(base_directory = base_directory, config = config, logger = logger)












