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
import datetime
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
    try:
        date = str(date)
        if date.lower() in  ['today','tonight']:
            filename = utils.tonight()
        else:
            date_obj = datetime.datetime.strptime(date,'%Y%m%d')
            filename = 'n' + date_obj.strftime('%Y%m%d')
    except:
        print('Date format invalid, should be YYYYMMDD')
    
    filename = filename + '.sch'
    # Copy the sample schedule file
    schedulepath = os.getcwd() + '/scheduleFiles/'
    samplefile =  'example_ztf_schedule.csv'
    shutil.copyfile(schedulepath + samplefile, schedulepath + filename)
    print(f'Wrote Sample Schedule File to: {schedulepath + filename}')
    
            
    

class schedule(object):
    # This is a class that holds the full schedule 
    def __init__(self,base_directory):
        self.base_directory = base_directory
        

#if __name__ == '__main__':

#with open(file) as f:
 #   ncols = len(f.readline().split(','))
#s = np.genfromtxt(file,delimiter = ',',names = True,usecols = range(1,ncols))

# reads a csv into a dictionary, the header line becomes the keys for lists
# stolen graciously from MINERVA and adapted to py3


makeSampleSchedule(date = 'today')
    
    


