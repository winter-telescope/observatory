#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
The focus loop object class

@author: C. Soto and V. Karambelkar
"""
import os
import numpy as np
import matplotlib.pyplot as plt
import sys
import scipy.interpolate
import scipy.ndimage
pixscale = 0.466

wsp_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),'wsp')

# add the wsp directory to the PATH
sys.path.insert(1, wsp_path)

from focuser import plot_curve


datafilename = 'HFD_Focus_Test_Data.txt'
datafilename = 'SampleFocus_r_20220211_190647.txt'
#datafilename = 'SampleFocus_r_20220212_032207.txt'


datapath = os.path.join(os.path.dirname(wsp_path), 'development','focusing', datafilename)
pos_ref, HFD_med_ref, HFD_mean_ref, HFD_stderr_mean_ref, HFD_stderr_med_ref, FWHM_mean_ref, FWHM_med_ref, FWHM_std_ref = np.loadtxt(datapath, unpack = True)

# sort all by position
pos_indx = pos_ref.argsort()
pos_ref = pos_ref[pos_indx]
HFD_med_ref = HFD_med_ref[pos_indx]

pos_ref_orig = pos_ref
HFD_med_ref_orig = HFD_med_ref

#% DETERMINE WHICH DATA TO USE FOR HFD LINEAR FITTING
cond = (HFD_med_ref_orig > 2.0) & (HFD_med_ref_orig < 3.5) #& (pos_ref_orig > 9600) & (pos_ref_orig < 13000)
pos_select = pos_ref_orig[cond]
HFD_select = HFD_med_ref_orig[cond]

fig2,ax2 = plt.subplots(1,1)
fit_x = np.linspace(min(pos_select), max(pos_select), 1000)
ax2.plot(pos_select, HFD_select,'o')
HFD_smooth = scipy.ndimage.median_filter(HFD_select, 10)
HFD_interp = scipy.interpolate.interp1d(pos_select, HFD_select, kind = 'linear')
HFD_interp_spline = scipy.interpolate.UnivariateSpline(fit_x, HFD_interp(fit_x))

ax2.plot(fit_x, HFD_interp(fit_x),'-')
ax2.plot(fit_x, HFD_interp_spline(fit_x),'--')
ax2.plot(pos_select, HFD_smooth, '--')

ax3 = ax2.twinx()
HFD_deriv = HFD_interp_spline.derivative()(pos_select)
ax3.plot(fit_x, HFD_interp_spline.derivative()(fit_x),'-')

    

cond_lh = (HFD_deriv < -0.004)
cond_rh = (HFD_deriv > 0.004)
pos_lh = pos_select[cond_lh]
pos_rh = pos_select[cond_rh]
HFD_med_lh = HFD_select[cond_lh]
HFD_med_rh = HFD_select[cond_rh]

ax2.plot(pos_lh, HFD_med_lh,'go')
ax2.plot(pos_rh, HFD_med_rh, 'ro')
#%%
# try to remove some obvious junk points
HFD_min = 2.0

cond = HFD_med_ref > 2.0
pos_ref = pos_ref[cond]
HFD_mean_ref = HFD_mean_ref[cond]
HFD_med_ref = HFD_med_ref[cond]
HFD_stderr_mean_ref = HFD_stderr_mean_ref[cond]
HFD_stderr_med_ref = HFD_stderr_med_ref[cond]
FWHM_mean_ref = FWHM_mean_ref[cond]
FWHM_med_ref = FWHM_med_ref[cond]
FWHM_std_ref = FWHM_std_ref[cond]

nomfoc = 9967

# fit the right hand line
#cond_rh = (pos_ref>nomfoc + 50) & (pos_ref<10300)
#pos_rh = pos_ref[cond_rh]
#HFD_med_rh = HFD_med_ref[cond_rh]
rh_fit = np.polyfit(pos_rh, HFD_med_rh, 1)
HFD_ref_fit_rh = np.polyval(rh_fit, pos_ref)

# fit the left hand line
#cond_lh = (pos_ref>9650) & (pos_ref<nomfoc-50)
#pos_lh = pos_ref[cond_lh]
#HFD_med_lh = HFD_med_ref[cond_lh]
lh_fit = np.polyfit(pos_lh, HFD_med_lh, 1)
HFD_ref_fit_lh = np.polyval(lh_fit, pos_ref)


# get the slopes and x-intercepts
m_rh = rh_fit[0]
b_rh = rh_fit[1]

m_lh = lh_fit[0]
b_lh = lh_fit[1]

xint_rh = -b_rh/m_rh
xint_lh = -b_lh/m_lh
PID = np.abs(np.abs(xint_rh) - np.abs(xint_lh))

#xfoc = (xint_rh + xint_lh)/2

xfoc = (b_lh - b_rh)/(m_rh - m_lh)

foc = m_rh*xfoc + b_rh
# PLOTS

fig,axes= plt.subplots(1,2,figsize = (16,10))
ax = axes[0]
#plt.plot(focuser_pos, HFD_med, 'ks')
ax.errorbar(pos_ref, HFD_med_ref, yerr = HFD_stderr_med_ref, capsize = 5, fmt = 'ks', label = 'Reference Data: 2022-02-10')
ax.plot(pos_ref, HFD_ref_fit_lh, 'g-', label = f'LH Fit: m = {m_lh:0.4f}, xint = {xint_lh:0.2f}')
ax.plot(pos_ref, HFD_ref_fit_rh, 'r-', label = f'RH Fit: m =  {m_rh:0.4f}, xint = {xint_rh:0.2f}')
ax.plot(pos_ref, 0*pos_ref, 'k--')
ax.plot(xint_rh,0, 'ro')
ax.plot(xint_lh,0,'go')
ax.plot(xfoc, foc, 'ko', label = f'HFD Foc = {xfoc:0.2f} (parabolic Foc = {nomfoc:0.2f}), PID = {PID:0.2f}')
#ax.plot()
ax.set_xlabel('Focuser Position [micron]')
ax.set_ylabel('Half-Focus Diameter [arcseconds]')
ax.set_ylim(-1,8)


'''

#%% Pull up the next night's focus data to compare

datafilename = 'SampleFocus_r_20220211.txt'
#datafilename = 'SampleFocus_r_20220211_2.txt' # BAD
datafilename = 'SampleFocus_r_20220119.txt'
datafilename = 'SampleFocus_r_20220211_190647.txt'

date = datafilename.strip('SampleFocus_r_').strip('.txt')

datapath = os.path.join(os.path.dirname(wsp_path), 'development','focusing', datafilename)
pos, HFD_med, HFD_mean, HFD_stderr_mean, HFD_stderr_med, FWHM_mean, FWHM_med, FWHM_std = np.loadtxt(datapath, unpack = True)

pos_orig = pos
HFD_med_orig = HFD_med

#%% DETERMINE WHICH DATA TO USE FOR HFD LINEAR FITTING

pos_select = pos_orig[(HFD_med_orig > 2.0) & (HFD_med_orig < 4.0)]
HFD_select = HFD_med_orig[(HFD_med_orig > 2.0) & (HFD_med_orig < 4.0)]

fig2,ax2 = plt.subplots(1,1)
fit_x = np.linspace(min(pos_select), max(pos_select), 1000)
ax2.plot(pos_select, HFD_select,'o')
HFD_interp = scipy.interpolate.interp1d(pos_select, HFD_select, kind = 'linear')
HFD_interp_spline = scipy.interpolate.UnivariateSpline(fit_x, HFD_interp(fit_x))

ax2.plot(fit_x, HFD_interp(fit_x),'-')
ax2.plot(fit_x, HFD_interp_spline(fit_x),'--')

ax3 = ax2.twinx()
HFD_deriv = HFD_interp_spline.derivative()(pos_select)
ax3.plot(fit_x, HFD_interp_spline.derivative()(fit_x),'-')

cond_lh = (HFD_deriv < -0.005)
cond_rh = (HFD_deriv > 0.005)
pos_lh = pos_select[cond_lh]
pos_rh = pos_select[cond_rh]
HFD_med_lh = HFD_select[cond_lh]
HFD_med_rh = HFD_select[cond_rh]

ax2.plot(pos_lh, HFD_med_lh,'go')
ax2.plot(pos_rh, HFD_med_rh, 'ro')


try:
    # fit a parabola
    popt, pcov = plot_curve.fit_parabola(pos, FWHM_mean, FWHM_std)
        
    x = np.linspace(np.min(pos), np.max(pos), 1000)
    y = plot_curve.parabola(x, *popt)
    
    perr = np.sqrt(np.diag(pcov))
    x0_fit = popt[0]
    x0_err = perr[0]
    
    #print(f"x0 from fit = {x0_fit}")
    #print(f"x0 = [{x0_fit:.0f} +/- {x0_err:.0f}] microns ({x0_err/x0_fit*100:.0f}%)")
    
    best_fwhm = plot_curve.parabola(x0_fit, *popt)

except:
    print('Data too bad to fit parabola...')
    x = None
    y = None
    x0_fit = None
    x0_err = None


    
ax1 = axes[1]
#plt.errorbar(pos, FWHM_med, yerr = FWHM_stderr_med, capsize = 5, fmt = 'ks', label = 'Median')
ax1.plot(pos, FWHM_med, 'ks', label = 'FWHM Data')
ax1.plot(x, y, 'r-', label = 'Parabolic Fit')
ax1.legend()
ax1.set_xlabel('Focuser Position [micron]')
ax1.set_ylabel('FWHM [arcseconds]')
ax1.set_title(f'Best Parabolic Focus = [{x0_fit:.0f} +/- {x0_err:.0f}] micron ({x0_err/x0_fit*1000:.0f}%)')



# fit a spline through the HFD points
interp_func = scipy.interpolate.interp1d(pos, HFD_med, kind = 'cubic')
parabolic_HFD_fit = interp_func(x0_fit)
#ax.plot(x, interp_func(x),'m--', label = 'Cubic Interpolation')
ax.errorbar(pos, HFD_med, yerr = HFD_stderr_med, capsize = 5, fmt = 'bs', label = f'Focus Data: {date}')

"""
ax.plot(pos, HFD_med, 'bs', label = 'Sample Focus Data')

