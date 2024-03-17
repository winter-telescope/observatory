#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Feb 17 07:41:11 2024

@author: nlourie
"""

import pandas as pd
import sqlalchemy as db
import os
import glob

config = dict({
                # location of the schedule files (home + this directory)
                "scheduleFile_directory": 'data/schedules',
                "scheduleFile_nightly_prefix": 'nightly_',
                "scheduleFile_nightly_link_directory": 'data',
                "scheduleFile_nightly_link_name": 'nightly_schedule.lnk',
                
                # ToO: Target of Opportunity Scheduling
                "scheduleFile_ToO_directory": 'data/schedules/ToO',
                })


def get_planned_exptimes():
    # get all the files in the ToO High Priority folder
    ToO_schedule_directory = os.path.join(os.getenv("HOME"), config['scheduleFile_ToO_directory'])
    schedules_to_query = glob.glob(os.path.join(ToO_schedule_directory, '*.db'))
    
    # also get the nightly schedule
    
    nightlyschedulefile = os.path.realpath(os.path.join(os.getenv("HOME"), config['scheduleFile_nightly_link_directory'], config['scheduleFile_nightly_link_name']))
    
    schedules_to_query.append(nightlyschedulefile)
    
    print(f'found these schedules to query: {schedules_to_query}')
    print(f'analyzing schedules...')
    
    if len(schedules_to_query) > 0:
        # bundle up all the schedule files in a single pandas dataframe
        full_df = pd.DataFrame()
        # add all the ToOs
        for schedulefile in schedules_to_query:
            try:
                ### try to read in the SQL file
                engine = db.create_engine('sqlite:///'+schedulefile)
                conn = engine.connect()
                df = pd.read_sql('SELECT * FROM summary;',conn)
                conn.close()
                
                df['image_exptime'] = df['visitExpTime']/df['ditherNumber']
                                    
                # now add the schedule to the master TOO list
                full_df = pd.concat([full_df,df])
                
            except Exception as e:
                print(f'could not load schedule, {e}')
                
    unique_exptimes = full_df['image_exptime'].unique()
    print()
    print(f'Unique Exptimes = {unique_exptimes}')
    return unique_exptimes

get_planned_exptimes()