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
import getopt
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



@Pyro5.server.expose
class Counter(QtCore.QObject):
    def __init__(self, start = 0, step = 10, dt = 1000, name = 'counter', verbose = False):
        
        super(Counter, self).__init__()   
        
        self.name = name
        self.dt = dt
        self.start = start
        self.step = step
        self.count = self.start
        self.msg = 'initial message'
        
        self.expTimer = QtCore.QTimer()
        self.expTimer.setSingleShot(True)
        self.expTimer.timeout.connect(self.print_done)
        #self.timer.start()
        
        if verbose:
            self.daqloop = data_handler.daq_loop(self.update, dt = self.dt, name = self.name, print_thread_name_in_update = True, thread_numbering = 'norm')
        else:
            self.daqloop = data_handler.daq_loop(self.update, dt = self.dt, name = self.name)
    
    def run_timer(self):
        print()
        print('running timer')
        self.timerthread = TimerThread(5)
        self.timerthread.timerTimeout.connect(self.print_done)
        self.timerthread.timerTimeout.connect(self.timerthread.terminate)
        self.timerthread.run()
        
        
        
    def update(self):
        #self.msg = f'{self.name}: {self.count}'
        self.count += self.step
        
        #print(self.msg)
        
    def getMsg(self):
        return self.msg
    
    def getCount(self):
        return self.count
    
    def print_done(self):
        print('TIMER IS DONE!')
    



        
class PyroGUI(QtCore.QObject):   

                  
    def __init__(self, ns_host, parent=None ):            
        super(PyroGUI, self).__init__(parent)   
        print(f'main: running in thread {threading.get_ident()}')
        
        self.counter = Counter(start = 0, step = 1, dt = 1000, name = 'counter', verbose = False)
                
        self.pyro_thread = daemon_utils.PyroDaemon(obj = self.counter, name = 'counter', ns_host = ns_host)
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
    
    main.counter.daqloop.quit()
    
    QtCore.QCoreApplication.quit()

if __name__ == "__main__":
    
    ##### GET ANY COMMAND LINE ARGUMENTS #####
    
    args = sys.argv[1:]
    print(f'args = {args}')
    
    # set the defaults
    verbose = False
    doLogging = True
    ns_host = None
    
    options = "vpn:"
    long_options = ["verbose", "print", "ns_host:"]
    arguments, values = getopt.getopt(args, options, long_options)
    # checking each argument
    print()
    print(f'Parsing sys.argv...')
    print(f'arguments = {arguments}')
    print(f'values = {values}')
    for currentArgument, currentValue in arguments:
        if currentArgument in ("-v", "--verbose"):
            verbose = True
            print("Running in VERBOSE mode")
        
        elif currentArgument in ("-p", "--print"):
            doLogging = False
            print("Running in PRINT mode (instead of log mode).")
        elif currentArgument in ("-n", "--ns_host"):
            ns_host = currentValue
    
    ##### RUN THE APP #####
    app = QtCore.QCoreApplication(sys.argv)
    
    
    main = PyroGUI(ns_host = ns_host)

    
    signal.signal(signal.SIGINT, sigint_handler)

    # Run the interpreter every so often to catch SIGINT
    timer = QtCore.QTimer()
    timer.start(500) 
    timer.timeout.connect(lambda: None) 

    sys.exit(app.exec_())

