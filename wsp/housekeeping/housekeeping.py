#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jan 27 16:13:17 2020

housekeeping.py

This file is part of wsp

# PURPOSE #
This module has dedicated QThread loops that run at various times 
and log system information.

@author: nlourie
"""

# system packages
import sys
import os
import numpy as np
import time
from PyQt5 import uic, QtCore, QtGui, QtWidgets

# add the wsp directory to the PATH
wsp_path = os.path.dirname(os.getcwd())
sys.path.insert(1, wsp_path)



class slowLoop(QtCore.QThread):
    
    def __init__(self,dome):
        QtCore.QThread.__init__(self)
        #self.n = input("  Enter a number to count up to: ")
        self.index = 0
        self.dome = dome
    def __del__(self):
        self.wait()
    
    def loop(self):
        self.index +=1
        if (self.index % 2) == 0:
            #Then it's even
            print("Slow Loop: i = %d" % self.index)
        
            print(f'Dome Az = {self.dome.az}')
        
        
    def run(self):
        print("Starting 1 Hz Loop")
        self.timer = QtCore.QTimer()
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.loop)
        self.timer.start()
        self.exec() # YOU NEED THIS TO START UP THE THREAD!
        # NOTE: only QThreads have this exec() function, NOT QRunnables
        # If you don't do the exec(), then it won't start up the event loop
        # QThreads have event loops, not QRunnables
        """
        # NOTE: only QThreads have this exec() function, NOT QRunnables
        #       If you don't do the exec(), then it won't start up the event 
        #       loop QThreads have event loops, not QRunnables
        
        # Source: https://doc.qt.io/qtforpython/overviews/timers.html 
        Quote:
          In multithreaded applications, you can use the timer mechanism in any
          thread that has an event loop. To start an event loop from a non-GUI 
          thread, use exec()
          
        """
class update_status(QtCore.QThread):
    
    def __init__(self):
        QtCore.QThread.__init__(self)
        
    def __del__(self):
        self.wait()
    
    def get_status(self):
        
        
        