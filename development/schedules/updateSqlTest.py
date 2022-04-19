#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Apr  9 04:24:19 2022

@author: nlourie
"""

import sqlalchemy as db
import os




schedulefile = os.path.join(os.getenv("HOME"), 'data','schedules','ToO','timed_requests_04_09_2022_04_1649502448_.db')

engine = db.create_engine('sqlite:///' + schedulefile)    
conn = engine.connect()
print('scheduler: successfully connected to db')
print()

#metadata = db.MetaData()
#summary = db.Table('Summary', metadata, autoload=True, autoload_with=engine)

obstime_mjd = (59677.9861111111	+ 59678.5416666667)/2


#get

# display all the rows
stmt = f'SELECT * from summary'
tmpresult = conn.execute(stmt)
alldata = tmpresult.fetchall()
print('All observations:')
for i in range(len(alldata)):
    row = dict(alldata[i])
    print(f'  {i}: obsHistID = {row["obsHistID"]}, Priority = {row["Priority"]}, validStop = {row["validStop"]}, observed = {row["observed"]}')


print()
# get all the rows that can be observed
stmt = f'SELECT obsHistID, validStop, Priority, observed from summary WHERE validStart <= {obstime_mjd} and validStop >= {obstime_mjd} and observed = 4 ORDER by Priority, validStop'
tmpresult = conn.execute(stmt)

dataRanked = tmpresult.fetchall()

print('Selected Observations Ranked by Priority, then validStop:')
for i in range(len(dataRanked)):
    row = dict(dataRanked[i])
    print(f'  {i}: obsHistID = {row["obsHistID"]}, Priority = {row["Priority"]}, validStop = {row["validStop"]}, observed = {row["observed"]}')





"""

# log that the observation was dispatched
stmt = 'UPDATE summary SET observed = 4 WHERE obsHistID = 0'
conn.execute(stmt)

"""
"""
stmt = 'SELECT obsHistID, observed from summary'
tmpresult = conn.execute(stmt)

tmpresult.execute(stmt)

data = tmpresult.fetchall()

"""






conn.close()
