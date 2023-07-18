#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jul 18 10:23:47 2023

@author: winter
"""


import os
import glob
from pathlib import Path
from astropy.io import fits
import numpy as np
import subprocess
import re
from winter_utils import focusloop_winter as foc
from winter_utils.paths import astrom_sex, astrom_param, astrom_filter, astrom_nnw, MASK_DIR, MASTERDARK_DIR, MASTERFLAT_DIR, DEFAULT_OUTPUT_DIR
from winter_utils.io import get_focus_images_in_directory
from winter_utils import quick_combine_images
#%%
board_ids_to_use = [1, 2, 3, 4]

plot_all = True

image_dir = '/home/winter/data/images/20230717/focusLoop_20230718-115854-098/'

foc. matplotlib_init()
best_focus = foc. calculate_best_focus_from_images(image_dir,
                                              #masterdarks_dir=MASTERDARK_DIR,
                                              #masterflats_dir=MASTERFLAT_DIR,
                                              #maskdir=MASK_DIR,
                                              board_ids_to_use=board_ids_to_use,
                                              statsfile=os.path.join(DEFAULT_OUTPUT_DIR,
                                                                     'focusloop_stats.txt')
                                              )

if plot_all:
    for board_id in range(6):
        _ = foc.calculate_best_focus_from_images(image_dir,
                                             #masterdarks_dir=MASTERDARK_DIR,
                                             #masterflats_dir=MASTERFLAT_DIR,
                                             #maskdir=MASK_DIR,
                                             #board_ids_to_use=[board_id],
                                             statsfile=
                                             os.path.join(DEFAULT_OUTPUT_DIR,
                                                          f'focusloop_stats_{board_id}'
                                                          f'.txt')
                                             )

foc.plot_all_detectors_focus(DEFAULT_OUTPUT_DIR)
print()
print(f'Analyzed data from directory: {os.path.basename(image_dir)}')
print(f'Best Focus =  {best_focus}')


#%% Make a set of split 120s master darks
# split up the darks
exptime = 120.0

darkpath = '/home/winter/data/images/master_darks/20230717/'
imgs = glob.glob(darkpath+'*_mef.fits')
print(f'found these images: {imgs}')
image_list = []
# get the darks
for image_path in imgs:
    if Path(image_path).is_symlink():
        image_path = os.readlink(image_path)
    if fits.getval(image_path, 'OBSTYPE') == 'DARK':
        if fits.getval(image_path, 'FILTERID') in ["dark"]:
            if fits.getval(image_path, 'EXPTIME') in [exptime]:
                image_list.append(image_path)
print(f'found these 120s darks: {image_list}')
#%
for image in image_list:
    foc.save_split_images(image, boardids=list(range(6)),
                          output_dir='/home/winter/data/images/master_darks/20230717/')
#% median combine the darks

darkdir = '/home/winter/data/images/master_darks/20230717/20230717/split/'

outputdir = '/home/winter/GIT/winter_utils/data/masterdarks/'



for boardid in [2,0,5,1,3,4]:
    # get all the images and median combine
    darks_boardid = glob.glob(darkdir+f'*_mef_{boardid}.fits')
                    
    stacked_mef_hdulist = quick_combine_images.combine_images(darks_boardid)
    
    outputfile = f'master_dark_boardid_{boardid}_exptime_{int(exptime)}.fits'
    
    outputpath = os.path.join(outputdir, outputfile)
    stacked_mef_hdulist.writeto(outputpath, overwrite=True)

# write the master dark to a single MEF

#%% Use the winterutils methods to make a dark/flat corrected image
config = dict({'image_directory': 'data/images',
               'image_data_link_directory': 'data',
               'image_data_link_name': 'tonight_images.lnk',
               'image_last_taken_link': 'last_image.lnk',
               })
software_path = '/home/winter/GIT/firmware/software/'


def makeSymLink_lastImage(image_path):
    # make a symbolic link to the last image taken: self.lastfilename
    
    last_image_link_path = os.path.join(os.getenv("HOME"), config['image_data_link_directory'],config['image_last_taken_link'])     
    
    
    try:
        os.symlink(image_path, last_image_link_path)
    except FileExistsError:
        print('deleting existing symbolic link to last image taken')
        os.remove(last_image_link_path)
        os.symlink(image_path, last_image_link_path)



def packageMultiExt(frame_array, header_array, outfile):
    '''
    Rob's script to package a bunch of frames into a single multi-extension
    FITS file
    '''
    hdr = fits.Header()
    """
    # add in the mega header from WSP
    if type(self.metadata) is list:
        # assume it's a list of three element tuples that easily can be unpacked into a fits.Card object
        # eg, each element in the list is something like: ("CAMERA", "WINTER", "Camera Used for Observation")
        for cardtuple in self.metadata:
            card = fits.Card(*cardtuple)
            try:
                hdr.append(card)
            except Exception as e:
                self.log(f'could not add {card[0]} to header: {e}')
    elif type(self.metadata) is dict:
        # it's a dictionary of values to add
        for key in self.metadata:
            try:
                hdr[key] = self.metadata[key]
            except Exception as e:
                self.log(f'could not add {key} to header: {e}')
                
    """
    header_hdu = fits.PrimaryHDU(header=hdr)
    hdu_list = fits.HDUList([header_hdu])

    for i in range(len(frame_array)):
        frame = frame_array[i]
        header = header_array[i]
        img_hdu = fits.ImageHDU(frame, header=header)
        hdu_list.append(img_hdu)
    
    hdu_list.writeto(outfile, overwrite = True)

def flattenMultiExt(mef_file, outpath, overwrite = True, postPlot = True):
    
    # expects mef in this order:
        # order = ['sa', 'sb', 'sc', 'pa', 'pb', 'pc']
        # new_order = ['sc', 'sb', 'sa', 'pa', 'pb', 'pc']
    
    
    hdu = fits.open(mef_file)
    padding = 20

    datasec = (np.array(re.split(r'[,:]', hdu[1].header['DATASEC'][1:-1]))).astype(int)
    data = hdu[1].data[datasec[2]:datasec[3],datasec[0]:datasec[1]]

    naxis1 = data.shape[0]
    naxis2 = data.shape[1]

    big_naxis1 = 3 * naxis1 + 2 * padding
    big_naxis2 = 2 * naxis2 + 1 * padding

    mosaic_image = np.zeros((big_naxis1, big_naxis2)) - 1000
    # account for order swap on starboard side
    star_indices = [3,2,1]
    for i in range(3):

        # Starboard
        data = hdu[star_indices[i]].data[datasec[2]:datasec[3],datasec[0]:datasec[1]]
        y0 = i * (naxis1 + padding)
        y1 = y0 + naxis1
        x0 = naxis2 + padding
        x1 = x0 + naxis2
        mosaic_image[y0:y1,x0:x1] = np.rot90(np.rot90(data[:,:]))

        # Port
        data = hdu[i+4].data[datasec[2]:datasec[3],datasec[0]:datasec[1]]
        y0 = i * (naxis1 + padding)
        y1 = y0 + naxis1
        x0 = 0
        x1 = naxis2
        mosaic_image[y0:y1,x0:x1] = data[:,:]
    
    flathdu = fits.PrimaryHDU()
    

    flathdu.data = mosaic_image  
    
    hdr = flathdu.header
    """
    # add in the mega header from WSP
    if type(self.metadata) is list:
        # assume it's a list of three element tuples that easily can be unpacked into a fits.Card object
        # eg, each element in the list is something like: ("CAMERA", "WINTER", "Camera Used for Observation")
        for cardtuple in self.metadata:
            card = fits.Card(*cardtuple)
            try:
                hdr.append(card)
            except Exception as e:
                self.log(f'could not add {card[0]} to header: {e}')
    elif type(self.metadata) is dict:
        # it's a dictionary of values to add
        for key in self.metadata:
            try:
                hdr[key] = self.metadata[key]
            except Exception as e:
                self.log(f'could not add {key} to header: {e}')
    """
    
    filestring = outpath
    flathdu.writeto(filestring, overwrite=overwrite)
    
    # make symbolic link to flattened image for easy plotting
    makeSymLink_lastImage(outpath)
    
    # now post the image to slack
    if postPlot:
        plotterpath = os.path.join(software_path, 'plotLastImg.py')
        postImage_process = subprocess.Popen(args = ['python', plotterpath])
       
 
       
output_directory = os.path.join(os.getenv("HOME"), 'data', 'images', 'quickcal_test')
output_filename = 'WINTERcamera_20230718-114315-114'



mef_output_path = os.path.join(output_directory, output_filename+'_mef.fits')
flatcomposite_output_path = os.path.join(output_directory, output_filename +'_flatcomp.fits')

flattenMultiExt(mef_file = mef_output_path, outpath = flatcomposite_output_path, overwrite = True)
#%%
split_path_list = foc.split_and_calibrate_images(imglist = [mef_output_path],
                               board_ids = list(range(6)),
                               #masterdarks_dir: str | Path = MASTERDARK_DIR,
                               #masterflats_dir: str | Path = MASTERFLAT_DIR,
                               #saturate_value: int = 40000,
                               output_dir = output_directory,
                               )[0]

   
frames  = []
headers = []

for i in range(len(split_path_list)):
    try:
        file = split_path_list[i]
    except Exception as e:
        print(f'could not get image: {e}')
    hdu = fits.open(file)

    header = hdu[0].header

    image  = hdu[0].data
        
        
    frames.append(image)
    headers.append(header)
        
mef_output_path = os.path.join(output_directory, output_filename)+'_cal_mef.fits'
packageMultiExt(frames, headers, mef_output_path)

cal_flatcomposite_output_path = os.path.join(output_directory, output_filename +'_cal_flatcomp.fits')

flattenMultiExt(mef_file = mef_output_path, outpath = cal_flatcomposite_output_path, overwrite = True)