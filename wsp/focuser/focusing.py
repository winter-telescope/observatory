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
import matplotlib.pyplot as plt
#import numpy as np
import pandas as pd
#from scipy.optimize import curve_fit
import yaml
import subprocess
import sys
from datetime import datetime
import traceback
import pytz
from scipy.optimize import curve_fit

# add the wsp directory to the PATH
wsp_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),'wsp')
# switch to this when ported to wsp
#wsp_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

sys.path.insert(1, wsp_path)
print(f'focusing: wsp_path = {wsp_path}')
from alerts import alert_handler
from focuser import plot_curve
from focuser import genstats




class Focus_loop_v3:
    """
    # this is the 2-step version of the focus loop which handles the V-curve focus loop
    
    it is called like this in roboOperator.do_focusLoop:
        
        x0_fit, x0_err = loop.analyzeData(focuser_pos, images)
    
    """
    def __init__(self, config, nom_focus, total_throw, nsteps, pixscale):
        
        self.config = config
        self.nom_focus = nom_focus
        self.total_throw = total_throw
        self.nsteps = nsteps
        self.pixscale = pixscale
        self.filter_range_nom = np.linspace(nom_focus - total_throw/2, nom_focus + total_throw/2, nsteps)
        
        self.fitresults = dict()
    
    def analyzeData(self, filterpos_list, imglist, do_parabola = True):
        """
        Takes in list of filter position and image paths
        outputs the best focus position and an estimate of the std error of that position
        """
        # first analyze the images
        self.rate_images(imglist)
        
        # now fit the v-curve to the data
        cond = (self.HFD_med > 2)
        self.pos_vcurve = self.pos[cond]
        self.HFD_med_vcurve = self.HFD_med[cond]
        self.HFD_med_stderr_vcurve = self.HFD_med_stderr[cond]
        
        ml0 = -0.01
        xc0 = self.nom_focus
        delta0 = 286
        y00 = max(HFD_med_vcurve)#HFD_med[0]
        
        popt, pcov = plot_curve.Fit_FocV(self.pos_vcurve, self.HFD_med_vcurve, self.HFD_med_stderr_vcurve, ml = ml0, xc = xc0, delta = delta0, y0 = y00)
        
        self.mlfit = popt[0]
        self.xcfit_vcurve = popt[1]
        self.deltafit = popt[2]
        self.y0fit = popt[3]
        
        perr = np.sqrt(np.diag(pcov))
        self.xcfit_vcurve_err = perr[1]
        
        # make a curve to save for later plotting and get the start and stop of the v (xa, xb)
        self.vcurve_fit_x = np.linspace(min(pos_vcurve), max(pos_vcurve), 1000)
        self.vcurve_fit_y, self.xafit, self.xbfit, xcfit = plot_curve.FocV(self.vcurve_fit_x, self.mlfit, self.xcvit_vcurve, self.deltafit, self.y0fit, return_x = True)
        
        # update the fit results for the v-curve fit
        self.fitresults.update({'vcurve_fit':
                                {'param':
                                     {'ml' : self.mlfit,
                                      'xc' : self.xcfit_vcurve,
                                      'xc_err' : self.xcfit_vcurve_err,
                                      'y0' : self.y0fit,
                                      'xa' : self.xafit,
                                      'xb' : self.xbfit},
                                 'fit_data':
                                     {'x' : self.vcurve_fit_x,
                                      'y' : self.vcurve_fit_y},
                                 'raw_data':
                                     {'x' : self.pos_vcurve,
                                      'y' : self.HFD_med_vcurve,
                                      'yerr': self.HFD_med_stderr_vcurve}
                                     }
                                    })
        
        # now try to fit a parabola to the data within the linear region based on the v-curve results
        
        
    
    def rate_images(self, imglist):
        focuser_pos_good = []
        images_good = []
        HFD_mean = []
        HFD_med = []
        HFD_std = []
        HFD_stderr_mean = []
        HFD_stderr_med = []
        FWHM_mean = []
        FWHM_med = []
        FWHM_std = []
        for i in range(len(imglist)):#image in images:
            image = images[i]
            focus = focuser_pos[i]
            try:
                #mean, median, std, stderr_mean, stderr_med
                mean, median, std, stderr_mean, stderr_med = genstats.get_img_fluxdiameter(image, pixscale = self.pixscale, 
                                                                                           exclude = False)
                mean_fwhm, med_fwhm, std_fwhm = genstats.get_img_fwhm(image, pixscale = self.pixscale, 
                                                                                           exclude = False)
                focuser_pos_good.append(focus)
                images_good.append(image)
                
                HFD_mean.append(mean*pixscale)
                HFD_med.append(median*pixscale)
                HFD_std.append(std*pixscale)
                HFD_stderr_mean.append(stderr_mean*self.pixscale)
                HFD_stderr_med.append(stderr_med*self.pixscale)
                
                FWHM_mean.append(mean_fwhm*self.pixscale)
                FWHM_med.append(med_fwhm*self.pixscale)
                FWHM_std.append(std_fwhm*self.pixscale)
                
            except Exception as e:
                print(f'could not analyze image {image}: {e}')
                
        self.pos = np.array(focuser_pos_good)
        self.images = np.array(images_good)
        self.HFD_mean = np.array(HFD_mean)
        self.HFD_med = np.array(HFD_med)
        self.HFD_std = np.array(HFD_std)
        self.HFD_stderr_mean = np.array(HFD_stderr_mean)
        self.HFD_stderr_med = np.array(HFD_stderr_med)
        self.FWHM_mean = np.array(self.FWHM_mean)
        self.FWHM_med = np.array(self.FWHM_med)
        self.FWHM_std = np.array(self.FWHM_std)
        
    def plot_focus_curve(self, plotting, timestamp_utc = None):
        
        pass
        
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
        
        popt, pcov = plot_curve.fit_parabola(self.filter_range, self.med_fwhms, self.std_fwhms)
        
        perr = np.sqrt(np.diag(pcov))
        x0_fit = popt[0]
        x0_err = perr[0]
        
        return x0_fit, x0_err
        
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

    def plot_focus_curve(self, plotting, timestamp_utc = None):
        filter_range = np.array(self.filter_range)
        med_fwhms = np.array(self.med_fwhms)
        std_fwhms = np.array(self.std_fwhms)
        
        popt, pcov = plot_curve.fit_parabola(filter_range, med_fwhms, std_fwhms)
        
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
            if timestamp_utc is None:
                args = ['python', os.path.join(wsp_path, 'focuser','plot_support.py'), '--p','/home/winter/data/df_focuser/']
            
            else:
                args = ['python', os.path.join(wsp_path, 'focuser','plot_support.py'), '--p','/home/winter/data/df_focuser/', '--t', str(timestamp_utc)]
                print(f'args = {args}')
            process = subprocess.call(args)
        
        #pid = process.pid
        
        
        #return list(plotfoc), list(plot_curve.parabola(plotfoc,popt[0],popt[1],popt[2]))








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
    pixscale = 0.466
    loop = Focus_loop_v3(config, nom_focus = 10000, total_throw = 300, nsteps = 5, pixscale = pixscale)

    
    image_log_path = config['focus_loop_param']['image_log_path']
    """
    focuser_pos = np.linspace(9000, 11150, 7)
    images = ['/home/winter/data/images/20210730/SUMMER_20210729_225354_Camera0.fits',
              '/home/winter/data/images/20210730/SUMMER_20210729_225417_Camera0.fits',
              '/home/winter/data/images/20210730/SUMMER_20210729_225438_Camera0.fits',
              '/home/winter/data/images/20210730/SUMMER_20210729_225500_Camera0.fits',
              '/home/winter/data/images/20210730/SUMMER_20210729_225521_Camera0.fits',
              '/home/winter/data/images/20210730/SUMMER_20210729_225542_Camera0.fits',
              '/home/winter/data/images/20210730/SUMMER_20210729_225604_Camera0.fits']
        
    """
    """
    #u-band results, off by a bit
     [1] Focuser Pos: 9650.0, /home/winter/data/images/20220119/SUMMER_20220119_214924_Camera0.fits
     [2] Focuser Pos: 9775.0, /home/winter/data/images/20220119/SUMMER_20220119_215022_Camera0.fits
     [3] Focuser Pos: 9900.0, /home/winter/data/images/20220119/SUMMER_20220119_215120_Camera0.fits
     [4] Focuser Pos: 10025.0, /home/winter/data/images/20220119/SUMMER_20220119_215217_Camera0.fits
     [5] Focuser Pos: 10150.0, /home/winter/data/images/20220119/SUMMER_20220119_215314_Camera0.fits
     
     # u-band results on second attempt:
     FOCUS LOOP DATA:
     [1] Focuser Pos: 9761.414819232772, /home/winter/data/images/20220119/SUMMER_20220119_221347_Camera0.fits
     [2] Focuser Pos: 9861.414819232772, /home/winter/data/images/20220119/SUMMER_20220119_221444_Camera0.fits
     [3] Focuser Pos: 9961.414819232772, /home/winter/data/images/20220119/SUMMER_20220119_221541_Camera0.fits
     [4] Focuser Pos: 10061.414819232772, /home/winter/data/images/20220119/SUMMER_20220119_221641_Camera0.fits
     [5] Focuser Pos: 10161.414819232772, /home/winter/data/images/20220119/SUMMER_20220119_221741_Camera0.fits
     
     # r-band results on second attempt
      [1] Focuser Pos: 9771.63951636189, /home/winter/data/images/20220119/SUMMER_20220119_220748_Camera0.fits
     [2] Focuser Pos: 9871.63951636189, /home/winter/data/images/20220119/SUMMER_20220119_220848_Camera0.fits
     [3] Focuser Pos: 9971.63951636189, /home/winter/data/images/20220119/SUMMER_20220119_220943_Camera0.fits
     [4] Focuser Pos: 10071.63951636189, /home/winter/data/images/20220119/SUMMER_20220119_221041_Camera0.fits
     [5] Focuser Pos: 10171.63951636189, /home/winter/data/images/20220119/SUMMER_20220119_221141_Camera0.fits


    """
    focuser_pos = [9761.414819232772, 9861.414819232772, 9961.414819232772, 10061.414819232772, 10161.414819232772]
    images = ['/home/winter/data/images/20220119/SUMMER_20220119_221347_Camera0.fits',
              '/home/winter/data/images/20220119/SUMMER_20220119_221444_Camera0.fits',
              '/home/winter/data/images/20220119/SUMMER_20220119_221541_Camera0.fits',
              '/home/winter/data/images/20220119/SUMMER_20220119_221641_Camera0.fits',
              '/home/winter/data/images/20220119/SUMMER_20220119_221741_Camera0.fits']
    
    
    """
     # save the data to a csv for later access
    try:
        data = {'images': images, 'focuser_pos' : list(focuser_pos)}
        df = pd.DataFrame(data)
        df.to_csv(image_log_path + 'focusLoop_' + str(datetime.utcnow().timestamp()) + '.csv')
    
    except Exception as e:
        msg = f'Unable to save files to focus csv due to {e.__class__.__name__}, {e}'
        print(msg)
    """
    
    system = 'focuser'
    # fit the data and find the best focus
    try:
        
        
        # now analyze the data (rate the images and load the observed filterpositions)
        #loop.analyzeData(focuser_pos, images)
        # now analyze the data (rate the images and load the observed filterpositions)
        x0_fit, x0_err = loop.analyzeData(focuser_pos, images)
        timestamp_utc = datetime.now(tz = pytz.utc).timestamp()
        loop.plot_focus_curve(plotting = True, timestamp_utc = timestamp_utc)
        #xvals, yvals = loop.plot_focus_curve(plotting = True)
        #focuser_pos_best = xvals[yvals.index(min(yvals))]
        focuser_pos_best = x0_fit
        print(f'Focuser_going to final position at {focuser_pos_best} microns')
        

    except FileNotFoundError as e:
        print(f"You are trying to modify a catalog file or an image with no stars , {e}")
        pass

    except Exception as e:
        msg = f'could not run focus loop due due to {e.__class__.__name__}, {e}, traceback = {traceback.format_exc()}'
        print(msg)
    
    """
    # Try something else
    
    HFD_mean = []
    HFD_med = []
    HFD_std = []
    HFD_stderr_mean = []
    HFD_stderr_med = []
    
    
    for image in images:
        try:
            #mean, median, std, stderr_mean, stderr_med
            mean, median, std, stderr_mean, stderr_med = genstats.get_img_fluxdiameter(image, 0.466, exclude = False)
            HFD_mean.append(mean*pixscale)
            HFD_med.append(median*pixscale)
            HFD_std.append(std*pixscale)
            HFD_stderr_mean.append(stderr_mean*pixscale)
            HFD_stderr_med.append(stderr_med*pixscale)
        except Exception as e:
            print(f'could not analyze image {image}: {e}')
    plt.figure()
    #plt.plot(focuser_pos, HFD_meds, 'ks')
    plt.errorbar(focuser_pos, HFD_med, yerr = HFD_stderr_med, capsize = 5, fmt = 'ks', label = 'Median')
    plt.errorbar(focuser_pos, HFD_mean, yerr = HFD_stderr_mean, capsize = 5, fmt = 'ro', label = 'Mean')
    plt.legend()
    plt.xlabel('Focuser Position [micron]')
    plt.ylabel('Half-Focus Diameter [arcseconds]')
    
    # F
    """
    