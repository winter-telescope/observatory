#!/usr/bin/env python3

import os
from datetime import datetime
import sqlalchemy as db
from astropy.time import Time
import numpy as np
import pathlib
import yaml
import sys

import matplotlib.pyplot as plt
from astropy.coordinates import SkyCoord

from alerts import alert_handler

wsp_path = os.path.dirname( os.path.abspath(__file__) )
sys.path.insert(1, wsp_path)

auth_config_file  = wsp_path + '/credentials/authentication.yaml'
user_config_file = wsp_path + '/credentials/alert_list.yaml'
alert_config_file = wsp_path + '/config/alert_config.yaml'

auth_config  = yaml.load(open(auth_config_file) , Loader = yaml.FullLoader)
user_config = yaml.load(open(user_config_file), Loader = yaml.FullLoader)
alert_config = yaml.load(open(alert_config_file), Loader = yaml.FullLoader)

alertHandler = alert_handler.AlertHandler(user_config, alert_config, auth_config)

############# The historical log ###############
#### (Plot survey history with blue dots) #######

filenm = '/home/winter/data/WINTER_ObsLog.db'
engine = db.create_engine('sqlite:///'+filenm)
conn = engine.connect()
metadata = db.MetaData()
summary = db.Table('Observation',metadata,autoload=True,autoload_with=engine)
mjdnow = Time(datetime.utcnow()).mjd+2

try:
    result = conn.execute(summary.select().where(summary.c.expMJD <= mjdnow))
except:
    print("Failed")

qresult = np.array(result.fetchall())

ra  = np.array(qresult[:,27],dtype=np.float32)
ra = ra / 24.0 * 360.0 * np.pi/180.0
ra[ra > np.pi] -= 2*np.pi
dec = np.array(qresult[:,28],dtype=np.float32)
dec = dec * np.pi / 180.0

plt.figure()
plt.subplot(111,projection='aitoff')
plt.grid(True)
plt.scatter(ra,dec,alpha=0.2,label='History')

################# Tonight ##################
################ (Red dots) #################

filenm = '/home/winter/data/nightly_schedule.lnk'
engine = db.create_engine('sqlite:///'+filenm)
conn = engine.connect()
metadata = db.MetaData()
summary = db.Table('Summary',metadata,autoload=True,autoload_with=engine)

try:
    result = conn.execute(summary.select().where(summary.c.expMJD <= mjdnow))
except:
    print("Failed")

qresult = np.array(result.fetchall())
    
# Already in radians
ra  = np.array(qresult[:,4],dtype=np.float32)
ra[ra > np.pi] -= 2*np.pi
dec = np.array(qresult[:,5],dtype=np.float32)

plt.scatter(ra,dec,alpha=0.2, color='r',label='Tonight')
plt.legend(loc='lower right',frameon=True)
# plt.show()

figname = os.path.join(os.getenv("HOME"),'data','skymap_tonight.jpg')
plt.savefig(figname)

alertHandler.slack_postImage(figname)
