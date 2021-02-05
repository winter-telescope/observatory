#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import os
import Pyro5.core
import Pyro5.server
import random
from datetime import datetime
import time
from PyQt5 import uic, QtCore, QtGui, QtWidgets

# add the wsp directory to the PATH
#wsp_path = os.path.dirname(os.getcwd())
#sys.path.insert(1, wsp_path)

import weather
from utils import utils
from utils import logging_setup




class weatherMonitor(QtCore.QThread):
    def __init__(self, weather):
        super().__init__()
        self.running = False
        self.weather = weather

    def stop(self):
        self.running = False

    def run(self):
        self.running = True

        while self.running:
            print("Thread calling get Weather")
            self.weather.getWeather()
            time.sleep(5)


@Pyro5.server.expose
class Weather(object):
    # ... methods that can be called go here...
    def __init__(self):
        pass



    def startWeather(self, base_directory):
        # launch a thread which periodically updates the weather

        self.base_directory = base_directory


        # load the config
        config_file = base_directory + '/config/config.yaml'
        self.config = utils.loadconfig(config_file)

        # set up the logger
        self.logger = logging_setup.setup_logger(self.base_directory, self.config)

        # init the weather
        try:
            # self.logger.info('control: trying to load weather')
            print('control: trying to load weather')
            self.palomarWeather = weather.palomarWeather(self.base_directory,config = self.config, logger = self.logger)
        except Exception as e:
            self.palomarWeather = None
            # self.logger.warning(f"control: could not load weather data: {e}")
            print(f"control: could not load weather data: {e}")

        self.weatherThread = weatherMonitor(self.palomarWeather)
        self.weatherThread.start()

    def shutdownWeather(self):
        #kill the weather thread
        self.weatherThread.stop()


    def getWeather(self):
        self.PTS_status = self.palomarWeather.PTS_status
        self.status_p200 = self.PTS_status[0]
        self.status_p60 = self.PTS_status[1]
        self.status_p48 = self.PTS_status[2]

        self.ok_to_observe = self.palomarWeather.ok_to_observe
        print(f'weatherd: ok to observe? {self.ok_to_observe}')
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



    def weather_safe(self):
        #return the most recent value of the weather since it was last updated
        self.weatherValue = self.weather.weatherValue
        return self.weatherValue

if __name__ == '__main__':
    #launch the daemon in a seperate thread. This allows this program to not block when daemon.requestLoop is called
    #We can now do other things in this program I guess

    # Big Question: How do we run a continuous process that the daemon is monitoring.
        #One way I guess could be to have a program that constantly checks weather and writes it down somewhere. The daemon just looks it up then
    daemon = Pyro5.server.Daemon()
    ns = Pyro5.core.locate_ns()
    uri = daemon.register(Weather)
    ns.register("weather", uri)
    print("weather daemon running")
    daemon.requestLoop()
