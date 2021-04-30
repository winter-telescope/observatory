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
import pytz
import shutil

import sqlalchemy as db
# import ObsWriter
import logging

# add the wsp directory to the PATH
wsp_path = os.path.dirname(os.getcwd())
sys.path.insert(1, wsp_path)

# winter Modules
from utils import utils


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
                self.schedulefile_name = self.config['scheduleFile_nightly_prefix'] + utils.tonight() +'.db'
                self.scheduleType = 'nightly'
            else:
                if '.db' not in schedulefile_name:
                    schedulefile_name = schedulefile_name + '.db'
                self.schedulefile_name = schedulefile_name
                self.scheduleType = 'target'
            
        #self.schedulefile = self.base_directory + '/' + self.scheduleFile_directory + '/' + self.schedulefile_name
        self.schedulefile = os.getenv("HOME") + '/' + self.scheduleFile_directory + '/' + self.schedulefile_name
        
        self.logger.info(f'scheduler: creating sql engine to schedule file at {self.schedulefile}')
        self.engine = db.create_engine('sqlite:///' + self.schedulefile)
        #TODO: NPL: what happens if this file doesn't exist?

        self.conn = self.engine.connect()
        self.logger.error('scheduler: successfully connected to db')
        metadata = db.MetaData()
        summary = db.Table('Summary', metadata, autoload=True, autoload_with=self.engine)

        #Query the database starting at the correct time of night
        try:
            self.result = self.conn.execute(summary.select().where(summary.c.obsHistID >= currentTime))
            self.logger.debug('successfully queried db')
        except Exception as e:
            self.logger.error(f'query failed because of {type(e)}: {e}', exc_info=True )

        # The fetchone method grabs the first row in the result of the query and stores it as currentObs
        self.currentObs = dict(self.result.fetchone())
        self.logger.debug('popped first result')


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

    def gotoNextObs(self):
        """
        Moves down a line in the database.
        When there are no more lines fetchone returns None and we know we've finished
        """
        self.currentObs = dict(self.result.fetchone())
        #Commented following lines to separate the close connection code from gotoNext. There are other situations which prompt closure
        # if self.currentObs == None:
        #     self.closeConnection()

    def closeConnection(self):
        """
        Closes the result and the connection to the database
        """
        self.result.close()
        self.conn.close()




if __name__ == '__main__':
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
