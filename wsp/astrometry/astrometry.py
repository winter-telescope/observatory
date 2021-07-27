# -*- coding: utf-8 -*-
"""
@author: Cruz Soto

Plate Solving Algorithm using Astrometry
"""

from astropy.io import fits

from PIL import Image

import numpy

import argparse

import sys
import os
import subprocess

def fits_to_Tiff(imagepath):
    img = fits.open(imagepath)
    data = img[0].data
    
    w = data.shape[1]
    h = data.shape[0]
    
    outputArray = numpy.array(data, dtype=numpy.int16)

    output = Image.fromarray(outputArray.reshape((h, w)), "I;16")
    
    newpath = imagepath[:len(imagepath)-5] + ".tif"
    output.save(newpath)
    
    return newpath

def Astrometry(imagepath):
    print("running")
    tiff = fits_to_Tiff(imagepath)
    print(tiff)
    try:
        command = 'solve-field'+ ' ' + tiff
        print('Executing command : %s'%(command))
        rval = subprocess.run(command.split(),check=True,capture_output=True)
        print('Process completed')
        print(rval.stdout.decode())

    except subprocess.CalledProcessError as err:
        print('Could not run Astrometry.net with error %s.'%(err))
	
    return 'hi'

if __name__=='__main__':
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--d", type=str,help='directory')
    args = parser.parse_args()
    
    Astrometry(args.d)
    