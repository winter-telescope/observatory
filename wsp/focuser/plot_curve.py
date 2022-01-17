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
    return popt, pcov

if __name__ == '__main__':
    focus_vals = np.array([ 9000. ,9358.33333333,  9716.66666667, 10075., 10433.33333333, 10791.66666667, 11150.        ])
    fwhms = np.array([2.97752818, 2.82161681, 2.39297943, 2.03755009, 2.32122086, 2.62719668, 3.28458147])
    stds = np.array([0.83647298, 0.73628424, 0.43677995, 0.33736188, 0.40130216, 0.53013957, 0.83345092])
    
    popt, pcov = fit_parabola(focus_vals, fwhms, stds)
    
    # calculate one standard deviation errors on the fit parameters: https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.curve_fit.html
    perr = np.sqrt(np.diag(pcov))
    x0_fit = popt[0]
    x0_err = perr[0]
    
    print(f"x0 from fit = {x0_fit}")
    print(f"x0 = [{x0_fit:.0f} +/- {x0_err:.0f}] microns ({x0_err/x0_fit*100:.0f}%)")
    
    x = np.linspace(np.min(focus_vals), np.max(focus_vals), 1000)
    y = parabola(x, *popt)
    
    # cruz's original method... 
    plotfoc = np.linspace(np.min(focus_vals),np.max(focus_vals),20)
    xvals = list(plotfoc)
    yvals = list(parabola(plotfoc,popt[0],popt[1],popt[2]))
    focuser_pos_best = xvals[yvals.index(min(yvals))]
    print(f"Cruz's best fit focus: = {focuser_pos_best}")
    # note: NPL 1-14-22: this isn't really what we want to do. this is dependent
    # on the sampling of the linspace line. it just gets the min value
    # of the sampled curve... should just report the x0 val instead
    
    fig = plt.figure()
    plt.errorbar(focus_vals,fwhms,yerr=stds,fmt='.',c='red')
    plt.plot(x,y)
    #plt.title('Best FWHM : %.1f arcsec'%(np.min(med_fwhms)))