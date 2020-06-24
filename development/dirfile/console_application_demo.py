#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jun 22 10:44:17 2020

Console application from here: https://stackoverflow.com/questions/10641055/using-pyqt-for-a-command-prompt-python-program

@author: nlourie
"""

from PyQt5 import QtCore

class Hello(QtCore.QObject):

    def __init__(self, msg):
        super(Hello, self).__init__()
        self.msg = msg
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.say)
        self.timer.start(500)
        self.i = 0

    def say(self):
        print (self.msg)
        self.i += 1
        if self.i > 5:
            QtCore.QCoreApplication.instance().quit()

if __name__ == "__main__":
    import sys
    app = QtCore.QCoreApplication(sys.argv)
    hello = Hello("Hello World!")
    sys.exit(app.exec_())