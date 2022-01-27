#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jan 25 11:15:41 2022

@author: frostig
"""


import json
import numpy as np
import pandas as pd
from sqlalchemy import create_engine
from datetime import datetime




def make_timed_request(env, ra, dec, exptime, n_exp, start, stop, exp_arr, filt, dither): 
    
    if env == "PRODUCTION":
        save_path = 'sqlite:////home/winter/data/schedules/ToO/HighPriority/'
    else:
        save_path = 'sqlite:///'
        
    # make sqlite database
    date = datetime.now().strftime('%m_%d_%Y_%H_%s')
    engine = create_engine(save_path+'timed_requests_'+date+'.db?check_same_thread=False', echo=True)
    sqlite_connection = engine.connect()
    
    # get header keys
    config_file = '../../wsp/config/scheduleconfig.json'
    
    with open(config_file, "r") as jsonfile:
        data = json.load(jsonfile)
    
    keys = data['Summary'].keys()
    key_array = []
    for key in keys:
        key_array.append(key)
        #print(key)
        
    # make dataframe structure
    n_lines = n_exp
    ind = range(n_lines)
    df_data = np.zeros((n_lines, len(key_array)))
    df_data[:] = np.NaN
    save_df = pd.DataFrame(data=df_data, index=ind,
                           columns=key_array)
    
    # add values
    save_df["obsHistID"] = ind
    save_df["requestID"] = ind
    save_df["propID"] = 4
    save_df["fieldRA"] = ra
    save_df["fieldDec"] = dec
    save_df["propID"] = 4
    save_df["validStart"] = start
    save_df["validStop"] = stop
    save_df["expMJD"] = exp_arr
    save_df["filter"] = filt
    save_df["dither"] = dither
    save_df["fieldID"] = 999999999 # protected id for guest obs
    
    #save_df.reset_index(drop=True, inplace=True)
    

    # save
    sqlite_table = "Summary"
    
    save_df.to_sql(sqlite_table, sqlite_connection, if_exists='replace', index=False)
    sqlite_connection.close()
    
