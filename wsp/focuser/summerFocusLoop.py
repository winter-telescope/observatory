#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
The focus loop object class

@author: cruzss
"""
import os
import glob
from focuser import genstats
from astropy.io import fits

class Fit_curve:
    
    def __init__(self, A, B, x, x0):
        self.A = A
        self.B = B
        self.x = x
        self.x0 = x0
        
    def parabola_curve(self):
        return self.A + self.B*(self.x-self.x0)**2
    
    #def fit_curve(self):

class Focus_loop:
    
    def __init__(self, filt, config): 
        self.config = config
        self.interval = self.config['focus_loop_param']['micron_interval']
        
        self.pixscale = self.config['focus_loop_param']['pixscale']
        self.filter_range = range(self.config['filt_limits'][filt]['lower'],self.config['filt_limits'][filt]['upper']+self.interval,self.interval)
        
        self.path = self.config['focus_loop_param']['recent_path']+ "*"

    def analyze_img_focus(self, imgname):
        mean, med, std = get_img_fwhm(imgname, self.pixscale,exclude = False)
        return med
    
    def rate_imgs(self,imglist):
        #Create grading list
        medlist = []
        
        for imgname in imglist:
            medlist.append(analyze_img_focus(self,imgname))
        
        return medlist
    
    def return_Range(self):
        return self.filter_range
    
    def get_Recent_File(self):
        list_of_files = glob.glob(self.path)
        return max(list_of_files, key=os.path.getctime)
            
            
            
        
        
        
        
        
        
