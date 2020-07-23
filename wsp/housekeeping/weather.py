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
import io
from configobj import ConfigObj
import urllib.request
import urllib.error
import urllib.parse
import numpy as np
from datetime import datetime,timedelta
import pytz
import sys
import traceback


# add the wsp directory to the PATH
wsp_path = os.path.dirname(os.getcwd())
sys.path.insert(1, wsp_path)

from utils import utils

#%%
# PDU Properties
class palomarWeather(object):
    def __init__(self,base_directory, config, logger):
        
        self.base_directory = base_directory
        self.config = config
        self.logger = logger
        
        # THIS IS A FLAG THAT CAN BE SET TO OVERRIDE THE WEATHER DOME OPEN VETO:
        self.override = False 
        
        self.getWeatherLimits()
        self.getWeather(firsttime = True)
        #self.caniopen() # checks all the dome vetoes based on weather
        
    
    def getWeatherLimits(self):
        try: # Load in the weather limits from the config file
            
            #configObj = ConfigObj(self.base_directory + '/config/' + self.limits_file)
            section = 'weather_limits'
            self.TEMP_OUT_MIN = self.config[section]['TEMP_OUT']['MIN']
            self.TEMP_OUT_MAX = self.config[section]['TEMP_OUT']['MAX']
            
            self.TEMP_IN_MIN = self.config[section]['TEMP_IN']['MIN']
            self.TEMP_IN_MAX = self.config[section]['TEMP_IN']['MAX']
            
            self.RH_OUT_MIN = self.config[section]['RH_OUT']['MIN']
            self.RH_OUT_MAX = self.config[section]['RH_OUT']['MAX']
            
            self.RH_IN_MIN = self.config[section]['RH_IN']['MIN']
            self.RH_IN_MAX = self.config[section]['RH_IN']['MAX']
            
            self.WIND_GUST_MIN = self.config[section]['WIND_GUST']['MIN']
            self.WIND_GUST_MAX = self.config[section]['WIND_GUST']['MAX'] 
            
            self.WIND_SPEED_MIN = self.config[section]['WIND_SPEED']['MIN']
            self.WIND_SPEED_MAX = self.config[section]['WIND_SPEED']['MAX']            
            
            self.DEWPOINT_IN_MIN = self.config[section]['DEWPOINT_IN']['MIN']
            self.DEWPOINT_IN_MAX = self.config[section]['DEWPOINT_IN']['MAX']
            
            self.DEWPOINT_OUT_MIN = self.config[section]['DEWPOINT_OUT']['MIN']
            self.DEWPOINT_OUT_MAX = self.config[section]['DEWPOINT_OUT']['MAX']
            
            self.TRANS_MIN = self.config[section]['TRANSPARENCY']['MIN']
            self.TRANS_MAX = self.config[section]['TRANSPARENCY']['MAX']
            
            self.SEEING_MIN = self.config[section]['SEEING']['MIN']
            self.SEEING_MAX = self.config[section]['SEEING']['MAX']
        
            self.CLOUD_MIN = self.config[section]['CLOUDS']['MIN']
            self.CLOUD_MAX = self.config[section]['CLOUDS']['MAX']
            
            
        except Exception as e:
            self.logger.warning('Unable to Load the Weather Limits : ',e)
        
    def getWeather(self,firsttime = False):
        #print(' Getting weather data...')
        
        #######################################################################
        # PTS: PALOMAR TELEMETRY SERVER
    
        #try: # LOAD DATA FROM THE PALOMAR TELEMETRY SERVER
        
        # Query the Telemetry Server
        server = 'telemetry_server'
        
        newstatus = utils.query_server(cmd = self.config[server]['cmd'],
                                    ipaddr = self.config[server]['addr'],
                                    port = self.config[server]['port'],
                                    end_char= self.config[server]['endchar'],
                                    timeout = self.config[server]['timeout'],
                                    logger = self.logger)
        
        # if the query_server command fails it returns None
        if newstatus is None:
            self.PTS_status = [dict(), dict(), dict()]
            self.P48_Online = 1
        else:
            self.PTS_status = newstatus
            self.P48_Online = 0
            
        #except Exception as e:
        #    errmsg = f"could not load weather from palomar telemetry server, {type(e)}: {e}"
        #    print(errmsg)
            
            #self.logger.warning(errmsg)
            #traceback.print_exc()
            #pass
        #print()
        #print('PTS Status: ', self.PTS_status)
        self.status_p200 = self.PTS_status[0]
        self.status_p60 = self.PTS_status[1]
        self.status_p48 = self.PTS_status[2]
        
        
        default = self.config['default_value']
        self.P48_UTC                        = self.status_p48.get('P48_UTC', '1970-01-01 00:00:00.00')     # last query timestamp
        self.P48_UTC_datetime_obj           = datetime.strptime(self.P48_UTC, '%Y-%m-%d %H:%M:%S.%f')   # last query time string
        self.P48_UTC_timestamp              = self.P48_UTC_datetime_obj.timestamp()                     # last read timestamp
        self.P48_Windspeed_Avg_Threshold    = self.status_p48.get('P48_Windspeed_Avg_Threshold', default)  # windspeed threshold (m/s)
        self.P48_Gust_Speed_Threshold       = self.status_p48.get('P48_Gust_Speed_Threshold', default)     # gust wind speed threshold (m/s)
        self.P48_Alarm_Hold_Time            = self.status_p48.get('P48_Alarm_Hold_Time', default)                      # alarm hold time (s)
        self.P48_Remaining_Hold_Time        = self.status_p48.get('P48_Remaining_Hold_Time', default)                    # remaining hold time (s)
        self.P48_Outside_DewPt_Threshold    = self.status_p48.get('P48_Outside_DewPt_Threshold', default)                # outside dewpoint (C)
        self.P48_Inside_DewPt_Threshold     = self.status_p48.get('P48_Inside_DewPt_Threshold', default)                  # inside dewpoint (C)
        self.P48_Wind_Dir_Current           = self.status_p48.get('P48_Wind_Dir_Current', default)                  # wind direction angle (deg)
        self.P48_Windspeed_Current          = self.status_p48.get('P48_Windspeed_Current', default)                       # windspeed current (m/s)
        self.P48_Windspeed_Average          = self.status_p48.get('P48_Windspeed_Average', default)                        # windspeed average (m/s)
        self.P48_Outside_Air_Temp           = self.status_p48.get('P48_Outside_Air_Temp', default)                         # outside air temp (C)
        self.P48_Outside_Rel_Hum            = self.status_p48.get('P48_Outside_Rel_Hum', default)                        # outside RH (%)
        self.P48_Outside_DewPt              = self.status_p48.get('P48_Outside_DewPt', default)                        # outside dewpoint (C)
        self.P48_Inside_Air_Temp            = self.status_p48.get('P48_Inside_Air_Temp', default)                        # inside air temp (C)
        self.P48_Inside_Rel_Hum             = self.status_p48.get('P48_Inside_Rel_Hum', default)                     # inside RH (%)
        self.P48_Inside_DewPt               = self.status_p48.get('P48_Inside_DewPt', default)                      # inside dewpoint (C)
        self.P48_Wetness                    = self.status_p48.get('P48_Wetness', 'YES')
        self.P48_Wetness_Num                = self.config['status_dict']['P48_Wetness'].get(self.P48_Wetness,  default) # wetness (0 or 1)
        self.P48_Weather_Status             = self.status_p48.get('P48_Weather_Status', 'UNKNOWN')                      
        self.P48_Weather_Status_Num         = self.config['status_dict']['P48_Weather_Status'].get(self.P48_Weather_Status, default) # ready? (1 if "READY", 0 if anything else)
                             
        
        
            
        """

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
        
        
        # get weather from the swerver
        #self.P4OTAIRT = status['P48_Outside_Air_Temp']
        
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
        '''
        # If the current air temp is near freezing, note the time as the "last freezing time"
        if self.P4OTAIRT < 1:
            self.P4LASTFRZ_TIME = self.P4LASTQUERY
        
        # If the current wetness status is True, then log the time as the last wet time
        if self.P4WETNES:
            self.P4LASTWET_TIME = self.P4LASTQUERY
         

        '''  
        """                  
        
        
        
        #######################################################################
        # PCS: Palomar Command Server
        
        # Query the command Server
        server = 'command_server'
        
        # LOAD DATA FROM THE PALOMAR COMMAND SERVER
        newstatus = utils.query_server(cmd = self.config[server]['cmd'],
                                    ipaddr = self.config[server]['addr'],
                                    port = self.config[server]['port'],
                                    end_char= self.config[server]['endchar'],
                                    timeout = self.config[server]['timeout'],
                                    logger = self.logger)
        
        # if the query_server command fails it returns None
        if newstatus is None:
            self.status_PCS = dict()
            self.PCS_Online = 1
        else:
            self.status_PCS = newstatus
            self.PCS_Online = 0
        
        
        default = self.config['default_value']
        self.PCS_UTC                        = self.status_PCS.get('UTC', '1970-01-01 00:00:00.00') # last query timestamp
        self.PCS_UTC_datetime_obj           = datetime.strptime(self.PCS_UTC, '%Y-%m-%d %H:%M:%S.%f')        # last query time string
        self.PCS_UTC_timestamp              = self.PCS_UTC_datetime_obj.timestamp()                          # last read timestamp
        self.PCS_Dome_Azimuth               = self.status_PCS.get('Dome_Azimuth', default)                                # azimuth of observatory dome
        self.PCS_Dome_Status                = self.status_PCS.get('Dome_Status', 'FAULT')               # status of observatory dome
        self.PCS_Dome_Status_Num            = self.config['status_dict']['Dome_Status'].get(self.PCS_Dome_Status, default)
        self.PCS_Shutter_Status             = self.status_PCS.get('Shutter_Status','FAULT')
        self.PCS_Shutter_Status_Num         = self.config['status_dict']['Shutter_Status'].get(self.PCS_Shutter_Status, default)
        self.PCS_Control_Status             = self.status_PCS.get('Control_Status','FAULT')
        self.PCS_Control_Status_Num         = self.config['status_dict']['Control_Status'].get(self.PCS_Control_Status, default)      
        self.PCS_Close_Status               = self.status_PCS.get('Close_Status','FAULT')
        self.PCS_Close_Status_Num           = self.config['status_dict']['Close_Status'].get(self.PCS_Close_Status, default) 
        self.PCS_Weather_Status             = self.status_PCS.get('Weather_Status','FAULT')
        self.PCS_Weather_Status_Num         = self.config['status_dict']['Weather_Status'].get(self.PCS_Weather_Status, default) 
        self.PCS_Outside_Dewpoint_Threshold = self.status_PCS.get('Outside_Dewpoint_Threshold',default)
        self.PCS_Outside_Temp               = self.status_PCS.get('Outside_Temp', default)
        self.PCS_Outside_RH                 = self.status_PCS.get('Outside_RH', default)
        self.PCS_Outside_Dewpoint           = self.status_PCS.get('Outside_Dewpoint', default)
        self.PCS_Weather_Hold_time          = self.status_PCS.get('Weather_Hold_time', default)
        
        
        
        
        try: # Load data from clear dark skies at palomar
            url = 'https://www.cleardarksky.com/txtc/PalomarObcsp.txt'
            page = urllib.request.urlopen(url)
            cdsdata = page.read()
            
            
            cdsdata = cdsdata.decode("utf-8")
            cdsdata = cdsdata.replace('"','')
            cdsdata = cdsdata.replace(')','')
            cdsdata = cdsdata.replace('(','')
            weather_filestream = io.StringIO(cdsdata)
            # Get the data in usable format, just grab the first 24 hours in the table
            wtime,cloud,trans,seeing,wind,hum,temp = np.loadtxt(weather_filestream,\
                                                                   unpack = True,\
                                                                   dtype = '|U32,int,int,int,int,int,int',\
                                                                   skiprows = 7,max_rows = 24,\
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
                    # 5 = 0-5 mph
                    # 4 = 6-11 mph
                    # 3 = 12-16 mph
                    # 2 = 17-28 mph
                    # 1 = 29-45 mph
                    # 0 = 45+ mph
            wind_min = [45,29,17,12,6,0]
            wind_max = [100,45,28,16,11,5]
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
            
            
        except Exception as e:
            print(f"problem loading weather data from clear dark skies, {type(e)}: {e}")
            #traceback.print_exc()
      
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
            print(f' P48 says the outside temp is bad')
        ok.append(temp_out)
        
        temp_in = (self.P4INAIRT >= self.TEMP_IN_MIN) & (self.P4INAIRT <= self.TEMP_IN_MAX)
        if not temp_in:
            print(f' P48 says the inside temp is bad')
        ok.append(temp_in)
        
        rh_out = (self.P4OTRHUM >= self.RH_OUT_MIN) & (self.P4OTRHUM <= self.RH_OUT_MAX)
        if not rh_out:
            print(f' P48 says the outside RH is bad')
        ok.append(rh_out)
        
        rh_in = (self.P4INRHUM >= self.RH_IN_MIN) & (self.P4INRHUM <= self.RH_IN_MAX)
        if not rh_in:
            print(f' P48 says the inside RH is bad')
        ok.append(rh_in)
        
        wind_gust = (self.P4WINDSP >= self.WIND_GUST_MIN) & (self.P4WINDSP <= self.WIND_GUST_MAX)
        if not wind_gust:
            print(f' P48 says the wind gust speed is bad')
        ok.append(wind_gust)
        
        wind_speed = (self.P4WINDAV >= self.WIND_SPEED_MIN) & (self.P4WINDAV <= self.WIND_SPEED_MAX)
        if not wind_speed:
            print(f' P48 says the average wind speed is bad')
        ok.append(wind_speed)
        
        dp_out = (self.P4OUTDEW >= self.DEWPOINT_OUT_MIN) & (self.P4OUTDEW <= self.DEWPOINT_OUT_MAX)
        if not dp_out:
            print(f' P48 says the outside dewpoint is bad')
        ok.append(dp_out)
        
        dp_in = (self.P4INDEW >= self.DEWPOINT_IN_MIN) & (self.P4INDEW <= self.DEWPOINT_IN_MAX)
        if not dp_in:
            print(f' P48 says the inside dewpoint is bad')
        ok.append(dp_in)       
        
        ### 2. check the inside temperature is higher than the outside dewpoint
        no_condensation = (self.P4INAIRT > self.P4OUTDEW)
        if not no_condensation:
            print(f' P48 says the inside temp is too cold and may condense if opened')
        ok.append(no_condensation)
        
        """
        ### 3. it hasn't rained in 1 hour
        rain_time_limit = 3600.0 # 1 hour
        no_rain = (self.P4LASTREAD - self.P4LASTWET_TIME).total_seconds() > rain_time_limit
        if not no_rain:
            print(f'P48 says it has been wet in the last {rain_time_limit/3600} hours')
        ok.append(no_rain)
        #TODO ADD THIS FEATURE ONCE WE GET THE TELEMETRY SERVER ONLINE
        
        ### 4. it hasn't been snowy (<freezing and wet) in 24 hours
        snow_time_limit = 24*3600.0 # 24 hours
        no_snow = ((self.P4LASTREAD - self.P4LASTWET_TIME).total_seconds() > snow_time_limit) & ((self.P4LASTREAD - self.P4LASTFRZ_TIME).total_seconds() > snow_time_limit)
        if not no_snow:
            print(f'P48 says it may have snowed in the last {snow_time_limit/3600} hours')
        ok.append(no_snow)
        #TODO ADD THIS FEATURE ONCE WE GET THE TELEMETRY SERVER ONLINE
        """
        
        if self.override == True:
            self.okaytoopen = True
            print()
            print('################### DANGER ###################')
            print('WEATHER OVERRIDE IS VETOING P48 WEATHER CHECK')
            print('################### DANGER ###################')
            print()
            return True
        else:
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
            print(f' CDS says Temperature is not okay: T = [{self.CDSTEMPMIN} - {self.CDSTEMPMAX}] Allowed = [{self.TEMP_OUT_MIN},{self.TEMP_OUT_MAX}]')
        ok.append(temp)
        
        cloud = ((self.CDSCLOUD >= self.CLOUD_MIN) & (self.CDSCLOUD <= self.CLOUD_MAX))
        if not cloud:
            print(f' CDS says too cloudy: Cloud Cover = {self.CDSCLOUD}, Max Allowed = {self.CLOUD_MAX}')
        ok.append(cloud)
        
        trans = ((self.CDSTRANS >= self.TRANS_MIN) & (self.CDSTRANS <= self.TRANS_MAX))
        if not trans:
            print(f' CDS says not transparent enough: Transparency = {self.CDSTRANS}, Max Allowed = {self.TRANS_MAX}')
        ok.append(trans)
        
        seeing = ((self.CDSSEEING >= self.SEEING_MIN) & (self.CDSSEEING <= self.SEEING_MAX))
        if not seeing:
            print(f' CDS says seeing is bad: Seeing = {self.CDSSEEING}, Allowed = [{self.SEEING_MIN},{self.SEEING_MAX}]')
        ok.append(seeing)
        
        wind = ((self.CDSWINDMIN >= self.WIND_SPEED_MIN) & (self.CDSWINDMAX <= self.WIND_SPEED_MAX))
        if not wind:
            print(f' CDS says too windy: Wind = [{self.CDSWINDMIN}-{self.CDSWINDMAX}], Max Allowed = {self.WIND_SPEED_MAX}') 
        ok.append(wind)
        
        rh = ((self.CDSRHMIN >= self.RH_OUT_MIN) & (self.CDSRHMAX <= self.RH_OUT_MAX))
        if not rh:
            print(f' CDS says RH is not in range: RH = [{self.CDSRHMIN}-{self.CDSRHMAX}], Allowed Range = [{self.RH_OUT_MIN},{self.RH_OUT_MAX}]')
        ok.append(rh)
        
        
        
        if self.override == True:
            self.oktoopen = True
            print()
            print('################### DANGER ###################')
            print('WEATHER OVERRIDE IS VETOING CDS WEATHER CHECK')
            print('################### DANGER ###################')
            print()
            return True
        else:
            self.oktoopen_cds = all(ok)
            return self.oktoopen_cds
        
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
    config = utils.loadconfig(wsp_path + '/config/config.yaml')
    night = utils.night()
    logger = utils.setup_logger(wsp_path, night, logger_name = 'logtest')
     
    weather = palomarWeather(os.path.dirname(os.getcwd()),config = config, logger = logger)
    
    #print('CDS Says OK to Open? ',weather.oktoopen_cds())
    #print('P48 Says OK to Open? ',weather.oktoopen_p48())
    #print(weather.cds)
    #weather.caniopen()
    print()
    print('Checking Weather:')
    try:
        #print(weather.status_p48)
        print(f'\tP48_Wetness = {weather.P48_Wetness}')
        print(f'\tP48_Wetness_Num = {weather.P48_Wetness_Num}')
    except Exception as e:
        print(f'\tcould not get P48 weather, {type(e)}: {e}')
    print()
    try:
        #print(weather.status_p48)
        print(f'\tPCS_Shutter_Status = {weather.PCS_Shutter_Status}')
        print(f'\tPCS_Shutter_Status_Num = {weather.PCS_Shutter_Status_Num}')
    except Exception as e:
        print(f'\tcould not get P48 weather, {type(e)}: {e}')
    print()
    try:
        print(f'\tweather.CDSCLOUD = {weather.CDSCLOUD}')
    except Exception as e:
        print(f'\tcould not get CDS weather, {type(e)}: {e}')

    #weather.override = True
    
    #print('Checking Weather:')
    #print(weather.caniopen())
    
#%%
"""
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


weather_filestream = io.StringIO(cdsdata)

wtime,cloud,trans,seeing,wind,hum,temp = np.loadtxt(weather_filestream,\
                                                       unpack = True,\
                                                       dtype = '|U32,int,int,int,int,int,int',\
                                                       skiprows = 7,max_rows = 24,\
                                                       delimiter = ',\t',usecols = (0,1,2,3,4,5,6),
                                                       encoding = "utf-8")
print(wtime)

"""