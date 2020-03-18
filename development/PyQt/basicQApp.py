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


app = QtWidgets.QApplication(sys.argv)

window = MainWindow()
window.show()

app.exec_()

