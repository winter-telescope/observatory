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
import pandas as pd
import yaml
import subprocess
import sys
from datetime import datetime
import traceback
import pytz
from scipy.optimize import curve_fit
import pathlib
import json

# add the wsp directory to the PATH
wsp_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),'wsp')
# switch to this when ported to wsp
#wsp_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

sys.path.insert(1, wsp_path)
print(f'focusing: wsp_path = {wsp_path}')
from alerts import alert_handler
from focuser import plot_curve
from focuser import genstats
from utils import utils



class Focus_loop_v3:
    """
    # this is the 2-step version of the focus loop which handles the V-curve focus loop
    
    it is called like this in roboOperator.do_focusLoop:
        
        x0_fit, x0_err = loop.analyzeData(focuser_pos, images)
    
    """
    def __init__(self, config, nom_focus, total_throw, nsteps, pixscale, state = {}):
        
        self.config = config
        self.state = state
        self.nom_focus = nom_focus
        self.total_throw = total_throw
        self.nsteps = nsteps
        self.pixscale = pixscale
        if nom_focus is None:
            self.filter_range_nom = None
        else:
            self.filter_range_nom = np.linspace(nom_focus - total_throw/2, nom_focus + total_throw/2, nsteps)
        self.filter_range = self.filter_range_nom
        self.fitresults = dict()
    
    def analyzeData(self, filterpos_list, imglist, do_parabola = True):
        """
        Takes in list of filter position and image paths
        outputs the best focus position and an estimate of the std error of that position
        """
        self.filter_range = filterpos_list
        self.imglist = imglist
        
        # first analyze the images
        self.rate_images(self.imglist)
        
        
        
        ####### DO THE V-CURVE FIT TO THE HFD #######
        cond = (self.HFD_med > 1) & (self.HFD_med < 6)
        self.images_vcurve = self.images[cond]
        self.pos_vcurve = self.pos[cond]
        self.HFD_med_vcurve = self.HFD_med[cond]
        self.HFD_stderr_med_vcurve = self.HFD_stderr_med[cond]
        
        ml0 = -0.01
        if self.nom_focus is None:
            xc0 = self.pos_vcurve[np.argmin(self.HFD_med_vcurve)]
            
        else:
            xc0 = self.nom_focus
        delta0 = 286
        y00 = max(self.HFD_med_vcurve)#HFD_med[0]
        print()
        print(f'y00 = {y00}')
        print()
        popt, pcov = plot_curve.Fit_FocV(self.pos_vcurve, self.HFD_med_vcurve, self.HFD_stderr_med_vcurve, ml = ml0, xc = xc0, delta = delta0, y0 = y00)

        
        self.mlfit = popt[0]
        self.xcfit_vcurve = popt[1]
        self.deltafit = popt[2]
        self.y0fit = popt[3]
        
        print('V-Curve Fit Results:')
        print(f'    ml = {self.mlfit}')
        print(f'    xc = {self.xcfit_vcurve}')
        print(f'    delta = {self.deltafit}')
        print(f'    y0 = {self.y0fit}')
        print()
        perr = np.sqrt(np.diag(pcov))
        self.xcfit_vcurve_err = perr[1]
        
        # make a curve to save for later plotting and get the start and stop of the v (xa, xb)
        #self.vcurve_fit_x = np.linspace(min(self.pos_vcurve), max(self.pos_vcurve), 1000)
        self.vcurve_fit_x = np.linspace(9500, 10500, 1000)
        self.vcurve_fit_y, self.xafit, self.xbfit, xcfit = plot_curve.FocV(self.vcurve_fit_x, self.mlfit, self.xcfit_vcurve, self.deltafit, self.y0fit, return_x = True)
        
        
        ####### NOW DO THE FOLLOW-UP PARABOLIC FIT TO THE FWHM #######
        
        cond = (self.FWHM_med > 0) #& (self.pos > self.xafit) & (self.pos < (self.xbfit))  # & (self.FWHM_med < 7) #& (self.HFD_med < 6) # changed from FWHM>1.5
        self.pos_parabola = self.pos[cond]
        self.FWHM_med_parabola = self.FWHM_med[cond]
        self.FWHM_std_parabola = self.FWHM_std[cond]
        self.images_parabola = self.images[cond]
        """
        print(self.pos_parabola)
        popt, pcov = plot_curve.fit_parabola(self.pos_parabola, self.FWHM_med_parabola, stds = None)
        
        #arabola(x,x0,A,B):
        self.xc_parfit = popt[0]
        self.A_parfit = popt[1]
        self.B_parfit = popt[2]
        
        perr = np.sqrt(np.diag(pcov))
        self.xc_parfit_err = perr[0]
        
        # get the FWHM at the parabola min
        self.FWHM_at_xc = plot_curve.parabola(x = self.xc_parfit, x0 = self.xc_parfit, A = self.A_parfit, B = self.B_parfit)
        
        # now make the fit data
        #def parabola(x,x0,A,B):
        #return A + B*(x-x0)**2
        self.parfit_fit_x = np.linspace(min(self.pos_parabola), max(self.pos_parabola), 1000)
        self.parfit_fit_y = plot_curve.parabola(x = self.parfit_fit_x, x0 = self.xc_parfit, A = self.A_parfit, B = self.B_parfit)
        
        print()
        print(f'parabola: y = {self.A_parfit:.1f} + {self.B_parfit:.1f}*(x-{self.xc_parfit:.1f})**2') 
        print(f'parabola: x0 = [{self.xc_parfit:.1f} +/- {self.xc_parfit_err:.1f}] ({(100*self.xc_parfit_err/self.xc_parfit):.0f}%)')
        print()
        
        # get the difference between the two fits and use this as a measure for the error
        self.delta_xc = np.abs(self.xcfit_vcurve - self.xc_parfit)
        
        """
        
        # update the fit results for the v-curve fit
        self.fitresults.update({'telemetry':
                                    {'camera' : 'SUMMER',
                                     'filtername' : utils.getFromFITSHeader(self.imglist[0], 'FILTER'),
                                     'filterID' : utils.getFromFITSHeader(self.imglist[0], 'FILTERID'),
                                     'filterPos' : utils.getFromFITSHeader(self.imglist[0], 'FILPOS'),
                                     'az' : utils.getFromFITSHeader(self.imglist[0], 'AZIMUTH'),
                                     'alt' : utils.getFromFITSHeader(self.imglist[0], 'ALTITUDE'),
                                     'ra' : utils.getFromFITSHeader(self.imglist[0], 'TELRA'),
                                     'dec' : utils.getFromFITSHeader(self.imglist[0], 'TELDEC'),
                                     'AIRMASS' : utils.getFromFITSHeader(self.imglist[0], 'AIRMASS')},
                                'results':
                                    {'focus': self.xcfit_vcurve,
                                     #'focus_err': self.delta_xc,
                                     'time_utc_iso': utils.getFromFITSHeader(self.imglist[0], 'UTCISO')},
                                'raw_data':
                                    {'positions' : filterpos_list,
                                     'images': imglist},
                                'vcurve_fit':
                                    {'param':
                                         {'ml' : self.mlfit,
                                          'xc_initial_guess' : self.nom_focus,
                                          'xc' : self.xcfit_vcurve,
                                          'xc_err' : self.xcfit_vcurve_err,
                                          'delta' : self.deltafit,
                                          'y0' : self.y0fit,
                                          'xa' : self.xafit,
                                          'xb' : self.xbfit},
                                     'raw_data':
                                         {'x' : list(self.pos_vcurve),
                                          'y' : list(self.HFD_med_vcurve),
                                          'yerr': list(self.HFD_stderr_med_vcurve),
                                          'images': list(self.images_vcurve)}
                                         },
                                'fwhm':
                                    {'raw_data':
                                        {'x' : list(self.pos_parabola),
                                         'y' : list(self.FWHM_med_parabola),
                                         'yerr': list(self.FWHM_std_parabola),
                                         'images': list(self.images_parabola)},
                                    },
                                """
                                'parabolic_fit':
                                    {'param':
                                         {'xc' : self.xc_parfit,
                                          'xc_err' : self.xc_parfit_err,
                                          'A' : self.A_parfit,
                                          'B' : self.B_parfit,
                                          'FWHM_at_xc' : self.FWHM_at_xc},
                                     'raw_data':
                                         {'x' : list(self.pos_parabola),
                                          'y' : list(self.FWHM_med_parabola),
                                          'yerr': list(self.FWHM_std_parabola),
                                          'images': list(self.images_parabola)}},
                                """
                                'temperatures':
                                    {'m1' : self.state.get('telescope_temp_m1', None),
                                     'm2' : self.state.get('telescope_temp_m2', None),
                                     'm3' : self.state.get('telescope_temp_m1', None),
                                     'telescope_ambient' : self.state.get('telescope_temp_ambient', None),
                                     'outside_pcs' : self.state.get('T_outside_pcs', None)},
                                        })
        
        # now try to fit a parabola to the data within the linear region based on the v-curve results
        
        x0_fit = self.xcfit_vcurve
        #x0_diff = abs(self.nom_focus - x0_fit)
        #x0_err = self.delta_xc
            
        #self.save_focus_data()
        
        #return x0_fit, x0_err
        return x0_fit
    
    def analyze_best_focus_image(self, best_focus_image):
        
        try:
            mean, median, std, stderr_mean, stderr_med = genstats.get_img_fluxdiameter(best_focus_image, pixscale = self.pixscale, 
                                                                                       exclude = False)
            mean_fwhm, med_fwhm, std_fwhm = genstats.get_img_fwhm(best_focus_image, pixscale = self.pixscale, 
                                                                                       exclude = False)
            print(f'type(mean_fwhm) = {type(mean_fwhm)}, mean_fwhm = {mean_fwhm}')
            # now add the info to the focus data dictionary
            self.fitresults.update({'best_focus_image': 
                                        {'hfd' : 
                                             {'mean'    : mean*self.pixscale,
                                              'med'     : median*self.pixscale,
                                              'std'     : std*self.pixscale,
                                              'stderr_mean'     : stderr_mean*self.pixscale,
                                              'stderr_med'      : stderr_med*self.pixscale,
                                              },
                                         'fwhm' : 
                                             {'mean'    : float(mean_fwhm*self.pixscale),
                                              'med'     : float(med_fwhm*self.pixscale),
                                              'std'     : float(std_fwhm*self.pixscale),
                                              },
                                         'image' : best_focus_image,
                                         },
                                    })
                
        except Exception as e:
                print(f'could not analyze image {best_focus_image}: {e}')
        
        
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
            image = imglist[i]
            #focus = focuser_pos[i]
            focus = self.filter_range[i]
            try:
                #mean, median, std, stderr_mean, stderr_med
                mean, median, std, stderr_mean, stderr_med = genstats.get_img_fluxdiameter(image, pixscale = self.pixscale, 
                                                                                           exclude = False)
                mean_fwhm, med_fwhm, std_fwhm = genstats.get_img_fwhm(image, pixscale = self.pixscale, 
                                                                                           exclude = False)
                focuser_pos_good.append(focus)
                images_good.append(image)
                
                HFD_mean.append(mean*self.pixscale)
                HFD_med.append(median*self.pixscale)
                HFD_std.append(std*self.pixscale)
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
        self.FWHM_mean = np.array(FWHM_mean)
        self.FWHM_med = np.array(FWHM_med)
        self.FWHM_std = np.array(FWHM_std)
        
        
        
    def save_focus_data(self):
        
        # dump the fit results to a json file
        
        results_parent_dir = os.path.join(os.getenv("HOME"),self.config['focus_loop_param']['results_log_parent_dir'])
        results_log_dir = os.path.join(results_parent_dir, self.config['focus_loop_param']['results_log_dir'])
        results_log_last_link = os.path.join(results_parent_dir, self.config['focus_loop_param']['results_log_last_link'])
        #results_plot_last_link = os.path.join(results_parent_dir, self.config['focus_loop_param']['results_plot_last_link'])
        
        #TODO: replace this with a more sensible naming system...
        #starttime_string = self.images[0].split('/')[-1].split('.fits')[0].strip('_Camera0')
        starttime_string = utils.getFromFITSHeader(self.imglist[0], 'UTC').split('.')[0]
        self.results_filepath = os.path.join(results_log_dir, f'focusResults_{starttime_string}.json')
        
        # create the data directory if it doesn't exist already
        pathlib.Path(results_parent_dir).mkdir(parents = True, exist_ok = True)
        print(f'focusLoop: making directory: {results_parent_dir}')
                
        # create the data link directory if it doesn't exist already
        pathlib.Path(results_log_dir).mkdir(parents = True, exist_ok = True)
        print(f'focusLoop: making directory: {results_log_dir}')

        with open(self.results_filepath, 'w+') as file:
            #yaml.dump(self.triglog, file)#, default_flow_style = False)
            json.dump(self.fitresults, file)
        
        # make the symbolic link to the last results data file
        print(f'focusLoop: trying to create link at {results_log_last_link}')
        
        try:
            os.symlink(self.results_filepath, results_log_last_link)
        except FileExistsError:
            print('focusLoop: deleting existing symbolic link')
            os.remove(results_log_last_link)
            os.symlink(self.results_filepath, results_log_last_link)
        
    
    def plot_focus_curve(self, timestamp_utc = None, best_focus_image_filepath = None):
        
        #path = '/home/winter/data/df_focuser/filter_range.csv'
        path = self.results_filepath
        args = ['python', os.path.join(wsp_path, 'focuser','vcurve_plot_support.py'), '--p',path]
        if timestamp_utc is None:
            pass
        
        else:
            args = args + ['--t', str(timestamp_utc)]
            
        if best_focus_image_filepath is None:
            pass
        else:
            args = args + ['--focus_image', best_focus_image_filepath]
            
        print(f'args = {args}')
        process = subprocess.call(args)
        


