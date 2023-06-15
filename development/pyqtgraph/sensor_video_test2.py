#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Feb  9 12:05:33 2023

@author: nlourie
"""

import numpy as np
from PyQt5 import QtWidgets, QtCore
from pyqtgraph import PlotWidget, plot
import pyqtgraph as pg
import sys  # We need sys so that we can pass argv to QApplication
import os
from random import randint

class MainWindow(QtWidgets.QMainWindow):

    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)
        
        height = 1000
        width = 1000
        
        
        self.setWindowTitle("My App")

        layout = QtWidgets.QVBoxLayout()

       
        
        widget = QtWidgets.QWidget()
        widget.setLayout(layout)
        self.setCentralWidget(widget)
        
        #self.setCentralWidget(widget)
        self.setMinimumHeight(height)
        self.setMinimumWidth(width)
        
    
        
        self.im1 = pg.ImageView()
        self.im2 = pg.ImageView()
        
        layout.addWidget(self.im1)
        layout.addWidget(self.im2)
        self.setCentralWidget(widget)
        self.show()
        
        # ROI Nominal Centers
        xpos = [1013, 258.0, 1767, 263, 1775]
        ypos = [545, 972.0, 981, 108, 119]
        
        self.roi_centers = np.column_stack((xpos, ypos))
        
        #self.graphWidget.setBackground('w')
        
        self.x = list(range(100))  # 100 time points
        self.y = [randint(0,100) for _ in range(100)]  # 100 data points

        pen = pg.mkPen(color=(255, 0, 0))
        #self.data_line =  self.graphWidget.plot(self.x, self.y, pen=pen)
        self.roi = pg.RectROI([0,0], [50,50], centered = True, pen = pen)
        
        imdata = 100*np.random.rand(1920, 1080)
        self.im1.setImage(imdata)

        self.timer = QtCore.QTimer()
        self.timer.setInterval(150)
        self.timer.timeout.connect(self.update_plot_data)
        self.timer.start()

    def update_plot_data(self):
        imdata = 100*np.random.rand(1920, 1080)
        self.im1.setImage(imdata, autoRange=False, autoLevels = False, autoHistogramRange = False) 
        
        self.roi_data = self.roi.getArrayRegion(self.im1.image, img=self.im1)
        
        print(f'ROI Mean = {np.mean(self.roi_data)}')

        
app = QtWidgets.QApplication(sys.argv)
w = MainWindow()
sys.exit(app.exec_())