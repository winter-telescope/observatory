#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Apr 21 06:53:06 2022

@author: winter
"""

from scipy.optimize import curve_fit
import numpy as np
import matplotlib.pyplot as plt

def polyval(x, *param):
    
    return np.polyval(param, x)

def polyfit_errs(x, y, errs, deg, returnCov = False):

    p0 = np.polyfit(x,y,deg)
    if errs is None:
        absolute_sigma = False
    else:
        absolute_sigma = True
    popt,pcov = curve_fit(polyval, xdata=x, ydata=y, p0=p0, sigma=errs, absolute_sigma = absolute_sigma)
    
    if returnCov:
        return popt, pcov
    else:
        return popt

npts = 10
x = np.linspace(1,10,npts)
m = 4.0
b = 5.0
p = [m,b]
y = m*x+b
ynoisy = y + 10*np.random.normal(loc = 0.0, scale = .5, size = npts)
errs = np.random.normal(loc = 0.0, scale = 5, size = npts)
#errs = None

plt.figure()
plt.errorbar(x, ynoisy,  yerr = errs, fmt = 'o', capsize = 5, label = 'Noisy Data')
plt.plot(x,y, label = 'Noiseless Data')
xline = np.linspace(min(x), max(x), 100)
p0 = np.polyfit(x, ynoisy, 1)

print(f'p       = {p}')
print(f'p0      = {p0}')

plt.plot(xline, np.polyval(p0, xline), '--', label = 'Fit (No Errorbars)')

pfit = polyfit_errs(x, ynoisy, errs, 1)
print(f'pfit    = {pfit}')

plt.plot(xline, np.polyval(pfit, xline), '--', label = 'Fit (With Errorbars)')

plt.legend()
