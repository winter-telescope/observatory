#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Aug  2 19:17:51 2021

@author: cruzss
"""
import os
import argparse
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


if __name__ == '__main__':
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--p", type=str,help='filepath')
    args = parser.parse_args()
    
    df = pd.read_csv(args.p + 'x_y.csv')
    print(df)
    x = df['x'].tolist()
    y = df['y'].tolist()
    df = pd.read_csv(args.p + 'fwhm.csv')
    med_fwhms = df['med_fwhms'].to_numpy()
    std_fwhms = df['std_fwhms'].to_numpy()
    df = pd.read_csv(args.p + 'filter_range.csv')
    filter_range = df['filter_range'].to_numpy()
    
    fig = plt.figure()
    plt.errorbar(filter_range,med_fwhms,yerr=std_fwhms,fmt='.',c='red')
    plt.plot(x,y)
    plt.title('Best FWHM : %.1f arcsec'%(np.min(med_fwhms)))
    plt.savefig('/home/winter/data/plots_focuser/latest_focusloop.pdf', bbox_inches='tight')