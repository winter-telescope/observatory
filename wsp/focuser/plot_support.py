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

import plot_curve

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
    focus_vals = filter_range
    
    popt, pcov = plot_curve.fit_parabola(focus_vals, med_fwhms, std_fwhms)
    
    x = np.linspace(np.min(focus_vals), np.max(focus_vals), 1000)
    y = plot_curve.parabola(x, *popt)
    
    perr = np.sqrt(np.diag(pcov))
    x0_fit = popt[0]
    x0_err = perr[0]
    
    #print(f"x0 from fit = {x0_fit}")
    #print(f"x0 = [{x0_fit:.0f} +/- {x0_err:.0f}] microns ({x0_err/x0_fit*100:.0f}%)")
    
    best_fwhm = plot_curve.parabola(x0_fit, *popt)
    
    fig = plt.figure()
    plt.errorbar(filter_range,med_fwhms,yerr=std_fwhms,fmt='.',c='red')
    plt.plot(x,y)
    plt.title(f'Best FWHM: {best_fwhm:.2f} @ focus = {x0_fit:.0f}')
    plt.savefig('/home/winter/data/plots_focuser/latest_focusloop.jpg', bbox_inches='tight')