#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Feb 16 17:42:28 2021

test daemon


@author: nlourie
"""
import os
import Pyro5.core
import Pyro5.server
import time
from PyQt5 import uic, QtCore, QtGui, QtWidgets
from astropy.io import fits
import numpy as np
import sys
import signal
import queue

# add the wsp directory to the PATH
wsp_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(1, wsp_path)
print(f'wsp_path = {wsp_path}')


from housekeeping import data_handler
from daemon import daemon_utils





@Pyro5.server.expose
class Counter(object):
    def __init__(self, start = 0, step = 10, dt = 1000, name = 'counter'):
        self.name = name
        self.dt = dt
        self.start = start
        self.step = step
        self.count = self.start
        self.msg = 'initial message'
        
        self.daqloop = data_handler.daq_loop(self.update, dt = self.dt, name = self.name)
    
    def update(self):
        self.msg = f'{self.name}: {self.count}'
        self.count += self.step
        
        #print(self.msg)
        
    def getMsg(self):
        return self.msg
    
    def getCount(self):
        return self.count
    



        
class PyroGUI(QtCore.QObject):   

                  
    def __init__(self, parent=None ):            
        super(PyroGUI, self).__init__(parent)   
        
        self.counter = Counter(start = 0, step = 1, dt = 1000, name = 'counter')
                
        self.pyro_thread = daemon_utils.PyroDaemon(obj = self.counter, name = 'counter')
        self.pyro_thread.start()
        
        """
        self.timer = QtCore.QTimer()
        self.timer.setInterval(500)
        self.timer.timeout.connect(self.check_pyro_queue)
        self.timer.start()
        """


            
        
def sigint_handler( *args):
    """Handler for the SIGINT signal."""
    sys.stderr.write('\r')
    
    
    QtCore.QCoreApplication.quit()

if __name__ == "__main__":
    app = QtCore.QCoreApplication(sys.argv)

    
    main = PyroGUI()

    
    signal.signal(signal.SIGINT, sigint_handler)

    # Run the interpreter every so often to catch SIGINT
    timer = QtCore.QTimer()
    timer.start(500) 
    timer.timeout.connect(lambda: None) 

    sys.exit(app.exec_())

