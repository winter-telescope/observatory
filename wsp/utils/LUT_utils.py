#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Feb 22 13:42:37 2023

@author: winter
"""
import os
import sys
import numpy as np
import matplotlib.pyplot as plt

# add the wsp directory to the PATH
wsp_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(1, wsp_path)
print(f'wsp_path = {wsp_path}')

class LUT_Object(object):
    # lookup table (LUT) class
    def __init__(self, x_lut, y_lut, *args, **kwargs):
        
        self.x_lut = x_lut
        self.y_lut = y_lut

    def linterp(self, x):
        y_linterp = np.interp(x, self.x_lut, self.y_lut)
        return y_linterp

if __name__ == '__main__':
    
    LUT_file = os.path.join(wsp_path,'config', 'Thermistor_10k_2p5v_beta3984_V_to_T.LUT')
    Vlut, Tlut = np.loadtxt(LUT_file, unpack = True)
    
    LUT_obj = LUT_Object(Vlut, Tlut)
    # Test V = 1.25000 --> T = 25.00000
    
    V = np.linspace(min(Vlut), max(Vlut), 1000)
    
    T = LUT_obj.linterp(V)
    
    plt.figure()
    plt.plot(Vlut, Tlut, 'o')
    plt.plot(V, T, '-')
    
    
    
    #LUTobj = LUT_Object()