#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jan 18 18:26:44 2022

@author: nlourie
"""

import numpy as np
import os
import glob
from datetime import datetime

def getLastModifiedFile(directory, name = '*'):
    """
    
    Gets the last modified file in the directory.
    
    If there are multiple with the same modification date, then get the first from the list
    
    directory is a complete filepath
    
    name: search specifier for file. '*' is anything, but can also do things like "*.txt"
    
    return the filepath of the last modified file

    """
    
    files = np.array(glob.glob(os.path.join(directory, name)))
    
    modtimes = np.array([os.stat(file).st_mtime for file in files])
    
    # get the most recent file(s)
    latest = files[modtimes == np.max(modtimes)]
    
    # return the first element of the latest array
    latest_filepath = latest[0]
    
    return latest_filepath
    
            
        
if __name__ == '__main__':
    
    directory = os.path.join(os.getenv("HOME"), 'data', 'schedules', 'ToO', 'HighPriority')
    name = '*.db'
    #latest_filepath = getLastModifiedFile(directory, name = '*.db')
    
    files = np.array(glob.glob(os.path.join(directory, name)))
    
    if len(files) == 0:
        latest_filepath = None
        
    else:
        modtimes = np.array([os.stat(file).st_mtime for file in files])
        
        # get the most recent file(s)
        latest = files[modtimes == np.max(modtimes)]
        
        # return the first element of the latest array
        latest_filepath = latest[0]
    
    #return latest_filepath
    
    print(f'the most recent file is: {latest_filepath}')