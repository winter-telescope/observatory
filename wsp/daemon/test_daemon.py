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





class daq_loop(QtCore.QThread):
    """
    This is a generic QThread which will execute the specified function
    at the specified cadence.

    It is meant for polling different sensors or instruments or servers
    each in their own thread so they don't bog each other down.
    """
    def __init__(self, func, dt, name = '', *args, **kwargs):
        QtCore.QThread.__init__(self)

        self.index = 0
        self.name = name
        
        # define the function and options that will be run in this daq loop
        self.func = func
        self.args = args
        self.kwargs = kwargs

        # describe the loop rate
        self.dt = dt
    
        print(f'{self.name}: starting timed loop')
        self.timer = QtCore.QTimer()
        self.timer.setInterval(self.dt)
        self.timer.timeout.connect(self.update)
        self.timer.start()
        #self.exec()
        print(f'{self.name}: running daqloop of func: {self.func.__name__} in thread {self.currentThread()}')
    
    def __del__(self):
        self.wait()

    def update(self):
        ### POLL THE DATA ###
        try:
            self.func(*self.args, **self.kwargs)
        except Exception as e:
            '''
            do nothing, don't want to clog up the program with errors if there's
            a problem. let this get handled elsewhere.
            '''
            print(f'could not execute function {self.func.__name__} because of {type(e)}: {e}')
            pass

        self.index += 1


@Pyro5.server.expose
class Counter(object):
    def __init__(self, start = 0, step = 10, dt = 1000, name = 'counter'):
        self.name = name
        self.dt = dt
        self.start = start
        self.step = step
        self.count = self.start
        self.msg = 'initial message'
        
        self.daqloop = daq_loop(self.update, dt = self.dt, name = self.name)
    
    def update(self):
        self.msg = f'{self.name}: {self.count}'
        self.count += self.step
        
        print(self.msg)
        
    def getMsg(self):
        return self.msg
    
    def getCount(self):
        return self.count
    
    
"""
print('test daemon will print to a file')

dirname = os.getenv("HOME") + '/Downloads/'
filename = dirname + 'test.txt'
print(f'test_daemon: daemon will print to file: {filename}')

if os.path.exists(filename):
    print('test_daemon: deleting existing file')
    os.remove(filename)

else:
  print("test_daemon: The file does not exist. Creating it now")
  
fp = open(dirname + 'test.txt','w')

i = 0
#print('Writing numbers to the file:')



try:
    while True:
        print(f'mainthread:  {i}')
        fp.write(f'{i}\n')
        fp.flush()
        i += 1
        time.sleep(1)
except KeyboardInterrupt:
    pass
"""

class PyroDaemon(QtCore.QThread):
    """
    This is a generic QThread which will execute the specified function
    at the specified cadence.

    It is meant for polling different sensors or instruments or servers
    each in their own thread so they don't bog each other down.
    """
    def __init__(self, obj):
        QtCore.QThread.__init__(self)
        
        self.obj = obj
        
        
    def run(self):
        daemon = Pyro5.server.Daemon()

        ns = Pyro5.core.locate_ns()
        self.uri = daemon.register(self.obj)
        ns.register("counter", self.uri)
        daemon.requestLoop()
        
        
class PyroGUI(QtCore.QObject):   

                  
    def __init__(self, parent=None ):            
        super(PyroGUI, self).__init__(parent)   
        
        self.counter = Counter(start = 0, step = 1, dt = 1000, name = 'counter')
                
        self.pyro_thread = PyroDaemon(obj = self.counter)
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

