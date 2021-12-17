#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Aug 31 15:55:54 2021

App to simulate the sun through the course of the day

@author: nlourie
"""



from PyQt5 import uic, QtCore, QtWidgets
import sys
import json
from datetime import datetime, timedelta
import Pyro5.core
import Pyro5.server
import os
import threading
import shlex
import time
import numpy as np
import traceback
import yaml
import logging
import pytz
import astropy.coordinates
import astropy.units as u

# add the wsp directory to the PATH
wsp_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),'wsp')
# switch to this when ported to wsp
#wsp_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

sys.path.insert(1, wsp_path)
print(f'sun_simulator: wsp_path = {wsp_path}')

from utils import logging_setup
from housekeeping import data_handler
#from utils import utils
from daemon import daemon_utils




class SunSimulator(QtWidgets.QMainWindow):

    """
    The class taking care for the main window.
    It is top-level with respect to other panes, menus, plots and
    monitors.
    """
    
    newState = QtCore.pyqtSignal(str)
    
    def __init__(self, logger = None, *args, **kwargs):

        """
        Initializes the main window
        """

        super(SunSimulator, self).__init__(*args, **kwargs)
        uic.loadUi(os.path.join(wsp_path, 'ephem', 'sun_simulator.ui'), self) # Load the .ui file
        
        self.threadpool = QtCore.QThreadPool()
        
        self.logger = logger
        
        self.log(f'main thread {threading.get_ident()}: setting up simulated dome')
        
        # init the time
        self.tz = pytz.timezone('America/Los_Angeles')
        
        # things that manage the time update loop
        self.update_dt = 1000 # ms
        self.speed = 1 # seconds per second

        
        #self.logger = logger
        
        # NEED TO SET UP A TEST LOGGER AND CONFIG OTHERWISE THIS WON'T RUN
        self.config = yaml.load(open(wsp_path + '/config/config.yaml'), Loader = yaml.FullLoader)
        
        # set up the site info for calculating ephemeris
        # set up site
        lat = astropy.coordinates.Angle(self.config['site']['lat'])
        lon = astropy.coordinates.Angle(self.config['site']['lon'])
        height = self.config['site']['height'] * u.Unit(self.config['site']['height_units'])
                                        
        self.site = astropy.coordinates.EarthLocation(lat = lat, lon = lon, height = height)
        
        # set up the daqloop to update the state
        self.updateLoop = data_handler.daq_loop(func = self.update_state, dt = self.update_dt, name = 'update_state', autostart = False)
        
        # load up the widgets
        
        # date/time input boxes
        self.datebox = self.findChild(QtWidgets.QDateEdit, "dateEdit")
        self.timebox = self.findChild(QtWidgets.QTimeEdit, "timeEdit")
        
        # date/time display boxes
        self.timeDisplay = self.findChild(QtWidgets.QLabel, "timeDisplay")
        self.dateDisplay = self.findChild(QtWidgets.QLabel, "dateDisplay")
        
        # reset date/time button
        self.reset_button = self.findChild(QtWidgets.QPushButton, "reset_button")
        
        # sun alt/az
        self.sun_alt_display = self.findChild(QtWidgets.QLabel, "sun_alt_display")
        self.sun_az_display  = self.findChild(QtWidgets.QLabel, "sun_az_display")
        
        # speedbox
        self.speedbox = self.findChild(QtWidgets.QSpinBox, "speedbox")
        self.speedbox.setSingleStep(10)
        
        # start/stop
        self.stop_button = self.findChild(QtWidgets.QPushButton, "stop_button")
        self.run_button = self.findChild(QtWidgets.QPushButton, "run_button")
        
        
        # connect signals/slots
        self.reset_button.pressed.connect(self.reset_time)
        self.run_button.pressed.connect(self.updateLoop.start)
        self.stop_button.pressed.connect(self.updateLoop.quit)
        
        
        # Set up the state dictionary
        self.state = dict()
        self.init_time()
        self.init_state()
        self.update_state()
        
        
        
        
    def log(self, msg, level = logging.INFO):
        if self.logger is None:
                print(msg)
        else:
            self.logger.log(level = level, msg = msg)
    
    def init_time(self):
        now_local = datetime.now(self.tz)
        year = now_local.year
        month = now_local.month
        day = now_local.day
        
        self.time = datetime(year = year, month = month, day = day, hour = 17, minute = 30, second = 0) 
        self.time = self.tz.localize(self.time)
        self.sun_timestamp = self.time.timestamp()
        self.sun_timeiso = self.time.isoformat(sep = ' ')
        
        self.qtime_requested = QtCore.QDateTime.fromTime_t(int(np.round(self.time.timestamp())))
        
        # update the reset time display to the initial qtime_requested
        self.datebox.setDateTime(self.qtime_requested)
        self.timebox.setDateTime(self.qtime_requested)
        
        
    
    def init_state(self):
        utc = datetime.utcnow()
        utc_datetime_str = datetime.strftime(utc, '%Y-%m-%d %H:%M:%S.%f')        # last query time string
        
        # init sun_timestamp to noon today
        
        self.state.update({'UTC' : utc_datetime_str})
        self.state.update({'sun_alt' : -888,
                           'sun_az'  : -888,
                           'timestamp' : self.time.timestamp()
                           }
                          )
   
    
    def reset_time(self):
        # get the time from the buttons
        date_requested_qtime = self.datebox.dateTime()
        time_requested_qtime = self.timebox.dateTime()
        # convert to datetime object because i know how to handle those!
        date_requested = date_requested_qtime.toPyDateTime().date()
        time_requested = time_requested_qtime.toPyDateTime().time()
        
        datetime_requested = datetime(year          = date_requested.year,
                                      month         = date_requested.month,
                                      day           = date_requested.day,
                                      hour          = time_requested.hour,
                                      minute        = time_requested.minute,
                                      second        = time_requested.second,
                                      microsecond   = time_requested.microsecond)
        
        self.time = self.tz.localize(datetime_requested)#NPL 12-17-21 added this localization to try and fix timezone errors
        
        self.update_state()
    
    def getSunAltAz(self, obstime, time_format = 'datetime'):
        
        
        # make sure we enforce the timezone
        #obstime = self.tz.localize(obstime)
        
        obstime_astropy = astropy.time.Time(obstime, format = time_format)
        
        frame = astropy.coordinates.AltAz(obstime = obstime_astropy, location = self.site)
        
        sunloc = astropy.coordinates.get_sun(obstime_astropy)
        
        sun_coords = sunloc.transform_to(frame)
        
        sun_alt = sun_coords.alt.value
        sun_az  = sun_coords.az.value       
        
        # get the sun_alt from 0.5 seconds ago to determine if the sun is rising or setting
        earlier_obstime = obstime - timedelta(seconds = 0.5)
        earlier_obstime_astropy = astropy.time.Time(earlier_obstime, format = time_format)
        earlier_frame = astropy.coordinates.AltAz(obstime = earlier_obstime_astropy, location = self.site)
        earlier_sunloc = astropy.coordinates.get_sun(obstime_astropy)
        
        earlier_sun_coords = earlier_sunloc.transform_to(earlier_frame)
        earlier_sun_alt = earlier_sun_coords.alt.value
        
        if sun_alt >= earlier_sun_alt:
            sun_rising = True
        else:
            sun_rising = False
        
        return sun_alt, sun_az, sun_rising
        
    def update_time(self):
        
        dt = (self.update_dt/1000.0) * self.speed
        
        newtime = self.time + timedelta(seconds = dt)
        
        self.time = newtime
        self.sun_timestamp = self.time.timestamp()
        
        
    
    def update_state(self):
        utc = datetime.utcnow()
        utc_datetime_str = datetime.strftime(utc, '%Y-%m-%d %H:%M:%S.%f')        # last query time string
        
        
        self.state.update({'UTC' : utc_datetime_str})
        
        self.qtime = QtCore.QDateTime.fromTime_t(int(np.round(self.sun_timestamp)))
        
        self.sun_alt, self.sun_az, self.sun_rising = self.getSunAltAz(self.time)
        
        # get the current speed
        self.speed = self.speedbox.value()
        
        
        # update the state
        self.state.update({'sun_alt' : self.sun_alt})
        
        self.state.update({'sun_az' : self.sun_az})
        
        self.state.update({'sun_rising' : self.sun_rising})
        
        self.state.update({'timestamp': self.sun_timestamp})
        
        
        # publisht the state
        self.state_json = json.dumps(self.state)
        self.update_display()
    
        self.newState.emit(self.state_json)
        
        self.update_time()
        
        
    def update_display(self):
        
        """"""
        
        self.dateDisplay.setText(self.time.strftime('%m/%d/%y'))   
        self.timeDisplay.setText(self.time.strftime('%H:%M:%S'))
        
        self.sun_az_display.setText( f'{self.sun_az :0.1f}')
        self.sun_alt_display.setText(f'{self.sun_alt : 0.1f}')
    
    
    @Pyro5.server.expose
    def getState(self):
        return self.state
    
    @Pyro5.server.expose
    def GetStatus(self):
        return self.state
    

class PyroGUI(QtCore.QObject):   

                  
    def __init__(self, logger = None, parent=None ):            
        super(PyroGUI, self).__init__(parent)   
        print(f'main: running in thread {threading.get_ident()}')
        
        self.sunsim = SunSimulator(logger = logger)
                
        self.pyro_thread = daemon_utils.PyroDaemon(obj = self.sunsim, name = 'sunsim')
        self.pyro_thread.start()

        
    
if __name__ == '__main__':
    
    doLogging = True
    sunsim = True
    
    config = yaml.load(open(wsp_path + '/config/config.yaml'), Loader = yaml.FullLoader)
    # set up the logger
    if doLogging:
        logger = logging_setup.setup_logger(wsp_path, config)    
    else:
        logger = None
        
        
    
    app = QtWidgets.QApplication(sys.argv)
    main = PyroGUI(logger = logger)
    
    

    main.sunsim.show()
    app.exec_()