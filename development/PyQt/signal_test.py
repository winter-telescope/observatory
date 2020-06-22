#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Apr 28 12:11:08 2020

@author: nlourie
"""


import sys
from PyQt5 import uic, QtCore, QtGui, QtWidgets
import os
import sys


# add the main directory to the PATH
main_path = os.path.dirname(os.getcwd())
sys.path.insert(1, main_path)








class MainWindow(QtWidgets.QMainWindow):
     #Define custom signal
    mySignal = QtCore.pyqtSignal(str, name = 'mySignal')
        
        
    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)
        
        #Define custom signal
        # FOR SOME REASON THIS CAN'T BE DEFINED HERE. NOT SURE WHY
        #self.mySignal = QtCore.pyqtSignal(str,name = 'mySignal')
        
        
        self.setWindowTitle("My Awesome App")
        
        layout = QtWidgets.QHBoxLayout()
        
        for n in [1,43,5]:
            btn = QtWidgets.QPushButton(str(n))
            #btn.pressed.connect(self.been_pressed)
            btn.pressed.connect(lambda x = n: self.btn_n_been_pressed(x))
            layout.addWidget(btn)
            
        # connect a slot that executes when mySignal is emitted
        self.mySignal.connect(self.caught_my_own_signal)
        
            
        widget = QtWidgets.QWidget()
        widget.setLayout(layout)
        
        self.setCentralWidget(widget)
        
    def been_pressed(self):
            print("Pressed a Button!")
            
            
    def btn_n_been_pressed(self,button_num):
            print(f"Pressed Button Number {button_num}")
            #tell mySignal to emit
            self.mySignal.emit("My Signal is Emitting!")
    
    # overrie the .contextMenuEvent on QMainWindow
    def contextMenuEvent(self,event):
        # this gets triggered by right-clicking on the window
        print("Context menu event!")
        
        # but we also want to keep the original (parent) event handler
        # make the function inheret the parent functions
        super(MainWindow,self).contextMenuEvent(event)
        
    # create a slot that will be executed with mySignal is emitted
    def caught_my_own_signal(self,emitted_string):
        print(emitted_string)
        
app = QtWidgets.QApplication(sys.argv)

window = MainWindow()
window.show()

app.exec_()