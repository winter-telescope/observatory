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
import astropy.coordinates
import astropy.units as u

import sys

# add the wsp directory to the PATH
wsp_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),'wsp')
sys.path.insert(1, wsp_path)
print(f'control: wsp_path = {wsp_path}')

try:
    
    from telescope import platesolver
except:
    import platesolver

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
        pass
    
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

imagefile = os.readlink(os.path.join(os.getenv("HOME"), 'data', 'last_image.lnk'))

#imagefile = 'sample_platesolve_image.fits'



#hdu.writeto(name,overwrite = True)


header, data = plotFITS(imagefile, xmax = 2048, ymax = 2048)

# reading some stuff from the header.
## the header is an astropy.io.fits.header.Header object, but it can be queried like a dict
"""
print(f'FILENAME = {header["FILENAME"]}')
print(f'RA = {header["RA"]}')
print(f'DEC  = {header["DEC"]}')
"""
#%%
plateSolver = platesolver.PlateSolver()

plateSolver.platesolve(imagefile, 0.47)

ra_j2000_hours = plateSolver.results.get('ra_j2000_hours')
dec_j2000_degrees = plateSolver.results.get('dec_j2000_degrees')
platescale = plateSolver.results.get('arcsec_per_pixel')
field_angle = plateSolver.results.get('rot_angle_degs')

ra_j2000 = astropy.coordinates.Angle(ra_j2000_hours * u.hour)
dec_j2000 = astropy.coordinates.Angle(dec_j2000_degrees * u.deg)

ra_j2000_nom = astropy.coordinates.Angle(header["RA"], unit = 'deg')
dec_j2000_nom = astropy.coordinates.Angle(header["DEC"], unit = 'deg')

print()
print(f'Platesolve Astrometry Solution: RA = {ra_j2000.to_string("hour")}, DEC = {dec_j2000.to_string("deg")}')
print(f'Nominal Position:               RA = {ra_j2000_nom.to_string("hour")}, DEC = {dec_j2000_nom.to_string("deg")}')
print(f'Platesolve:     Platescale = {platescale:.4f} arcsec/pix, Field Angle = {field_angle:.4f} deg')

"""
astrometryNet_ra_j2000 = astropy.coordinates.Angle(324.718667275 * u.deg)
astrometryNet_dec_2000 = astropy.coordinates.Angle(57.4977710915 * u.deg)
astrometryNet_platescale = 0.466266
astrometryNet_field_angle = 264.5
print(f'Astrometry.net Solution:        RA = {astrometryNet_ra_j2000.to_string("hour")}, DEC = {astrometryNet_dec_2000.to_string("deg")}')

print()
#print(f'Astrometry.net: Platescale = {astrometryNet_platescale:.4f} arcsec/pix, Field Angle = {astrometryNet_field_angle:.4f} deg')
"""
