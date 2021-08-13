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
from focuser import plot_curve
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.optimize import curve_fit
import subprocess

class Focus_loop:
    
    def __init__(self, filt, config, fine): 
        self.config = config
        self.interval = self.config['focus_loop_param']['micron_interval']
        if fine:
            self.interval = self.config['focus_loop_param']['fine_micron_interval']
        
        self.pixscale = self.config['focus_loop_param']['pixscale']
        
        self.filter_range = range(self.config['filt_limits'][filt]['lower'],self.config['filt_limits'][filt]['upper']+self.interval,self.interval)
        
        self.path = self.config['focus_loop_param']['recent_path']

        self.med_fwhms = []
        self.std_fwhms = []
    def analyze_img_focus(self, imgname):
        mean, med, std = genstats.get_img_fwhm(imgname, self.pixscale,exclude = False)
        return med, std
    
    def rate_images(self,imglist):
        #Create grading list
        medlist = []
        stdlist = []

        for imgname in imglist:
            med, std = self.analyze_img_focus(imgname = imgname)
            if self.nantest(med):
                medlist.append(0)
            else:
                medlist.append(med*self.pixscale)
            if self.nantest(std):
                stdlist.append(0)
            else:
                stdlist.append(std*self.pixscale)

        self.med_fwhms = medlist
        self.std_fwhms = stdlist
        
        return medlist
    
    def nantest(self, value):
        return np.isnan([value])[0]
        
    def return_Range(self):
        return self.filter_range

    def return_Path(self):
        real_path = os.readlink(self.path)
        return real_path   

    def get_Recent_File(self):
        list_of_files = glob.glob(self.path)
        return max(list_of_files, key=os.path.getctime)
    
    def fits_64_to_16(self, images, filter_range):
        images_16 = []
        try:
            for index in range(0, len(images)):
                sf_file = fits.open(images[index])
                data = sf_file[0].data
                head = sf_file[0].header
                
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
    
    def plot_focus_curve(self, plotting):
        filter_range = np.array(self.filter_range)
        med_fwhms = np.array(self.med_fwhms)
        std_fwhms = np.array(self.std_fwhms)
        
        popt = plot_curve.fit_parabola(filter_range, med_fwhms, std_fwhms)
        
        plotfoc = np.linspace(np.min(filter_range),np.max(filter_range),20)
        
        if plotting:
            data = {'x':list(plotfoc), 'y':list(plot_curve.parabola(plotfoc,popt[0],popt[1],popt[2]))}
            df = pd.DataFrame(data)
            path = '/home/winter/data/df_focuser/x_y.csv'
            df.to_csv(path)
            
            data = {'med_fwhms': list(med_fwhms), 'std_fwhms':list(std_fwhms)}
            df = pd.DataFrame(data)
            path = '/home/winter/data/df_focuser/fwhm.csv'
            df.to_csv(path)
            
            data = {'filter_range': list(filter_range)}
            df = pd.DataFrame(data)
            path = '/home/winter/data/df_focuser/filter_range.csv'
            df.to_csv(path)
        
            args = ['python', 'plot_support.py', '--p','/home/winter/data/df_focuser/']
            process = subprocess.call(args)
        
        #pid = process.pid
        
        
        return list(plotfoc), list(plot_curve.parabola(plotfoc,popt[0],popt[1],popt[2]))
        
        
        
        
        
