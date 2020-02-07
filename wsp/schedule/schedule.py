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
import os
import sys
import numpy as np
import unicodecsv
import datetime


class schedule(object):
    # This is a class that holds the full schedule 
    def __init__(self,base_directory):
        self.base_directory = base_directory
        
    

#if __name__ == '__main__':
wspdir = os.path.dirname(os.getcwd())
#schedule = schedule(base_directory = wspdir)
file = wspdir + '/schedule/example_ztf_schedule.csv'

with open(file) as f:
    ncols = len(f.readline().split(','))
s = np.genfromtxt(file,delimiter = ',',names = True,usecols = range(1,ncols))

# reads a csv into a dictionary, the header line becomes the keys for lists
# stolen graciously from MINERVA and adapted to py3
def readcsv(filename):
    # parse the csv file
    with open(filename,'rb') as f:
        reader = unicodecsv.reader(f)
        headers = next(reader)
        csv = {}
        for h in headers:
            csv[h.split('(')[0].strip()] = []
        for row in reader:
            for h,v in zip(headers,row):
                csv[h.split('(')[0].strip()].append(v)
        for key in csv.keys():
            try:csv[key] = np.asarray(csv[key],dtype = np.float32)
            except: csv[key] = np.asarray(csv[key])
        return csv
    
def night():
    # stolen graciously from MINERVA and adapted to py3
    today = datetime.datetime.utcnow()
    if datetime.datetime.now().hour >= 10 and datetime.datetime.now().hour <= 16:
        today = today + datetime.timedelta(days=1)
    return 'n' + today.strftime('%Y%m%d')    

csv = readcsv(file)
    
    


