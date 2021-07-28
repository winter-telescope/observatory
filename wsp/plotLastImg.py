#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jul 20 15:37:23 2021

@author: winter
"""


import os
import numpy as np
from astropy.io import fits
import matplotlib.pyplot as plt
import astropy.visualization 


def plotFITS(filename, printinfo = False, xmin = None, xmax = None, ymin = None, ymax = None):
    plt.close('all')
    plt.figure(figsize = (8,8))
    image_file = filename
    #plt.ion()
    hdu_list = fits.open(image_file,ignore_missing_end = True)
    if printinfo:
        hdu_list.info()
    
    image_data = hdu_list[0].data
    
    if xmin is None:
        xmin = 0
    if ymin is None:
        ymin = 0
    if xmax is None:
        xmax = np.shape(data)[0]
    if ymax is None:
        ymax = np.shape(data)[1]
        
    
    header = hdu_list[0].header
    image = image_data[xmin:xmax, ymin:ymax]
    try:
        filename = header["FILENAME"]
    except:
        filename = 'last image'
    median_counts = np.median(image)
    stddev = np.std(image)
    
    
    plt.title(f'Last Image Taken: {filename}\nMedian Counts = {median_counts}')#', stddev = {stddev}')
    
    
    
    
    
    #norm = astropy.visualization.simple_norm(image, 'sqrt')
    
    norm = astropy.visualization.ImageNormalize(image, 
                                             interval = astropy.visualization.ZScaleInterval(),
                                             stretch = astropy.visualization.SqrtStretch())
    
    
    plt.imshow(image, cmap = 'gray', origin = 'lower', norm = norm)
    plt.colorbar()
    plt.show()#block = False)
    plt.pause(0.1)
    return header, image_data


"""
npix_x = 1920
npix_y = 1080
data = np.random.random((npix_x,npix_y))
data = np.transpose(data)
hdu = fits.PrimaryHDU(data = data)
"""

#name = '/home/winter/data/viscam/test_images/20210503_171349_Camera00.fits'

name = os.path.join(os.getenv("HOME"), 'data', 'last_image.lnk')

#hdu.writeto(name,overwrite = True)


header, data = plotFITS(name, xmax = 2048, ymax = 2048)

# reading some stuff from the header.
## the header is an astropy.io.fits.header.Header object, but it can be queried like a dict
#print(f'FILENAME = {header["FILENAME"]}')
#print(f'RA = {header["RA"]}')
#print(f'DEC  = {header["DEC"]}')