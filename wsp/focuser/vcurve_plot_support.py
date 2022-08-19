#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Aug  2 19:17:51 2021

@author: cruzss
"""
import os
import argparse
import matplotlib.pyplot as plt
import matplotlib as mpl
import numpy as np
import pandas as pd
import yaml
import sys
from datetime import datetime
import pytz
import json

import plot_curve

# add the wsp directory to the PATH
wsp_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),'wsp')
sys.path.insert(1, wsp_path)

print(f'plot_support: wsp_path = {wsp_path}')


from alerts import alert_handler
from utils import utils
from focusing import plot_curve


#plt.style.use('tableau-colorblind10')
# from here: https://gist.github.com/thriveth/8560036
CB_color_cycle = ['#377eb8', '#ff7f00', '#4daf4a',
                  '#f781bf', '#a65628', '#984ea3',
                  '#999999', '#e41a1c', '#dede00']
mpl.rcParams['axes.prop_cycle'] = mpl.cycler(color=CB_color_cycle) 


#%%
if __name__ == '__main__':
    
    config = utils.loadconfig(os.path.join(wsp_path, 'config', 'config.yaml'))
    
    
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--p", type=str,help='results filepath')
    parser.add_argument("--t", type=float, help = 'timestamp')
    args = parser.parse_args()
    print(f'plot_support: args = {args}')
    results_filepath = args.p
    timestamp_utc = args.t
    
    results_parent_dir = os.path.join(os.getenv("HOME"), config['focus_loop_param']['results_log_parent_dir'])
    results_log_dir = os.path.join(results_parent_dir, config['focus_loop_param']['results_log_dir'])
    results_log_last_link = os.path.join(results_parent_dir, config['focus_loop_param']['results_log_last_link'])
    
    if results_filepath is None:
        results_filepath = os.readlink(results_log_last_link)
    
    
    
    print(f'plot_support: loading focus data from {results_filepath}')
    
    # load up the data
    results = json.load(open(results_filepath))
    
    pos     = results['vcurve_fit']['raw_data']['x']
    HFD_med = results['vcurve_fit']['raw_data']['y']
    HFD_stderr_med = results['vcurve_fit']['raw_data']['yerr']
    
    #pos_fit = results['vcurve_fit']['fit_data']['x']
    #HFD_fit = results['vcurve_fit']['fit_data']['y']
    
    xc_initial_guess = results['vcurve_fit']['param']['xc_initial_guess']
    xc      = results['vcurve_fit']['param']['xc']
    xc_err  = results['vcurve_fit']['param']['xc_err']
    ml      = results['vcurve_fit']['param']['ml']
    xa      = results['vcurve_fit']['param']['xa']
    xb      = results['vcurve_fit']['param']['xb']
    y0      = results['vcurve_fit']['param']['y0']
    delta      = results['vcurve_fit']['param']['delta']
    
    if xc_initial_guess is not None:
        xc_diff_from_model = abs(xc_initial_guess - xc)
    
    pos_fit = np.linspace(9500, 10500, 1000)
    HFD_fit = plot_curve.FocV(pos_fit, ml, xc, delta, y0, return_x = False)
    
    """
    # load up the parabolic fit data
    xc_par  = results['parabolic_fit']['param']['xc']
    xc_par_err = results['parabolic_fit']['param']['xc_err']
    A = results['parabolic_fit']['param']['A']
    B = results['parabolic_fit']['param']['B']
    FWHM_at_xc = results['parabolic_fit']['param']['FWHM_at_xc']
    
    pos_par = results['parabolic_fit']['raw_data']['x']
    FWHM = results['parabolic_fit']['raw_data']['y']
    FWHM_err = results['parabolic_fit']['raw_data']['yerr']
    
    
    pos_par_fit = np.linspace(min(pos_par), max(pos_par), 1000)
    FWHM_fit = plot_curve.parabola(pos_par_fit, xc_par, A, B)
    """
    
    pos_par = results['fwhm']['raw_data']['x']
    FWHM = results['fwhm']['raw_data']['y']
    FWHM_err = results['fwhm']['raw_data']['yerr']
    
    results_plot_filename = results_filepath.split('/')[-1].strip('.json')
    results_plot_filepath = os.path.join(results_log_dir, results_plot_filename+'.png')
    starttime_string = results_plot_filename.strip('focusResults_')
    
    #df = np.abs(xc - xc_par)
    
    
    
    fig, axes = plt.subplots(2,1, figsize = (8,8))
    ax = axes[0]
    
    #fig, axes = plt.subplots(1,1, figsize = (8,4))
    #ax = axes
    
    ### Upper plot: V-curve fit to HFD ###
    ax.errorbar(pos, HFD_med, yerr = HFD_stderr_med, fmt = 'ko', capsize = 5, capthick = 2, label = 'data')
    ax.plot(pos_fit, HFD_fit, '-', label = f'V-Curve Fit')
    xmin = min(pos_fit)
    xmax = max(pos_fit)
    ax.set_xlim(xmin, xmax)
    ax.set_ylabel('HFD [arcsec]')
    ax.set_xlabel('Focuser Position [micron]')
    yline = np.linspace(-10, 10, 100)
    #xc_label = f'xc = [{xc:.0f} +/- {xc_err:.0f}] ({100*xc_err/xc:.0f}%)'
    xc_label = f'xc = {xc:.0f}'
    xcplot = ax.plot(xc+0*yline, yline, '--', label = xc_label)
    xc_color = xcplot[0].get_color()
    if xc_initial_guess is not None:
        thermline = ax.plot(xc_initial_guess+0*yline, yline, '--', label = f'xc thermal model = {xc_initial_guess:.0f}')

    # add the data from the best focus image if present
    if 'best_focus_image' in results:
        
        ax.scatter(xc, results['best_focus_image']['hfd']['med'], s = 100, color = xc_color, edgecolors = 'k', label = 'best focus', zorder = 100)
        
    ax.legend(fontsize = 8)

    ax.set_ylim(0,6)
    
    ### Lower plot: parabolic fit to FWHM ###
    ax = axes[1]
    ax.errorbar(pos_par, FWHM, yerr = FWHM_err, fmt = 'ko', capsize = 5, capthick = 2, label = 'data')
    #ax.plot(pos_par_fit, FWHM_fit, '-', label = f'Parabolic Fit')
    ax.set_xlim(xmin, xmax)
    ax.set_xlabel('Focuser Position [micron]')
    ax.set_ylabel('FWHM [arcsec]')
    yline = np.linspace(0, 8, 100)
    #xc_label = f'xc = [{xc_par:.0f} +/- {xc_par_err:.0f}] ({100*xc_par_err/xc_par:.0f}%)'
    #xc_label = f'xc = {xc_par:.0f}'
    ax.plot(xc+0*yline, yline, '--', color = xc_color, label = xc_label)
    if xc_initial_guess is not None:
        ax.plot(xc_initial_guess+0*yline, yline, '--', color = thermline[0].get_color(), 
                            label = f'xc thermal model = {xc_initial_guess:.0f}')
    if 'best_focus_image' in results:
        best_fwhm = results['best_focus_image']['fwhm']['med']
        ax.scatter(xc, best_fwhm, s = 100, color = xc_color, edgecolors = 'k', label = 'best focus', zorder = 100)
    
    ax.legend(fontsize = 8)
    
    
        
        
        
    # create the figure title
    title = f'{results["telemetry"]["filterID"]}-band: '
    title+= f'Focus Best Fit = {xc:.0f}'
    if 'best_focus_image' in results:
        title+= f', FWHM = {best_fwhm:.1f}"'
    #title+='Focus = [{xc:.0f} +/- {xc_err:.0f}] micron ({100*xc_err/xc:.0f}%)'
    if xc_initial_guess is not None:
        title+= f'\nThermal Model = {xc_initial_guess:.0f}, $\Delta$ = {xc_diff_from_model:.0f}'
    
    #title += f'\nBest FWHM (est): {FWHM_at_xc:.2f} arcsec'
    
    try:
        title = title + f'\n{starttime_string}'
    except:
        pass
    
    ax = axes[0]
    ax.set_title(title)

    # save the image and plot it
    plt.tight_layout()
    # now save the plot
    plt.savefig(results_plot_filepath)
    
    results_plot_last_link = os.path.join(results_parent_dir, config['focus_loop_param']['results_plot_last_link'])

    
    try:        
        #focus_plot = '/home/winter/data/plots_focuser/latest_focusloop.jpg'
        focus_plot = results_plot_filepath
        
        auth_config_file  = wsp_path + '/credentials/authentication.yaml'
        user_config_file = wsp_path + '/credentials/alert_list.yaml'
        alert_config_file = wsp_path + '/config/alert_config.yaml'

        auth_config  = yaml.load(open(auth_config_file) , Loader = yaml.FullLoader)
        user_config = yaml.load(open(user_config_file), Loader = yaml.FullLoader)
        alert_config = yaml.load(open(alert_config_file), Loader = yaml.FullLoader)

        alertHandler = alert_handler.AlertHandler(user_config, alert_config, auth_config)
    
        alertHandler.slack_postImage(focus_plot)
        
        
        
    
    except Exception as e:
        msg = f'wintercmd: Unable to post focus graph to slack due to {e.__class__.__name__}, {e}'
        print(msg)
    