#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Apr  8 10:19:30 2021

App to simulate the Dome

Uses the dome_simulator.ui file


@author: nlourie
"""


#from PyQt5.QtGui import *
#from PyQt5.QtWidgets import *
#from PyQt5.QtCore import *

from PyQt5 import QtGui
from PyQt5 import QtWidgets
from PyQt5 import QtCore

import time
import traceback, sys
from datetime import datetime
import threading



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


            
class WorkerQThread(QtCore.QThread):
    '''
    Worker thread

    Inherits from QThread to handler worker thread setup, signals and wrap-up.

    :param callback: The function callback to run on this worker thread. Supplied args and 
                     kwargs will be passed through to the runner.
    :type callback: function
    :param args: Arguments to pass to the callback function
    :param kwargs: Keywords to pass to the callback function

    '''
    error    = QtCore.pyqtSignal(tuple)
    result   = QtCore.pyqtSignal(object)
    progress = QtCore.pyqtSignal(int)
    '''
    error
        `tuple` (exctype, value, traceback.format_exc() )
    
    result
        `object` data returned from processing, anything

    progress
        `int` indicating % progress 
    '''
    
    
    def __init__(self, fn, timeout = 2, *args, **kwargs):
        super(WorkerQThread, self).__init__()

        # Store constructor arguments (re-used for processing)
        self.fn = fn
        self.args = args
        
        # Set up the timeout. Convert seconds to ms
        self.timeout = timeout
        
        self.kwargs = kwargs

        # Add the callback to our kwargs
        self.kwargs['progress_callback'] = self.progress        
        
    def __del__(self):
        print("del")
        self.wait()
        
    def throwTimeoutError(self):
        msg = "command took too long to execute!"
        print(msg)
        #raise TimeoutError(msg)
        
        exctype, value = sys.exc_info()[:2]
        self.error.emit((exctype, value, traceback.format_exc()))

        print('worker thread shutting down...')
        # close the timerthread
        self.timerthread.quit()
        self.timerthread.terminate()
        #self.timerthread.wait()
        
        # kill the thread
        #self.finished.emit()  # Done
        # this says to put wait() after terminate to make sure it happens: https://het.as.utexas.edu/HET/Software/PyQt/qthread.html#terminate
        self.terminate()
        #self.wait()

        
    @QtCore.pyqtSlot()
    def run(self):
        '''
        Initialise the runner function with passed args, kwargs.
        '''
        print(f"wintercmd Worker running {self.fn.__name__} in thread {threading.get_ident()}")
        self.timerthread = TimerThread(self.timeout)
        # start the timer thread
        self.timerthread.start()
        
        self.timerthread.timerTimeout.connect(self.throwTimeoutError)
        
        
        
        # list all the active threads:
        """for thread in threading.enumerate(): 
            print(thread.name)"""
        # Retrieve args/kwargs here; and fire processing using them
        try:
            result = self.fn(*self.args, **self.kwargs)
        except Exception as e:
            msg = f"wintercmd Worker running {self.fn.__name__}: {e.__class__.__name__}, {e}"
            print(msg)
            #traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.error.emit((exctype, value, traceback.format_exc()))
        else:
            self.result.emit(result)  # Return the result of the processing
        finally:
            print('worker thread shutting down...')
            # close the timerthread
            self.timerthread.terminate()
            
            #self.finished.emit()  # Done
            
            
            

class MainWindow(QtWidgets.QMainWindow):


    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)
    
        self.counter = 0
    
        layout = QtWidgets.QVBoxLayout()
        
        self.l = QtWidgets.QLabel("Start")
        b = QtWidgets.QPushButton("DANGER!")
        b.pressed.connect(self.oh_no)
    
        layout.addWidget(self.l)
        layout.addWidget(b)
    
        w = QtWidgets.QWidget()
        w.setLayout(layout)
    
        self.setCentralWidget(w)
    
        self.show()

        self.timer = QtCore.QTimer()
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.recurring_timer)
        self.timer.start()

    def throwTimeoutError(self):
        msg = "command took too long to execute!"
        #print(msg)
        raise TimeoutError(msg)

    
    def progress_fn(self, n):
        print("%d%% done" % n)
        

    def execute_this_fn(self, progress_callback):
        for n in range(0, 5):
            time.sleep(1)
            progress_callback.emit(n*100/4)
            """if n>2:
                self.throwTimeoutError()"""
                
        return "Done."
 
    def print_output(self, s):
        print(s)
        

    def worker_thread_finished(self):
        print("WORKER THREAD FINISHED\n")
 
    def oh_no(self):
        print(f"main ({threading.get_ident()}): going to run function oh_no in a new worker thread")
        # Pass the function to execute
        #worker = Worker(self.execute_this_fn) # Any other args, kwargs are passed to the run function
        worker = WorkerQThread(self.execute_this_fn, timeout = 3.0)
        worker.start() # this has to happen before the signal connections otherwise it all crashes!
        worker.result.connect(self.print_output)
        worker.progress.connect(self.progress_fn)
        worker.finished.connect(self.worker_thread_finished)
        
        # Execute
        #self.threadpool.start(worker) 
        
    def recurring_timer(self):
        self.counter +=1
        self.l.setText("Counter: %d" % self.counter)
        #time.sleep(5)
    
app = QtWidgets.QApplication([])
window = MainWindow()
app.exec_()