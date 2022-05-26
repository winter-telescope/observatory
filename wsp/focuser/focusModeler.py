#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Mar 16 10:05:40 2022

Focus Model Maker

@author: winter
"""

import os
import sys
import numpy as np
import matplotlib.pyplot as plt
import glob
import yaml
import json
from datetime import datetime
import astropy.timeseries
import astropy.time
import astropy.units as u
import astropy.stats
from scipy.optimize import curve_fit


# add the wsp directory to the PATH
wsp_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),'wsp')
# switch to this when ported to wsp
#wsp_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
plt.style.use('tableau-colorblind10')

sys.path.insert(1, wsp_path)
print(f'FocusModeler: wsp_path = {wsp_path}')


def polyval(x, *param):
    
    return np.polyval(param, x)

def polyfit_errs(x, y, errs, deg, returnCov = False):

    p0 = np.polyfit(x,y,deg)
    if errs is None:
        absolute_sigma = False
    else:
        absolute_sigma = True
    popt,pcov = curve_fit(polyval, xdata=x, ydata=y, p0=p0, sigma=errs, absolute_sigma = absolute_sigma)
    
    if returnCov:
        return popt, pcov
    else:
        return popt

class FocusModeler(object):
    # this is an object that holds the focus results
    
    def __init__(self, config):
        
        self.config = config
        
        self.results = dict({'position' : np.array([]),
                             'position_err' : np.array([]),
                             'temperatures' : {},
                             'time_strings' : np.array([]),
                             'astropyTimes' : np.array([]),
                             'times'        : np.array([]),
                             'flag' : np.array([]),
                             })
        self._temperatures_keywords = ['m1',
                                      'm2',
                                      'm3',
                                      'telescope_ambient',
                                      'outside_pcs']
        
        self._setupResultsDict()
        #self.loadResults()
    
    def _setupResultsDict(self):
        
        # add a list to the results dict for each entry in the temperatures keywords
        for key in self._temperatures_keywords:
            self.results['temperatures'].update({key : []})
        
        self.n_temp_sensors = len(self._temperatures_keywords)

        
    def loadResults(self, filterID = None):
                
        # load all the focus data from the folder
        
        
        self._resultsDir = os.path.join(os.getenv("HOME"), 
                                  self.config['focus_loop_param']['results_log_parent_dir'], 
                                  self.config['focus_loop_param']['results_log_dir'])
        
        self._resultFiles = glob.glob(os.path.join(self._resultsDir, '*.json'))
        
        for file in self._resultFiles:
            try:
                resultDict = json.load(open(file))
                
                # don't load results that have None as a temperature
                if None in list(resultDict['temperatures'].values()):
                    pass
                else:
                    
                    if not filterID is None:
                        if resultDict['telemetry']['filterID'] == filterID:
                            #print(f"filter = {resultDict['telemetry']['filterID']}")
                            # try to load the results from the file into the dictionary
                            self.results['position'] = np.append(self.results['position'], resultDict['results']['focus'])
                            self.results['position_err'] = np.append(self.results['position_err'], resultDict['results']['focus_err'])
                            self.results['time_strings'] = np.append(self.results['time_strings'], resultDict['results']['time_utc_iso'])
                            self.results['times'] = np.append(self.results['times'], datetime.strptime(resultDict['results']['time_utc_iso'],'%Y-%m-%d %H:%M:%S.%f'))
                            self.results['astropyTimes'] = np.append(self.results['astropyTimes'], astropy.time.Time(datetime.strptime(resultDict['results']['time_utc_iso'],'%Y-%m-%d %H:%M:%S.%f'), format = 'datetime'))
                            self.results['flag'] = np.append(self.results['flag'], False)
                            for key in self._temperatures_keywords:
                                temp = resultDict['temperatures'][key]
                                self.results['temperatures'][key] = np.append(self.results['temperatures'][key], temp)
                                
                        else:
                            pass
                    else:
                        # try to load the results from the file into the dictionary
                        self.results['position'] = np.append(self.results['position'], resultDict['results']['focus'])
                        self.results['position_err'] = np.append(self.results['position_err'], resultDict['results']['focus_err'])
                        self.results['time_strings'] = np.append(self.results['time_strings'], resultDict['results']['time_utc_iso'])
                        self.results['times'] = np.append(self.results['times'], datetime.strptime(resultDict['results']['time_utc_iso'],'%Y-%m-%d %H:%M:%S.%f'))
                        self.results['astropyTimes'] = np.append(self.results['astropyTimes'], astropy.time.Time(datetime.strptime(resultDict['results']['time_utc_iso'],'%Y-%m-%d %H:%M:%S.%f'), format = 'datetime'))
                        self.results['flag'] = np.append(self.results['flag'], False)
                        for key in self._temperatures_keywords:
                            temp = resultDict['temperatures'][key]
                            self.results['temperatures'][key] = np.append(self.results['temperatures'][key], temp)
                            
            except Exception as e:
                print(f'could not load results data from {file}: {type(e)}: {e}')
        
        
            
            
    def identifyOutliers(self):
        
        for i in range(self.n_temp_sensors):
            # we'll do an iterative linear fit to remove outliers
            temp_name = self._temperatures_keywords[i]
            temps = np.array(self.results['temperatures'][temp_name])
            pos = np.array(self.results['position'])
            errs = np.array(self.results['position_err'])
            #param0 = np.polyfit(temps, pos, 1)
            param0 = polyfit_errs(temps, pos, errs, 1)
            tempsFit0 = np.polyval(param0, pos)
            resid0 = np.abs(temps - tempsFit0)
            sigma0 = np.std(resid0)
            scale = 1.0
            flags = resid0 > scale*sigma0
            self.results['flag'] = flags

                        
    def plotResults_individual(self):
        self.identifyOutliers()
        #fig, axes = plt.subplots(1, n_temp_sensors, figsize = (6*n_temp_sensors,6))
        #for temp in self._temperatures_keywords:
        xmin = np.min(list(self.results['temperatures'].values()))
        xmax = np.max(list(self.results['temperatures'].values()))
        ymin = np.min(self.results['position'])
        ymax = np.max(self.results['position'])
        for i in range(self.n_temp_sensors):
            fig, ax = plt.subplots(1,1, figsize = (6,6))
            temp = self._temperatures_keywords[i]
            #ax = axes[i]
            #ax.plot(self.results['temperatures'][temp], self.results['position'], 'o', label = temp)
            ax.errorbar(self.results['temperatures'][temp], self.results['position'],  yerr = self.results['position_err'], 
                        fmt = 'o', capsize = 5, label = temp)
            
            for j in range(len(self.results['temperatures'][temp])):
                txt = self.results['time_strings'][j]
                txt_x = self.results['temperatures'][temp][j]
                txt_y = self.results['position'][j]
                ax.annotate(txt, (txt_x, txt_y ), rotation = 90)
            ax.set_title(f'{temp}')
            ax.set_ylabel('Focuser Position [micron]')
            ax.set_xlabel('Temperature [C]')
            dy = 25
            dx = 2
            ax.set_ylim(ymin-dy, ymax + dy)
            ax.set_xlim(xmin-dx, xmax+dx)
            ax.legend()
            #plt.tight_layout()
    def plotResults(self):
        fig, ax = plt.subplots(1, 1, figsize = (6,6))
        
        xmin = np.min(list(self.results['temperatures'].values()))
        xmax = np.max(list(self.results['temperatures'].values()))
        ymin = np.min(self.results['position'])
        ymax = np.max(self.results['position'])
        
        #for temp in self._temperatures_keywords:
        for i in range(self.n_temp_sensors):
            temp = self._temperatures_keywords[i]
            
            #ax.plot(self.results['temperatures'][temp], self.results['position'], 'o', label = temp)
            ax.errorbar(self.results['temperatures'][temp], self.results['position'],  yerr = self.results['position_err'], 
                        fmt = 'o', capsize = 5, label = temp)
            ax.set_title(f'{temp}')
            ax.set_ylabel('Focuser Position [micron]')
            ax.set_xlabel('Temperature [C]')
            
            dy = 25
            dx = 2
            ax.set_ylim(ymin-dy, ymax + dy)
            ax.set_xlim(xmin-dx, xmax+dx)
            
            ax.legend()
        plt.tight_layout()
            
if __name__ == '__main__':
    config = yaml.load(open(wsp_path + '/config/config.yaml'), Loader = yaml.FullLoader)
    
    results = dict()
    filterTimeseries = dict()
    alltimes = np.array([])
    filters = ['u', 'g', 'r', 'i']
    for filterID in filters:
        focusModeler = FocusModeler(config)
        results.update({filterID : focusModeler})
        focusModeler.loadResults(filterID = filterID)
        alltimes = np.append(alltimes, focusModeler.results['times'])
        #focusModeler.plotResults_individual()
        #focusModeler.plotResults()
        #
        """
        fig, axes = plt.subplots(2, 1, figsize = (5,8))
        ax = axes[0]
        """
        fig, ax = plt.subplots(1, 1, figsize = (5,4))
        
        temps = focusModeler.results['temperatures']['telescope_ambient']
        pos = focusModeler.results['position']
        errs = focusModeler.results['position_err']
        #param0 = np.polyfit(temps, pos, 1)
        param0 = polyfit_errs(temps, pos, errs, 1)
        posFit0 = np.polyval(param0, temps)
        resid0 = pos - posFit0
        sigma0 = np.std(resid0)
        scale = 1.5
        flags = resid0 > scale*sigma0
        
        model0_x = np.linspace(min(temps), max(temps), 100)
        model0_y = np.polyval(param0, model0_x)
        
        #param1 = np.polyfit(temps[flags == False], pos[flags == False], 1)
        param1, cov1 = polyfit_errs(temps[flags == False], pos[flags == False], errs[flags == False], 1, returnCov = True)
        mfit = param1[0]
        bfit = param1[1]
        stderr1 = np.sqrt(np.diag(cov1))
        mfit_stderr = stderr1[0]
        bfit_stderr = stderr1[1]    
        model_x = np.linspace(min(temps), max(temps), 100)
        model_y = np.polyval(param1, model_x)
        
        #ax.plot(temps, pos, 'o', label = 'All Data')
        ax.errorbar(temps[flags == False], pos[flags == False],  yerr = errs[flags == False], 
                    fmt = 'o', capsize = 5, label = 'Unflagged Data')
        ax.plot(temps[flags == True], pos[flags == True], 'o', label = 'Flagged Outliers')
        ax.plot(model0_x, model0_y, 'g--', label = f'Initial Fit for Outlier ID')
        #ax.plot(model_x, model_y, 'r-', label = f'Fit: Focus = {param1[0]:.3f}'+'$xT_{AMBIENT}$' + f' + {param1[1]:.3f}')
        ax.plot(model_x, model_y, 'r-', label = f'Fit: Focus = [{mfit:.3f} +/- {mfit_stderr:.3f}]'+'$xT_{AMBIENT}$' + f' + [{bfit:.1f} +/- {bfit_stderr:.1f}]')
        ax.legend(fontsize = 8)
        ax.set_ylabel('Focus Position [micron]')
        ax.set_xlabel('Ambient Temperature [C]')
        ax.set_title(f'Focus Model for {filterID}-band')
        
        """
        ax = axes[1]
        ax.plot(temps, resid0, 'o')
        ax.plot(model0_x, model0_y*0.0, 'g--')
        ax.plot(model0_x, model0_x*0.0 + scale*sigma0, 'r--', label = f'+/- {scale}$\sigma$')
        ax.plot(model0_x, model0_x*0.0 - scale*sigma0, 'r--')
        ax.set_ylabel('Focus Initial Fit Residual [micron]')
        ax.set_xlabel('Ambient Temperature [C]')
        ax.set_title('Outlier Identification')
        ax.legend(fontsize = 8)
        plt.tight_layout()
        """
        
        # bin with date
        times = focusModeler.results['astropyTimes']
        ts = astropy.timeseries.TimeSeries(time = times[flags == False])
        ts['pos']  = pos[flags == False]
        ts['temp'] = temps[flags == False]
        ts['pos_err'] = errs[flags == False ]
        filterTimeseries.update({filterID : ts})
        
    earliest_time = min(alltimes)
    latest_time = max(alltimes)
    dt = latest_time - earliest_time
    starttime = datetime(year = earliest_time.year, month = earliest_time.month, day = earliest_time.day, hour = 3, minute = 0, second = 0, microsecond = 0)
    starttime_astropy = astropy.time.Time(starttime, format = 'datetime')
    
    binsize_hours = 6
    nbins = int((dt.days+1)*24/binsize_hours)+1
    
    filterTimeseriesBinned = astropy.timeseries.TimeSeries(time_delta = binsize_hours*u.hour, time_start = starttime_astropy, n_samples = nbins)

    for filterID in filters:
        ts = filterTimeseries[filterID]
        ts_binned = astropy.timeseries.aggregate_downsample(ts, time_bin_size = binsize_hours*u.hour, time_bin_start = starttime_astropy, n_bins = nbins)
        
        filterTimeseriesBinned[f'pos_{filterID}'] = ts_binned['pos']
        filterTimeseriesBinned[f'temp_{filterID}'] = ts_binned['temp']
        filterTimeseriesBinned[f'pos_err_{filterID}'] = ts_binned['pos_err']
        
    # now get the offsets
    filterTimeseriesBinned['g-u'] = filterTimeseriesBinned['pos_g'] - filterTimeseriesBinned['pos_u']
    filterTimeseriesBinned['g-r'] = filterTimeseriesBinned['pos_g'] - filterTimeseriesBinned['pos_r']
    filterTimeseriesBinned['g-i'] = filterTimeseriesBinned['pos_g'] - filterTimeseriesBinned['pos_i']
    #%%
    nsigma = 3.0
    fig, ax = plt.subplots(1,1)
    for filterID in ['u','r','i']:
        
        x = filterTimeseriesBinned['temp_g']
        y = filterTimeseriesBinned[f'g-{filterID}']
        mean, median, stddev = astropy.stats.sigma_clipped_stats(y, sigma = nsigma)
        
        
        yerr = np.sqrt(filterTimeseriesBinned['pos_err_g']**2 + filterTimeseriesBinned[f'pos_err_{filterID}']**2)
        #p = plt.plot(filterTimeseriesBinned['temp_g'], filterTimeseriesBinned[f'g-{filterID}'],'o', label = f"{filterID}: {binsize_hours}-hr binned data")
        
        cond = (x.mask == False) & (y.mask == False) & (yerr.mask == False)
        popt = polyfit_errs(x = x[cond].value.data, y = y[cond].value.data,
                                  errs = yerr[cond].value.data, deg = 0, returnCov = False)
        
        offset_fit = popt[0]
        
        plot = ax.errorbar(x, y, yerr = yerr,
                         fmt = 'o', label = f"{filterID}: {binsize_hours}-hr binned data",
                         capsize = 5)

        color = plot[0].get_color()
        line_x = np.linspace(x.min(0), x.max(0), 100)
        
        ax.plot(line_x, 0.0*line_x+median,'--', color = color, label = f"{filterID}: $\sigma$-clipped ({nsigma}*$\sigma$) median = {median:.1f} $\mu$m")
        ax.plot(line_x, 0.0*line_x+offset_fit,'-', color = color, label = f"{filterID}: fit with errorbars = {offset_fit:.1f} $\mu$m")

    ax.set_ylabel('Offset [microns]')
    ax.set_xlabel('Ambient Temperature [C]')
    ax.set_title('Relative Filter Offsets from g')
    #ax.set_ylim(-100,100)
    ax.legend(fontsize = 5)
    
    # just throw all the data together
    results = dict()
    filterTimeseries = dict()
    alltimes = np.array([])
    filters = ['u', 'g', 'r', 'i']
    #fig, axes = plt.subplots(2, 1, figsize = (5,8))
    fig, ax = plt.subplots(1, 1, figsize = (5,4))

    temps = np.array([])
    pos = np.array([])
    errs = np.array([])
    for filterID in filters:
        focusModeler = FocusModeler(config)
        results.update({filterID : focusModeler})
        focusModeler.loadResults(filterID = filterID)
        alltimes = np.append(alltimes, focusModeler.results['times'])
        #focusModeler.plotResults_individual()
        #focusModeler.plotResults()
        #
        
        
        temps = np.append(temps, focusModeler.results['temperatures']['telescope_ambient'])
        pos = np.append(pos, focusModeler.results['position'])
        errs = np.append(errs, focusModeler.results['position_err'])
                
    #ax = axes[0]
    param0 = polyfit_errs(temps, pos, errs, 1)
    posFit0 = np.polyval(param0, temps)
    resid0 = pos - posFit0
    sigma0 = np.std(resid0)
    scale = 1.5
    flags = resid0 > scale*sigma0
    
    model0_x = np.linspace(min(temps), max(temps), 100)
    model0_y = np.polyval(param0, model0_x)
    
    #param1 = np.polyfit(temps[flags == False], pos[flags == False], 1)
    param1, cov1 = polyfit_errs(temps[flags == False], pos[flags == False], errs[flags == False], 1, returnCov = True)
    mfit = param1[0]
    bfit = param1[1]
    stderr1 = np.sqrt(np.diag(cov1))
    mfit_stderr = stderr1[0]
    bfit_stderr = stderr1[1]    
    model_x = np.linspace(min(temps), max(temps), 100)
    model_y = np.polyval(param1, model_x)
    
    #ax.plot(temps, pos, 'o', label = 'All Data')
    ax.errorbar(temps[flags == False], pos[flags == False],  yerr = errs[flags == False], 
                fmt = 'o', capsize = 5, label = 'Unflagged Data')
    ax.plot(model0_x, model0_y, 'g--', label = f'Initial Fit for Outlier ID')
    ax.plot(model_x, model_y, 'r-', label = f'Fit: Focus = [{mfit:.3f} +/- {mfit_stderr:.3f}]'+'$xT_{AMBIENT}$' + f' + [{bfit:.1f} +/- {bfit_stderr:.1f}]')
    ax.set_ylabel('Focus Position [micron]')
    ax.set_xlabel('Ambient Temperature [C]')
    ax.set_title(f'Focus Model for All Filters Combined')
    
    # now plot again so that we label the points a different color for reference
    for filterID in filters:
             
        ax.plot(results[filterID].results['temperatures']['telescope_ambient'], results[filterID].results['position'], 'o', label = filterID, zorder = 5)
    ax.plot(temps[flags == True], pos[flags == True], 'ms', markersize = 7, label = 'Flagged Outliers', zorder = 10)

    ax.legend(fontsize = 5)

    
    """
    ax = axes[1]
    ax.plot(temps, resid0, 'o')
    ax.plot(model0_x, model0_y*0.0, 'g--')
    ax.plot(model0_x, model0_x*0.0 + scale*sigma0, 'r--', label = f'+/- {scale}$\sigma$')
    ax.plot(model0_x, model0_x*0.0 - scale*sigma0, 'r--')
    ax.set_ylabel('Focus Initial Fit Residual [micron]')
    ax.set_xlabel('Ambient Temperature [C]')
    ax.set_title('Outlier Identification')
    ax.legend(fontsize = 8)
    plt.tight_layout()
    """