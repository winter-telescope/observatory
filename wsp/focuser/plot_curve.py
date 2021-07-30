#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jul 29 20:51:28 2021

@author: C. Soto
"""


def parabola_curve(A, B, x, x0):
        return A + B*(x-x0)**2
    
def fit_parabola(focus_vals, fwhms, stds):
    p0 = [np.mean(focus_vals),np.min(fwhms),np.std(fwhms)]
    popt,pcov = curve_fit(parabola_curve,xdata=focus_vals,ydata=fwhms,p0=p0,sigma=stds)
    return popt

