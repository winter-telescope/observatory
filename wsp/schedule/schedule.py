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
    # This is a class that holds the full schedule
    # def __init__(self,base_directory,date = 'today'):
    #     """
    #     # Initiatialization procedure:
    #         1. look for a schedule based on the input date
    #         2. check if there is an obslog for tonight
    #         3. if there is an obslog:
    #                >load up the last observation,
    #                >then find where that observation is in the most recent
    #              schedule, of just start from the beginning if it's not found
    #            else:
    #                >create a new obslog
    #                >start observations at the first line in the schedule
    #         4. load the current line in the schedule into a bunch of useful fields
    #         5. when commanded (by systemControl), write the current observation
    #            line to the obslog
    #         6. when commanded (by systemControl), increment the schedule to the
    #            next line
    #         7. when the schedule is completed, go into stop mode
    #     """
    #
    #
    #     self.base_directory = base_directory
    #     self.date = utils.getdatestr(date)
    #     self.schedulefile = base_directory + '/schedule/scheduleFiles/n' + self.date  +'_sch.csv'#'.sch'
    #     self.obslogfile = base_directory + '/schedule/obslog/n' + self.date + '_obs.csv'#'.obs'
    #     try:
    #         self.loadSchedule()
    #         self.currentScheduleLine = 0 # by default the current line should be line zero
    #                                      # if all observations are done, then currentScheduleLine is set to -1
    #         self.forceRestart = False # a flag to force the scheduler to restart from the beginning of the schedule
    #         self.loadObslog()
    #         self.getCurrentObs()
    #     except:
    #         print("Unable to make an observing plan for tonight!")

    def __init__(self, base_directory, config, logger):#, date = 'today'):
        """
        sets up logging and opens connection to the database. Does
        not actually access any data yet.
        """
        # take in the config
        self.config = config
            
        #set up logging
        self.logger = logger

        self.base_directory = base_directory
        self.scheduleFile_directory = self.config['scheduleFile_directory']
        # NL 9-21-20: moving these into the loadSchedule method
        #self.schedulefile = base_directory + '/schedule/scheduleFiles/1_night_test.db'
        #self.engine = db.create_engine('sqlite:///' + self.schedulefile)
        self.scheduleType = None


    # def loadSchedule(self):
    #     try:
    #         # Try to load the schedule for the specified date
    #         print(f' Importing schedule file for {self.date}')
    #         self.schedule = utils.readcsv(self.schedulefile)
    #
    #         # Convert the altitude and azimuth from radians to degrees, which is easier for the telescope to ingest
    #         for angle in ['altitude','azimuth']:
    #             self.schedule[angle]= [(val*180.0/np.pi) for val in self.schedule[angle]]
    #
    #         # Some things should be converted to integers
    #         #TODO there is a better way than this!
    #         for intField in ['','requestID','obsHistID','propID','fieldID','totalRequestsTonight']:
    #             self.schedule[intField]= [int(val) for val in self.schedule[intField]]
    #
    #
    #     except:
    #         #TODO log this error
    #         print(f" error loading schedule file: {self.schedulefile} (probably because it doesn't exist!)")
    def log(self, msg, level = logging.INFO):
        if self.logger is None:
            print(f'schedule: {msg}')
        else:
            self.logger.log(level, msg)
    
    
    def loadSchedule(self, schedulefile_name, currentTime=0, startFresh=False):
        """
        Load the schedule starting at the currentTime.
        ### Note: At the moment currentTime is a misnomer, we are selecting by the IDs of the observations
        since the schedule database does not include any time information. Should change this to
        actually refer to time before deployment.
        """
        
        # set up the schedule file
        if schedulefile_name is None:
            self.schedulefile = None
            #TODO: this isn't handled properly!
        else:
            if schedulefile_name.lower() == 'nightly':
                #self.schedulefile_name = self.config['scheduleFile_nightly_prefix'] + utils.tonight_local() +'.db'
                self.schedulefile_name = 'data'
                self.scheduleType = 'nightly'
                self.schedulefile = os.readlink(os.path.join(os.getenv("HOME"), self.config['scheduleFile_nightly_link_directory'], self.config['scheduleFile_nightly_link_name']))
            else:
                if '.db' not in schedulefile_name:
                    schedulefile_name = schedulefile_name + '.db'
                self.schedulefile_name = schedulefile_name
                self.scheduleType = 'target'
                self.schedulefile = os.getenv("HOME") + '/' + self.scheduleFile_directory + '/' + self.schedulefile_name
            
        #self.schedulefile = self.base_directory + '/' + self.scheduleFile_directory + '/' + self.schedulefile_name
        #self.schedulefile = os.getenv("HOME") + '/' + self.scheduleFile_directory + '/' + self.schedulefile_name
        
        self.log(f'scheduler: creating sql engine to schedule file at {self.schedulefile}')
        self.engine = db.create_engine('sqlite:///' + self.schedulefile)
        #TODO: NPL: what happens if this file doesn't exist?

        self.conn = self.engine.connect()
        self.log('scheduler: successfully connected to db')
        metadata = db.MetaData()
        summary = db.Table('Summary', metadata, autoload=True, autoload_with=self.engine)
        
        self.summary = summary
        
        
        #Query the database starting at the correct time of night
        try:
            # get all results that come after currentTime
            #self.result = self.conn.execute(summary.select().where(summary.c.obsHistID >= currentTime))
            self.result = self.conn.execute(summary.select().where(summary.c.expMJD >= currentTime))
            
            # get only results that are within alid times
            #self.result = self.getValidObs(obstime_mjd = currentTime)
            #self.log('successfully queried db')
        except Exception as e:
            #self.logger.error(f'query failed because of {type(e)}: {e}', exc_info=True )
            self.log(f'query failed because of {type(e)}: {e}')
        
         
        # Don't need this anymore, just call gotoNextObs directly #
        self.gotoNextObs(obstime_mjd = currentTime)
        
        """
        # The fetchone method grabs the first row in the result of the query and stores it as currentObs
        nextResult = self.result.fetchone()
        self.logger.debug('popped first result')
        if nextResult is None:
            self.currentObs = None
        else:
            self.currentObs = dict(nextResult)
        """
        

    # def getCurrentObs(self):
    #     if self.currentScheduleLine == -1:
    #         cur_keys = self.schedule.keys()
    #         cur_vals = []
    #         cur_vals = [cur_vals.append('None') for key in cur_keys]
    #         self.currentObs = dict(zip(cur_keys,cur_vals))
    #     else:
    #         # makes a dictionary to hold the current observation
    #         cur_vals = [elem[self.currentScheduleLine] for elem in self.schedule.values()]
    #         cur_keys = self.schedule.keys()
    #         self.currentObs = dict(zip(cur_keys,cur_vals))
    # def gotoNextObs(self):
    #     if self.forceRestart == True:
    #         self.currentScheduleLine = 0
    #     elif (self.currentScheduleLine >= self.schedule[''][-1]) or (self.currentScheduleLine == -1):
    #         print('cannot go to next obs')
    #         # you've hit the end of the schedule
    #         self.currentScheduleLine = -1
    #     else:
    #         # increments the schedule and just goes to the next line
    #         self.currentScheduleLine += 1
    #
    #     self.getCurrentObs()

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
            #mjdnow = Time(datetime.utcnow()).mjd
            #tmpresult = self.conn.execute(self.summary.select().where(db.and_(self.summary.c.validStart <= obstime_mjd, self.summary.c.validStop >= obstime_mjd)) )
            tmpresult = self.conn.execute(self.summary.select().where(self.summary.c.expMJD >= obstime_mjd))

            #self.result = tmpresult
        except Exception as e:
            print(f"ERROR [schedule.py]: database query failed for next object: {e}")
            
 
        return tmpresult
    
    def gotoNextObs(self, obstime_mjd = 'now'):
        """
        Moves down a line in the database.
        When there are no more lines fetchone returns None and we know we've finished
        """
        """
        #self.currentObs = dict(self.result.fetchone())

        # This would just choose the next item in the previously fetched
        # query.  Instead we want to query the db every time to see what is
        # the next object envisioned for the queue, i.e. the one that
        # matches this mjd most closely.
        
        # by default just evaluate the current time and use that to compare against the obstime, but can also take in one
        if obstime_mjd == 'now':
            obstime_mjd = astropy.time.Time(datetime.utcnow()).mjd
        
        
        metadata = db.MetaData()
        summary  = db.Table('Summary',metadata,autoload=True,autoload_with=self.engine)
        self.summary = summary
        try:
            #mjdnow = Time(datetime.utcnow()).mjd
            tmpresult = self.conn.execute(summary.select().where(summary.c.expMJD >= obstime_mjd))
            self.result = tmpresult
        except:
            print("ERROR [schedule.py]: database query failed for next object")
            # leaves self.result unchanged
        
        # Grab the first row in the list of oservations for which the scheduled
        # mjd is later than the current mjd.
        
        """
        nextResult = self.result.fetchone()
    
            
        #else:
        if nextResult is None:
            self.currentObs = None
            self.log('schedule file has no more entries')
        else:
            
            nextResult_dict = dict(nextResult)
            self.log(f'got next entry from schedule file: obsHistID = {nextResult_dict["obsHistID"]}, requestID = {nextResult_dict["requestID"]}')
            # check to see if the nextResult is within valid times
            time_is_valid = (nextResult_dict['validStart'] <= obstime_mjd) and (obstime_mjd <= nextResult_dict['validStop'])
            self.log(f'entry within allowed times = {time_is_valid}')
            if not time_is_valid:
                self.log('current observation not in time window. searching for next valid obs...')
                # rerun the next valid observation check
                self.result = self.getValidObs(obstime_mjd)
                nextResult = self.result.fetchone()
                
            
            if nextResult is None:
                self.currentObs = None
                self.log('schedule file has no more entries')
            else:
                #self.currentObs = dict(nextResult)
                self.log('loading entry as currentObs')
                nextResult_dict = dict(nextResult)
                self.currentObs = nextResult_dict
                #self.log(f'got next entry from schedule file: obsHistID = {self.currentObs["obsHistID"]}, requestID = {self.currentObs["requestID"]}')
            #Commented following lines to separate the close connection code from gotoNext. There are other situations which prompt closure
            # if self.currentObs == None:
            #     self.closeConnection()
        
        
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
    #mjd = 59557.1
    mjd = (59557.0698429301 + 59557.0712318189)/2
    
    mjd_start = 59557.5556068189
    mjd_end = 59557.5603521893
    
    schedule.loadSchedule(schedulefile_name, currentTime = mjd_start)
    

    
    
    #%%
    obstime_mjd = mjd_start
    
   
    obstimes = []
    obsHistIDs = []
    
    while obstime_mjd < mjd_end:
        t = astropy.time.Time(obstime_mjd, format = 'mjd')
        dt = astropy.time.TimeDelta(30 * u.s) 
        t_new = t+dt
        obstime_mjd = t_new.mjd
        print(obstime_mjd)
        obstimes.append(obstime_mjd)
        if schedule.currentObs is None:
            obsHistIDs.append(np.nan)
        else:
            obsHistIDs.append(schedule.currentObs['obsHistID'])
        schedule.gotoNextObs(obstime_mjd = obstime_mjd)
        
    pass
    # date = 'today'
    # makeSampleSchedule(date = date)
    # s = Schedule(base_directory = wsp_path, date = date)
    # print()
    # print(f" the current line in the schedule file is {s.currentScheduleLine}")
    # print(f" the current RA/DEC = {s.currentObs['fieldRA']}/{s.currentObs['fieldDec']}"	)
    # print()
    # print('Now go to the next line!')
    #
    # for j in range(2):
    #     for i in range(100):
    #         s.logCurrentObs()
    #         s.gotoNextObs()
    #
    #         print()
    #         print(f" the current line in the schedule file is {s.currentScheduleLine}")
    #         print(f" the current RA/DEC = {s.currentObs['fieldRA']}/{s.currentObs['fieldDec']}"	)
    #         print()
    #         print('Now go to the next line!')
    a = np.array([[59557.5556068189,	59557.5569957078],
    [59557.5564170041,	59557.557805893],
    [59557.5572271893,	59557.5586160782],
    [59557.5580373745,	59557.5594262634],
    [59557.5588475597,	59557.5602364486],
    [59557.5596577449,	59557.5610466338]])
    
    
    lines = range(len(a))
    fig, ax = plt.subplots(1,1,figsize = (10,10))    
    for ob in obstimes:
        ax.plot(ob+0*np.array(lines), np.array(lines), 'k-', alpha = 0.5)
        pass
    for i in lines:
        ax.plot(a[i], 0*a[i] + i, '-', linewidth = 20)
    
    ax1 = ax.twinx()
    ax1.plot(obstimes, obsHistIDs, 'ko', linewidth = 5)
    
    """plt.figure()
    plt.plot(np.ravel(a), (np.ravel(a))*0, 'o',label = 'obstimes 600-605')
    plt.plot(np.array(obstimes), 0*np.array(obstimes), label = 'obstimes')
    plt.legend()"""