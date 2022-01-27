#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jan 26 12:34:34 2022

@author: frostig
"""

import json
import numpy as np
from datetime import datetime 
from utils import get_field_ids
import re


def make_untimed_request(env, camera, data, field_opts, filters): 
    
    
    date = datetime.now().strftime('%m_%d_%Y_%H_%s')
    if env == "PRODUCTION":
        if camera == 'WINTER':
            write_path = '/home/winter/data/schedules/requests/winter_untimed_request'+date+'.json'
        else:
             write_path = '/home/winter/data/schedules/requests/summer_untimed_request'+date+'.json'
    else:
        if camera == 'WINTER':
            write_path = './winter_untimed_request'+date+'.json'
        else:
             write_path = './summer_untimed_request'+date+'.json'
    
    # parse priority (get string before : )
    nightly_priority = str(data['priority'])[:str(data['priority']) .index(":")]
    
    # parse field selections
    
    # sort by field ids
    if data['field_selection'] == field_opts[0]:
        field_selection = "field_ids"
        # check if ra and dec are empty 
        if len(data['ra']) == 0 or len(data['dec']) == 0:
            return 0
        else:
            # pasre ra dec
            ra = re.split(r',|\[|\]', data['ra'])
            ra = [i for i in ra if i]
            dec = re.split(r',|\[|\]', data['dec'])
            dec = [i for i in dec if i]
            field_cut = get_field_ids(ra, dec, units="degrees")
    
    # sort by ra and dec cuts
    elif data['field_selection'] == field_opts[1]: 
        # check if cuts are empty 
        if len(data['ra_cut']) == 0 or len(data['dec_cut']) == 0:
            return 0
        else:
            field_selection = "field_selections"
            if len(data['ra_cut']) != 0 and len(data['dec_cut']) != 0:
                ra_cut = re.split(r',|\[|\]', data['ra_cut']) 
                ra_cut = [float(i) for i in ra_cut if i]
                dec_cut = re.split(r',|\[|\]', data['dec_cut']) 
                dec_cut = [float(i) for i in dec_cut if i]
                field_cut = {"ra_range": ra_cut ,
                             "dec_range": dec_cut}
            elif len(data['ra_cut']) != 0 and len(data['dec_cut']) == 0:
                ra_cut = re.split(r',|\[|\]', data['ra_cut'])
                ra_cut = [float(i) for i in ra_cut if i]
                field_cut = {"ra_range": ra_cut}
            else:
                dec_cut = re.split(r',|\[|\]', data['dec_cut'])
                dec_cut = [float(i) for i in dec_cut if i]
                field_cut = {"dec_range": dec_cut}
                
    # sort by galactic longitude and latitude cuts
    elif data['field_selection'] == field_opts[2]:
        if len(data['ra_cut']) == 0 or len(data['dec_cut']) == 0:
            return 0
        else:
            field_selection = "field_selections"
            if len(data['ra_cut']) != 0 and len(data['dec_cut']) != 0:
                ra_cut = re.split(r',|\[|\]', data['ra_cut']) 
                ra_cut = [float(i) for i in ra_cut if i]
                dec_cut = re.split(r',|\[|\]', data['dec_cut']) 
                dec_cut = [float(i) for i in dec_cut if i]
                field_cut = {"l_range": ra_cut ,
                             "b_range": dec_cut}
            elif len(data['ra_cut']) != 0 and len(data['dec_cut']) == 0:
                ra_cut = re.split(r',|\[|\]', data['ra_cut'])
                ra_cut = [float(i) for i in ra_cut if i]
                field_cut = {"l_range": ra_cut}
            else:
                dec_cut = re.split(r',|\[|\]', data['dec_cut'])
                dec_cut = [float(i) for i in dec_cut if i]
                field_cut = {"b_range": dec_cut}
        
    # parse filter selections
    filter_choice = str(data['filter_choice'])[:str(data['filter_choice']) .index(":")]
    
    # convert filter names to id numbers
    filter_ids = []
    for filt in data['filters']:
         filter_ids.append(filters.index(filt)+1)
         
    
    
    program_data = {"program_name": "collaboration",
 		 "subprogram_name": str(data['prog_name']),
 		 "program_pi": str(data['name']),
 		 "program_observing_fraction": 0.0, # to be calculated later
 		 "subprogram_fraction": 0.0, # to be calculated later
         field_selection: field_cut, 
 		 "filter_choice": filter_choice,
 		 "filter_ids": filter_ids,
 		 "internight_gap_days": int(data['internight_gap_days']),
 		 "n_visits_per_night": int(data['n_visits_per_night']),
 		 "nightly_priority": nightly_priority,
                 "exposure_time": float(data['exp']),
 		 "active_months": "all"
    
    }

    # add optional arguments
    if data['intranight_gap_min'] != None:
        program_data['intranight_gap_min'] =int(data['intranight_gap_min'])

    if data['intranight_half_width_min'] != None:
        program_data['intranight_half_width_min'] =int(data['intranight_half_width_min'])
    
    json_data = json.dumps(program_data)
    
    with open(write_path, "w") as jsonfile:
        jsonfile.write(json_data)
        print("Write successful")
        
    return 1
        
#make_untimed_request("test_prog", "my_name")
