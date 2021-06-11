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
#import time
#from PyQt5 import uic, QtGui, QtWidgets
from PyQt5 import QtCore
#from astropy.io import fits
#import numpy as np
import sys
import signal
#import queue
import threading

# add the wsp directory to the PATH
wsp_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(1, wsp_path)
print(f'wsp_path = {wsp_path}')


from housekeeping import data_handler
from daemon import daemon_utils


class TimerThread(QtCore.QThread):
    '''
    This is a thread that just counts up the timeout and then emits a 
    timeout signal. It will be connected to the worker thread so that it can
    run a separate thread that times each worker thread's execution
    '''
    timerTimeout = QtCore.pyqtSignal()
    
    def __init__(self, timeout, *args, **kwargs):
        super(TimerThread, self).__init__()
        print('created a timer thread')
        # Set up the timeout. Convert seconds to ms
        self.timeout = timeout*1000.0
        
        
    def run(self):
        def printTimeoutMessage():
            print(f'timer thread: timeout happened')
        print(f'running timer in thread {threading.get_ident()}')
        # run a single shot QTimer that emits the timerTimeout signal when complete
        self.timer= QtCore.QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(printTimeoutMessage)
        self.timer.timeout.connect(self.timerTimeout.emit)
        self.timer.start(self.timeout)
        self.exec_() 


class Counter(QtCore.QObject):
    
    runTimerSignal = QtCore.pyqtSignal(object)
    
    def __init__(self, start = 0, step = 10, dt = 1000, name = 'counter', verbose = False):
        
        super(Counter, self).__init__()   
        
        self.name = name
        self.dt = dt
        self.start = start
        self.step = step
        self.count = self.start
        self.msg = 'initial message'


        
        if verbose:
            self.daqloop = data_handler.daq_loop(self.update, dt = self.dt, name = self.name, print_thread_name_in_update = True, thread_numbering = 'norm')
        else:
            self.daqloop = data_handler.daq_loop(self.update, dt = self.dt, name = self.name)
    
    @Pyro5.server.expose
    def run_timer(self):
        waittime = 5000.5
        print(f'Signaling Main to Run Timer (waittime = {waittime} from thread {threading.get_ident()}')
        self.runTimerSignal.emit(waittime)
        
        
    @Pyro5.server.expose    
    def update(self):
        #self.msg = f'{self.name}: {self.count}'
        self.count += self.step
        
        #print(self.msg)
    
    @Pyro5.server.expose
    def getMsg(self):
        return self.msg
    
    @Pyro5.server.expose
    def getCount(self):
        return self.count
    
    @Pyro5.server.expose
    def print_done(self):
        print('TIMER IS DONE!')
        
    def timerDone(self):
        print('Got signal from PyroGUI that the timer is done :D')
    



        
class PyroGUI(QtCore.QObject):   

    expTimerComplete = QtCore.pyqtSignal()
                  
    def __init__(self, parent=None ):            
        super(PyroGUI, self).__init__(parent)   
        print(f'main: running in thread {threading.get_ident()}')
        
        self.timer = QtCore.QTimer()
        self.timer.setSingleShot(True)
        #self.timer.setInterval(5000.5)
        self.timer.timeout.connect(self.print_done)
        
        
        self.counter = Counter(start = 0, step = 1, dt = 1000, name = 'counter', verbose = False)
        
        #self.counter.runTimerSignal.connect(self.timer.start)
        self.counter.runTimerSignal.connect(self.startExpTimer)
        self.expTimerComplete.connect(self.counter.timerDone)
        
        self.pyro_thread = daemon_utils.PyroDaemon(obj = self.counter, name = 'counter')
        self.pyro_thread.start()
        
  
    def print_done(self):
        print('TIMER IS DONE! Emitting expTimerComplete signal')
        self.expTimerComplete.emit()

    def startExpTimer(self, waittime):
        self.timer.setInterval(waittime)
        self.timer.start()
            
        
def sigint_handler( *args):
    """Handler for the SIGINT signal."""
    sys.stderr.write('\r')
    
    main.counter.daqloop.quit()
    
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

