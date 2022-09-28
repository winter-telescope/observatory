#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Sep 20 13:22:24 2022

@author: nlourie
"""

import matplotlib.pyplot as plt
from photutils.detection import IRAFStarFinder, find_peaks
from photutils.centroids import centroid_sources, centroid_com
from photutils.datasets import make_4gaussians_image
import astropy.stats
import astropy.visualization
plt.close('all')
data = make_4gaussians_image()

mean, median, std = astropy.stats.sigma_clipped_stats(data, sigma=3.0)  
threshold = median + (5. * std)


daofind = IRAFStarFinder(fwhm=7.0, 
                         threshold=threshold,
                         peakmax = 30000.0,
                         brightest = 4)  

#sources = daofind(data)  
#x_init = sources['xcentroid']
#y_init = sources['ycentroid']

box_size = 51
source_tbl = find_peaks(data, threshold, box_size=box_size)
x_init = source_tbl['x_peak']
y_init = source_tbl['y_peak']
#x_init = (25, 91, 151, 160)
#y_init = (40, 61, 24, 71)



x, y = centroid_sources(data, x_init, y_init, box_size=box_size,
                        centroid_func=centroid_com)
h = 8.0
plt.figure(figsize=(2*h, h))
plt.imshow(data, origin='lower', interpolation='nearest')
plt.plot(x_init, y_init, 'x', color = 'white', label = 'initial guess')
plt.plot(x, y, '+',  color='red', label = 'com centroids')
plt.legend(fontsize = 12)
plt.tight_layout()

from photutils.psf import extract_stars
from astropy.nddata import NDData
from astropy.table import Table

nddata = NDData(data=data)
stars_tbl = Table()
stars_tbl['x'] = x  
stars_tbl['y'] = y
stars = extract_stars(nddata, stars_tbl, size=box_size)  

fig, axes = plt.subplots(nrows=1, ncols=len(stars_tbl), figsize=(20, 20),
                       squeeze=True)

for i in range(len(source_tbl)):
    ax = axes[i]
    norm = astropy.visualization.simple_norm(stars[i], 'log', percent = 99.0)
    ax.imshow(stars[i], norm = norm, origin = 'lower', cmap = 'coolwarm')

