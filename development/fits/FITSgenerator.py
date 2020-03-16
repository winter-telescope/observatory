# -*- coding: utf-8 -*-
"""
Created on Wed Mar  4 10:05:01 2020


Sample FITS file generator


@author: nlourie
"""

import os
import sys

""" 
#These lines only are useful if you're working in the code GIT repo
    # if you're not, just keep them commented out.
    # this allows you to plot using >> utils.plotFITS(filename)
# add the wsp directory to the PATH
code_path = os.path.dirname(os.path.dirname(os.getcwd()))
wsp_path = os.path.join(code_path,'wsp')
sys.path.insert(1, wsp_path)
from utils import utils


"""

import numpy as np
from astropy.io import fits
import matplotlib.pyplot as plt



def plotFITS(filename):
    plt.close('all')
    image_file = filename
    #plt.ion()
    hdu_list = fits.open(image_file,ignore_missing_end = True)
    hdu_list.info()
    
    image_data = hdu_list[0].data
    plt.title('Last Image Taken:')
    
    plt.imshow(image_data,cmap = 'gray')
    plt.show(block = False)
    plt.pause(0.1)



npix_x = 1920
npix_y = 1080
data = np.random.random((npix_x,npix_y))
data = np.transpose(data)
hdu = fits.PrimaryHDU(data = data)


name = 'rand_img.FITS'
hdu.writeto(name,overwrite = True)


plotFITS(name)