#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Apr  4 14:44:43 2022

@author: nlourie
"""

import photutils.detection
import astropy.stats
from astropy.io import fits
import scipy.interpolate
import numpy as np
import matplotlib.pyplot as plt
import astropy.visualization
import photutils.aperture
import photutils.centroids
from datetime import datetime
import scipy.ndimage
#from astropy.visualization import SqrtStretch
#from astropy.visualization.mpl_normalize import ImageNormalize
#from photutils.aperture import CircularAperture

#%% calculate the centroid

def physicalCentroid(X, Y, Z, method = 'com', plots = False, *args, **kwargs):
    
    if method == 'com':
        xc_pix, yc_pix = photutils.centroids.centroid_com(Z, *args, **kwargs)
    elif method == '1dg':
        xc_pix, yc_pix = photutils.centroids.centroid_1dg(Z, *args, **kwargs)
    elif method == '2dg':
        xc_pix, yc_pix = photutils.centroids.centroid_2dg(Z, *args, **kwargs)
    else:
        raise TypeError('invalid method. acceptable types are: com, 1dg (1d Gaussian), 2dg (2d Gaussian)')
    x = X[0,:]
    y = Y[:,0]
    ix = np.arange(0,len(x))
    iy = np.arange(0,len(y))
    
    fx = scipy.interpolate.interp1d(ix,x)
    fy = scipy.interpolate.interp1d(iy,y)
    
    xc = fx(xc_pix)
    yc = fy(yc_pix)
    if plots:
        print(f'Centroid Calculation: centroid at (i,j) = ({xc_pix},{yc_pix}), (x,y) = ({xc},{yc})')
        plt.figure()
        plt.subplot(1,2,1)
        plt.title('Interpolating X')
        plt.plot(ix,x,'k.')
        plt.plot(ix,fx(ix),'r-')
        plt.plot(xc_pix, xc,'gx')
        
        plt.subplot(1,2,2)
        plt.title('Interpolating Y')
        plt.plot(iy,y,'k.')
        plt.plot(iy,fy(iy),'r-')
        plt.plot(yc_pix, yc,'gx')
    return xc, yc


plt.close('all')

start = datetime.now().timestamp()
#impath = 'SUMMER_20220331_230838_Camera0.fits'
impath = 'Preview_20220914_213835_2sec_Bin4_-19.8C_gain390.fit'
hdu = fits.open(impath)[0]

darkpath = 'Dark_ASIImg_2sec_Bin4_-19.8C_gain390_2022-09-14_205448_frame0001.fit'
darkhdu = fits.open(darkpath)[0]


rawdata = hdu.data - darkhdu.data #

mean, median, std = astropy.stats.sigma_clipped_stats(rawdata, sigma=3.0)  
print((mean, median, std))  

data = rawdata -median

#data = data[920:1000,750:900]
#data = data[300:1700, 800:1900]

yi = np.arange(0,np.shape(data)[0])
xi = np.arange(0,np.shape(data)[1])
X,Y = np.meshgrid(xi, yi, indexing = 'xy')


#%%


daofind = photutils.detection.IRAFStarFinder(fwhm=7.0, 
                                            threshold=5.*std,
                                            peakmax = 30000.0,
                                            brightest = 5)  
sources = daofind(data)  
end = datetime.now().timestamp()
dt = end - start
print(f'runtime = {dt} s')

print(sources)


positions = np.transpose((sources['xcentroid'], sources['ycentroid']))
apertures = photutils.aperture.CircularAperture(positions, r=4.)

norm = astropy.visualization.ImageNormalize(data, 
                                             interval = astropy.visualization.ZScaleInterval(),
                                             stretch = astropy.visualization.SqrtStretch())



#%%


#norm = astropy.visualization.mpl_normalize.ImageNormalize(stretch=astropy.visualization.SqrtStretch())
plt.figure()
plt.imshow(data, cmap='Greys', origin='lower', norm=norm,
           interpolation='nearest')

apertures.plot(color='m', lw=1.5, alpha=1)




#%%

#plt.figure()
#plt.plot(sources['id'], sources['peak'],'o')

xpos = sources['xcentroid']
ypos = sources['ycentroid']
box_size = 100
# centroid the sources
x, y = photutils.centroids.centroid_sources(data, xpos = xpos, ypos = ypos, box_size = box_size, 
                                            footprint = None, error = None, mask = None, 
                                            centroid_func = photutils.centroids.centroid_com)

plt.scatter(x, y, marker='+', s=80, color='red')


# plot the cutouts
footprint = np.ones(np.repeat(box_size, 2), dtype=bool)
h = 3.5
fig, axes = plt.subplots(1, len(sources), figsize = (h*len(sources),h))
test_offset_pix = 0
for i in range(len(xpos)):
    xp = xpos[i]
    yp = ypos[i]
    xc = x[i]
    yc = y[i]
    
    ax = axes[i]
    slices_large, slices_small = astropy.nddata.utils.overlap_slices(data.shape,
                                                footprint.shape, (yp+test_offset_pix, xp+test_offset_pix))
    data_cutout = data[slices_large]
    #plt.figure(figsize = (4,4))
    #plt.imshow(data_cutout, origin='lower', interpolation='nearest')
    p = ax.pcolormesh(X[slices_large], Y[slices_large], data[slices_large], norm = None, shading = 'nearest')
    ax.plot(xc, yc, marker='+', color='red', markersize = 15)
    ax.scatter(xp, yp, s = 1000, marker = 'o', color = 'm', facecolors = 'none')
    
    xc_range, yc_range = physicalCentroid(X[slices_large], Y[slices_large], data[slices_large], method = 'com')
    ax.plot(xc_range, yc_range, marker = 'x', color = 'k', markersize = 10)
    #fig.colorbar(p)
    ax.set_aspect('equal')
plt.tight_layout()
#%%

plt.figure()
plt.imshow(data,norm = norm, origin='lower', interpolation='nearest', cmap = 'Greys')
plt.axis('equal')
plt.scatter(x, y, marker='+', s=80, color='red')
apertures.plot(color='m', lw=1.5, alpha=1)

plt.figure()
plt.pcolormesh(X,Y, data, norm = norm, shading = 'nearest', cmap = 'Greys')
plt.axis('equal')
plt.scatter(x, y, marker='+', s=80, color='red')
apertures.plot(color='m', lw=1.5, alpha=1)