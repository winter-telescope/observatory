#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
The focus loop object class

@author: C. Soto and V. Karambelkar
"""
import os
import glob
from focuser import genstats
from astropy.io import fits
import numpy as np
from plot_curve import *

class Focus_loop:
    
    def __init__(self, filt, config): 
        self.config = config
        self.interval = self.config['focus_loop_param']['micron_interval']
        
        self.pixscale = self.config['focus_loop_param']['pixscale']
        self.filter_range = range(self.config['filt_limits'][filt]['lower'],self.config['filt_limits'][filt]['upper']+self.interval,self.interval)
        
        self.path = self.config['focus_loop_param']['recent_path']

        self.med_fwhms = []
        self.std_fwhms = []
    def analyze_img_focus(self, imgname):
        mean, med, std = genstats.get_img_fwhm(imgname, self.pixscale,exclude = False)
        self.med_fwhm = med*self.pixscale
        self.std_fwhm = std*self.pixscale
        return med
    
    def rate_imgs(self,imglist):
        #Create grading list
        medlist = []
        
        for imgname in imglist:
            medlist.append(self.analyze_img_focus(imgname = imgname))
        
        return medlist
    
    def return_Range(self):
        return self.filter_range

    def return_Path(self):
        real_path = os.readlink(self.path)
        return real_path   

    def get_Recent_File(self):
        list_of_files = glob.glob(self.path)
        return max(list_of_files, key=os.path.getctime)
    '''
    def fits_64_to_16(self, images, filter_range):
        images_16 = []
        try:
            for index in range(0, len(images)):
                64_file = fits.open(images[index])
                data = 64_file[0].data
                head = 64_file[0].header
                
                try:
                    filename = '/home/winter/data/images/focusing/' + head['FILENAME']
                    
                except Exception as e:
                    msg = 'Error in header format, saving with temporary filename'
                    print(msg)
                    filename = '/home/winter/data/images/focusing/' + filter_range[index] + '.fits'
                    pass
                
                fits.writeto(filename, data.astype(np.int16))
        
        except Exception as e:
            msg = f'wintercmd: Focuser could not convert images due to {e.__class__.__name__}, {e}'
            print(msg)
            
        return images_16
    '''
    def plot(self):
        
        filter_range = np.array(self.filter_range)
        med_fwhm = np.array(self.med_fwhms)
        std_fwhm = np.array(self.std_fwhms)
        
        curve = fit_Curve()
        popt = plot_curve.fit_parabola(filter_range, med_fwhms, std_fwhms)
        
        plt.figure()
		plt.errorbar(focus_vals,fwhms,yerr=stds,fmt='.',c='red')
		plotfoc = np.linspace(np.min(focus_vals),np.max(focus_vals),20)
		print(popt)
		plt.plot(plotfoc,parabola(plotfoc,popt[0],popt[1],popt[2]))
		plt.title('Best FWHM : %.1f arcsec'%(np.min(fwhms)))
		plt.savefig('focusloop.pdf',bbox_inches='tight')
        
        return popt
        
        
        
        
        
