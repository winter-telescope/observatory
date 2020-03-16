#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Mar 10 15:36:19 2020

This is a pthread test script:
    qt5_pthread_reddit_test.py

@author: nlourie
"""

import urllib.request
import urllib.parse
import json
import time
import numpy as np
from PyQt5.QtCore import QThread, QObject,pyqtSignal
from PyQt5.QtWidgets import QApplication, QWidget

"""

def get_top_post(subreddit):
    url = "https://www.reddit.com/r/{}.json?limit=1".format(subreddit)
    headers = {'User-Agent': 'nikolak@outlook.com tutorial code'}
    request = urllib.request.Request(url, headers=headers)
    response = urllib.request.urlopen(request)
    data = json.load(response)
    top_post = data['data']['children'][0]['data']
    return "'{title}' by {author} in {subreddit}".format(**top_post)

def get_top_from_subreddits(subreddits):
    for subreddit in subreddits:
        yield get_top_post(subreddit)
        time.sleep(2)

if __name__ == '__main__':
    for post in get_top_from_subreddits(['python', 'linux', 'learnpython']):
        print (post)



"""


def printword():
    word_to_print = input("Enter a word to parrot back: ")
    
    print("Parrot says: ",word_to_print)
    
    
def countOutLoud(n):
    
    
    print("  I will now count out loud!")
    for i in np.arange(int(n))+1:
        print('   ...',i)
        time.sleep(1)
   
        
class countThread(QThread):
    
    def __init__(self):
        QThread.__init__(self)
        self.n = input("  Enter a number to count up to: ")
    def __del__(self):
        self.wait()
        
    def run(self):
        countOutLoud(self.n)
        
    def fart(self):
        print('THBFHHHFFF')
        
class mainClass(QObject):
    doneSig = pyqtSignal()

    def __init__(self, parent=None):
        QObject.__init__(self)
        self.startCounter()

    def startCounter(self):
        self.counter = countThread()
        self.counter.start()
        
               


program = mainClass()

"""
    
from PyQt5.QtWidgets import QApplication, QWidget,QPushButton
import sys
from PyQt5.QtCore import pyqtSlot
from PyQt5.QtGui import *
 
# ... insert the rest of the imports here
# Imports must precede all others ...
 
# Create a Qt app and a window
app = QApplication(sys.argv)
 
win = QWidget()
win.setWindowTitle('Test Window')
 
# Create a button in the window
btn = QPushButton('Test', win)
 
@pyqtSlot()
def on_click():
    ''' Tell when the button is clicked. '''
    print('clicked')
 
@pyqtSlot()
def on_press():
    ''' Tell when the button is pressed. '''
    print('pressed')
 
@pyqtSlot()
def on_release():
    ''' Tell when the button is released. '''
    print('released')
 
# connect the signals to the slots
btn.clicked.connect(on_click)
btn.pressed.connect(on_press)
btn.released.connect(on_release)
 
# Show the window and run the app
win.show()
app.exec_()
"""