if __name__ == '__main__':
    # test area
    
    config = yaml.load(open(wsp_path + '/config/config.yaml'), Loader = yaml.FullLoader)
    
    
    #image_log_path = config['focus_loop_param']['image_log_path']
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
    focuser_pos = [9650, 9775, 9900, 10025, 10150]
    images = ['/home/winter/data/images/20220119/SUMMER_20220119_214924_Camera0.fits',
              '/home/winter/data/images/20220119/SUMMER_20220119_215022_Camera0.fits',
              '/home/winter/data/images/20220119/SUMMER_20220119_215120_Camera0.fits',
              '/home/winter/data/images/20220119/SUMMER_20220119_215217_Camera0.fits',
              '/home/winter/data/images/20220119/SUMMER_20220119_215314_Camera0.fits']
    """
    #starttime = '20220301_045946'
    #endtime = '20220301_050946'
    #starttime= '20220228_183604'
    #endtime = '20220228_184153'
    #night = '20220228'
    
    #starttime = '20220301_225614'
    #endtime = '20220301_230252'
    #night = '20220301'
    
    #starttime = '20220308_190459'
    #endtime = '20220308_191149'
    #night = '20220308'
    
    starttime = '20220315_214546'
    endtime = '20220315_215255'
    night = '20220315'
    
    starttime = '20220420_023517'
    endtime = '20220420_024605'
    night = '20220419'
    
    starttime = '20220510_020943'
    endtime = '20220510_021634'
    night = '20220509'
    
    #starttime = '20220415_212336'
    #endtime = '20220415_213056'
    #night = '20220415'
    
    starttime = '20220630_032244'
    endtime = '20220630_032848'
    night = '20220629'
    
    starttime = '20220630_031235'
    endtime = '20220630_032020'
    night = '20220629'
    
    # g-band, 2022-7-29
    starttime = '20220729_214643'
    endtime = '20220729_215251'
    night = '20220729'
    
    # r-band, 2022-07-29
    starttime = '20220729_215452'
    endtime = '20220729_220059'
    night = '20220729'
    
    datetime_start = datetime.strptime(starttime, '%Y%m%d_%H%M%S') 
    datetime_end = datetime.strptime(endtime, '%Y%m%d_%H%M%S')
    impath = os.path.join(os.getenv("HOME"),'data','images',night)
    filelist = glob.glob(os.path.join(impath, '*.fits'))
    select_files = []
    images = []
    focuser_pos = []
    for file in filelist:
        timestr = file.split('SUMMER_')[1].split('_Camera0.fits')[0]
        datetime_file = datetime.strptime(timestr, '%Y%m%d_%H%M%S')
        if (datetime_file <= datetime_end) & (datetime_file >= datetime_start):
            images.append(file)
            focuser_pos.append(utils.getFromFITSHeader(file, 'FOCPOS'))
    
    state = {"telescope_temp_m1": utils.getFromFITSHeader(images[0], 'TEMPM1'), 
             "telescope_temp_m2": utils.getFromFITSHeader(images[0], 'TEMPM2'), 
             "telescope_temp_m3": utils.getFromFITSHeader(images[0], 'TEMPM3'), 
             "telescope_temp_ambient": utils.getFromFITSHeader(images[0], 'TEMPAMB'), 
             "T_outside_pcs": utils.getFromFITSHeader(images[0], 'TEMPTURE')}
    pix_scale = 0.466
    
    
    # use the thermal model to estimate the nominal focus
    try:
        focus_model_path = os.path.join(os.getenv("HOME"), config['focus_loop_param']['results_log_parent_dir'], config['focus_loop_param']['focus_model_params'])
        focus_model = json.load(open(focus_model_path))
        
        nom_focus = focus_model['focus_model']['summer']['slope'] * state['telescope_temp_ambient'] + focus_model['focus_model']['summer']['intercept']
    except:
        nom_focus = None
    loop = Focus_loop_v3(config, nom_focus = nom_focus, total_throw = 300, nsteps = 5, pixscale = pix_scale, state = state)

    
    
    system = 'focuser'
    # fit the data and find the best focus
    try:
        
        
        # now analyze the data (rate the images and load the observed filterpositions)
        #loop.analyzeData(focuser_pos, images)
        # now analyze the data (rate the images and load the observed filterpositions)
        #x0_fit, x0_err = loop.analyzeData(focuser_pos, images)
        x0_fit = loop.analyzeData(focuser_pos, images)
        # get a fake best focus image
        index_near_focus = np.argmin(loop.fitresults['fwhm']['raw_data']['y'])
        best_focus_image_filepath = loop.fitresults['fwhm']['raw_data']['images'][index_near_focus]
        loop.analyze_best_focus_image(best_focus_image_filepath)
        
        loop.save_focus_data()
        
        timestamp_utc = datetime.now(tz = pytz.utc).timestamp()
        loop.plot_focus_curve(timestamp_utc = timestamp_utc)
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
    
    
    
    
    fig, axes = plt.subplots(2,1, figsize = (8,8))
    
    axes[0].plot(loop.pos, loop.HFD_med, 'o')
    axes[0].set_ylabel('HFD (arcsec)')
    axes[0].set_xlabel('Position (microns)')
    
    axes[1].plot(loop.pos, loop.FWHM_med, 'o')
    axes[1].set_ylabel('FWHM (arcsec)')
    axes[1].set_xlabel('Position (microns)')