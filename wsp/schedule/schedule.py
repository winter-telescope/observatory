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

# add the wsp directory to the PATH
wsp_path = os.path.dirname(os.getcwd())
sys.path.insert(1, wsp_path)

# winter Modules
from utils import utils


def makeSampleSchedule(date = 'today'):
    # Takes in a date (string or int) or 'today'/'tonight' and makes a sample
    # schedule file based on the example file, just resaves it with a name
    # based on the date provided
    
    #TODO want this to make a file like 20200215_000.sch which increments if
    # there is already a file with that name in the directory. That way old 
    # files are preserved
    filename = 'n' + utils.getdatestr(date)
    
    filename = filename + '.sch'
    # Copy the sample schedule file
    schedulepath = os.getcwd() + '/scheduleFiles/'
    samplefile =  'example_ztf_schedule.csv'
    shutil.copyfile(schedulepath + samplefile, schedulepath + filename)
    print(f'Wrote Sample Schedule File to: {schedulepath + filename}')
    
            
    

class schedule(object):
    # This is a class that holds the full schedule 
    def __init__(self,base_directory,date = 'today'):
        """
        # Initiatialization procedure:
            1. look for a schedule based on the input date
            2. check if there is an obslog for tonight
            3. if there is an obslog:
                   >load up the last observation,
                   >then find where that observation is in the most recent
                 schedule, of just start from the beginning if it's not found
               else:
                   >create a new obslog
                   >start observations at the first line in the schedule
            4. load the current line in the schedule into a bunch of useful fields
            5. when commanded (by systemControl), write the current observation 
               line to the obslog
            6. when commanded (by systemControl), increment the schedule to the
               next line
            7. when the schedule is completed, go into stop mode
        """
        
        
        self.base_directory = base_directory
        self.date = utils.getdatestr(date)
        self.schedulefile = base_directory + '/schedule/scheduleFiles/n' + self.date + '.sch'
        self.obslogfile = base_directory + '/schedule/obslog/n' + self.date + '.obs'
        self.loadSchedule()
        self.currentScheduleLine = 0 # by default the current line should be line zero
        self.loadObslog()
        self.getCurrentObs()
        
    def loadSchedule(self):
        try:
            # Try to load the schedule for the specified date
            self.schedule = utils.readcsv(self.schedulefile)
            
            # Some things should be converted to integers
            #TODO there is a better way than this!
            for intField in ['','obsHistID','propID','fieldID','totalRequestsTonight']:
                self.schedule[intField]= [int(val) for val in s.schedule[intField]]
            

        except:
            #TODO log this error
            print(" error loading schedule file")
    def loadObslog(self):
        try:
            # Try to load the observation log for tonight
            if os.path.isfile(self.obslogfile):
                print(" found obslog for tonight")
            else:
                print(" could not find obslog for tonight. making one...")
                self.makeObslog()
        except:
            print(" could not verify if the obslog exists!")
    def makeObslog(self):
        # Make a new obslog
        # Never overwrite stuff in the log, only append!
        file = open(self.obslogfile,'a')
        date_obj = datetime.strptime(self.date,'%Y%m%d')
        now_obj  = datetime.utcnow()
        
        calitz = pytz.timezone('America/Los_Angeles')
        cali_now = datetime.now(calitz)
        
        file.write(f"# WINTER Observation Log for the night of {date_obj.strftime('%Y-%m-%d')}\n")
        file.write(f"# Created: {now_obj.strftime('%Y-%m-%d %H:%M:%S')} UTC, {cali_now.strftime('%Y-%m-%d %H:%M:%S')} Palomar Time\n")
        file.write(f"Time,\t")
        for key in self.schedule.keys():
            file.write(f"{key},\t")
        file.write("\n")
        file.close()
    
    def logCurrentObs(self):
        # log the current observation 
        now_obj  = datetime.utcnow()
        file = open(self.obslogfile,'a')
        #file.write(f" new observation made at {now_obj.strftime('%Y-%m-%d %H:%M:%S')} UTC")
        file.write('{int(datetime.timestamp(now_obj))},\t')
        for val in self.currentObs.values():
            file.write(f"{val},\t")
        file.write("\n")
        file.close()
    def getCurrentObs(self):
        # makes a dictionary to hold the current observation
        cur_vals = [elem[self.currentScheduleLine] for elem in self.schedule.values()]
        cur_keys = self.schedule.keys()
        self.currentObs = dict(zip(cur_keys,cur_vals))
    def gotoNextObs(self):
        # increments the schedule and just goes to the next line
        self.currentScheduleLine += 1
        
        
                    

        

if __name__ == '__main__':
    date = 'today'
    makeSampleSchedule(date = date)
    schedule = schedule(base_directory = wsp_path, date = date)
    print()
    print(f" the current line in the schedule file is {schedule.currentScheduleLine}")
    print(f" the current RA/DEC = {schedule.currentObs['fieldRA']}/{schedule.currentObs['fieldDec']}"	)
    print()
    print('Now go to the next line!')
    
    schedule.logCurrentObs()
    schedule.gotoNextObs()
    print()
    print(f" the current line in the schedule file is {schedule.currentScheduleLine}")
    print(f" the current RA/DEC = {schedule.currentObs['fieldRA']}/{schedule.currentObs['fieldDec']}"	)
    print()
    print('Now go to the next line!')
    
    
    
    


