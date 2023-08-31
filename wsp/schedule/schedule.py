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
from datetime import datetime,timedelta
#from astropy.time import Time
import astropy.time
import astropy.units as u
import pytz
import shutil
import matplotlib.pyplot as plt
import traceback as tb
import sqlalchemy as db
import pandas as pd
# import ObsWriter
import logging
import subprocess

#import wintertoo.validate

# add the wsp directory to the PATH
wsp_path = os.path.dirname(os.getcwd())
sys.path.insert(1, wsp_path)

# winter Modules
from utils import utils
from utils import logging_setup

try:
    import wintertoo_validate
except:
    from schedule import wintertoo_validate


class Schedule(object):
    # This is a class that handles the connection between WSP/roboOperator and the schedule file SQLite database

    def __init__(self, base_directory, config, logger, scheduleFile_directory = 'default', verbose = True):#, date = 'today'):
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
        self.remaining_observable_entries = 1000

   
    def log(self, msg, level = logging.INFO):
        if self.logger is None:
            print(f'schedule: {msg}')
        else:
            self.logger.log(level, msg)
    
    def validateSchedule(self):
        # try to validate the schedule:
        try:
            # first connect to the database
            self.connectToDB()
            
            # get all the rows that can be observed
            stmt = f'SELECT * FROM Summary'
            
            #### THIS DOES THE SORTING USING PANDAS DATAFRAME COMMANDS ####
            #df = pd.read_sql(stmt, self.conn)
            self.log(f'type(self.conn) = {type(self.conn)}')
            df = pd.read_sql('SELECT * FROM Summary;',self.conn)
            # now close the connection to the database
            self.closeConnection
            
            # Now make some additions to the observations
            # Priority: if not in database, add default 0 priority column
            if 'priority' not in df:
                df['priority'] = 0
            
            ### NOW VALIDATE THE SCHEDULE FILE DATAFRAME ###
            # a bad schedule file will raise an exception here
            wintertoo_validate.validate_schedule_df(df)

            
            return True
        
        except Exception as e:
            #print(e)
            self.log(f'schedule not valid: {e}')
            
            return False
    
    
    #def loadSchedule(self, schedulefile_name, obsHistID = 0, startFresh=False):
    def loadSchedule(self, schedulefile_name, obsHistID = 0, postPlot = False):

        #print(f'schedulefile_name = {schedulefile_name}')
        # set up the schedule file
        if schedulefile_name is None:
            self.schedule_is_valid = False
            
        else:
            
            
            if schedulefile_name.lower() == 'nightly':
                self.scheduleType = 'nightly'
                self.schedulefile = os.readlink(os.path.join(os.getenv("HOME"), self.config['scheduleFile_nightly_link_directory'], self.config['scheduleFile_nightly_link_name']))
                self.schedulefile_name = os.path.basename(os.path.normpath(self.schedulefile))
                if postPlot:
                    res = subprocess.Popen(args=['python','plotTonightSchedule.py'])
                    pass
            else:
                if '.db' not in schedulefile_name:
                    schedulefile_name = schedulefile_name + '.db'
                schedulefile_name = schedulefile_name
                self.scheduleType = 'target'
                #self.schedulefile = os.getenv("HOME") + '/' + self.scheduleFile_directory + '/' + self.schedulefile_name
                # nifty fact: this works whether schedulefile_name is name or the full path
                self.schedulefile = os.path.join(self.scheduleFile_directory, schedulefile_name)
                # just want the name of the file here not the full pathname
                self.schedulefile_name = os.path.basename(os.path.normpath(self.schedulefile))
                
            # validate the scheule:
            self.log(f'checking if schedule is valid:')
            self.schedule_is_valid = self.validateSchedule()
            #print(f'self.scheduleFile_directory = {self.scheduleFile_directory}')
            #print(f'self.schedulefile = {self.schedulefile}')
            #print(f'self.schedulefile_name = {self.schedulefile_name}')
                
        if not self.schedule_is_valid:
            self.schedulefile = None
            self.currentObs = None
            self.currentObsHistID = None
            self.schedulefile_name = None
            self.scheduleType = None
            
    def connectToDB(self):
        
        try:
            
            self.log(f'scheduler: attempting to create sql engine to schedule file at {self.schedulefile}')
            self.engine = db.create_engine('sqlite:///' + self.schedulefile)    
            self.conn = self.engine.connect()
            self.log('scheduler: successfully connected to db')
            
        
        except Exception as e:
            self.log(f'could not connect to schedule file! error: {e}', level = logging.WARNING)
            # NPL 12-14-21 put this all in a try/except to handle bad schedule path
            #TODO: note that there may be downstream effects to setting this stuff to None that may need debugging
            self.conn = None
            self.engine = None    
            
    def closeConnection(self):
        """
        Closes the result and the connection to the database
        """
        try:
            self.conn.close()
        except Exception as e:
            self.log(f'schedule: COULD NOT CLOSE DB CONNECTION DURING SHUTDOWN: {e}')       

    def getCurrentObs(self):
        """
        Returns the observation that the telescope should be making at the current time
        """
        return self.currentObs
    
    
    
    def getRankedObs(self, obstime_mjd = 'now', printList = True):
        #print(f'in getRanked Obs, obstime_mjd = {obstime_mjd}')
        # check if the schedule is invalid
        if self.schedule_is_valid is False:
            dataRanked = None
            self.log('schedule file is invalid. cannot query observations')
        else:
            try:
                # first connect to the database
                self.connectToDB()
                
                # get all the rows that can be observed
                stmt = f'SELECT * from summary'
                #stmt += f' WHERE validStart <= {obstime_mjd} and validStop >= {obstime_mjd} and observed = 0'
                
                #### THIS DOES THE SORTING USING PANDAS DATAFRAME COMMANDS ####
                #df = pd.read_sql('SELECT * FROM summary;',self.conn)
                self.df = pd.read_sql(stmt, self.conn)
                
                self.df = self.df[self.df["validStop"] >= obstime_mjd]
                self.df = self.df[self.df["observed"] == 0]
                
                # Now make some additions to the observations
                # Priority: if not in database, add default 0 priority column
                if 'priority' not in self.df:
                    self.df['priority'] = 0
                # Filename: add the name of the file so that this gets passed through to the 
                self.df['origin_filename'] = self.schedulefile_name
                self.df['origin_filepath'] = self.schedulefile
                
                ### NOW VALIDATE THE SCHEDULE FILE DATAFRAME ###
                # a bad schedule file will raise an exception here
                wintertoo_validate.validate_schedule_df(self.df)
    
                # we have now validatd the schedule and only selected observations whose validStop time haven't passed
                # at this point make a note of the total number of remaining observable targets
                self.remaining_observable_entries = len(self.df)
                print(f'remaining_observable_entries = {self.remaining_observable_entries}')
                
                # now select only observations that are currently in their observing window
                self.df = self.df[self.df["validStart"]<= obstime_mjd]

    
    
                # let's turn it into a list of dicts
                dataRanked = []
                for i in range(len(self.df)):
                    dataRanked.append(dict(self.df.iloc[i]))
            
                
                # now close the connection to the database
                self.closeConnection
            
            except Exception as e:
                # now close the connection to the database
                self.closeConnection()
                dataRanked = None
                print(f"ERROR [schedule.py]: database query failed for next object: {e}")
                #print(tb.format_exc())
            if printList:
                # list the observations in their ranked order:
                self.log('Valid Observations Ranked by validStop:')
                for i in range(len(dataRanked)):
                    row = dataRanked[i]
                    self.log(f'  {i}: obsHistID = {row["obsHistID"]}, validStop = {row["validStop"]}, observed = {row["observed"]}')
                    
        return dataRanked
    
    def updateCurrentObs(self, currentObs, obstime_mjd = 'now'):
        self.getRemainingValidObs(obstime_mjd)
            
        if currentObs is None:
            self.currentObs = None
            self.currentObsHistID = None
            if self.verbose:
                self.log('no valid entries at this time')
                self.log(f'remaining valid observations: {self.remaining_valid_observations}')

        else:
            
            #nextResult_dict = dict(nextResult)
            if self.verbose:
                self.log(f'got next entry from schedule file: obsHistID = {currentObs["obsHistID"]}')#', requestID = {nextResult_dict["requestID"]}')
                self.log(f'remaining valid observations: {self.remaining_valid_observations}')
                self.log('> loading entry as currentObs')
            #nextResult_dict = dict(nextResult)
            self.currentObs = currentObs
            self.currentObsHistID = self.currentObs['obsHistID']
            self.last_obsHistID = self.currentObs['obsHistID']
            
            # make a not of what kind of schedule this is
            self.currentObs.update({'scheduleType' : self.scheduleType})
        
        
    def getRemainingValidObs(self, obstime_mjd):
        if obstime_mjd == 'now':
            obstime_mjd = astropy.time.Time(datetime.utcnow()).mjd
        
        
        dataRanked = self.getRankedObs(obstime_mjd)
        if dataRanked is None:
            self.remaining_valid_observations = 0
            self.end_of_schedule = True
        else:
            # moved this to inside getRankedObs
            self.remaining_valid_observations = len(dataRanked)
            if self.remaining_observable_entries == 0:
                     self.end_of_schedule = True
            else:
                self.end_of_schedule = False
        
    
    def getTopRankedObs(self, obstime_mjd = 'now'):
        
        """
        run a SQL query to rank all the valid observations, and then return the row of the top ranked one
        """
        # by default just evaluate the current time and use that to compare against the obstime, but can also take in one
        if obstime_mjd == 'now':
            obstime_mjd = astropy.time.Time(datetime.utcnow()).mjd
        
        # check if the schedule is invalid
        if self.schedule_is_valid is False:
            dataRanked = None
            self.log('schedule file is invalid. cannot query observations')
        else:
            # if the schedule is okay then rank valid observations
            dataRanked = self.getRankedObs(obstime_mjd)
        #print(dataRanked)
        if dataRanked is None:
            self.remaining_valid_observations = 0
            self.end_of_schedule = True
            topRankedObs = None
        else:
            self.remaining_valid_observations = len(dataRanked)
       
            if self.remaining_valid_observations == 0:
                self.end_of_schedule = True
                topRankedObs = None
            else:
                self.end_of_schedule = False
                topRankedObs = dict(dataRanked[0])
                
        return topRankedObs
    
    def log_observation(self, obsHistID = 'current'):
        """
        Update the schedule file by changing observed to 1 for the row that matchese obsHistID

        """
        
        if obsHistID == 'current':
            obsHistID = self.currentObsHistID
        else:
            pass
        
        if obsHistID is None:
            return
        
        try:
            # first connect to the database
            self.connectToDB()
            
            stmt = f'UPDATE summary SET observed = 1 WHERE obsHistID = {obsHistID}'
            self.conn.execute(stmt)
            
            # now close the connection to the database
            self.closeConnection
            
        except Exception as e:
            # now close the connection to the database
            self.closeConnection
            self.log(f'ERROR: could not log observation due to {type(e)}: {e}')
    
    def _reset_observation_log(self):
        """
        changes observed --> 0 for all rows in the schedule file
        this is just for testing, you don't really ever want to do this operationally...
        """
        
        try:
            # first connect to the database
            self.connectToDB()
            
            stmt = f'UPDATE summary SET observed = 0'
            self.conn.execute(stmt)
            
            # now close the connection to the database
            self.closeConnection
            
        except Exception as e:
            # now close the connection to the database
            self.closeConnection
            self.log(f'ERROR: could not log observation due to {type(e)}: {e}')
            
        
    
    def gotoNextObs(self, obstime_mjd = 'now'):
        """
        --> THIS IS WHAT IS CALLED BY roboOperator! <--

        """
        
        nextResult = self.getTopRankedObs(obstime_mjd)
        
            
        if nextResult is None:
            self.currentObs = None
            self.currentObsHistID = None
            if self.verbose:
                self.log('no valid entries at this time')
                self.log(f'remaining valid observations: {self.remaining_valid_observations}')

        else:
            
            #nextResult_dict = dict(nextResult)
            if self.verbose:
                self.log(f'got next entry from schedule file: obsHistID = {nextResult["obsHistID"]}')#', requestID = {nextResult_dict["requestID"]}')
                self.log(f'remaining_observable_entries: {self.remaining_observable_entries}')
                self.log('> loading entry as currentObs')
            #nextResult_dict = dict(nextResult)
            self.currentObs = nextResult
            self.currentObsHistID = self.currentObs['obsHistID']
            self.last_obsHistID = self.currentObs['obsHistID']
        
    




