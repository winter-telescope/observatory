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

# add the wsp directory to the PATH
wsp_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),'wsp')
# switch to this when ported to wsp
#wsp_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


sys.path.insert(1, wsp_path)
print(f'FocusModeler: wsp_path = {wsp_path}')

class FocusModeler(object):
    # this is an object that holds the focus results
    
    def __init__(self, config):
        
        self.config = config
        
        self.results = dict({'position' : np.array([]),
                             'position_err' : np.array([]),
                             'temperatures' : {},
                             'time_strings' : np.array([]),
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
                if not filterID is None:
                    if resultDict['telemetry']['filterID'] == filterID:
                        #print(f"filter = {resultDict['telemetry']['filterID']}")
                        # try to load the results from the file into the dictionary
                        self.results['position'] = np.append(self.results['position'], resultDict['results']['focus'])
                        self.results['position_err'] = np.append(self.results['position_err'], resultDict['results']['focus_err'])
                        self.results['time_strings'] = np.append(self.results['time_strings'], resultDict['results']['time_utc_iso'])
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

            param0 = np.polyfit(temps, pos, 1)
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
    
    focusModeler = FocusModeler(config)
    focusModeler.loadResults(filterID = 'r')
    #focusModeler.plotResults_individual()
    #focusModeler.plotResults()
    #%%
    fig, axes = plt.subplots(2, 1, figsize = (5,8))
    
    ax = axes[0]
    temps = focusModeler.results['temperatures']['telescope_ambient']
    pos = focusModeler.results['position']
    param0 = np.polyfit(temps, pos, 1)
    posFit0 = np.polyval(param0, temps)
    resid0 = np.abs(pos - posFit0)
    sigma0 = np.std(resid0)
    scale = .75
    flags = resid0 > scale*sigma0
    
    model0_x = np.linspace(min(temps), max(temps), 100)
    model0_y = np.polyval(param0, model0_x)
    
    param1 = np.polyfit(temps[flags == False], pos[flags == False], 1)
    model_x = np.linspace(min(temps), max(temps), 100)
    model_y = np.polyval(param1, model_x)
    
    ax.plot(temps, pos, 'o', label = 'All Data')
    ax.plot(temps[flags == True], pos[flags == True], 'o', label = 'Flagged Outliers')
    ax.plot(model0_x, model0_y, 'g--', label = f'Initial Fit for Outlier ID')
    ax.plot(model_x, model_y, 'r-', label = f'Fit: Focus = {param1[0]:.3f}'+'$xT_{AMBIENT}$' + f' + {param1[1]:.3f}')
    ax.legend()
    ax.set_ylabel('Focus Position [micron]')
    ax.set_xlabel('Ambient Temperature [C]')
    ax.set_title('Focus Model')
    
    ax = axes[1]
    ax.plot(temps, resid0, 'o')
    ax.plot(model0_x, model0_y*0.0, 'g--')
    ax.plot(model0_x, model0_x*0.0 + scale*sigma0, 'r--', label = f'+/- {scale}$\sigma$')
    ax.plot(model0_x, model0_x*0.0 - scale*sigma0, 'r--')
    ax.set_ylabel('Focus Initial Fit Residual [micron]')
    ax.set_xlabel('Ambient Temperature [C]')
    ax.set_title('Outlier Identification')
    ax.legend()
    plt.tight_layout()