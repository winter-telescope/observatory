#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
The focus loop object class

@author: C. Soto and V. Karambelkar
"""
import os
import glob
from astropy.io import fits
import numpy as np
#import matplotlib.pyplot as plt
#import numpy as np
import pandas as pd
#from scipy.optimize import curve_fit
import yaml
import subprocess
import sys
from datetime import datetime
import traceback


# add the wsp directory to the PATH
wsp_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),'wsp')
# switch to this when ported to wsp
#wsp_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

sys.path.insert(1, wsp_path)
print(f'focusing: wsp_path = {wsp_path}')
from alerts import alert_handler
from focuser import plot_curve
from focuser import genstats




class Focus_loop_v2:
    
    def __init__(self, config, nom_focus, total_throw, nsteps, pixscale): 
        """
        INPUTS:
            nom_focus:      nominal focus position in microns
            total_throw:    total focus throw over which to probe focus
            nsteps:         number of images to take/how many points along throw (foc_range) to examine
            pixscale:       pixel plate scale (width) in arcseconds
    
        """
        self.config = config
        self.pixscale = pixscale
        
        #self.filter_range = range(self.config['filt_limits'][filt]['lower'],self.config['filt_limits'][filt]['upper']+self.interval,self.interval)
        self.filter_range_nom = np.linspace(nom_focus - total_throw/2, nom_focus + total_throw/2, nsteps)
        
        #self.path = self.config['focus_loop_param']['recent_path']
        self.filter_range = []
        self.med_fwhms = []
        self.std_fwhms = []
        
    def analyzeData(self, filterpos_list, imglist):
        self.filter_range = filterpos_list
        self.rate_images(imglist)
        
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
        
    """
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
                    msg = f'Error in header format: {e}, saving with temporary filename'
                    print(msg)
                    filename = '/home/winter/data/images/focusing/' + filter_range[index] + '.fits'
                    pass
                
                fits.writeto(filename, data.astype(np.int16))
        
        except Exception as e:
            msg = f'wintercmd: Focuser could not convert images due to {e.__class__.__name__}, {e}'
            print(msg)
            
        return images_16
    """
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
        
        popt, pcov = plot_curve.fit_parabola(filter_range, med_fwhms, std_fwhms)
        # note here that popt are the fit parameters of the parabola: y = A + B*(x-x0)**2
        # so the center of the parabola is x0 = popt[2]
        
        
        
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
        
        return popt, pcov
        #return list(plotfoc), list(plot_curve.parabola(plotfoc,popt[0],popt[1],popt[2]))
        

if __name__ == '__main__':
    # test area
    
    config = yaml.load(open(wsp_path + '/config/config.yaml'), Loader = yaml.FullLoader)
    
    loop = Focus_loop_v2(config, nom_focus = 10000, total_throw = 300, nsteps = 5, pixscale = 0.466)

    
    image_log_path = config['focus_loop_param']['image_log_path']

    focuser_pos = np.linspace(9000, 11150, 7)
    images = ['/home/winter/data/images/20210730/SUMMER_20210729_225354_Camera0.fits',
              '/home/winter/data/images/20210730/SUMMER_20210729_225417_Camera0.fits',
              '/home/winter/data/images/20210730/SUMMER_20210729_225438_Camera0.fits',
              '/home/winter/data/images/20210730/SUMMER_20210729_225500_Camera0.fits',
              '/home/winter/data/images/20210730/SUMMER_20210729_225521_Camera0.fits',
              '/home/winter/data/images/20210730/SUMMER_20210729_225542_Camera0.fits',
              '/home/winter/data/images/20210730/SUMMER_20210729_225604_Camera0.fits']
        
        
     # save the data to a csv for later access
    try:
        data = {'images': images, 'focuser_pos' : list(focuser_pos)}
        df = pd.DataFrame(data)
        df.to_csv(image_log_path + 'focusLoop_' + str(datetime.utcnow().timestamp()) + '.csv')
    
    except Exception as e:
        msg = f'Unable to save files to focus csv due to {e.__class__.__name__}, {e}'
        print(msg)
    
    
    system = 'focuser'
    # fit the data and find the best focus
    try:
        
        
        # now analyze the data (rate the images and load the observed filterpositions)
        loop.analyzeData(focuser_pos, images)
        
        xvals, yvals = loop.plot_focus_curve(plotting = True)
        focuser_pos_best = xvals[yvals.index(min(yvals))]
        print(f'Focuser_going to final position at {focuser_pos_best} microns')
        

    except FileNotFoundError as e:
        print(f"You are trying to modify a catalog file or an image with no stars , {e}")
        pass

    except Exception as e:
        msg = f'could not run focus loop due due to {e.__class__.__name__}, {e}, traceback = {traceback.format_exc()}'
        print(msg)
        

    # now print the best fit focus to the slack
    try:        
        focus_plot = '/home/winter/data/plots_focuser/latest_focusloop.jpg'
        
        auth_config_file  = wsp_path + '/credentials/authentication.yaml'
        user_config_file = wsp_path + '/credentials/alert_list.yaml'
        alert_config_file = wsp_path + '/config/alert_config.yaml'

        auth_config  = yaml.load(open(auth_config_file) , Loader = yaml.FullLoader)
        user_config = yaml.load(open(user_config_file), Loader = yaml.FullLoader)
        alert_config = yaml.load(open(alert_config_file), Loader = yaml.FullLoader)

        alertHandler = alert_handler.AlertHandler(user_config, alert_config, auth_config)
    
        focus_plot = '/home/winter/data/plots_focuser/latest_focusloop.jpg'
        alertHandler.slack_postImage(focus_plot)
        
        
        
    
    except Exception as e:
        msg = f'wintercmd: Unable to post focus graph to slack due to {e.__class__.__name__}, {e}'
        print(msg)
    
    
