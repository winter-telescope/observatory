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


class Worker(QtCore.QRunnable):
    '''
    Worker thread
    '''

    @QtCore.pyqtSlot()
    def run(self):
        '''
        Your code goes in this function
        '''
        print("Thread start") 
        time.sleep(5)
        print("Thread complete")


class MainWindow(QtWidgets.QMainWindow):

    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)
        
        # set up the threadpool
        self.threadpool = QtCore.QThreadPool()
        print("Multithreading with maximum %d threads" % self.threadpool.maxThreadCount())


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
        worker = Worker()
        self.threadpool.start(worker)
        
    
    def recurring_timer(self):
        self.counter +=1
        self.l.setText("Counter: %d" % self.counter)
    
app = QtWidgets.QApplication([])
window = MainWindow()
app.exec_()