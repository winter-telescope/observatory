#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Apr  4 14:44:43 2022

@author: nlourie
"""
import os
import photutils.detection
import astropy.stats
from astropy.io import fits
import scipy.interpolate
import scipy
import numpy as np
import matplotlib.pyplot as plt
import matplotlib as mpl
import astropy.visualization
import photutils.aperture
import photutils.centroids
from datetime import datetime
import scipy.ndimage
import glob
from mpl_toolkits.axes_grid1 import make_axes_locatable


#from astropy.visualization import SqrtStretch
#from astropy.visualization.mpl_normalize import ImageNormalize
#from photutils.aperture import CircularAperture

#%% calculate the centroid

def physicalCentroid(X, Y, Z, method = 'com', return_centroid_dt = False, plots = False, *args, **kwargs):
    t0 = datetime.now().timestamp()
    if method == 'com':
        xc_pix, yc_pix = photutils.centroids.centroid_com(Z, *args, **kwargs)
    elif method == '1dg':
        xc_pix, yc_pix = photutils.centroids.centroid_1dg(Z, *args, **kwargs)
    elif method == '2dg':
        xc_pix, yc_pix = photutils.centroids.centroid_2dg(Z, *args, **kwargs)
    elif method == 'scipy_com':
        xc_pix, yc_pix = scipy.ndimage.center_of_mass(Z, *args, **kwargs)
    else:
        raise TypeError('invalid method. acceptable types are: com, 1dg (1d Gaussian), 2dg (2d Gaussian)')
    
    tf = datetime.now().timestamp()
    dt_centroid = tf - t0
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
    if return_centroid_dt:
        return xc, yc, dt_centroid
    else:
        return xc, yc


plt.close('all')

start = datetime.now().timestamp()
#impath = 'SUMMER_20220331_230838_Camera0.fits'
imdir = 'GuiderDitherData_20220918'
impath = os.path.join(imdir, 'Preview_20220918_201222_2sec_Bin4_-19.8C_gain390.fit')
hdu = fits.open(impath)[0]

#darkpath = os.path.join(imdir, 'Calibrations', 'Dark_ASIImg_2sec_Bin4_-19.8C_gain390_2022-09-18_201707_frame0001.fit')
darks = glob.glob(os.path.join(imdir, 'Calibrations','Dark*'))
darkarr = []
for darkpath in darks:
    darkarr.append(fits.open(darkpath)[0].data.astype(np.float32))

darkdata = np.average(darkarr, axis = 0)
#%%

rawdata = hdu.data.astype(np.float32)
#darkdata = darkhdu.data.astype(np.float32)

mean, median, std = astropy.stats.sigma_clipped_stats(rawdata, sigma=3.0)  
print((mean, median, std))  

data = hdu.data# rawdata# -median


# just plot the data
#scaledata = darkhdu.data
scaledata = darkdata
norm = astropy.visualization.ImageNormalize(scaledata, 
                                             interval = astropy.visualization.ZScaleInterval(),
                                             stretch = astropy.visualization.SqrtStretch())


cmap = 'cividis'



#norm = astropy.visualization.mpl_normalize.ImageNormalize(stretch=astropy.visualization.SqrtStretch())
fig, axes = plt.subplots(1,3, figsize = (18,6))

ax = axes[0]
plotdata = darkdata
divider = make_axes_locatable(ax)
ax_cb = divider.append_axes("right", size="5%", pad=0.05)
fig = ax.get_figure()
fig.add_axes(ax_cb)
im = ax.imshow(plotdata, cmap=cmap, origin='lower', norm=norm,
           interpolation='nearest')
ax.set_title('Average Combined Dark Master(N=5)')
plt.colorbar(im, cax=ax_cb)

ax = axes[1]
plotdata = rawdata
divider = make_axes_locatable(ax)
ax_cb = divider.append_axes("right", size="5%", pad=0.05)
fig = ax.get_figure()
fig.add_axes(ax_cb)
im = ax.imshow(plotdata, cmap=cmap, origin='lower', norm=norm,
           interpolation='nearest')
plt.colorbar(im, cax=ax_cb)
ax.set_title('Light')

ax = axes[2]
plotdata = rawdata-darkdata

norm = astropy.visualization.ImageNormalize(plotdata, 
                                             interval = astropy.visualization.ZScaleInterval(),
                                             stretch = astropy.visualization.SqrtStretch())

divider = make_axes_locatable(ax)
ax_cb = divider.append_axes("right", size="5%", pad=0.05)
fig = ax.get_figure()
fig.add_axes(ax_cb)
im = ax.imshow(plotdata, cmap=cmap, origin='lower', norm=norm,
           interpolation='nearest')
plt.colorbar(im, cax=ax_cb)
ax.set_title('Light - Dark Master')


plt.tight_layout()




#%%
data = rawdata-darkdata


#data = data[920:1000,750:900]
#data = data[300:1700, 800:1900]

yi = np.arange(0,np.shape(data)[0])
xi = np.arange(0,np.shape(data)[1])
X,Y = np.meshgrid(xi, yi, indexing = 'xy')





daofind = photutils.detection.IRAFStarFinder(fwhm=7.0, 
                                            threshold=5.*std,
                                            peakmax = 30000.0,
                                            brightest = 5)  
sources = daofind(data)  
end = datetime.now().timestamp()
dt = end - start
print(f'runtime = {dt} s')

print(sources)

box_size = 50


positions = np.transpose((sources['xcentroid'], sources['ycentroid']))
#apertures = photutils.aperture.CircularAperture(positions, r=4.)
apertures = photutils.aperture.RectangularAperture(positions, w = box_size, h = box_size)

#%%
norm = astropy.visualization.ImageNormalize(data, 
                                             interval = astropy.visualization.ZScaleInterval(),
                                             stretch = astropy.visualization.LinearStretch())






#norm = astropy.visualization.mpl_normalize.ImageNormalize(stretch=astropy.visualization.SqrtStretch())
plt.figure(figsize = (16,12))
plt.imshow(data, cmap='Greys', origin='lower', norm=norm,
           interpolation='nearest')
plt.title(f'Bin4 Frame: {np.shape(data)[0]} x {np.shape(data)[1]} pixels, {np.shape(data)[0]*0.3183/60:.0f} x {np.shape(data)[1]*0.3183/60:.0f} arcmin')
#%%
for i in range(len(apertures)):
    # can plot them all at once, but this way i only get one label entry
    if i == 0:
        label = f'IRAF Star Finder Source Detections'
    else:
        label = None
    apertures[i].plot(color='m', lw=1.5, alpha=1, label = label)
    x = apertures[i].positions[0]
    y = apertures[i].positions[1]
    plt.text(x, y+box_size-10, f'Source {i}', color = 'w', horizontalalignment = 'center', fontsize = 12)



#%%

#plt.figure()
#plt.plot(sources['id'], sources['peak'],'o')

xpos = sources['xcentroid']
ypos = sources['ycentroid']
# centroid the sources on the full image
t0 = datetime.now().timestamp()
x, y = photutils.centroids.centroid_sources(data, xpos = xpos, ypos = ypos, box_size = box_size, 
                                            footprint = None, error = None, mask = None, 
                                            centroid_func = photutils.centroids.centroid_com)
tf = datetime.now().timestamp()
dt_full_frame_centroid = (tf - t0)*1000

plt.scatter(x, y, marker='+', s=80, color='red', label = f'COM centroid sources algorithm over full frame')


plt.legend()
#%%
# plot the cutouts
footprint = np.ones(np.repeat(box_size, 2), dtype=bool)
h = 5
fig, axes = plt.subplots(1, len(sources), figsize = (h*len(sources),h))

for i in range(len(xpos)):
    xp = xpos[i]
    yp = ypos[i]
    xc = x[i]
    yc = y[i]
    
    xtest_offset_pix = np.random.randint(0,10)
    ytest_offset_pix = np.random.randint(0,10)
    
    ax = axes[i]
    slices_large, slices_small = astropy.nddata.utils.overlap_slices(data.shape,
                                                footprint.shape, (yp+xtest_offset_pix, xp+ytest_offset_pix))
    data_cutout = data[slices_large]
    
    # smooth it?
    kernel = astropy.convolution.Gaussian2DKernel(x_stddev = 1)
    smoothdata = astropy.convolution.convolve(data_cutout, kernel)
    #data_cutout = smoothdata
    #plt.figure(figsize = (4,4))
    #plt.imshow(data_cutout, origin='lower', interpolation='nearest')
    norm = mpl.colors.Normalize(vmin = 0, vmax = 6000.0)
    norm = mpl.colors.LogNorm(vmin = 1, vmax = 20000)
    norm = astropy.visualization.simple_norm(data_cutout, 'log', percent = 99.0)

    cmap = 'cividis'
    p = ax.pcolormesh(X[slices_large], Y[slices_large], data_cutout, norm = norm, cmap = cmap, shading = 'nearest')
    ax.plot(xc, yc, marker='+', color='red', markeredgewidth =2, markersize = 15, label = f'COM centroid sources algorithm over full frame, dt = {dt_full_frame_centroid:.2f} ms')
    ax.scatter(xp, yp, s = 1000, marker = 'o', color = 'm', facecolors = 'none', label = 'initial IRAF source detection')
    
    roi_centroid_method = '1dg'
    xc_range, yc_range, dt = physicalCentroid(X[slices_large], Y[slices_large], data[slices_large], method = roi_centroid_method, return_centroid_dt = True)
    dt_1dg = dt*1000
    ax.plot(xc_range, yc_range, marker = 'x', color = 'k', markeredgewidth =2, markersize = 10, label = f'roi centroid with method = {roi_centroid_method}, dt = {dt_1dg:.2f} ms')
    
    roi_centroid_method = 'com'
    xc_range, yc_range, dt = physicalCentroid(X[slices_large], Y[slices_large], data[slices_large], method = roi_centroid_method, return_centroid_dt = True)
    dt_com = dt*1000
    ax.plot(xc_range, yc_range, marker = '+', color = 'w', markeredgewidth =2, markersize = 15, label = f'roi centroid with method = {roi_centroid_method}, dt = {dt_com:.2f} ms')
    
    """
    roi_centroid_method = 'scipy_com'
    xc_range, yc_range = physicalCentroid(X[slices_large], Y[slices_large], data[slices_large], method = roi_centroid_method)
    ax.plot(xc_range, yc_range, marker = '+', color = 'b', markeredgewidth =2, markersize = 15, label = f'roi centroid with method = {roi_centroid_method}')
    """
    ax.set_aspect('equal')
    ax.set_title(f'Source {i}')

#fig.colorbar(p)
plt.legend(bbox_to_anchor=(1.04, 1), loc="upper left", fontsize = 8, facecolor = 'lightgrey')
plt.tight_layout()
plt.suptitle(f'Box Size = {box_size} pixels = {box_size*0.3183:.0f} as')

#%%
"""
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
"""