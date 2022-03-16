#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Feb  7 11:20:31 2020

schedule.py

This is part of wsp

# Purpose #

This program loads the schedule files saved by the WINTER scheduler, and
updates the observation log (obslog) based on completed observations. The input
file format is based on the ZTF scheduler which has been modified and
adapted for use by WINTER.

It loads in a csv file with the following columns:

    	obsHistID
        requestID
        propID
        fieldID
        fieldRA
        fieldDec
        filter
        expDate
        expMJD
        night
        visitTime
        visitExpTime
        FWHMgeom
        FWHMeff
        airmass
        filtSkyBright
        lst
        altitude
        azimuth
        dist2Moon
        solarElong
        moonRA
        moonDec
        moonAlt
        moonAZ
        moonPhase
        sunAlt
        sunAz
        slewDist
        slewTime
        fiveSigmaDepth
        totalRequestsTonight
        metricValue
        subprogram

@author: nlourie
"""
# system packages
import os
import sys
import numpy as np
import unicodecsv
from datetime import datetime,timedelta
#from astropy.time import Time
import astropy.time
import astropy.units as u
import pytz
import shutil
import matplotlib.pyplot as plt
import sqlalchemy as db
# import ObsWriter
import logging

# add the wsp directory to the PATH
wsp_path = os.path.dirname(os.getcwd())
sys.path.insert(1, wsp_path)

# winter Modules
from utils import utils
from utils import logging_setup


class Schedule(object):
    # This is a class that handles the connection between WSP/roboOperator and the schedule file SQLite database

    def __init__(self, base_directory, config, logger, scheduleFile_directory = 'default', verbose = False):#, date = 'today'):
        """
        sets up logging and opens connection to the database. Does
        not actually access any data yet.
        """
        # take in the config
        self.config = config
        self.verbose = verbose
        #set up logging
        self.logger = logger

        self.base_directory = base_directory
        if scheduleFile_directory == 'default':
            self.scheduleFile_directory = os.path.join(os.getenv("HOME"), self.config['scheduleFile_directory'])
        else:
            self.scheduleFile_directory = scheduleFile_directory
        self.scheduleType = None
        
        # keep track of the last obsHistID observed
        self.last_obsHistID = -1
        
        # flag to track if we've hit the bottom of the schedule
        self.end_of_schedule = False
        # number of observations after the current time
        self.remaining_valid_observations = 1000

   
    def log(self, msg, level = logging.INFO):
        if self.logger is None:
            print(f'schedule: {msg}')
        else:
            self.logger.log(level, msg)
    
    
    #def loadSchedule(self, schedulefile_name, obsHistID = 0, startFresh=False):
    def loadSchedule(self, schedulefile_name):

        """
        Load the schedule starting at the currentTime.
        ### Note: At the moment currentTime is a misnomer, we are selecting by the IDs of the observations
        since the schedule database does not include any time information. Should change this to
        actually refer to time before deployment.
        """
        # NPL: 12-14-21 removed any time stuff here and any calls to query the schedule
        # now this method just loads up the schedule and tries to make a connection
        # other methods are now used to actually try to pull observations
        
        
        # set up the schedule file
        if schedulefile_name is None:
            self.schedulefile = None
            #TODO: this isn't handled properly!
        else:
            if schedulefile_name.lower() == 'nightly':
                self.schedulefile_name = 'data'
                self.scheduleType = 'nightly'
                self.schedulefile = os.readlink(os.path.join(os.getenv("HOME"), self.config['scheduleFile_nightly_link_directory'], self.config['scheduleFile_nightly_link_name']))
            else:
                if '.db' not in schedulefile_name:
                    schedulefile_name = schedulefile_name + '.db'
                self.schedulefile_name = schedulefile_name
                self.scheduleType = 'target'
                #self.schedulefile = os.getenv("HOME") + '/' + self.scheduleFile_directory + '/' + self.schedulefile_name
                self.schedulefile = os.path.join(self.scheduleFile_directory, self.schedulefile_name)
        try:
            
            self.log(f'scheduler: attempting to create sql engine to schedule file at {self.schedulefile}')
            self.engine = db.create_engine('sqlite:///' + self.schedulefile)    
            self.conn = self.engine.connect()
            self.log('scheduler: successfully connected to db')
            metadata = db.MetaData()
            summary = db.Table('Summary', metadata, autoload=True, autoload_with=self.engine)
            
            self.summary = summary
        
        except Exception as e:
            self.log(f'schedule file could not be loaded! error: {e}', level = logging.WARNING)
            # NPL 12-14-21 put this all in a try/except to handle bad schedule path
            #TODO: note that there may be downstream effects to setting this stuff to None that may need debugging
            self.conn = None
            self.engine = None
            self.summary = None
            self.schedulefile = None
            self.schedulefile_name = None
            self.scheduleType = None
            
            

    def getCurrentObs(self):
        """
        Returns the observation that the telescope should be making at the current time
        """
        return self.currentObs
    
    
    def getValidObs(self, obstime_mjd = 'now'):
        """
        searches the database to find all the allowed observations (within validStart and validStop)
        and returns the first one
        """
        
        # by default just evaluate the current time and use that to compare against the obstime, but can also take in one
        if obstime_mjd == 'now':
            obstime_mjd = astropy.time.Time(datetime.utcnow()).mjd
            
        
        try:
            tmpresult = self.conn.execute(self.summary.select().where(db.and_(self.summary.c.validStart <= obstime_mjd, 
                                                                              self.summary.c.validStop >= obstime_mjd,
                                                                              self.summary.c.obsHistID > self.last_obsHistID) 
                                                                              ))
            self.result = tmpresult
            
            # calculate how many observations remain that have times after obstime_mjd
            remaining_observations = self.conn.execute(self.summary.select().where(db.and_(self.summary.c.expMJD > obstime_mjd)))
            self.remaining_valid_observations = len([observation for observation in remaining_observations])
            if self.remaining_valid_observations == 0:
                self.end_of_schedule = True
            else:
                self.end_of_schedule = False
            
        except Exception as e:
            print(f"ERROR [schedule.py]: database query failed for next object: {e}")
            
 
        return tmpresult
    
    def gotoNextObs(self, obstime_mjd = 'now'):
        """
        Moves down a line in the database.
        When there are no more lines fetchone returns None and we know we've finished
        """
        
        self.getValidObs(obstime_mjd = obstime_mjd)
        nextResult = self.result.fetchone()
    
            
        if nextResult is None:
            self.currentObs = None
            if self.verbose:
                self.log('no valid entries at this time')
        else:
            
            nextResult_dict = dict(nextResult)
            if self.verbose:
                self.log(f'got next entry from schedule file: obsHistID = {nextResult_dict["obsHistID"]}')#', requestID = {nextResult_dict["requestID"]}')
            
                self.log('loading entry as currentObs')
            nextResult_dict = dict(nextResult)
            self.currentObs = nextResult_dict
            self.last_obsHistID = self.currentObs['obsHistID']
        
    def closeConnection(self):
        """
        Closes the result and the connection to the database
        """
        try:
            self.result.close()
        except Exception as e:
            self.log(f'schedule: COULD NOT CLOSE RESULT DURING SHUTDOWN: {e}')
        self.conn.close()




if __name__ == '__main__':
    
    
    
    # set the wsp path as the base directory
    base_directory = wsp_path

    # load the config
    config_file = base_directory + '/config/config.yaml'
    config = utils.loadconfig(config_file)
    
    #logger = logging_setup.setup_logger(base_directory, config)    
    logger = None
    print('\n\n\n')
    schedule = Schedule(base_directory, config, logger)
    
    schedulefile_name = 'test_schedule.db'
    
    #%%
    0#mjd = 59557.1
    mjd = (59557.0698429301 + 59557.0712318189)/2
    
    mjd_start = 59557.5556068189+1e-10 #for whatever reason it seems like it MUST be bigger to count, like the >= is only being read as > for wahtever reason
    #mjd_start = 59557.5556068189+2e-3

    mjd_end = 59557.5603521893 + 2e-3
    
    schedule.loadSchedule(schedulefile_name)
    
    
    #%%
    obstime_mjd = mjd_start
    
   
    obstimes = []
    obsHistIDs = []
    
    last_obsHistID = 0
    observations_remaining = []
    end_of_schedule = []
    
    while obstime_mjd < mjd_end:
        obstimes.append(obstime_mjd)
        t = astropy.time.Time(obstime_mjd, format = 'mjd')
        dt = astropy.time.TimeDelta(60 * u.s) 
        t_new = t+dt
        obstime_mjd = t_new.mjd
    
    
    # these are some time windows from the test schedule
    a = np.array([[59557.5556068189,	59557.5569957078],
    [59557.5564170041,	59557.557805893],
    [59557.5572271893,	59557.5586160782],
    [59557.5580373745,	59557.5594262634],
    [59557.5588475597,	59557.5602364486],
    [59557.5596577449,	59557.5610466338]])
    
    
    a_raw = a
    a0 = a[0][0]
    aScale = (a-a0)[1][-1]
    
    a_norm = (a-a0)/aScale
    a = a_norm


    a_dict = dict()
    akey = 600
    for j in range(len(a)):
        a_dict.update({akey:a[j]})
        akey+=1
        
    for i in range(len(obstimes)):  
        obstime_mjd = obstimes[i]
        print(f'\n[{i} / {len(obstimes)-1}]: ObsTime(scaled) = {(obstime_mjd-a0)/aScale:0.2f}')
        schedule.gotoNextObs(obstime_mjd = obstime_mjd)
        if schedule.currentObs is None:
            obsHistIDs.append(np.nan)
        else:
            obsHistIDs.append(schedule.currentObs['obsHistID'])
        observations_remaining.append(schedule.remaining_valid_observations)
        end_of_schedule.append(schedule.end_of_schedule)
    obstimes = np.array(obstimes)
    obstimes = (obstimes-a0)/aScale
    
    lines = np.arange(600,608,1)#np.arange(len(a))+ 600
    fig, ax = plt.subplots(1,1,figsize = (15,10))    
    for ob in obstimes:
        ax.plot(ob+0*np.array(lines), np.array(lines), 'k-', alpha = 0.5)
    for i in range(len(a)):
        y1 = 0*a[i] +lines[i] - 0.1
        y2 = 0*a[i] +lines[i] + 0.1
        ax.fill_between(a[i], y1, y2)
        
    ax.plot(obstimes, obsHistIDs, 'ko', linewidth = 5)
    ax.set_xlabel('Normalized Time')
    ax.set_ylabel('obsHistID')
    ax.set_yticks(np.arange(600,608,1))
    for i in range(len(obstimes)):
        ax.annotate(f'Remaining Obs = {observations_remaining[i]}', (obstimes[i]+0.03, 605.1), rotation = 90)
        ax.annotate(f'End of Sched. = {end_of_schedule[i]}', (obstimes[i]+0.08, 605.1), rotation = 90)
