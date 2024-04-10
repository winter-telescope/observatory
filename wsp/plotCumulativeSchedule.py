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
from matplotlib.patches import Polygon
import matplotlib.colors as colors
import matplotlib.cm as cmx
from astropy.coordinates import SkyCoord
import sqlalchemy


wsp_path = os.path.dirname( os.path.abspath(__file__) )
sys.path.insert(1, wsp_path)

auth_config_file  = wsp_path + '/credentials/authentication.yaml'
user_config_file = wsp_path + '/credentials/alert_list.yaml'
alert_config_file = wsp_path + '/config/alert_config.yaml'


auth_config  = yaml.load(open(auth_config_file) , Loader = yaml.FullLoader)
user_config = yaml.load(open(user_config_file), Loader = yaml.FullLoader)
alert_config = yaml.load(open(alert_config_file), Loader = yaml.FullLoader)



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
                    exposures.fid, exposures."expmjd", exposures."exptime",exposures.airmass,
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

#history = history[history['expMJD']>60310]
#ra  = np.array(qresult[:,27],dtype=np.float32)
ra = np.array(history['ra'], dtype=np.float32)#[0:100]
#ra = ra / 24.0 * 360.0 * np.pi/180.0
#ra[ra > np.pi] -= 2*np.pi
dec = np.array(history['dec'], dtype=np.float32)#[0:100]
#dec = np.array(qresult[:,28],dtype=np.float32)
#dec = dec * np.pi / 180.0


ra  = np.array(ra,dtype=np.float32) * np.pi/180.0
ra[ra > np.pi] -= 2*np.pi
dec = np.array(dec,dtype=np.float32) * np.pi/180.0

ra_deg = ra * (180/np.pi)
dec_deg = dec * (180/np.pi)

print(ra_deg, dec_deg)

#print(dec_deg*180./np.pi)
# Calculate number of instances per field
unique_positions, counts = np.unique(np.vstack((ra_deg, dec_deg)).T, axis=0, return_counts=True)

print(len(history), len(unique_positions), np.median(counts), np.max(counts))

# Round RA and DEC to the nearest degree to group observations into 1-degree squares
ra_rounded = np.round(ra_deg)
dec_rounded = np.round(dec_deg)

# Calculate the number of unique rounded positions
unique_positions_rounded, counts_rounded = np.unique(np.vstack((ra_rounded, dec_rounded)).T, axis=0, return_counts=True)

# The number of unique positions gives an estimate of the covered area in square degrees
estimated_covered_area = len(unique_positions_rounded)

print(f"Estimated covered area: {estimated_covered_area} square degrees")

#%%

# Setup plot
fig2 = plt.figure(figsize=(8,6), dpi=1200)
ax2 = fig2.add_axes([0.05,0.05,0.8,0.8], projection='aitoff')
field_size = 1 # degree on sky
half_size = field_size / 2

# Create a colormap based on the number of instances
norm = plt.Normalize(vmin=np.min(counts), vmax=np.max(counts))
cmap = cm.autumn

for pos, count in zip(unique_positions, counts):
    rad_dec = pos[1] * np.pi / 180
    rad_ra = pos[0] * np.pi / 180
    decsB = pos[1] - half_size
    decsT = pos[1] + half_size
    radiffB = (half_size*np.pi/180)/np.cos(decsB*np.pi/180)
    radiffT = (half_size*np.pi/180)/np.cos(decsT*np.pi/180)
    ra1 = rad_ra - radiffB
    ra2 = rad_ra + radiffB
    ra4 = rad_ra - radiffT
    ra3 = rad_ra + radiffT
    color = cmap(norm(count))
    ax2.fill([ra1, ra2, ra3, ra4], [rad_dec - half_size*np.pi/180, rad_dec - half_size*np.pi/180, rad_dec + half_size*np.pi/180, rad_dec + half_size*np.pi/180], color=color, alpha=0.5, edgecolor='none')

# Add color bar
sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
sm.set_array([])
cbar = fig2.colorbar(sm, ax=ax2, orientation='vertical', fraction=0.02, pad=0.04)
cbar.set_label('Number of Visits')


figname = os.path.join(os.getenv("HOME"),'data','skymap_cumulative.jpg')
plt.savefig(figname, bbox_inches='tight')