if __name__ == '__main__':
    
    
    
    # set the wsp path as the base directory
    base_directory = wsp_path

    # load the config
    config_file = base_directory + '/config/config.yaml'
    config = utils.loadconfig(config_file)
    
    #logger = logging_setup.setup_logger(base_directory, config)    
    logger = None
    schedule = Schedule(base_directory, config, logger, verbose = True)
    
    obstime_mjd = 59804.1530797029


    schedulefile_path = os.readlink(os.path.join(os.getenv("HOME"), 'data','nightly_schedule.lnk'))
    #schedulefile_path = os.path.join(os.getenv("HOME"), 'data','schedules', 'nightly_20220810.db')
    #schedulefile_path = os.path.join(os.getenv("HOME"), 'data', 'schedules','ToO', 'timed_requests_08_15_2022_15_1660601716_.db')
    schedulefile_dir = os.path.dirname(schedulefile_path)
    schedulefile_name = schedulefile_path.split('/')[-1]
    
    
    #schedule.loadSchedule(os.path.join(schedulefile_dir, schedulefile_name))
    #schedule.loadSchedule('nightly')
    #schedule.loadSchedule(schedulefile_name)
    #schedule.loadSchedule(None)
    schedulefile = '/home/winter/data/schedules/ToO/testcrab.db'
    """
    print(f'scheduler: attempting to create sql engine to schedule file at {schedulefile}')
    engine = db.create_engine('sqlite:///' + schedulefile)    
    conn = engine.connect()
    
    stmt = f'SELECT * FROM Summary'
    
    #### THIS DOES THE SORTING USING PANDAS DATAFRAME COMMANDS ####
    #df = pd.read_sql(stmt, self.conn)
    print(f'type(conn) = {type(conn)}')
    df = pd.read_sql('SELECT * FROM Summary;',conn)
    conn.close()
    
    """
    schedule.loadSchedule(schedulefile)
    
    # reset the schedule to fully unobserved
    schedule._reset_observation_log()
    
    # list the ranked observations
    #order = schedule.getRankedObs(obstime_mjd = obstime_mjd, printList = True)
    schedule.log('')
    currentObs = schedule.getTopRankedObs(obstime_mjd)
    schedule.log(f'remaining_observable_entries: {schedule.remaining_observable_entries}')
    
    # now fake observe by stepping through the observations in the ranked order and logging them
    while schedule.remaining_valid_observations > 0:
        #schedule.gotoNextObs(obstime_mjd)
        currentObs = schedule.getTopRankedObs(obstime_mjd)
        schedule.updateCurrentObs(currentObs, obstime_mjd)
        schedule.log_observation()
    
    schedule.log('all done with schedule!')
    
    # reset the schedule to fully unobserved
    schedule.log('resetting observed to false again')
    schedule._reset_observation_log()
    
    