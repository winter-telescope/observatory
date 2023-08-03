#!/usr/bin/env python3

import os
from datetime import datetime
import sqlalchemy as db
from astropy.time import Time
import numpy as np
import pathlib
import yaml
import sys
import psycopg
import  pandas as pd
import matplotlib.pyplot as plt
import matplotlib.cm as cm
from astropy.coordinates import SkyCoord
import sqlalchemy

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

#filenm = '/home/winter/data/WINTER_ObsLog.db'
#engine = db.create_engine('sqlite:///'+filenm)
#conn = engine.connect()
#metadata = db.MetaData()
#summary = db.Table('Observation',metadata,autoload=True,autoload_with=engine)



mjdnow = Time(datetime.utcnow()).mjd+2

try:
    conn = psycopg.connect('dbname=winter user='+str(auth_config['drp']['USERNAME'])+' password='+str(auth_config['drp']['PASSWORD'])+
                       ' host='+str(auth_config['drp']['HOSTNAME']))
    
    cur = conn.cursor()

    command = '''SELECT exposures.progname, exposures.fieldid, exposures.ra, exposures.dec,
                    exposures.fid, exposures."expMJD", exposures."ExpTime",exposures.airmass,
                    programs.progid, programs.progname, programs.progtitle FROM exposures INNER JOIN programs ON
                    programs.progname=exposures.progname; '''

    cur.execute(command)

    res = cur.fetchall()

    history = pd.DataFrame(res, columns=['puid', 'fieldid', 'ra', 'dec', 'fid', 'expMJD',
                                    'ExpTime', 'airmass', 'progid', 'progname', 'progtitle'])
#    print(history)
except Exception as e:
    history = pd.DataFrame(columns=['puid', 'fieldid', 'ra', 'dec', 'fid', 'expMJD',
                                    'ExpTime', 'airmass', 'progid', 'progname', 'progtitle'])
    print("Failed to grab history: ", e)


#ra  = np.array(qresult[:,27],dtype=np.float32)
ra = np.array(history['ra'], dtype=np.float32)
ra = ra / 24.0 * 360.0 * np.pi/180.0
ra[ra > np.pi] -= 2*np.pi
dec = np.array(history['dec'], dtype=np.float32)
#dec = np.array(qresult[:,28],dtype=np.float32)
dec = dec * np.pi / 180.0

plt.figure()
plt.subplot(111,projection='aitoff')
plt.grid(True)
#plt.scatter(ra,dec,alpha=0.2,label='History')

df_ra = history.groupby('progtitle').agg({'ra':lambda x: list(x)})
df_dec =history.groupby('progtitle').agg({'dec':lambda x: list(x)})

programs = np.unique(df_ra.index.get_level_values(0))
colors = cm.BuGn(np.linspace(0, 1, len(programs)))

for idx, prog in enumerate(programs):
    ra = list(df_ra[df_ra.index.get_level_values(0)==prog]['ra'])[0]
    dec = list(df_dec[df_dec.index.get_level_values(0)==prog]['dec'])[0]
    # RA and DEC are in degrees, but radians are needed for plotting
    ra  = np.array(ra,dtype=np.float32) * np.pi/180.0
    ra[ra > np.pi] -= 2*np.pi
    dec = np.array(dec,dtype=np.float32) * np.pi/180.0
    plt.scatter(ra,dec,alpha=0.1,label="history: "+prog, color = colors[idx])
#plt.legend(loc='lower right',frameon=True)

################# Tonight ##################
################ (Red dots) #################


file = '/home/winter/data/nightly_schedule.lnk'
dbEngine=sqlalchemy.create_engine('sqlite:///'+file)
df = pd.read_sql('select * from Summary',dbEngine)
df_ra = df.groupby('progTitle').agg({'raDeg':lambda x: list(x)})
df_dec = df.groupby('progTitle').agg({'decDeg':lambda x: list(x)})

programs = np.unique(df_ra.index.get_level_values(0))
colors = cm.OrRd(np.linspace(0.2, 1, len(programs)))

for idx, prog in enumerate(programs):
    ra = list(df_ra[df_ra.index.get_level_values(0)==prog]['raDeg'])[0]
    dec = list(df_dec[df_dec.index.get_level_values(0)==prog]['decDeg'])[0]
    # RA and DEC are in degrees, but radians are needed for plotting
    ra  = np.array(ra,dtype=np.float32) * np.pi/180.0
    ra[ra > np.pi] -= 2*np.pi
    dec = np.array(dec,dtype=np.float32) * np.pi/180.0
    plt.scatter(ra,dec,alpha=.9,label="tonight: "+prog, color = colors[idx])
plt.legend(loc='lower right',frameon=True)
# plt.show()

figname = os.path.join(os.getenv("HOME"),'data','skymap_tonight.jpg')
plt.savefig(figname)

alertHandler.slack_postImage(figname)
