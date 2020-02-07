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

# add the wsp directory to the PATH
wsp_path = os.path.dirname(os.getcwd())
sys.path.insert(1, wsp_path)


# PDU Properties
class palomarWeather(object):
    def __init__(self,base_directory,weather_file,limits_file):
        
        self.base_directory = base_directory
        self.weather_file = weather_file
        self.limits_file = limits_file
        self.full_filename = base_directory + '/housekeeping/' + weather_file
        self.getWeatherLimits()
        self.getWeather(firsttime = True)
        self.caniopen() # checks all the dome vetoes based on weather
        # THIS IS A FLAG THAT CAN BE SET TO OVERRIDE THE WEATHER DOME OPEN VETO:
        self.override = False 
        
    def getWeatherLimits(self):
        try: # Load in the weather limits from the config file
            
            configObj = ConfigObj(self.base_directory + '/config/' + self.limits_file)
            
            self.TEMP_OUT_MIN = float(configObj['DOME']['TEMP_OUT']['MIN'])
            self.TEMP_OUT_MAX = float(configObj['DOME']['TEMP_OUT']['MAX'])
            
            self.TEMP_IN_MIN = float(configObj['DOME']['TEMP_IN']['MIN'])
            self.TEMP_IN_MAX = float(configObj['DOME']['TEMP_IN']['MAX'])
            
            self.RH_OUT_MIN = float(configObj['DOME']['RH_OUT']['MIN'])
            self.RH_OUT_MAX = float(configObj['DOME']['RH_OUT']['MAX'])
            
            self.RH_IN_MIN = float(configObj['DOME']['RH_IN']['MIN'])
            self.RH_IN_MAX = float(configObj['DOME']['RH_IN']['MAX'])
            
            self.WIND_GUST_MIN = float(configObj['DOME']['WIND_GUST']['MIN'])
            self.WIND_GUST_MAX = float(configObj['DOME']['WIND_GUST']['MAX'] ) 
            
            self.WIND_SPEED_MIN = float(configObj['DOME']['WIND_SPEED']['MIN'])
            self.WIND_SPEED_MAX = float(configObj['DOME']['WIND_SPEED']['MAX'] )            
            
            self.DEWPOINT_IN_MIN = float(configObj['DOME']['DEWPOINT_IN']['MIN'])
            self.DEWPOINT_IN_MAX = float(configObj['DOME']['DEWPOINT_IN']['MAX'])
            
            self.DEWPOINT_OUT_MIN = float(configObj['DOME']['DEWPOINT_OUT']['MIN'])
            self.DEWPOINT_OUT_MAX = float(configObj['DOME']['DEWPOINT_OUT']['MAX'])
            
            self.TRANS_MIN = float(configObj['DOME']['TRANSPARENCY']['MIN'])
            self.TRANS_MAX = float(configObj['DOME']['TRANSPARENCY']['MAX'])
            
            self.SEEING_MIN = float(configObj['DOME']['SEEING']['MIN'])
            self.SEEING_MAX = float(configObj['DOME']['SEEING']['MAX'])
            
            self.CLOUD_MIN = float(configObj['DOME']['CLOUDS']['MIN'])
            self.CLOUD_MAX = float(configObj['DOME']['CLOUDS']['MAX'])
            
            
        except:
            print('Unable to Load the Weather Limits File: ',self.base_directory + '/config/' + self.limits_file)
        
    def getWeather(self,firsttime = False):
        try: # LOAD DATA FROM THE PALOMAR TELEMETRY SERVER
            configObj = ConfigObj(self.full_filename)
            
            # Load the P200 Properties
            site = 'P200'
            self.P2UTCTS = configObj[site]['P2UTCTS']['VAL']
            #print(f'Loaded the {site} Property: ',configObj[site]['P2UTCTS']['INFO'])
            #
            # Load the P48 Properties
            site = 'P48'
            self.P4WINDS = configObj[site]['P4WINDS']['VAL']
            #print(f'Loaded the {site}  Property: ',configObj[site]['P4WINDS']['INFO'])
            self.P4UTCTS  = int(configObj[site]['P4UTCTS']['VAL'])      # last query timestamp
            self.P4LDT    = configObj[site]['P4LDT']['VAL']             # last query time string
            self.P4WTS    = int(configObj[site]['P4WTS']['VAL'])        # last read timestamp
            self.P4WINDS  = float(configObj[site]['P4WINDS']['VAL'])    # windspeed threshold (m/s)
            
            self.P4GWINDS = float(configObj[site]['P4GWINDS']['VAL'])   # gust wind speed threshold (m/s)
            self.P4ALRMHT = float(configObj[site]['P4ALRMHT']['VAL'])   # alarm hold time (s)
            self.P4REMHLD = float(configObj[site]['P4REMHLD']['VAL'])   # remaining hold time (s)
            self.P4OTDEWT = float(configObj[site]['P4OTDEWT']['VAL'])   # outside dewpoint (C)
            self.P4INDEWT = float(configObj[site]['P4INDEWT']['VAL'])   # inside dewpoint (C)
            self.P4WINDD  = float(configObj[site]['P4WINDD']['VAL'])    # wind direction angle (deg)
            self.P4WINDSP = float(configObj[site]['P4WINDSP']['VAL'])   # windspeed current (m/s)
            self.P4WINDAV = float(configObj[site]['P4WINDAV']['VAL'])   # windspeed average (m/s)
            self.P4OTAIRT = float(configObj[site]['P4OTAIRT']['VAL'])   # outside air temp (C)
            self.P4OTRHUM = float(configObj[site]['P4OTRHUM']['VAL'])   # outside RH (%)
            self.P4OUTDEW = float(configObj[site]['P4OUTDEW']['VAL'])   # outside dewpoint (C)
            self.P4INAIRT = float(configObj[site]['P4INAIRT']['VAL'])   # inside air temp (C)
            self.P4INRHUM = float(configObj[site]['P4INRHUM']['VAL'])   # inside RH (%)
            self.P4INDEW  = float(configObj[site]['P4INDEW']['VAL'])    # inside dewpoint (C)
            
            P4WETNES = configObj[site]['P4WETNES']['VAL']               # wetness
            if P4WETNES.lower() == 'NO':
                self.P4WETNES = False
            elif P4WETNES == 'YES':
                self.P4WETNES = True
            else:
                self.P4WETNES = 'Error'
            P4STATUS = configObj[site]['P4STATUS']['VAL']               # status
            if P4STATUS.lower() == 'ready':
                self.P4STATUS = True
            else:
                self.P4STATUS = False
            
            # Make useful timestamp objects
            self.P4LASTQUERY = datetime.fromtimestamp(self.P4UTCTS) #timestamp object of last query time
            self.P4LASTREAD  = datetime.fromtimestamp(self.P4WTS) #timestamp object of last read time from P48
            
            # if it's the first time checking the weather, or the weatherrecord the last time
            #   it was wet in the last 24 hours, and record the coldest temp
            #   in the last 24 hours, or if its been 24 hours since the coldest temp was recorded
            
            if firsttime:
                # if its the first time checking the weather, set: 
                    # coldest temp in last 24 hours to current temp
                    # time the coldest temp was recorded to now
                    #TODO query the last 24 hours from the telescope
                    
                self.P4LASTWET_TIME = self.P4LASTREAD
                self.P4LASTFRZ_TIME = self.P4LASTREAD
                
                #TODO: QUERY THE LAST 24 HOURS OF DATA
                #If there has been no rain in the last 24 hours then just set
                #the last rain time to 24 hours ago
                self.P4LASTWET_TIME = self.P4LASTREAD + timedelta(days = -1.0)
                self.P4LASTFRZ_TIME = self.P4LASTREAD + timedelta(days = -1.0)
            """
            # If the current air temp is near freezing, note the time as the "last freezing time"
            if self.P4OTAIRT < 1:
                self.P4LASTFRZ_TIME = self.P4LASTQUERY
            
            # If the current wetness status is True, then log the time as the last wet time
            if self.P4WETNES:
                self.P4LASTWET_TIME = self.P4LASTQUERY
             

            """                    
        except:
            print('ERROR loading weather config file: ',self.full_filename)
            #TODO add an entry to the log
            #sys.exit()
            
        try: # Load data from clear dark skies at palomar
            url = 'https://www.cleardarksky.com/txtc/PalomarObcsp.txt'
            page = urllib.request.urlopen(url)
            cdsdata = page.read()
            
            
            cdsdata = cdsdata.decode("utf-8")
            cdsdata = cdsdata.replace('"','')
            cdsdata = cdsdata.replace(')','')
            cdsdata = cdsdata.replace('(','')
            weather_filename = "current_cds_weather.txt"
            text_file = open(weather_filename, "w")
            text_file.write(cdsdata)
            text_file.close()
            wtime,cloud,trans,seeing,wind,hum,temp = np.loadtxt(weather_filename,\
                                                                   unpack = True,\
                                                                   dtype = '|U32,int,int,int,int,int,int',\
                                                                   skiprows = 7,max_rows = 46,\
                                                                   delimiter = ',\t',usecols = (0,1,2,3,4,5,6),
                                                                   encoding = "utf-8")
            
            
            calitz = pytz.timezone('America/Los_Angeles')
            times = [ datetime.strptime(time, '%Y-%m-%d %H:%M:%S') for time in wtime]
            # set the timezone
            times_cali = [calitz.localize(time) for time in times]
            
            # make the ctimes
            times_ctime = np.array([int(datetime.timestamp(time)) for time in times_cali])
            cali_now = datetime.now(calitz)
            
            now_ctime = int(datetime.timestamp(cali_now))
            #print('cali now_ctime = ',now_ctime)
            #print('current time in california is:',cali_now)
            
            #Find the closest time in the CDS weather forecast
            closest_index = np.argmin(np.abs(times_ctime-now_ctime))
            #print('closest time is: ',wtime[closest_index])
            
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
            wind_min = [0,6,12,17,29,45]
            wind_max = [5,11,16,28,45,100]
            self.CDSWINDMAX = wind_max[self.CDSWINDI]
            self.CDSWINDMIN = wind_min[self.CDSWINDI]
            self.CDSRHI = hum[closest_index] # RH index 0-15 
                # RH = (20% + measure*5%) to (20% + INDEX*5% + 5%)
                # ie INDEX = 15 --> RH = 90%-95%
            self.CDSRHMIN = (self.CDSRHI*5) + 20
            self.CDSRHMAX = (self.CDSRHI*5) + 25 #max RH in %
            self.CDSTEMPI = temp[closest_index] # temperature index 
                # Temp index: T = -45C + INDEX*5C
                    # 0 = <-40
                    # 1 = -40 to -35
                    # ETC
            self.CDSTEMPMAX = (self.CDSTEMPI * 5) - 40
            self.CDSTEMPMIN = (self.CDSTEMPI * 5) - 45
            
            
        except:
            print("problem loading weather data from clear dark skies")
            
      
    def caniopen_p48(self):
        """
        It is okay to open the p48 if:
            1. all fields are within their individual limits
            2. the inside temperature is higher than the outside dewpoint
            3. it hasn't rained in 1 hour
            4. it hasn't been snowy (<freezing and wet) in 24 hours
            
            self.P4GWINDS =  # gust wind speed threshold (m/s)
            self.P4ALRMHT =  # alarm hold time (s)
            self.P4REMHLD =  # remaining hold time (s)
            self.P4OTDEWT =  # outside dewpoint (C)
            self.P4INDEWT =  # inside dewpoint (C)
            self.P4WINDD  =  # wind direction angle (deg)
            self.P4WINDSP =  # windspeed current (m/s)
            self.P4WINDAV =  # windspeed average (m/s)
            self.P4OTAIRT =  # outside air temp (C)
            self.P4OTRHUM =  # outside RH (%)
            self.P4OUTDEW =  # outside dewpoint (C)
            self.P4INAIRT =  # inside air temp (C)
            self.P4INRHUM =  # inside RH (%)
            self.P4INDEW  =  # inside dewpoint (C)
        """
        ok = []

        ### 1. check all fields are within their individual limits:
        temp_out = (self.P4OTAIRT >= self.TEMP_OUT_MIN) & (self.P4OTAIRT <= self.TEMP_OUT_MAX)
        if not temp_out:
            print(f'P48 says the outside temp is bad')
        ok.append(temp_out)
        
        temp_in = (self.P4INAIRT >= self.TEMP_IN_MIN) & (self.P4INAIRT <= self.TEMP_IN_MAX)
        if not temp_in:
            print(f'P48 says the inside temp is bad')
        ok.append(temp_in)
        
        rh_out = (self.P4OTRHUM >= self.RH_OUT_MIN) & (self.P4OTRHUM <= self.RH_OUT_MAX)
        if not rh_out:
            print(f'P48 says the outside RH is bad')
        ok.append(rh_out)
        
        rh_in = (self.P4INRHUM >= self.RH_IN_MIN) & (self.P4INRHUM <= self.RH_IN_MAX)
        if not rh_in:
            print(f'P48 says the inside RH is bad')
        ok.append(rh_in)
        
        wind_gust = (self.P4WINDSP >= self.WIND_GUST_MIN) & (self.P4WINDSP <= self.WIND_GUST_MAX)
        if not wind_gust:
            print(f'P48 says the wind gust speed is bad')
        ok.append(wind_gust)
        
        wind_speed = (self.P4WINDAV >= self.WIND_SPEED_MIN) & (self.P4WINDAV <= self.WIND_SPEED_MAX)
        if not wind_speed:
            print(f'P48 says the average wind speed is bad')
        ok.append(wind_speed)
        
        dp_out = (self.P4OUTDEW >= self.DEWPOINT_OUT_MIN) & (self.P4OUTDEW <= self.DEWPOINT_OUT_MAX)
        if not dp_out:
            print(f'P48 says the outside dewpoint is bad')
        ok.append(dp_out)
        
        dp_in = (self.P4INDEW >= self.DEWPOINT_IN_MIN) & (self.P4INDEW <= self.DEWPOINT_IN_MAX)
        if not dp_in:
            print(f'P48 says the inside dewpoint is bad')
        ok.append(dp_in)       
        
        ### 2. check the inside temperature is higher than the outside dewpoint
        no_condensation = (self.P4INAIRT > self.P4OUTDEW)
        if not no_condensation:
            print(f'P48 says the inside temp is too cold and may condense if opened')
        ok.append(no_condensation)
        
        ### 3. it hasn't rained in 1 hour
        rain_time_limit = 3600.0 # 1 hour
        no_rain = (self.P4LASTREAD - self.P4LASTWET_TIME).total_seconds() > rain_time_limit
        if not no_rain:
            print(f'P48 says it has been wet in the last {rain_time_limit/3600} hours')
        ok.append(no_rain)
        
        ### 4. it hasn't been snowy (<freezing and wet) in 24 hours
        snow_time_limit = 24*3600.0 # 24 hours
        no_snow = ((self.P4LASTREAD - self.P4LASTWET_TIME).total_seconds() > snow_time_limit) & ((self.P4LASTREAD - self.P4LASTFRZ_TIME).total_seconds() > snow_time_limit)
        if not no_snow:
            print(f'P48 says it may have snowed in the last {snow_time_limit/3600} hours')
        ok.append(no_snow)
        
        self.oktoopen_p48 = all(ok)
        return self.oktoopen_p48
    
    def caniopen_cds(self):
        # this checks the Clear Dark Skies (CDS) data against the allowed limits
        # this is just a very basic sky quality check, not a way to guess the
        # real weather on the mountain (ie wetnes, rain, etc)
        
        # MAKE SURE EVERYTHING IS WITHIN THE LIMITS
        # Make a big array of booleans
        ok = []
        temp = ((self.CDSTEMPMIN >= self.TEMP_OUT_MIN) & (self.CDSTEMPMAX <= self.TEMP_OUT_MAX))
        if not temp:
            print(f'CDS says Temperature is not okay: T = [{self.CDSTEMPMIN} - {self.CDSTEMPMAX}] Allowed = [{self.TEMP_OUT_MIN},{self.TEMP_OUT_MAX}]')
        ok.append(temp)
        
        cloud = ((self.CDSCLOUD >= self.CLOUD_MIN) & (self.CDSCLOUD <= self.CLOUD_MAX))
        if not cloud:
            print(f'CDS says too cloudy: Cloud Cover = {self.CDSCLOUD}, Max Allowed = {self.CLOUD_MAX}')
        ok.append(cloud)
        
        trans = ((self.CDSTRANS >= self.TRANS_MIN) & (self.CDSTRANS <= self.TRANS_MAX))
        if not trans:
            print(f'CDS says not transparent enough: Transparency = {self.CDSTRANS}, Max Allowed = {self.TRANS_MAX}')
        ok.append(trans)
        
        seeing = ((self.CDSSEEING >= self.SEEING_MIN) & (self.CDSSEEING <= self.SEEING_MAX))
        if not seeing:
            print(f'CDS says seeing is bad: Seeing = {self.CDSSEEING}, Allowed = [{self.SEEING_MIN},{self.SEEING_MAX}]')
        ok.append(seeing)
        
        wind = ((self.CDSWINDMIN >= self.WIND_SPEED_MIN) & (self.CDSWINDMAX <= self.WIND_SPEED_MAX))
        if not wind:
            print(f'CDS says too windy: Wind = [{self.CDSWINDMIN}-{self.CDSWINDMAX}], Max Allowed = {self.WIND_SPEED_MAX}') 
        ok.append(wind)
        
        rh = ((self.CDSRHMIN >= self.RH_OUT_MIN) & (self.CDSRHMAX <= self.RH_OUT_MAX))
        if not rh:
            print(f'CDS says RH is not in range: RH = [{self.CDSRHMIN}-{self.CDSRHMAX}], Allowed Range = [{self.RH_OUT_MIN},{self.RH_OUT_MAX}]')
        ok.append(rh)
        
        
        self.oktoopen_cds = all(ok)
        return self.oktoopen_cds #returns True if all conditions are met, otherwise false
      
        
    def caniopen(self):
        # checks all the weather system checks
        ok = []
        ok.append(self.caniopen_cds())
        ok.append(self.caniopen_p48())
        self.oktoopen = all(ok)
        if self.oktoopen:
            print(f" All weather checks passed, ok to open the dome!")
        else:
            print(f" All weather checks not passed. NOT OK TO OPEN THE DOME.")
        return self.oktoopen
            
if __name__ == '__main__':
    weather = palomarWeather(os.path.dirname(os.getcwd()),'palomarWeather.ini','weather_limits.ini')
    
    #print('CDS Says OK to Open? ',weather.oktoopen_cds())
    #print('P48 Says OK to Open? ',weather.oktoopen_p48())
    #print(weather.cds)
    #weather.caniopen()
    weather.oktoopen
    
    
    