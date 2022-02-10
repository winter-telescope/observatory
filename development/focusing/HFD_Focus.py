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


# add the wsp directory to the PATH
wsp_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),'wsp')
# switch to this when ported to wsp
#wsp_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

sys.path.insert(1, wsp_path)
print(f'focusing: wsp_path = {wsp_path}')
from alerts import alert_handler
from focuser import plot_curve
from focuser import genstats




if __name__ == '__main__':
    # test area
    
    config = yaml.load(open(wsp_path + '/config/config.yaml'), Loader = yaml.FullLoader)
    pixscale = 0.466

    
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

    
    #focuser_pos = [10169.417]
    #images = ['/home/winter/data/images/20220209/SUMMER_20220209_211205_Camera0.fits']
    
    last_image = os.readlink(os.path.join(os.getenv("HOME"), 'data','last_image.lnk'))
    
    
    # Try something else
    
    HFD_mean = []
    HFD_med = []
    HFD_std = []
    HFD_stderr_mean = []
    HFD_stderr_med = []
    
    weightimg=os.path.join(wsp_path,'focuser/weight.fits')
    
    
    for image in images:
        try:
            #mean, median, std, stderr_mean, stderr_med
            mean, median, std, stderr_mean, stderr_med = genstats.get_img_fluxdiameter(image, pixscale = pixscale, 
                                                                                       weightimg=weightimg,
                                                                                       exclude = False)
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
    