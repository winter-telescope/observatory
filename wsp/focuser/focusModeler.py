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
        
        self.results = dict({'position' : [],
                             'position_err' : [],
                             'temperatures' : {},
                             })
        self._temperatures_keywords = ['m1',
                                      'm2',
                                      'm3',
                                      'telescope_ambient',
                                      'outside_pcs']
        self._setupResultsDict()
        
        self.loadResults()
    
    def _setupResultsDict(self):
        
        # add a list to the results dict for each entry in the temperatures keywords
        for key in self._temperatures_keywords:
            self.results['temperatures'].update({key : []})
            
        
    def loadResults(self):
                
        # load all the focus data from the folder
        
        
        self._resultsDir = os.path.join(os.getenv("HOME"), 
                                  self.config['focus_loop_param']['results_log_parent_dir'], 
                                  self.config['focus_loop_param']['results_log_dir'])
        
        self._resultFiles = glob.glob(os.path.join(self._resultsDir, '*.json'))
        
        for file in self._resultFiles:
            try:
                resultDict = json.load(open(file))
                # try to load the results from the file into the dictionary
                self.results['position'].append(resultDict['results']['focus'])
                self.results['position_err'].append(resultDict['results']['focus_err'])
                for key in self._temperatures_keywords:
                    temp = resultDict['temperatures'][key]
                    self.results['temperatures'][key].append(temp)
    
            except Exception as e:
                print(f'could not load results data from {file}: {type(e)}: {e}')
    
    def plotResults(self):
        fig, ax = plt.subplots(1,1, figsize = (6,6))
        
        for temp in self._temperatures_keywords:
            #ax.plot(self.results['temperatures'][temp], self.results['position'], 'o', label = temp)
            ax.errorbar(self.results['temperatures'][temp], self.results['position'],  yerr = self.results['position_err'], 
                        fmt = 'o', capsize = 5, label = temp)
        ax.set_title('Focus Results')
        ax.set_ylabel('Focuser Position [micron]')
        ax.set_xlabel('Temperature [C]')
        plt.legend()
            
if __name__ == '__main__':
    config = yaml.load(open(wsp_path + '/config/config.yaml'), Loader = yaml.FullLoader)
    
    focusModeler = FocusModeler(config)
    
    focusModeler.plotResults()