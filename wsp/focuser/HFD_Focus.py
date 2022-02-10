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
     [1] Focuser Pos: 9657.772915078624, /home/winter/data/images/20220209/SUMMER_20220209_214912_Camera0.fits
     [2] Focuser Pos: 9710.404494025992, /home/winter/data/images/20220209/SUMMER_20220209_214949_Camera0.fits
     [3] Focuser Pos: 9763.03607297336, /home/winter/data/images/20220209/SUMMER_20220209_215026_Camera0.fits
     [4] Focuser Pos: 9815.667651920729, /home/winter/data/images/20220209/SUMMER_20220209_215106_Camera0.fits
     [5] Focuser Pos: 9868.299230868097, /home/winter/data/images/20220209/SUMMER_20220209_215145_Camera0.fits
     [6] Focuser Pos: 9920.930809815465, /home/winter/data/images/20220209/SUMMER_20220209_215226_Camera0.fits
     [7] Focuser Pos: 9973.562388762834, /home/winter/data/images/20220209/SUMMER_20220209_215306_Camera0.fits
     [8] Focuser Pos: 10026.193967710202, /home/winter/data/images/20220209/SUMMER_20220209_215344_Camera0.fits
     [9] Focuser Pos: 10078.82554665757, /home/winter/data/images/20220209/SUMMER_20220209_215425_Camera0.fits
     [10] Focuser Pos: 10131.457125604938, /home/winter/data/images/20220209/SUMMER_20220209_215506_Camera0.fits
     [11] Focuser Pos: 10184.088704552309, /home/winter/data/images/20220209/SUMMER_20220209_215545_Camera0.fits
     [12] Focuser Pos: 10236.720283499677, /home/winter/data/images/20220209/SUMMER_20220209_215626_Camera0.fits
     [13] Focuser Pos: 10289.351862447045, /home/winter/data/images/20220209/SUMMER_20220209_215704_Camera0.fits
     [14] Focuser Pos: 10341.983441394414, /home/winter/data/images/20220209/SUMMER_20220209_215745_Camera0.fits
     [15] Focuser Pos: 10394.615020341782, /home/winter/data/images/20220209/SUMMER_20220209_215817_Camera0.fits
     [16] Focuser Pos: 10447.24659928915, /home/winter/data/images/20220209/SUMMER_20220209_215851_Camera0.fits
     [17] Focuser Pos: 10499.878178236519, /home/winter/data/images/20220209/SUMMER_20220209_215925_Camera0.fits
     [18] Focuser Pos: 10552.509757183887, /home/winter/data/images/20220209/SUMMER_20220209_220006_Camera0.fits
     [19] Focuser Pos: 10605.141336131255, /home/winter/data/images/20220209/SUMMER_20220209_220046_Camera0.fits
     [20] Focuser Pos: 10657.772915078624, /home/winter/data/images/20220209/SUMMER_20220209_220124_Camera0.fits
     """
    """
    focuser_pos = [9657.772915078624,
                   9710.404494025992,
                   9763.03607297336,
                   9815.667651920729,
                   9868.299230868097,
                   9920.930809815465,
                   9973.562388762834,
                   10026.193967710202,
                   10078.82554665757,
                   10131.457125604938,
                   10184.088704552309,
                   10236.720283499677,
                   10289.351862447045,
                   10341.983441394414,
                   10394.615020341782,
                   10447.24659928915,
                   10499.878178236519,
                   #10552.509757183887,
                   10605.141336131255,
                   10657.772915078624,
                   ]
    images = ['/home/winter/data/images/20220209/SUMMER_20220209_214912_Camera0.fits',
     '/home/winter/data/images/20220209/SUMMER_20220209_214949_Camera0.fits',
     '/home/winter/data/images/20220209/SUMMER_20220209_215026_Camera0.fits',
     '/home/winter/data/images/20220209/SUMMER_20220209_215106_Camera0.fits',
     '/home/winter/data/images/20220209/SUMMER_20220209_215145_Camera0.fits',
     '/home/winter/data/images/20220209/SUMMER_20220209_215226_Camera0.fits',
     '/home/winter/data/images/20220209/SUMMER_20220209_215306_Camera0.fits',
     '/home/winter/data/images/20220209/SUMMER_20220209_215344_Camera0.fits',
     '/home/winter/data/images/20220209/SUMMER_20220209_215425_Camera0.fits',
     '/home/winter/data/images/20220209/SUMMER_20220209_215506_Camera0.fits',
     '/home/winter/data/images/20220209/SUMMER_20220209_215545_Camera0.fits',
     '/home/winter/data/images/20220209/SUMMER_20220209_215626_Camera0.fits',
     '/home/winter/data/images/20220209/SUMMER_20220209_215704_Camera0.fits',
     '/home/winter/data/images/20220209/SUMMER_20220209_215745_Camera0.fits',
     '/home/winter/data/images/20220209/SUMMER_20220209_215817_Camera0.fits',
     '/home/winter/data/images/20220209/SUMMER_20220209_215851_Camera0.fits',
     '/home/winter/data/images/20220209/SUMMER_20220209_215925_Camera0.fits',
     #'/home/winter/data/images/20220209/SUMMER_20220209_220006_Camera0.fits',
     '/home/winter/data/images/20220209/SUMMER_20220209_220046_Camera0.fits',
     '/home/winter/data/images/20220209/SUMMER_20220209_220124_Camera0.fits'
     ]
    """
    
    """
    [1] Focuser Pos: 9470.0, /home/winter/data/images/20220209/SUMMER_20220209_222247_Camera0.fits
     [2] Focuser Pos: 9490.408163265307, /home/winter/data/images/20220209/SUMMER_20220209_222326_Camera0.fits
     [3] Focuser Pos: 9510.816326530612, /home/winter/data/images/20220209/SUMMER_20220209_222401_Camera0.fits
     [4] Focuser Pos: 9531.224489795919, /home/winter/data/images/20220209/SUMMER_20220209_222436_Camera0.fits
     [5] Focuser Pos: 9551.632653061224, /home/winter/data/images/20220209/SUMMER_20220209_222516_Camera0.fits
     [6] Focuser Pos: 9572.040816326531, /home/winter/data/images/20220209/SUMMER_20220209_222556_Camera0.fits
     [7] Focuser Pos: 9592.448979591836, /home/winter/data/images/20220209/SUMMER_20220209_222636_Camera0.fits
     [8] Focuser Pos: 9612.857142857143, /home/winter/data/images/20220209/SUMMER_20220209_222716_Camera0.fits
     [9] Focuser Pos: 9633.265306122448, /home/winter/data/images/20220209/SUMMER_20220209_222756_Camera0.fits
     [10] Focuser Pos: 9653.673469387755, /home/winter/data/images/20220209/SUMMER_20220209_222836_Camera0.fits
     [11] Focuser Pos: 9674.081632653062, /home/winter/data/images/20220209/SUMMER_20220209_222916_Camera0.fits
     [12] Focuser Pos: 9694.489795918367, /home/winter/data/images/20220209/SUMMER_20220209_222956_Camera0.fits
     [13] Focuser Pos: 9714.897959183674, /home/winter/data/images/20220209/SUMMER_20220209_223036_Camera0.fits
     [14] Focuser Pos: 9735.30612244898, /home/winter/data/images/20220209/SUMMER_20220209_223119_Camera0.fits
     [15] Focuser Pos: 9755.714285714286, /home/winter/data/images/20220209/SUMMER_20220209_223156_Camera0.fits
     [16] Focuser Pos: 9776.122448979591, /home/winter/data/images/20220209/SUMMER_20220209_223236_Camera0.fits
     [17] Focuser Pos: 9796.530612244898, /home/winter/data/images/20220209/SUMMER_20220209_223316_Camera0.fits
     [18] Focuser Pos: 9816.938775510203, /home/winter/data/images/20220209/SUMMER_20220209_223356_Camera0.fits
     [19] Focuser Pos: 9837.34693877551, /home/winter/data/images/20220209/SUMMER_20220209_223436_Camera0.fits
     [20] Focuser Pos: 9857.755102040815, /home/winter/data/images/20220209/SUMMER_20220209_223516_Camera0.fits
     [21] Focuser Pos: 9878.163265306122, /home/winter/data/images/20220209/SUMMER_20220209_223556_Camera0.fits
     [22] Focuser Pos: 9898.57142857143, /home/winter/data/images/20220209/SUMMER_20220209_223636_Camera0.fits
     [23] Focuser Pos: 9918.979591836734, /home/winter/data/images/20220209/SUMMER_20220209_223716_Camera0.fits
     [24] Focuser Pos: 9939.387755102041, /home/winter/data/images/20220209/SUMMER_20220209_223756_Camera0.fits
     [25] Focuser Pos: 9959.795918367347, /home/winter/data/images/20220209/SUMMER_20220209_223836_Camera0.fits
     [26] Focuser Pos: 9980.204081632653, /home/winter/data/images/20220209/SUMMER_20220209_223916_Camera0.fits
     [27] Focuser Pos: 10000.612244897959, /home/winter/data/images/20220209/SUMMER_20220209_223956_Camera0.fits
     [28] Focuser Pos: 10021.020408163266, /home/winter/data/images/20220209/SUMMER_20220209_224036_Camera0.fits
     [29] Focuser Pos: 10041.42857142857, /home/winter/data/images/20220209/SUMMER_20220209_224116_Camera0.fits
     [30] Focuser Pos: 10061.836734693878, /home/winter/data/images/20220209/SUMMER_20220209_224156_Camera0.fits
     [31] Focuser Pos: 10082.244897959183, /home/winter/data/images/20220209/SUMMER_20220209_224229_Camera0.fits
     [32] Focuser Pos: 10102.65306122449, /home/winter/data/images/20220209/SUMMER_20220209_224304_Camera0.fits
     [33] Focuser Pos: 10123.061224489797, /home/winter/data/images/20220209/SUMMER_20220209_224339_Camera0.fits
     [34] Focuser Pos: 10143.469387755102, /home/winter/data/images/20220209/SUMMER_20220209_224416_Camera0.fits
     [35] Focuser Pos: 10163.877551020409, /home/winter/data/images/20220209/SUMMER_20220209_224456_Camera0.fits
     [36] Focuser Pos: 10184.285714285714, /home/winter/data/images/20220209/SUMMER_20220209_224536_Camera0.fits
     [37] Focuser Pos: 10204.69387755102, /home/winter/data/images/20220209/SUMMER_20220209_224616_Camera0.fits
     [38] Focuser Pos: 10225.102040816326, /home/winter/data/images/20220209/SUMMER_20220209_224656_Camera0.fits
     [39] Focuser Pos: 10245.510204081633, /home/winter/data/images/20220209/SUMMER_20220209_224736_Camera0.fits
     [40] Focuser Pos: 10265.918367346938, /home/winter/data/images/20220209/SUMMER_20220209_224816_Camera0.fits
     [41] Focuser Pos: 10286.326530612245, /home/winter/data/images/20220209/SUMMER_20220209_224856_Camera0.fits
     [42] Focuser Pos: 10306.734693877552, /home/winter/data/images/20220209/SUMMER_20220209_224937_Camera0.fits
     [43] Focuser Pos: 10327.142857142857, /home/winter/data/images/20220209/SUMMER_20220209_225019_Camera0.fits
     [44] Focuser Pos: 10347.551020408164, /home/winter/data/images/20220209/SUMMER_20220209_225057_Camera0.fits
     [45] Focuser Pos: 10367.959183673469, /home/winter/data/images/20220209/SUMMER_20220209_225138_Camera0.fits
     [46] Focuser Pos: 10388.367346938776, /home/winter/data/images/20220209/SUMMER_20220209_225216_Camera0.fits
     [47] Focuser Pos: 10408.775510204081, /home/winter/data/images/20220209/SUMMER_20220209_225256_Camera0.fits
     [48] Focuser Pos: 10429.183673469388, /home/winter/data/images/20220209/SUMMER_20220209_225336_Camera0.fits
     [49] Focuser Pos: 10449.591836734693, /home/winter/data/images/20220209/SUMMER_20220209_225416_Camera0.fits
     [50] Focuser Pos: 10470.0, /home/winter/data/images/20220209/SUMMER_20220209_225456_Camera0.fits
     """
    focuser_pos = [9470.0,
     9490.408163265307,
     9510.816326530612, 
     9531.224489795919, 
     9551.632653061224, 
     9572.040816326531, 
     9592.448979591836, 
     9612.857142857143, 
     9633.265306122448, 
     9653.673469387755, 
     9674.081632653062, 
     9694.489795918367, 
     9714.897959183674, 
     9735.30612244898, 
     9755.714285714286, 
     9776.122448979591,
     9796.530612244898, 
     9816.938775510203, 
     9837.34693877551, 
     9857.755102040815, 
     9878.163265306122, 
     9898.57142857143, 
     9918.979591836734, 
     9939.387755102041, 
     9959.795918367347, 
     9980.204081632653, 
     10000.612244897959, 
     10021.020408163266,
     10041.42857142857,
     10061.836734693878, 
     10082.244897959183, 
     10102.65306122449, 
     10123.061224489797, 
     10143.469387755102, 
     10163.877551020409, 
     10184.285714285714, 
     10204.69387755102, 
     10225.102040816326, 
     10245.510204081633, 
     10265.918367346938, 
     10286.326530612245, 
     10306.734693877552, 
     10327.142857142857, 
     10347.551020408164, 
     10367.959183673469, 
     10388.367346938776, 
     10408.775510204081, 
     10429.183673469388, 
     10449.591836734693, 
     10470.0]
    
    
    images = ['/home/winter/data/images/20220209/SUMMER_20220209_222247_Camera0.fits',
     '/home/winter/data/images/20220209/SUMMER_20220209_222326_Camera0.fits',
     '/home/winter/data/images/20220209/SUMMER_20220209_222401_Camera0.fits',
     '/home/winter/data/images/20220209/SUMMER_20220209_222436_Camera0.fits',
     '/home/winter/data/images/20220209/SUMMER_20220209_222516_Camera0.fits',
     '/home/winter/data/images/20220209/SUMMER_20220209_222556_Camera0.fits',
     '/home/winter/data/images/20220209/SUMMER_20220209_222636_Camera0.fits',
     '/home/winter/data/images/20220209/SUMMER_20220209_222716_Camera0.fits',
     '/home/winter/data/images/20220209/SUMMER_20220209_222756_Camera0.fits',
     '/home/winter/data/images/20220209/SUMMER_20220209_222836_Camera0.fits',
     '/home/winter/data/images/20220209/SUMMER_20220209_222916_Camera0.fits',
     '/home/winter/data/images/20220209/SUMMER_20220209_222956_Camera0.fits',
     '/home/winter/data/images/20220209/SUMMER_20220209_223036_Camera0.fits',
     '/home/winter/data/images/20220209/SUMMER_20220209_223119_Camera0.fits',
     '/home/winter/data/images/20220209/SUMMER_20220209_223156_Camera0.fits',
     '/home/winter/data/images/20220209/SUMMER_20220209_223236_Camera0.fits',
     '/home/winter/data/images/20220209/SUMMER_20220209_223316_Camera0.fits',
     '/home/winter/data/images/20220209/SUMMER_20220209_223356_Camera0.fits',
     '/home/winter/data/images/20220209/SUMMER_20220209_223436_Camera0.fits',
     '/home/winter/data/images/20220209/SUMMER_20220209_223516_Camera0.fits',
     '/home/winter/data/images/20220209/SUMMER_20220209_223556_Camera0.fits',
     '/home/winter/data/images/20220209/SUMMER_20220209_223636_Camera0.fits',
     '/home/winter/data/images/20220209/SUMMER_20220209_223716_Camera0.fits',
     '/home/winter/data/images/20220209/SUMMER_20220209_223756_Camera0.fits',
     '/home/winter/data/images/20220209/SUMMER_20220209_223836_Camera0.fits',
     '/home/winter/data/images/20220209/SUMMER_20220209_223916_Camera0.fits',
     '/home/winter/data/images/20220209/SUMMER_20220209_223956_Camera0.fits',
     '/home/winter/data/images/20220209/SUMMER_20220209_224036_Camera0.fits',
     '/home/winter/data/images/20220209/SUMMER_20220209_224116_Camera0.fits',
     '/home/winter/data/images/20220209/SUMMER_20220209_224156_Camera0.fits',
     '/home/winter/data/images/20220209/SUMMER_20220209_224229_Camera0.fits',
     '/home/winter/data/images/20220209/SUMMER_20220209_224304_Camera0.fits',
     '/home/winter/data/images/20220209/SUMMER_20220209_224339_Camera0.fits',
     '/home/winter/data/images/20220209/SUMMER_20220209_224416_Camera0.fits',
     '/home/winter/data/images/20220209/SUMMER_20220209_224456_Camera0.fits',
     '/home/winter/data/images/20220209/SUMMER_20220209_224536_Camera0.fits',
     '/home/winter/data/images/20220209/SUMMER_20220209_224616_Camera0.fits',
     '/home/winter/data/images/20220209/SUMMER_20220209_224656_Camera0.fits',
     '/home/winter/data/images/20220209/SUMMER_20220209_224736_Camera0.fits',
     '/home/winter/data/images/20220209/SUMMER_20220209_224816_Camera0.fits',
     '/home/winter/data/images/20220209/SUMMER_20220209_224856_Camera0.fits',
     '/home/winter/data/images/20220209/SUMMER_20220209_224937_Camera0.fits',
     '/home/winter/data/images/20220209/SUMMER_20220209_225019_Camera0.fits',
     '/home/winter/data/images/20220209/SUMMER_20220209_225057_Camera0.fits',
     '/home/winter/data/images/20220209/SUMMER_20220209_225138_Camera0.fits',
     '/home/winter/data/images/20220209/SUMMER_20220209_225216_Camera0.fits',
     '/home/winter/data/images/20220209/SUMMER_20220209_225256_Camera0.fits',
     '/home/winter/data/images/20220209/SUMMER_20220209_225336_Camera0.fits',
     '/home/winter/data/images/20220209/SUMMER_20220209_225416_Camera0.fits',
     '/home/winter/data/images/20220209/SUMMER_20220209_225456_Camera0.fits']
     
    
    # Try something else
    
    HFD_mean = []
    HFD_med = []
    HFD_std = []
    HFD_stderr_mean = []
    HFD_stderr_med = []
    
    FWHM_mean = []
    FWHM_med = []
    FWHM_std = []
    
    weightimg=os.path.join(wsp_path,'focuser/weight.fits')
    
    focuser_pos_good = []
    images_good = []
    
    #last_image = os.readlink(os.path.join(os.getenv("HOME"), 'data','last_image.lnk'))
    #genstats.run_sextractor(last_image,pixscale,weightimg=weightimg)
    
    for i in range(len(images)):#image in images:
        image = images[i]
        focus = focuser_pos[i]
        try:
            #mean, median, std, stderr_mean, stderr_med
            mean, median, std, stderr_mean, stderr_med = genstats.get_img_fluxdiameter(image, pixscale = pixscale, 
                                                                                       weightimg=weightimg,
                                                                                       exclude = False)
            mean_fwhm, med_fwhm, std_fwhm = genstats.get_img_fwhm(image, pixscale = pixscale, 
                                                                                       weightimg=weightimg,
                                                                                       exclude = False)
            focuser_pos_good.append(focus)
            images_good.append(image)
            
            HFD_mean.append(mean*pixscale)
            HFD_med.append(median*pixscale)
            HFD_std.append(std*pixscale)
            HFD_stderr_mean.append(stderr_mean*pixscale)
            HFD_stderr_med.append(stderr_med*pixscale)
            
            FWHM_mean.append(mean_fwhm*pixscale)
            FWHM_med.append(med_fwhm*pixscale)
            FWHM_std.append(std_fwhm*pixscale)
        except Exception as e:
            print(f'could not analyze image {image}: {e}')
    
    
    pos = np.array(focuser_pos_good)
    HFD_med = np.array(HFD_med)
    HFD_mean = np.array(HFD_mean)
    HFD_stderr_mean = np.array(HFD_stderr_mean)
    HFD_stderr_med = np.array(HFD_stderr_med)
    
    
    # save for access later
    HFD_out = np.column_stack((pos, HFD_med, HFD_mean, HFD_stderr_mean, HFD_stderr_med, FWHM_mean, FWHM_med, FWHM_std))
    np.savetxt(os.path.join(os.getenv("HOME"), 'data', 'df_focuser', 'HFD_Focus_Test_Data.txt'),
               X = HFD_out,
               delimiter = '\t',
               header = 'pos\tHFD_med\tHFD_mean\tHFD_stderr_mean\tHFD_stderr_med\tFWHM_mean\tFWHM_med\tFWHM_std')
    
    # fit the right hand line
    cond_rh = (pos>9960) & (pos<10300)
    pos_rh = pos[cond_rh]
    HFD_med_rh = HFD_med[cond_rh]
    rh_fit = np.polyfit(pos_rh, HFD_med_rh, 1)
    HFD_fit_rh = np.polyval(rh_fit, pos)
    
    # fit the left hand line
    cond_lh = (pos>9700) & (pos<9960)
    pos_lh = pos[cond_lh]
    HFD_med_lh = HFD_med[cond_lh]
    lh_fit = np.polyfit(pos_lh, HFD_med_lh, 1)
    HFD_fit_lh = np.polyval(lh_fit, pos)
    
    plt.figure()
    #plt.plot(focuser_pos, HFD_med, 'ks')
    plt.errorbar(pos, HFD_med, yerr = HFD_stderr_med, capsize = 5, fmt = 'ks', label = 'Median')
    plt.plot(pos, HFD_fit_rh, 'r-', label = 'RH Fit')
    plt.plot(pos, HFD_fit_lh, 'g-', label = 'LH Fit')

    #plt.errorbar(focuser_pos, HFD_mean, yerr = HFD_stderr_mean, capsize = 5, fmt = 'ro', label = 'Mean')
    plt.legend()
    plt.xlabel('Focuser Position [micron]')
    plt.ylabel('Half-Focus Diameter [arcseconds]')
    """
    plt.figure()
    FWHM_med = np.array(FWHM_med)
    FWHM_std = np.array(FWHM_std)
    FWHM_stderr_med = (np.pi/2)**0.5 * FWHM_std/np.sqrt(26)
    plt.errorbar(pos, FWHM_med, yerr = FWHM_stderr_med, capsize = 5, fmt = 'ks', label = 'Median')
    
    plt.legend()
    plt.xlabel('Focuser Position [micron]')
    plt.ylabel('FWHM [arcseconds]')
    
    # F
    """