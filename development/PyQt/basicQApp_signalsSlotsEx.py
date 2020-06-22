#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Mar 17 15:47:09 2020


Very basic QApplication

@author: nlourie
"""



import sys
from PyQt5 import uic, QtCore, QtGui, QtWidgets

def printWord(word):
    print("I'm printing the word: ",word)

"""
# Subclass QMainWindow to customise your application's main window
class MainWindow(QtWidgets.QMainWindow):

    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)

        self.setWindowTitle("My Awesome App")

        label = QtWidgets.QLabel("This is a PyQt5 window!")

        # The `Qt` namespace has a lot of attributes to customise
        # widgets. See: http://doc.qt.io/qt-5/qt.html
        label.setAlignment(QtCore.Qt.AlignCenter)

        # Set the central widget of the Window. Widget will expand
        # to take up all the space in the window by default.
        self.setCentralWidget(label)
"""

class MainWindow(QtWidgets.QMainWindow):

    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)
        
        # SIGNAL: The connected function will be called whenever the window
        # title is changed. The new title will be passed to the function.
        # The signal contains a string containing the new window title
        #self.windowTitleChanged.connect(self.onWindowTitleChange)

        # SIGNAL: The connected function will be called whenever the window
        # title is changed. The new title is discarded in the lambda and the
        # function is called without parameters.
        #self.windowTitleChanged.connect(lambda x: self.my_custom_fn())
        
        
        # SIGNAL: The connected function will be called whenever the window
        # title is changed. The new title is passed to the function
        # and replaces the default parameter
        #self.windowTitleChanged.connect(lambda x: self.my_custom_fn(x))

        # SIGNAL: The connected function will be called whenever the window
        # title is changed. The new title is passed to the function
        # and replaces the default parameter. Extra data is passed from
        # within the lambda.
        self.windowTitleChanged.connect(lambda x: self.my_custom_fn(x, 25))
        
        # This sets the window title which will trigger all the above signals
        # sending the new title to the attached functions or lambdas as the
        # first parameter.
        self.setWindowTitle("My Awesome App")
        
        label = QtWidgets.QLabel("THIS IS AWESOME!!!")
        label.setAlignment(QtCore.Qt.AlignCenter)

        self.setCentralWidget(label)
        
        
    # SLOT: This accepts a string, e.g. the window title, and prints it
    def onWindowTitleChange(self, s):
        print(s)

    # SLOT: This has default parameters and can be called without a value
    def my_custom_fn(self, a="HELLLO!", b=5):
        print(a, b)


app = QtWidgets.QApplication(sys.argv)

window = MainWindow()
window.show()

app.exec_()

