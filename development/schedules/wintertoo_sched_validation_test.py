#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jun  7 09:29:29 2022

@author: winter
"""

import os
import wintertoo.validate
#from wintertoo import validate as wintertoo_validate
import pandas as pd
import sqlalchemy as db

schedulepaths = [os.readlink(os.path.join(os.getenv("HOME"), 'data', 'nightly_schedule.lnk')),
                 os.path.join(os.getenv("HOME"), 'data','schedules','ToO','timed_requests_06_08_2022_12_1654715434_.db')]

for schedulepath in schedulepaths:
    engine = db.create_engine('sqlite:///'+schedulepath)
    
    conn = engine.connect()
    df = pd.read_sql('SELECT * FROM summary;',conn)
    
    df['priority'] = 0
    
    #df['origin_filename'] = too_file
    #full_df = pd.concat([full_df,df])
    conn.close()
    
    def validateSchedule(df):
        # try to validate the schedule:
        try:
            wintertoo.validate.validate_schedule_df(df)
            return True
        
        except Exception as e:
            #print(e)
            print('schedule not valid')
            
            return False
        
    schedvalid = validateSchedule(df)
    print(f'Schedulefile: {schedulepath}')
    print(f'Valid Schedule? {schedvalid}')