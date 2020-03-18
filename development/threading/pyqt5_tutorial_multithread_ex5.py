#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Mar 16 11:40:22 2020

This is a tutorial on pyqt and multithreading from here:
https://www.learnpyqt.com/courses/concurrent-execution/multithreading-pyqt-applications-qthreadpool/

@author: nlourie
"""


from PyQt5 import uic, QtCore, QtGui, QtWidgets
#from PyQt5.QtWidgets import QMessageBox


import time
import sys


class Worker(QtCore.QRunnable):
    '''
    Worker thread

    :param args: Arguments to make available to the run code
    :param kwargs: Keywords arguments to make available to the run code

    '''

    def __init__(self, *args, **kwargs):
        super(Worker, self).__init__()
        self.args = args
        self.kwargs = kwargs
        self.counter = 0
        
        
    @QtCore.pyqtSlot()
    def run(self):
        '''
        Initialise the runner function with passed self.args, self.kwargs.
        '''
        print("Starting QRunnable Worker Thread from QThreadpool")
        time.sleep(5)
        print("Ending QRunnable Worker Thread from QThreadpool")
        #print(self.args, self.kwargs)

        
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

    
    def change_message(self):
        self.message = "OH NO"
    
    def oh_no(self):
        self.message = "Pressed"        
        # now we can pass any random args or keyword args (ie thing = 'Thing') to Worker
        worker = Worker('farts','fartz',farts = 'wet',gross = 'farts')
        self.threadpool.start(worker)
        
    
    def recurring_timer(self):
        self.counter +=1
        self.l.setText("Counter: %d" % self.counter)
    
app = QtWidgets.QApplication([])
window = MainWindow()
app.exec_()