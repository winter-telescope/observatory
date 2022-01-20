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
import yaml
import sys
from datetime import datetime
import pytz

import plot_curve

# add the wsp directory to the PATH
wsp_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),'wsp')
sys.path.insert(1, wsp_path)

print(f'plot_support: wsp_path = {wsp_path}')


from alerts import alert_handler

#%%
if __name__ == '__main__':
    
    
    
    
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--p", type=str,help='filepath')
    parser.add_argument("--t", type=float, help = 'timestamp')
    args = parser.parse_args()
    
    dirpath = args.p
    timestamp_utc = args.t
    
    if dirpath is None:
        dirpath = os.path.join(os.getenv("HOME"), 'data', 'df_focuser')
    
    df = pd.read_csv(os.path.join(dirpath, 'x_y.csv'))
    print(df)
    #x = df['x'].tolist()
    #y = df['y'].tolist()
    df = pd.read_csv(os.path.join(dirpath, 'fwhm.csv'))
    med_fwhms = df['med_fwhms'].to_numpy()
    std_fwhms = df['std_fwhms'].to_numpy()
    df = pd.read_csv(os.path.join(dirpath, 'filter_range.csv'))
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
    plt.errorbar(filter_range,med_fwhms,yerr=std_fwhms,fmt='.',c='red', capsize = 2)
    plt.plot(x,y)
    
    title = f'Best FWHM: {best_fwhm:.2f} arcmin @ focus = {x0_fit:.0f}'
    if timestamp_utc is None:
        pass
    else:
        utc = datetime.fromtimestamp(timestamp_utc, tz = pytz.utc)
        local_datetime_str = datetime.strftime(utc.astimezone(tz = pytz.timezone('America/Los_Angeles')), '%Y-%m-%d %H:%M:%S')
        title = title + f'\nLocal Time = {local_datetime_str}'
    
    plt.title(title)
    plt.xlabel('Focus Position [microns]')
    plt.ylabel('Mean FWHM [arcmin]')
    plt.grid('on')
    plt.savefig('/home/winter/data/plots_focuser/latest_focusloop.jpg', bbox_inches='tight')
    
    try:        
        focus_plot = '/home/winter/data/plots_focuser/latest_focusloop.jpg'
        
        auth_config_file  = wsp_path + '/credentials/authentication.yaml'
        user_config_file = wsp_path + '/credentials/alert_list.yaml'
        alert_config_file = wsp_path + '/config/alert_config.yaml'

        auth_config  = yaml.load(open(auth_config_file) , Loader = yaml.FullLoader)
        user_config = yaml.load(open(user_config_file), Loader = yaml.FullLoader)
        alert_config = yaml.load(open(alert_config_file), Loader = yaml.FullLoader)

        alertHandler = alert_handler.AlertHandler(user_config, alert_config, auth_config)
    
        focus_plot = '/home/winter/data/plots_focuser/latest_focusloop.jpg'
        alertHandler.slack_postImage(focus_plot)
        
        
        
    
    except Exception as e:
        msg = f'wintercmd: Unable to post focus graph to slack due to {e.__class__.__name__}, {e}'
        print(msg)
    