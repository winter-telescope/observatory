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


def powerLaw(x, a, n):
    y = a*x**n
    return y
#%%
#data_directory = os.readlink(os.path.join(os.getenv("HOME"), 'data', 'tonight_images.lnk'))
# evening skyflats
#

#image_path = os.readlink(os.path.join(os.getenv("HOME"), 'data', 'last_image.lnk'))
#image_path = '/home/winter/data/images/20210817/SUMMER_20210816_235912_Camera0.fits'
imlist = []
# g-band images
gband_flats_data_directory = os.path.join(os.getenv("HOME"), 'data', 'images','20220810')
gband_images = glob.glob(os.path.join(gband_flats_data_directory, '*.fits'))


gband_extra_images = ['/home/winter/data/images/20220810/SUMMER_20220810_201621_Camera0.fits',
                '/home/winter/data/images/20220811/SUMMER_20220811_200113_Camera0.fits',
                '/home/winter/data/images/20220811/SUMMER_20220811_200037_Camera0.fits',
                '/home/winter/data/images/20220811/SUMMER_20220812_053812_Camera0.fits']
imlist = imlist + gband_images
imlist = imlist + gband_extra_images


# r-band images
rband_flats_data_directory = os.path.join('/data', 'images','20210817')
rband_images = glob.glob(os.path.join(rband_flats_data_directory, '*.fits'))
rband_extra_images = ['/home/winter/data/images/20220726/SUMMER_20220726_201910_Camera0.fits',
                      '/home/winter/data/images/20220728/SUMMER_20220729_053343_Camera0.fits',
                      '/home/winter/data/images/20220728/SUMMER_20220729_053429_Camera0.fits',
                      ]
imlist = imlist + rband_images
#imlist = imlist + rband_extra_images

#%%
images = []
flats = []
biases = []

for image_path in imlist:
    ccd = astropy.nddata.CCDData.read(image_path, unit = 'adu')
    #images.append(ccd)
    if (ccd.header["OBSTYPE"] == "FLAT") or (image_path in gband_extra_images):
        flats.append(ccd)
    
    
    
#%%

fig, axes = plt.subplots(1,2, figsize = (12,6))
fig.suptitle(f'Sky Flat Model', fontsize = 16)

for filterID in ['r', 'g']:
    
    sunalt = []
    medcnts = []
    exptimes = []
    
    bias_medcnts = []
    
            
    for flat in flats:
        #plotFITSdata(flat, printinfo = False, xmax = 2048, ymax = 2048, hist = False)
        #plt.figure()
        #plt.imshow(flat.data)
        filt = flat.header["FILTERID"]
        if filt == filterID:
            sunalt.append(flat.header["SUNALT"])
            medcnts.append(np.median(flat.data))
            exptimes.append(flat.header["EXPTIME"])
        
    
    for bias in biases:
        bias_medcnts.append(np.median(bias.data))
    
    meanbias = np.mean(bias_medcnts)
    
    
    
    
    sunalt = np.array(sunalt)
    medcnts = np.array(medcnts) 
    exptimes = np.array(exptimes)
    
    max_sunalt = -5
    
    medcnts = medcnts[sunalt<max_sunalt]
    exptimes = exptimes[sunalt<max_sunalt]
    sunalt = sunalt[sunalt<max_sunalt]
    
    if filterID == 'r':
        sunalt = sunalt[exptimes>6]
        medcnts = medcnts[exptimes>6]
        exptimes = exptimes[exptimes>6]
        
        exptimes = exptimes[sunalt>-10]
        medcnts = medcnts[sunalt>-10]
        sunalt = sunalt[sunalt>-10]
    
        
        sunalt = np.append(sunalt[1:3], sunalt[5:])
        exptimes = np.append(exptimes[1:3], exptimes[5:])
        medcnts = np.append(medcnts[1:3], medcnts[5:])
        
    
    countrate = medcnts/exptimes
    """
    plt.figure()
    plt.plot(medcnts, 'o')
    plt.title('counts')
    plt.figure()
    plt.plot(sunalt, 'o')
    plt.title('sunalt')
    """
    
    
    p1 = axes[0].plot(sunalt, countrate, 's')
    color = p1[0].get_color()
    #fit = np.polyfit(sunalt, countrate, 6)
    #xfit = np.linspace(np.min(sunalt), np.max(sunalt), 100)
    xfit = np.linspace(np.min(sunalt), -5, 100)
    #yfit = np.polyval(fit, xfit)
    #plt.plot(xfit, yfit, 'm-')
    target_counts = 40000
    maxtime = 60
    times = target_counts/countrate
    
    if filterID in ['g', 'r']:
        # fit an powerlaw to  -1*alt vs ln(countrate)
        x = -1*sunalt
        y = np.log(countrate)
        params = scipy.optimize.curve_fit(powerLaw,x, y)[0]
        a = params[0]
        n = params[1]
        model_yfit = np.exp(a*(-1*xfit)**n)
        countrate_label = f'{filterID}-band: count rate = exp[{a:.2f}*(-sun_alt)^{n:.2f}]'
        exptime_label = f'{filterID}-band: exptime = {target_counts} / exp[{a:.2f}*(-sun_alt)^{n:.2f}]'
    elif filterID == 'other':
        x = -1*sunalt
        y = countrate
        params = scipy.optimize.curve_fit(powerLaw, x, y)[0]
        a = params[0]
        n = params[1]
        model_yfit = a*(-1*xfit)**n
        countrate_label = f'{filterID}-band: count rate = {a:.2f}*(-sun_alt)^{n:.2f}'
        exptime_label = f'{filterID}-band: exptime = {target_counts} / {a:.2f}*(-sun_alt)^{n:.2f}'
    
    axes[0].semilogy(xfit, model_yfit, '-', color = color, label = countrate_label)

    axes[0]
    axes[0].set_xlabel('Sun Altitude (deg)')
    axes[0].set_ylabel('Count Rate (counts/s)')
    axes[0].legend(fontsize = 10)
    
    times_fit = target_counts/model_yfit
    
    p2 = axes[1].plot(sunalt[times<maxtime], times[times<maxtime], 's')
    color = p2[0].get_color()
    axes[1].plot(xfit[times_fit<maxtime], times_fit[times_fit<maxtime], '-', color = color, label = exptime_label)
    axes[1].set_xlabel('Sun Altitude (degs)')
    axes[1].set_ylabel(f'Req Time for {target_counts} Counts (sec)')
    axes[1].legend(fontsize = 10)
    plt.tight_layout()
