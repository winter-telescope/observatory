#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Mar 10 16:46:45 2021

@author: nlourie
"""
import os
import sys
import threading
import signal
from PyQt5 import QtCore, QtWidgets
#from PyQt5.QtCore import QThread, QTimer
#from PyQt5.QtWidgets import QApplication, QPushButton, QWidget

# add the wsp directory to the PATH
code_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
wsp_path = os.path.join(code_path, 'wsp')
sys.path.insert(1, wsp_path)
print(f'__main__: wsp_path = {wsp_path}')

from housekeeping import data_handler

class daq_loop(QtCore.QThread):
    """
    This is a generic QThread which will execute the specified function
    at the specified cadence.

    It is meant for polling different sensors or instruments or servers
    each in their own thread so they don't bog each other down.
    """
    def __init__(self, func, dt, name = '', print_thread_name_in_update = False, *args, **kwargs):
        QtCore.QThread.__init__(self)

        self.index = 0
        self.name = name
        
        # define the function and options that will be run in this daq loop
        self.func = func
        self.args = args
        self.kwargs = kwargs

        # describe the loop rate
        self.dt = dt
        
        self._print_thread_name_in_update_ = print_thread_name_in_update
        
        # can i make it start itself?
        self.start()
        
    def run(self):
        def update():
            ### POLL THE DATA ###
            try:
                self.func(*self.args, **self.kwargs)
                
                print(f'{self.name}: running func: {self.func.__name__} in thread {threading.get_ident()}')
                
            except Exception as e:
                '''
                do nothing, don't want to clog up the program with errors if there's
                a problem. let this get handled elsewhere.
                '''
                print(f'could not execute function {self.func.__name__} because of {type(e)}: {e}')
                pass
    
            self.index += 1
        
        
        print(f'{self.name}: starting timed loop in thread {threading.get_ident()}')
        self.timer = QtCore.QTimer()
        self.timer.setInterval(self.dt)
        self.timer.timeout.connect(update)
        self.timer.start()
        self.exec_()
        print(f'{self.name}: running daqloop of func: {self.func.__name__} in thread {threading.get_ident()}')
    
    def __del__(self):
        self.wait()

    

class WorkerThread(QtCore.QThread):
    def run(self):
        def work():
            print("working from :" + str(threading.get_ident()))
            QtCore.QThread.sleep(5)
        print("thread started from :" + str(threading.get_ident()))
        timer = QtCore.QTimer()
        timer.timeout.connect(work)
        timer.start(10000)
        self.exec_()

"""
class MyGui(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.initUi()
"""
class MyGui(QtCore.QObject):   
    def __init__(self):            
        super().__init__()  
        #self.worker = WorkerThread(self)
        print("Starting worker from :" + str(threading.get_ident()))
        self.worker = data_handler.daq_loop(self.nullFunc,1000,'worker', print_thread_name_in_update = True, thread_numbering = 'norm')

    def initUi(self):
        self.setGeometry(500, 500, 300, 300)
        self.pb = QtWidgets.QPushButton("Button", self)
        self.pb.move(50, 50)
    
    def nullFunc(self):
        pass
"""
if __name__ == '__main__':    
    app = QtWidgets.QApplication(sys.argv)
    gui = MyGui()
    gui.show()
    sys.exit(app.exec_())

"""

def sigint_handler( *args):
    """Handler for the SIGINT signal."""
    sys.stderr.write('\r')
    
    # put in a quit for each thread to explicitly kill them
    
    
    QtCore.QCoreApplication.quit()

if __name__ == "__main__":
    app = QtCore.QCoreApplication(sys.argv)

    
    main = MyGui()

    
    signal.signal(signal.SIGINT, sigint_handler)

    # Run the interpreter every so often to catch SIGINT
    timer = QtCore.QTimer()
    timer.start(500) 
    timer.timeout.connect(lambda: None) 

    sys.exit(app.exec_())