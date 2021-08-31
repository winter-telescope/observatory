#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Aug 17 00:15:52 2021

@author: winter
"""

#from astropy.nddata import CCDData
import astropy.nddata
from astropy.io import fits
import os
import numpy as np
import glob
import matplotlib.pyplot as plt
from datetime import datetime
import astropy.visualization 
import  astropy.time
from mpl_toolkits.axes_grid1 import make_axes_locatable
import scipy.optimize



def plotFITSdata(CCDData, printinfo = False, xmin = None, xmax = None, ymin = None, ymax = None, hist = True, min_bin_counts = 1):
    plt.close('all')
    
    
    image_data = CCDData.data
    header = CCDData.header
    
    
    
    #image_file = filename
    #plt.ion()
    """
    hdu_list = fits.open(image_file,ignore_missing_end = True)
    if printinfo:
        hdu_list.info()
    
    image_data = hdu_list[0].data
    """
    if xmin is None:
        xmin = 0
    if ymin is None:
        ymin = 0
    if xmax is None:
        xmax = np.shape(image_data)[0]
    if ymax is None:
        ymax = np.shape(image_data)[1]
        
    
    #header = hdu_list[0].header
    image = image_data[xmin:xmax, ymin:ymax]
    
    filename = header.get("FILENAME", "")
    median_counts = np.median(image)
    stddev = np.std(image)
    
    if "OBSTYPE" in header.keys():
        if header.get("OBSTYPE", "?") in ["BIAS", "DARK", "FLAT"]:
            hist = True
            #print(f'hist = {hist}')
    
    if hist:
        fig, axarr = plt.subplots(2,1, gridspec_kw = {'height_ratios' : [3,1]}, figsize = (6,8))
        ax0 = axarr[0]
    else:
        fig, axarr = plt.subplots(1,1, figsize = (8,8))
        ax0 = axarr
    
    if "AEXPTIME" in header.keys():
        exptime_str = f'{header["AEXPTIME"]:0.1f}'
    else:
        exptime_str = '?'
    
    
    
    title = f'Last Image Taken: {filename}\nMedian Counts = {median_counts:.0f}, Std Dev = {stddev:.0f}, Exptime = {exptime_str} s'
    title+= f'\nFilter: {header.get("FILTERID","?")}, ObsType = {header.get("OBSTYPE", "?")}'
    title+=f'\nComment: {header.get("QCOMMENT", "?")}'
    if "UTC" in header:
        tstr = header['UTCISO']
        
        
        image_write_time = datetime.fromisoformat(tstr)
        now = datetime.utcnow()
        
        #td = tend - tstart
        td = now-image_write_time
        
        days = td.days
        hours, remainder = divmod(td.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        # If you want to take into account fractions of a second
        seconds += td.microseconds / 1e6
        
        #print(f'elapsed time = {days} days, {hours} hours, {minutes} minutes, {seconds} seconds')
        msg = f'{hours}:{minutes}:{seconds:0.2f}'
        msg =  f'{seconds:0.1f} sec'
        if minutes>0.0:
            msg = f'{minutes} min ' + msg
        if hours>0.0:
            msg = f'{hours} hours ' + msg
        if days>0.0:
            msg = f'{days} days ' + msg
        msg = f'Image taken {msg} ago'
        title = title + f'\n{msg}'
    ax0.set_title(title)#', stddev = {stddev}')
    
    
    #if header.get("OBSTYPE", "?") in ['BIAS', 'DARK']:
    #    hist = True
    
    
    #norm = astropy.visualization.simple_norm(image, 'sqrt')
    
    norm = astropy.visualization.ImageNormalize(image, 
                                             interval = astropy.visualization.ZScaleInterval(),
                                             stretch = astropy.visualization.SqrtStretch())
    
    
    im = ax0.imshow(image, cmap = 'gray', origin = 'lower', norm = norm)
    ax0.set_xlabel('X [pixels]')
    ax0.set_ylabel('Y [pixels]')
    
    # set up the colorbar. this is a pain in this format...
    # source: https://stackoverflow.com/questions/32462881/add-colorbar-to-existing-axis
    divider = make_axes_locatable(ax0)
    cax = divider.append_axes('right', size = '5%', pad = 0.05)
    fig.colorbar(im, cax = cax, orientation = 'vertical')
    
    
    
    # PLOT THE HISTOGRAM
    if hist:
        # Plot a histogram, do this iteratively to figure out good limits and binning
        # first flatten the data to 1d
        vec = np.ravel(image)
        
        # now make an initial histogram. use the full range
        lowerlim0 = 0
        upperlim0 = 2**16
        bins0 = np.linspace(lowerlim0, upperlim0, 1000)
        #n, bins, patches = axarr[1].hist(vec, bins = bins0)
        
        n0, bins0 = np.histogram(vec, bins = bins0)
        
        
        bin_left_edges0 = bins0[0:-1]
        
        # now remake the histogram to only make bins that have some minimum number of counts
        
        threshold = min_bin_counts
        full_bins = bin_left_edges0[n0>threshold]
        
        lowerlim = np.min(full_bins)
        upperlim = np.max(full_bins)
        
        # use arange for the bins since we only expect integer counts
        
        bins = np.arange(lowerlim, upperlim, 1)
        n, bins, patches = axarr[1].hist(vec, bins = bins, color = 'black')
        
        axarr[1].set_xlabel('Counts')
        axarr[1].set_ylabel('Nbins')
    
        axarr[1].set_yscale('log')
    

    #plt.show()#block = False)
    #plt.pause(0.1)
    
    
    return header, image_data



#%%
#data_directory = os.readlink(os.path.join(os.getenv("HOME"), 'data', 'tonight_images.lnk'))
# evening skyflats
data_directory = os.path.join(os.getenv("HOME"), 'data', 'images','20210817')

#image_path = os.readlink(os.path.join(os.getenv("HOME"), 'data', 'last_image.lnk'))
image_path = '/home/winter/data/images/20210817/SUMMER_20210816_235912_Camera0.fits'

imlist = glob.glob(os.path.join(data_directory, '*.fits'))


#%%
images = []
flats = []
biases = []

for image_path in imlist:
    ccd = astropy.nddata.CCDData.read(image_path, unit = 'adu')
    #images.append(ccd)
    if ccd.header["OBSTYPE"] == "FLAT":
        flats.append(ccd)
    
    elif ccd.header["OBSTYPE"] == "BIAS":
        biases.append(ccd)
        
    

#%%
        
def powerLaw(x, a, n):
    y = a*(-x)**n
    return y
        
sunalt = []
medcnts = []
exptimes = []

bias_medcnts = []
        
for flat in flats:
    #plotFITSdata(flat, printinfo = False, xmax = 2048, ymax = 2048, hist = False)
    #plt.figure()
    #plt.imshow(flat.data)
    
    sunalt.append(flat.header["SUNALT"])
    medcnts.append(np.median(flat.data))
    exptimes.append(flat.header["EXPTIME"])
    pass

for bias in biases:
    bias_medcnts.append(np.median(bias.data))

meanbias = np.mean(bias_medcnts)

i_outlier = 7
del sunalt[i_outlier]
del medcnts[i_outlier]
del exptimes[i_outlier]



sunalt = np.array(sunalt)
medcnts = np.array(medcnts) 
#medcnts -= meanbias
exptimes = np.array(exptimes)
"""
sunalt = sunalt[exptimes>6]
medcnts = medcnts[exptimes>6]
exptimes = exptimes[exptimes>6]

