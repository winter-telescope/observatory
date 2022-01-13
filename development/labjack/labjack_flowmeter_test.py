#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Sep 22 18:15:55 2020

Labjack Test


@author: winter
"""


from labjack import ljm
import numpy as np
import matplotlib.pyplot as plt
import time

from PyQt5 import uic, QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QMessageBox
import scipy.interpolate
import json

#handle = ljm.openS("T7", "ETHERNET", '192.168.1.110')
handle = ljm.openS("T7", "USB")



info = ljm.getHandleInfo(handle)





print(f"Opened a LabJack with \n\
      Device type{info[0]}, \n\
      Connection Type: {info[1]}, \n\
      Serial Number: {info[2]}, \n\
      IP addr: {ljm.numberToIP(info[3])}, port: {info[4]}, \n\
      max bytes per MB: {info[5]}\n")

### SET UP THE TEMPERATURE ANALOG INPUT CHANNELS ###

print("SETTING UP ANALOG INPUTS:")
opts = dict({'RESOLUTION_INDEX': 8,  # 8 is the max for the T7
        'NEGATIVE_CH': 199,     # 199 is the default: single-ended measurement
        'RANGE': 10,       # the max voltage (ie sets the gain): can be 10, 1, 0.1, 0.01
        'SETTLING_US': 0})      # settling time in microseconds. 0 is automatic settling (recommended))

ain_chans = [0,1,2,3]

analog_inputs = [f'AIN{chan}' for chan in ain_chans]
temps = [f'T{chan}' for chan in ain_chans]


for chan in analog_inputs:
    chan_opts = dict()
    for key in opts.keys():
        chan_opts.update({f'{chan}_{key}' : opts[key]})
    # send the options to the labjack
    ljm.eWriteNames(handle, len(chan_opts), chan_opts.keys(), chan_opts.values())
    print(f' > Set up chan: {chan}')
   


### SET UP THE FLOW METER ###
# set up the counter read on FIO0    
print("SETTING UP FLOW METER")
ljm.eWriteName(handle, "DIO0_EF_ENABLE", 0)
ljm.eWriteName(handle, "DIO0_EF_INDEX", 8)
ljm.eWriteName(handle, "DIO0_EF_ENABLE",1)

# set the dac1 output frequency to 10 Hz
ljm.eWriteName(handle, "DAC1_FREQUENCY_OUT_ENABLE", 1)

#%%
# this is a function which does a linear interpolation based on a provided LUT
LUT_Voltage, LUT_Temp = np.loadtxt('Thermistor_10k_2p5v_beta3984_V_to_T.LUT', unpack = True)

voltage_to_temp_function = scipy.interpolate.interp1d(LUT_Voltage, LUT_Temp, kind = 'linear')

#%%
### SET UP THE GUI ###

class MainWindow(QtWidgets.QMainWindow):


    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)
        
        layout = QtWidgets.QVBoxLayout()
        
        self.freq_disp = QtWidgets.QLabel("")
        self.flow_disp_gal = QtWidgets.QLabel("")
        self.flow_disp_liters = QtWidgets.QLabel("")    
        
        self.t0_disp = QtWidgets.QLabel("")    
        self.t1_disp = QtWidgets.QLabel("")    
        self.t2_disp = QtWidgets.QLabel("")    
        self.t3_disp = QtWidgets.QLabel("")    


        layout.addWidget(self.freq_disp)
        layout.addWidget(self.flow_disp_gal)
        layout.addWidget(self.flow_disp_liters)
        
        layout.addWidget(self.t0_disp)
        layout.addWidget(self.t1_disp)
        layout.addWidget(self.t2_disp)
        layout.addWidget(self.t3_disp)
        
        w = QtWidgets.QWidget()
        w.setLayout(layout)
    
        self.setCentralWidget(w)
    
        self.show()
        
        self.state = dict()
        
        self.old_count = 0.0
        
        self.dt = 500 #ms
        
        self.k_factor_gal = 3785.0
        self.k_factor_liter = 1000.0
        
        self.timer = QtCore.QTimer()
        self.timer.setInterval(self.dt)
        self.timer.timeout.connect(self.read_lj_vals)
        self.timer.start()

    def read_lj_vals(self):
        self.get_flow()
        self.get_temps()
        
        #print(json.dumps(self.state, indent = 2))

    def get_flow(self):
        
        new_count=ljm.eReadName(handle, "DIO0_EF_READ_A")
        
        delta_count = new_count - self.old_count
        self.old_count = new_count
        self.count_freq = delta_count/(self.dt/1000.0)
        self.state['count_freq'] = self.count_freq
        self.state['flow_liters'] = self.count_freq / self.k_factor_liter * 60.0 #L/m
        self.state['flow_gal'] = self.count_freq / self.k_factor_gal * 60.0 # gal/m
        
        self.freq_disp.setText(f"Pulse Freq: {self.count_freq:0.2f} Hz")
        self.flow_disp_liters.setText(f"Flow = {self.state['flow_liters']:0.2f} L/m")
        self.flow_disp_gal.setText(f"Flow = {self.state['flow_gal']:0.2f} gal/m")

    def get_temps(self):
        # read all of the inputs
        #print(f'reading labjack at {self.address}')
        vals = ljm.eReadNames(handle, len(analog_inputs), analog_inputs)
        for i in range(len(analog_inputs)):
            self.state.update({analog_inputs[i] : vals[i]})
            try:
                temp = voltage_to_temp_function(vals[i])
                self.state.update({temps[i] : temp})
            except Exception as e:
                #print(f'could not update {temps[i]}: {e}')
                self.state.update({temps[i] :   -999})     # update the display
        self.t0_disp.setText(f'T0 = {self.state["T0"]:0.2f} C')
        self.t1_disp.setText(f'T1 = {self.state["T1"]:0.2f} C')
        self.t2_disp.setText(f'T2 = {self.state["T2"]:0.2f} C')
        self.t3_disp.setText(f'T3 = {self.state["T3"]:0.2f} C')

        
        

app = QtWidgets.QApplication([])
main = MainWindow()
app.exec_()