NFP = pos[0]
F_NFP = HFD_med[0]

NFP_R = pos[-1]
F_NFP_R = HFD_med[-1]

c_lh = NFP - F_NFP/m_lh
c_rh = c_lh - PID

BFP = NFP - F_NFP/m_lh - PID/2
F_BFP = m_lh * BFP - m_lh*c_lh

#parabolic_foc = 9993
# make the lines for the shifted V-curve
HFD_fit_lh = m_lh*pos_ref - m_lh*c_lh
HFD_fit_rh = m_rh*pos_ref - m_rh*c_rh

ax.plot(pos_ref, HFD_fit_lh, 'g--', label = f'LH Fit: m = {m_lh:0.4f}, xint = {c_lh:0.2f}')
ax.plot(pos_ref, HFD_fit_rh, 'r--', label = f'RH Fit: m =  {m_rh:0.4f}, xint = {c_rh:0.2f}')
try:
    ax.plot(BFP, F_BFP, 'bo', label = f'HFD Best Foc = {BFP:0.2f}')
    ax.plot(x0_fit, parabolic_HFD_fit, 'y*', label = f'Parabolic Foc = {x0_fit:0.2f}')
except:
    print('Not Plotting Parabolic Results')
ax.legend()

"""
# try to remove some obvious junk points
HFD_min = 2.0

cond = (HFD_med > 2.0) & (HFD_med < 4.0)
pos = pos[cond]
HFD_mean = HFD_mean[cond]
HFD_med = HFD_med[cond]
HFD_stderr_mean = HFD_stderr_mean[cond]
HFD_stderr_med = HFD_stderr_med[cond]
FWHM_mean = FWHM_mean[cond]
FWHM_med = FWHM_med[cond]
FWHM_std = FWHM_std[cond]

nomfoc = 9967

# fit the right hand line
cond_rh = (pos>nomfoc + 50) & (pos<10300)
#pos_rh = pos[cond_rh]
#HFD_med_rh = HFD_med[cond_rh]
rh_fit = np.polyfit(pos_rh, HFD_med_rh, 1)
HFD_fit_rh = np.polyval(rh_fit, pos_ref)

# fit the left hand line
cond_lh = (pos>9650) & (pos<nomfoc-50)
#pos_lh = pos[cond_lh]
#HFD_med_lh = HFD_med[cond_lh]
lh_fit = np.polyfit(pos_lh, HFD_med_lh, 1)
HFD_fit_lh = np.polyval(lh_fit, pos_ref)


# get the slopes and x-intercepts
m_rh = rh_fit[0]
b_rh = rh_fit[1]

m_lh = lh_fit[0]
b_lh = lh_fit[1]

xint_rh = -b_rh/m_rh
xint_lh = -b_lh/m_lh
PID = np.abs(np.abs(xint_rh) - np.abs(xint_lh))

#xfoc = (xint_rh + xint_lh)/2

xfoc = (b_lh - b_rh)/(m_rh - m_lh)

foc = m_rh*xfoc + b_rh
# PLOTS

#plt.plot(focuser_pos, HFD_med, 'ks')
ax.plot(pos_ref, HFD_fit_lh, 'g--', label = f'LH Fit: m = {m_lh:0.4f}, xint = {xint_lh:0.2f}')
ax.plot(pos_ref, HFD_fit_rh, 'r--', label = f'RH Fit: m =  {m_rh:0.4f}, xint = {xint_rh:0.2f}')
ax.plot(x0_fit, parabolic_HFD_fit, 'y*', markersize = 20,label = f'Parabolic Foc = {x0_fit:0.2f}')
ax.plot(xfoc, foc, 'bo', label = f'HFD Foc = {xfoc:0.2f}, PID = {PID:0.2f}')
ax.plot(xint_rh,0, 'ro')
ax.plot(xint_lh,0,'go')
ax.legend()

plt.tight_layout()
'''