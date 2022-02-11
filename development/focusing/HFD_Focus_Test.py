#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
The focus loop object class

@author: C. Soto and V. Karambelkar
"""
import os
import numpy as np
import matplotlib.pyplot as plt


pixscale = 0.466



datapath = os.path.join(os.getenv("HOME"), 'data', 'df_focuser', 'HFD_Focus_Test_Data.txt')
pos, HFD_med, HFD_mean, HFD_stderr_mean, HFD_stderr_med, FWHM_mean, FWHM_med, FWHM_std = np.loadtxt(datapath, unpack = True)

# try to remove some obvious junk points
HFD_min = 2.0

cond = HFD_med > 2.0
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
pos_rh = pos[cond_rh]
HFD_med_rh = HFD_med[cond_rh]
rh_fit = np.polyfit(pos_rh, HFD_med_rh, 1)
HFD_fit_rh = np.polyval(rh_fit, pos)

# fit the left hand line
cond_lh = (pos>9650) & (pos<nomfoc-50)
pos_lh = pos[cond_lh]
HFD_med_lh = HFD_med[cond_lh]
lh_fit = np.polyfit(pos_lh, HFD_med_lh, 1)
HFD_fit_lh = np.polyval(lh_fit, pos)


# get the slopes and x-intercepts
m_rh = rh_fit[0]
b_rh = rh_fit[1]

m_lh = lh_fit[0]
b_lh = lh_fit[1]

xint_rh = -b_rh/m_rh
xint_lh = -b_lh/m_lh
deltaX = np.abs(np.abs(xint_rh) - np.abs(xint_lh))
xfoc = (xint_rh + xint_lh)/2
foc = m_rh*xfoc + b_rh
# PLOTS

fig,ax = plt.subplots(1,1,figsize = (8,10))
#plt.plot(focuser_pos, HFD_med, 'ks')
ax.errorbar(pos, HFD_med, yerr = HFD_stderr_med, capsize = 5, fmt = 'ks', label = 'Median')
ax.plot(pos, HFD_fit_lh, 'g-', label = f'LH Fit: m = {m_lh:0.4f}, xint = {xint_lh:0.2f}')
ax.plot(pos, HFD_fit_rh, 'r-', label = f'RH Fit: m =  {m_rh:0.4f}, xint = {xint_rh:0.2f}')
ax.plot(pos, 0*pos, 'k--')
ax.plot(xint_rh,0, 'ro')
ax.plot(xint_lh,0,'go')
ax.plot(xfoc, foc, 'ko', label = f'HFD Foc = {xfoc:0.2f} (parabolic Foc = {nomfoc:0.2f}), PID = {deltaX:0.2f}')
#ax.plot()
ax.legend()
ax.set_xlabel('Focuser Position [micron]')
ax.set_ylabel('Half-Focus Diameter [arcseconds]')
ax.set_ylim(-1,8)


"""
plt.figure()
FWHM_med = np.array(FWHM_med)
FWHM_std = np.array(FWHM_std)
FWHM_stderr_med = (np.pi/2)**0.5 * FWHM_std/np.sqrt(26)
plt.errorbar(pos, FWHM_med, yerr = FWHM_stderr_med, capsize = 5, fmt = 'ks', label = 'Median')

plt.legend()
plt.xlabel('Focuser Position [micron]')
plt.ylabel('FWHM [arcseconds]')

# F
"""