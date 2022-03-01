#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Feb 16 11:24:33 2022

@author: nlourie
"""

# Test function to plot a V-shaped model of the HFD through focus
import numpy as np
import matplotlib.pyplot as plt
import os

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

ml = -0.01
cl = 10130.99
mr = 0.01
cr = 9844.53

def FocV(x, ml, mr, cl, cr, y0, return_x = False):
    
    xa = (y0 + ml*cl)/ml
    xb = -(y0 + mr*cr)/ml
    xc = (mr*cr - ml*cl)/(mr-ml)
    y = 0*x
    
    cond = (x <= xa)
    y[cond] = y0
    
    cond = ((x > xa) & (x <= xc))
    y[cond] = ml * (x[cond] - cl)
    
    cond = ((x > xc) & (x <= xb))
    y[cond] = mr * (x[cond] - cr)
    
    cond = (x > xb)
    y[cond] = y0
    if return_x:
        return y, xa, xb, xc
    else:
        return y
    

def FocV2(x, ml, xc, delta, y0, return_x = False):
    
    mr = -ml
    cr = xc + (ml/(ml - mr))*(-1*delta)
    cl = cr - (-1*delta)
    
    xa = (y0 + ml*cl)/ml
    xb = -(y0 + mr*cr)/ml

    y = 0*x
    
    cond = (x <= xa)
    y[cond] = y0
    
    cond = ((x > xa) & (x <= xc))
    y[cond] = ml * (x[cond] - cl)
    
    cond = ((x > xc) & (x <= xb))
    y[cond] = mr * (x[cond] - cr)
    
    cond = (x > xb)
    y[cond] = y0
    if return_x:
        return y, xa, xb, xc
    else:
        return y


def Fit_FocV(x, y, yerr, ml, xc, delta, y0):
    
    #p0 = [ml, mr, cl, cr, y0]
    p0 = [ml, xc, delta, y0]
    popt, pcov = curve_fit(FocV2, x, y, p0, sigma = yerr)
    
    return popt, pcov


def parabola(x,x0,A,B):
        return A + B*(x-x0)**2
    
def fit_parabola(focus_vals, fwhms, stds):
    #print(focus_vals)
    #print(fwhms)
    #print(stds)
    p0 = [np.mean(focus_vals),np.min(fwhms),np.std(fwhms)]
    
    popt,pcov = curve_fit(parabola,xdata=focus_vals,ydata=fwhms,p0=p0, sigma=stds)
    #print(popt)
    return popt, pcov


x = np.linspace(9500, 10500, 1000)


xc = 9993.61
y0 = 3

y, xa, xb, xc = FocV2(x = x, ml = ml, xc = xc, delta = (cl - cr), y0 = y0, return_x = True)

print(f'xa = {xa:.1f}')
print(f'xb = {xb:.1f}')
print(f'xc = {xc:.1f}')

plt.figure()
plt.plot(x,y, linewidth = 10, label = 'model')
plt.plot(x, ml*(x-cl), 'g', label = 'left side of V')
plt.plot(x, mr*(x-cr), 'r', label = 'right side of V')
plt.plot(x, 0*x + y0, label = 'background')
plt.axis([min(x), max(x), 0, 6])
plt.legend()
#


#%% Try Fitting the data
wsp_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),'wsp')

files = ['HFD_Focus_Test_Data.txt', 'SampleFocus_r_20220211_190647.txt',  'SampleFocus_r_20220212_032207.txt', 'SampleFocus_r_20220211.txt']

#files = ['SampleFocus_r_20220212_032207.txt']

for datafilename in files:
    
    
    datapath = os.path.join(os.path.dirname(wsp_path), 'development','focusing', datafilename)
    pos_ref, HFD_med_ref, HFD_mean_ref, HFD_stderr_mean_ref, HFD_stderr_med_ref, FWHM_mean_ref, FWHM_med_ref, FWHM_std_ref = np.loadtxt(datapath, unpack = True)
    
    pos_indx = pos_ref.argsort()
    pos_ref = pos_ref[pos_indx]
    HFD_med_ref = HFD_med_ref[pos_indx]
    HFD_stderr_med_ref = HFD_stderr_med_ref[pos_indx]
    FWHM_med_ref = FWHM_med_ref[pos_indx]
    FWHM_std_ref = FWHM_std_ref[pos_indx]
    
    # down sample the data
    pos = [pos_ref[0]]
    HFD_med = [HFD_med_ref[0]]
    HFD_stderr_med = [HFD_stderr_med_ref[0]]
    FWHM_med = [FWHM_med_ref[0]]
    FWHM_std = [FWHM_std_ref[0]]
    
    
    for i in range(len(pos_ref)):
        min_spacing = 75
        if pos_ref[i] - pos[-1] >= min_spacing:
            pos.append(pos_ref[i])
            HFD_med.append(HFD_med_ref[i])
            HFD_stderr_med.append(HFD_stderr_med_ref[i])
            FWHM_med.append(FWHM_med_ref[i])
            FWHM_std.append(FWHM_std_ref[i])
    
    
    pos_downsampled = np.array(pos)
    HFD_med_downsampled = np.array(HFD_med)
    HFD_stderr_med_downsampled = np.array(HFD_stderr_med)
    FWHM_med_downsampled = np.array(FWHM_med)
    FWHM_std_downsampled = np.array(FWHM_std)
    
    
    cond = (HFD_med_downsampled > 2) & (pos_downsampled>9600) & (pos_downsampled < 10400)
    pos = pos_downsampled[cond]
    HFD_med = HFD_med_downsampled[cond]
    HFD_stderr_med = HFD_stderr_med_downsampled[cond]
    FWHM_med = FWHM_med_downsampled[cond]
    FWHM_std = FWHM_std_downsampled[cond]
    
    fig, axes = plt.subplots(2,1)
    ax = axes[0]
    #ax.plot(pos, HFD_med, 'ko', label = 'data')
    ax.errorbar(pos, HFD_med, yerr = HFD_stderr_med, fmt = 'ko', label = 'data')
    
    ml0 = -0.01
    mr0 = 0.01
    xc0 = 10000#pos[np.argmin(HFD_med)]
    delta0 = cl - cr
    y00 = max(HFD_med)#HFD_med[0]
    
    #ymodel0 = FocV(x, ml0, mr0, cl0, cr0, y00)
    
    ymodel0 = FocV2(x, ml0, xc0, delta0, y00)
    #ax.plot(x, ymodel0, '--', label = 'initial model')
    popt, pcov = Fit_FocV(pos, HFD_med, HFD_stderr_med, ml = ml0, xc = xc0, delta = delta0, y0 = y00)
    
    print(f'Fit Params = {popt}')
    print(f'Fit Covariance Matrix = {pcov}')
    mlfit = popt[0]
    xcfit = popt[1]
    deltafit = popt[2]
    y0fit = popt[3]
    
    perr = np.sqrt(np.diag(pcov))
    xcfit_err = perr[1]
    
    ymodel_fit, xafit, xbfit, xcfit = FocV2(x, mlfit, xcfit, deltafit, y0fit, return_x = True)
    print(f'xa = {xafit:.1f}')
    print(f'xb = {xbfit:.1f}')
    print(f'xc = [{xcfit:.0f} +/- {xcfit_err:.0f}] ({100*xcfit_err/xcfit:.0f}%)')
    
    yline = np.linspace(-10, 10, 100)

    
    ax.plot(x, ymodel_fit, '-', label = f'V-Curve Fit')
    ax.set_title(datafilename)
    ax.set_xlim(9500, 10500)
    ax.set_ylabel('HFD [arcsec]')
    ax.plot(xcfit+0*yline, yline, 'r--', label = f'xc = [{xcfit:.0f} +/- {xcfit_err:.0f}] ({100*xcfit_err/xcfit:.0f}%)')

    #ax.plot((xcfit_err+xcfit_err) + 0*yline, yline,'r--')
    #ax.plot((xcfit_err+xcfit_err) + 0*yline, yline,'r--')
    ax.legend(fontsize = 8)

    ax.set_ylim(0,6)
    ax = axes[1]
    
    # get just the FWHM data that is near the rough center
    cond = (pos_downsampled > xafit) & (pos_downsampled < (xbfit)) #& (pos_downsampled > 9600) & (pos_downsampled < 10400)
    #cond = (pos_ref > (xcfit-300)) & (pos_ref < (xcfit + 300))
    pos_parabola = pos_downsampled[cond]
    FWHM_med_parabola = FWHM_med_downsampled[cond]
    FWHM_std_parabola = FWHM_std_downsampled[cond]
    
    ax.errorbar(pos_parabola, FWHM_med_parabola, yerr = FWHM_std_parabola, fmt = 'ko')
    ax.set_xlim(9500, 10500)
    
    popt, pcov = fit_parabola(pos_parabola, FWHM_med_parabola, stds = None)
    
    #arabola(x,x0,A,B):
    x0_parfit = popt[0]
    A_parfit = popt[1]
    B_parfit = popt[2]
    
    perr = np.sqrt(np.diag(pcov))
    x0_parfit_err = perr[0]
    
    print(f'parabola: y = {A_parfit:.1f} + {B_parfit:.1f}*(x-{x0_parfit:.1f})**2')
    
    xfit_par = np.linspace(min(pos_parabola), max(pos_parabola), 1000)
    yfit_par = parabola(xfit_par, popt[0], popt[1], popt[2])
    ax.plot(xfit_par, yfit_par, '-', label = f'Parabola Fit')
    ax.plot(x0_parfit+0*yline, yline, 'r--', label = f'xc = [{x0_parfit:.0f} +/- {x0_parfit_err:.0f}] ({100*x0_parfit_err/x0_parfit:.0f}%)')
    #ax.plot((x0_parfit_err-x0_parfit) + 0*yline, yline,'r--')
    #ax.plot((x0_parfit_err+x0_parfit) + 0*yline, yline,'r--')
    ax.set_ylabel('FWHM [arcsec]')
    ax.set_xlabel('Focuser Position [micron]')
    ax.set_ylim(0,10)
    ax.legend(fontsize = 8)
    