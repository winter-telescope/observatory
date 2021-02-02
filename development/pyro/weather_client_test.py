#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Dec 16 18:38:48 2020

@author: nlourie
"""

# This is the code that visits the warehouse
import sys
#import Pyro5.api as pyro
import Pyro5.api as pyro
import Pyro5.errors as pyroErrors

sys.excepthook = pyroErrors.excepthook

weather = pyro.Proxy("PYRONAME:weather_daemon")

currentWeather = weather.getCurrent()
print(f"current weather: dt = {currentWeather['dt']}, temp = {currentWeather['temp']}")