#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Feb 24 15:58:21 2023

@author: winter
"""

import os
import sys
import numpy as np
import matplotlib.pyplot as plt
from ccdproc_convenience_functions import show_image
from PyQt5 import QtCore
import threading
import Pyro5.core
import Pyro5.server
import logging


# add the wsp directory to the PATH
wsp_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
print(f'wsp_path = {wsp_path}')
sys.path.insert(1, wsp_path)

from housekeeping import data_handler

class WINTERCamSim(QtCore.QObject):

    def __init__(self, config, logger = None, verbose = False ):
        super(WINTERCamSim, self).__init__()
        
        ## init things here
        self.state = dict()
        
        ## some things to keep track of what is going on
        # doing an exposure?
        self.doing_exposure = False
        
        ## set up poll status thread
        self.statusThread = data_handler.daq_loop(func = self.pollStatus, 
                                                       dt = self.pollTimer_dt,
                                                       name = 'WINTERCamSim Status Loop'
                                                       )
        
    def log(self, msg, level = logging.INFO):
            
        msg = f'ccd_daemon: {msg}'
        
        if self.logger is None:
            print(msg)
        else:
            self.logger.log(level = level, msg = msg)
    
    def doFakeExposure(self):
        """
        the idea here is to block the thread for the exposure time,
        while periodically updating the housekeeping. at the end of the exposure
        time use the getFakeImage method to generate a fake set of data,
        and then save it.
        """
        pass
    
    def getFakeImage(imsize, number, max_counts=10000, gain=1):
        """
        Add some stars to the image.
        # adapted from ccdproc tutorial: https://www.astropy.org/ccd-reduction-and-photometry-guide/v/dev/notebooks/01-03-Construction-of-an-artificial-but-realistic-image.html
        """
        image = np.zeros(imsize)
        from photutils.datasets import make_random_gaussians_table, make_gaussian_sources_image
        # Most of the code below is a direct copy/paste from
        # https://photutils.readthedocs.io/en/stable/_modules/photutils/datasets/make.html#make_100gaussians_image
        
        flux_range = [max_counts/10, max_counts]
        
        y_max, x_max = image.shape
        xmean_range = [0.1 * x_max, 0.9 * x_max]
        ymean_range = [0.1 * y_max, 0.9 * y_max]
        xstddev_range = [4, 4]
        ystddev_range = [4, 4]
        params = dict([('amplitude', flux_range),
                      ('x_mean', xmean_range),
                      ('y_mean', ymean_range),
                      ('x_stddev', xstddev_range),
                      ('y_stddev', ystddev_range),
                      ('theta', [0, 2*np.pi])])
    
        sources = make_random_gaussians_table(number, params)#,
                                              #seed=12345)
        
        star_im = make_gaussian_sources_image(image.shape, sources)
        
        return star_im


im = makeFakeImage((1080, 1920), 50)
show_image(im, cmap = 'gray', percu=99.9)