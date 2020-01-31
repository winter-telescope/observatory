#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Jan 31 10:53:15 2020

palomarWeather.py

This is part of wsp

# Purpose #

This program reads and parses weather data from the Palomar telemetry server

@author: nlourie
"""
import os
from configobj import ConfigObj
import urllib.request
import urllib.error
import urllib.parse
import numpy as np
from datetime import datetime,timedelta
import pytz


# PDU Properties
class palomarWeather(object):
    def __init__(self,weather_file,base_directory):
        
        self.base_directory = base_directory
        self.weather_file = weather_file
        self.full_filename = base_directory + '/' + weather_file
        self.getWeather()
        
    def getWeather(self):
        try: # LOAD DATA FROM THE PALOMAR TELEMETRY SERVER
            configObj = ConfigObj(self.full_filename)
            
            # Load the P200 Properties
            site = 'P200'
            self.P2UTCTS = configObj[site]['P2UTCTS']['VAL']
            print(f'Loaded the {site} Property: ',configObj[site]['P2UTCTS']['INFO'])
            
            # Load the P48 Properties
            site = 'P48'
            self.P4WINDS = configObj[site]['P4WINDS']['VAL']
            print(f'Loaded the {site}  Property: ',configObj[site]['P4WINDS']['INFO'])
            self.P4UTCTS  = configObj[site]['P4UTCTS']['VAL']
            self.P4UTCST  = configObj[site]['P4UTCST']['VAL']
            self.P4LDT    = configObj[site]['P4LDT']['VAL']
            self.P4WTS    = configObj[site]['P4WTS']['VAL']
            self.P4WINDS  = configObj[site]['P4WINDS']['VAL']
            self.P4GWINDS = configObj[site]['P4GWINDS']['VAL']
            self.P4ALRMHT = configObj[site]['P4ALRMHT']['VAL']
            self.P4REMHLD = configObj[site]['P4REMHLD']['VAL']
            self.P4OTDEWT = configObj[site]['P4OTDEWT']['VAL']
            self.P4INDEWT = configObj[site]['P4INDEWT']['VAL']
            self.P4WINDD  = configObj[site]['P4WINDD']['VAL']
            self.P4WINDSP = configObj[site]['P4WINDSP']['VAL']
            self.P4WINDAV = configObj[site]['P4WINDAV']['VAL']
            self.P4OTAIRT = configObj[site]['P4OTAIRT']['VAL']
            self.P4OTRHUM = configObj[site]['P4OTRHUM']['VAL']
            self.P4OUTDEW = configObj[site]['P4OUTDEW']['VAL']
            self.P4INAIRT = configObj[site]['P4INAIRT']['VAL']
            self.P4INRHUM = configObj[site]['P4INRHUM']['VAL']
            self.P4INDEW  = configObj[site]['P4INDEW']['VAL']
            self.P4WETNES = configObj[site]['P4WETNES']['VAL']
            self.P4STATUS = configObj[site]['P4STATUS']['VAL']
                                    
        except:
            print('ERROR loading weather config file: ',self.full_filename)
            #TODO add an entry to the log
            #sys.exit()
            
        try: # Load data from clear dark skies at palomar
            url = 'https://www.cleardarksky.com/txtc/PalomarObcsp.txt'
            page = urllib.request.urlopen(url)
            cdsdata = page.read()
            
            
            cdsdata = data.decode("utf-8")
            cdsdata = data.replace('"','')
            cdsdata = data.replace(')','')
            cdsdata = data.replace('(','')
            weather_filename = "current_cds_weather.txt"
            text_file = open(weather_filename, "w")
            text_file.write(data)
            text_file.close()
            wtime,cloud,trans,seeing,wind,hum,temp = np.loadtxt(weather_filename,\
                                                                   unpack = True,\
                                                                   dtype = '|U32,int,int,int,int,int,int',\
                                                                   skiprows = 7,max_rows = 46,\
                                                                   delimiter = ',\t',usecols = (0,1,2,3,4,5,6),
                                                                   encoding = "utf-8")
            
            
            times_ctime = np.array([int(datetime.timestamp(datetime.strptime(time, '%Y-%m-%d %H:%M:%S'))) for time in wtime])
            
            #TODO Make Sure this Time conversion is right for the observatory location!
            #TODO making it figure out where it is would be better than hard coding a time offset
            now = datetime.now() + timedelta(hours = -3)
            now_ctime = int(datetime.timestamp(now))
            print('current time in california is:',now)
            
            closest_index = np.argmin(np.abs(times_ctime-now_ctime))
            print('closest time is: ',wtime[closest_index])
            # Now save the Cold Dark Skies attributes
            self.CDSTIME = wtime[closest_index] # time that the prediction is coming from
            self.CDSCLOUD = cloud[closest_index] # cloud cover in percent of sky covered
            self.CDSTRANS = trans[closest_index] # transparency measure from 0-5
            self.CDSSEEING = seeing[closest_index] # seeing goodness from 0-5
            self.CDSWINDI = wind[closest_index]
                # Wind measure:
                    # 0 = 0-5 mph
                    # 1 = 6-11 mph
                    # 2 = 12-16 mph
                    # 3 = 17-28 mph
                    # 4 = 29-45 mph
                    # 5 = 45+ mph
            self.CDSRHI = hum[closest_index] # RH index 0-15 
                # RH = (20% + measure*5%) to (20% + INDEX*5% + 5%)
                # ie INDEX = 15 --> RH = 90%-95%
            self.CDSTEMPI = temp[closest_index] # temperature index 
                # Temp index: T = -45C + INDEX*5C
                    # 0 = <-40
                    # 1 = -40 to -35
                    # ETC
            
        except:
            print("problem loading weather data from clear dark skies")
            
      
    def oktoopen_p48(self):
        """
        It is okay to open the p48 if:
            1. the outside temperature 
        """
        return
        
            
if __name__ == '__main__':
    weather = palomarWeather('palomarWeather.ini',os.getcwd())
    #print(weather.cds)
    
    
    