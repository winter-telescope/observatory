#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jul 29 20:51:28 2021

@author: C. Soto
"""

import numpy as np
import matplotlib.pyplot as plt
import numpy as np
from scipy.optimize import curve_fit

def parabola(x,x0,A,B):
        return A + B*(x-x0)**2
    
def fit_parabola(focus_vals, fwhms, stds):
    print(focus_vals)
    print(fwhms)
    print(stds)
    p0 = [np.mean(focus_vals),np.min(fwhms),np.std(fwhms)]
    popt,pcov = curve_fit(parabola,xdata=focus_vals,ydata=fwhms,p0=p0, sigma=stds)
    print(popt)
    return popt

