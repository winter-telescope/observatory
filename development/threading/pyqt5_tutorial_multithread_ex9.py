#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Mar 16 11:40:22 2020

This is a tutorial on pyqt and multithreading from here:
https://www.learnpyqt.com/courses/concurrent-execution/multithreading-pyqt-applications-qthreadpool/


This example tries to implement everything as a text-only interface
and not use the GUI.

@author: nlourie
"""


from PyQt5 import uic, QtCore, QtGui, QtWidgets
#from PyQt5.QtWidgets import QMessageBox

import os
import time
import sys
import traceback
import signal


class WorkerSignals(QtCore.QObject):
    '''
    Defines the signals available from a running worker thread.

    In this example we've defined 5 custom signals:
        finished signal, with no data to indicate when the task is complete.
        error signal which receives a tuple of Exception type, Exception value and formatted traceback.
        result signal receiving any object type from the executed function.
    
    Supported signals are:

    finished
        No data
    
    error
        `tuple` (exctype, value, traceback.format_exc() )
    
    result
        `object` data returned from processing, anything

    progress
        `int` indicating % progress 
    '''
    finished = QtCore.pyqtSignal()
    error    = QtCore.pyqtSignal(tuple)
    result   = QtCore.pyqtSignal(object)
    progress = QtCore.pyqtSignal(int)

class Worker(QtCore.QRunnable):
    '''
    Worker thread

    Inherits from QRunnable to handler worker thread setup, signals and wrap-up.

    :param callback: The function callback to run on this worker thread. Supplied args and 
                     kwargs will be passed through to the runner.
    :type callback: function
    :param args: Arguments to pass to the callback function
    :param kwargs: Keywords to pass to the callback function

    '''

    def __init__(self, fn, *args, **kwargs): # Now the init takes any function and its args
        #super(Worker, self).__init__() # <-- this is what the tutorial suggest
        super().__init__() # <-- This seems to work the same. Not sure what the difference is???
        # Store constructor arguments (re-used for processing)
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        
        # This is a new bit: subclass an instance of the WorkerSignals class:
        self.signals = WorkerSignals()
        
        # A new bit since ex7: Add the callback to our kwargs
        self.kwargs['progress_callback'] = self.signals.progress 
        
        

    @QtCore.pyqtSlot()
    def run(self):
        '''
        Initialise the runner function with passed args, kwargs.
        
        Did some new stuff here since ex6.
        Now it returns an exception if the try/except doesn't work
        by emitting the instances of the self.signals QObject
        
        '''

        # Retrieve args/kwargs here; and fire processing using them
        try:
            result = self.fn(
                *self.args, **self.kwargs
            )
        except:
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.signals.error.emit((exctype, value, traceback.format_exc()))
        else:
            self.signals.result.emit(result)  # Return the result of the processing
        finally:
            self.signals.finished.emit()  # Done



        
class timedLoop_1Hz(QtCore.QThread):
    
    def __init__(self):
        QtCore.QThread.__init__(self)
        #self.n = input("  Enter a number to count up to: ")
        self.index = 0
    def __del__(self):
        self.wait()
    
    def counter(self):
        self.index +=1
        if (self.index % 2) == 0:
            #Then it's even
            print("1 Hz Loop: %d" % self.index)
    
    def run(self):
        print("Starting 1 Hz Loop")
        self.timer = QtCore.QTimer()
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.counter)
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
 

class timedLoop_0p5Hz(QtCore.QThread):
    
    def __init__(self):
        QtCore.QThread.__init__(self)
        #self.n = input("  Enter a number to count up to: ")
        self.index = 0
    def __del__(self):
        self.wait()
    
    def counter(self):
        # Only print the even numbers
        self.index +=1
        
        print("0.5 Hz Loop: %d" % self.index)

        
    def run(self):
        print("Starting 0.5 Hz Loop")
        
        self.timer = QtCore.QTimer()
        self.timer.setInterval(2000)
        self.timer.timeout.connect(self.counter)
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

class MainWindow(QtWidgets.QMainWindow):
    
    # Define the 
    
    
    
    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)
        
        # set up the threadpool
        self.threadpool = QtCore.QThreadPool()
        print("Multithreading with maximum %d threads" % self.threadpool.maxThreadCount())

        self.fastloop = timedLoop_1Hz()
        self.fastloop.start()
        
        self.slowloop = timedLoop_0p5Hz()
        self.slowloop.start()
        
        self.counter = 0
        
        # GUI Stuff
        layout = QtWidgets.QVBoxLayout()
    
        self.l = QtWidgets.QLabel("Start")
        b = QtWidgets.QPushButton("DANGER!")
        b.pressed.connect(self.oh_no)

        c = QtWidgets.QPushButton("?")
        c.pressed.connect(self.change_message)

        layout.addWidget(self.l)
        layout.addWidget(b)

        layout.addWidget(c)

        w = QtWidgets.QWidget()
        w.setLayout(layout)

        self.setCentralWidget(w)

        self.show()
        
        self.timer = QtCore.QTimer()
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.recurring_timer)
        self.timer.start()
        

    def thread_complete(self):
        # this is triggered when the worker emits the finished signal
        print("THREAD COMPLETE!")
    
    def change_message(self):
        self.message = "OH NO"
        
    def returnWord(self,word):
        return word
        
    def printWord(self,word):
        print("I'm printing the word: ",word)
        
    def progress_fn(self, n):
        print("%d%% done" % n)

    def execute_this_fn(self, progress_callback):
        for n in range(0, 5):
            time.sleep(1)
            progress_callback.emit(n*100/4)
            
        return "Done."
    def oh_no(self):
        self.message = "Pressed"        
        # now we can pass any random args or keyword args (ie thing = 'Thing') to Worker
        worker = Worker(self.execute_this_fn)
        
        # Connect the signals to slots
        worker.signals.result.connect(self.printWord)
        worker.signals.finished.connect(self.thread_complete)
        worker.signals.progress.connect(self.progress_fn)
        
        # Execute
        self.threadpool.start(worker)
        
    
    def recurring_timer(self):
        self.counter +=1
        self.l.setText("Counter: %d" % self.counter)


def sigint_handler(*args):
    """
    Make the thing die when you do ctl+c
    Source:
        https://stackoverflow.com/questions/19811141/make-qt-application-not-to-quit-when-last-window-is-closed
    """
    
    """Handler for the SIGINT signal."""
    sys.stderr.write('\r')
    qb = QtWidgets.QMessageBox()
    qb.raise_()
    """
    if qb.question(None, '', "Are you sure you want to quit?",
                            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                            QtWidgets.QMessageBox.No) == QtWidgets.QMessageBox.Yes:
        QtWidgets.QApplication.quit()
        print("Okay... quitting.")
    else:
        pass
    """
    ans = qb.question(None, '', "Are you sure you want to quit?",
                            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                            QtWidgets.QMessageBox.No)
    
    if ans== QtWidgets.QMessageBox.Yes:
        QtWidgets.QApplication.quit()
        print("Okay... quitting.")
    else:
        pass
signal.signal(signal.SIGINT, sigint_handler)    

# Standard way to start up the event loop in GUI mode
app = QtWidgets.QApplication([])
app.setQuitOnLastWindowClosed(False) #<-- otherwise it will quit once all windows are closed

window = MainWindow()
app.exec_()