"""
#
medcnts = medcnts[sunalt<-2.5]
exptimes = exptimes[sunalt<-2.5]
sunalt = sunalt[sunalt<-2.5]

countrate = medcnts/exptimes

#sunalt = np.abs(sunalt)

plt.figure()
plt.plot(sunalt, countrate, 'ks')

fit = np.polyfit(sunalt, countrate, 6)
#xfit = np.linspace(np.min(sunalt), np.max(sunalt), 100)
xfit = np.linspace(np.min(sunalt), -5, 100)
yfit = np.polyval(fit, xfit)
#plt.plot(xfit, yfit, 'm-')

params = scipy.optimize.curve_fit(powerLaw,sunalt, countrate)[0]
#%
powerlaw_yfit = powerLaw(xfit, *params)
label = f'rate = {params[0]:0.2e}*(-x)^{params[1]:0.2f}'
plt.plot(xfit, powerlaw_yfit, 'r-', label = label)
plt.xlabel('Sun Altitude (deg)')
plt.ylabel('Count Rate (counts/s)')
plt.legend()
#%%
target_counts = 40000
maxtime = 60
times = target_counts/countrate
times_fit = target_counts/powerlaw_yfit
plt.figure()
plt.plot(sunalt[times<maxtime], times[times<maxtime], 'ks')
plt.plot(xfit[times_fit<maxtime], times_fit[times_fit<maxtime], 'r-')
plt.xlabel('Sun Altitude (degs)')
plt.ylabel(f'Req Time for {target_counts} Counts (sec)')

