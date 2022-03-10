import json
import numpy as np
import pandas as pd
from sqlalchemy import create_engine
from datetime import datetime
from utils import get_alt_az
import astropy.units as u 

camera_field_size = 0.26112 /2

git_path = '../daily_summer_scheduler/data/'

field_filename = git_path + 'SUMMER_fields.txt'

def deg_to_rad(x):
    return (x*np.pi) / 180


def get_ra_dec(camera, field_ids):
    
    if camera == "WINTER":
        camera_field_size = 1 / 2
        git_path = '../daily_winter_scheduler/data/'
        field_filename = git_path + 'WINTER_fields.txt'
    else:
        camera_field_size = 0.26112 /2
        git_path = '../daily_summer_scheduler/data/'
        field_filename = git_path + 'SUMMER_fields.txt'

    summer_fields = pd.read_csv(field_filename,
     names=['field_id','ra','dec','ebv','l','b',
         'ecliptic_lon', 'ecliptic_lat', 'number'],
     sep='\s+',usecols=['field_id','ra','dec', 'l','b', 
         'ecliptic_lon', 'ecliptic_lat'],index_col='field_id',
     skiprows=1)

    ras = []
    decs = []
    for f in field_ids:

        #f_sort = summer_fields.iloc[summer_fields['field_id'] == f]
        f_sort = summer_fields.loc[f]
        ras.append(f_sort.ra)
        decs.append(f_sort.dec)

    return ras, decs

# f_list = [240940, 240941, 240942]
# ra, dec = get_ra_dec(f_list)
# print("\n ra dec", ra, dec)

def make_fieldid_request(camera, save_path, config_path, subprogram, field_ids, exptime, n_repeat_req, start, stop, filt, dither): 
    
    # make sqlite database
    date = datetime.now().strftime('%m_%d_%Y_%H_%s')
    engine = create_engine(save_path+'timed_requests_'+date+'.db?check_same_thread=False', echo=True)
    sqlite_connection = engine.connect()
    
    # get header keys   
    with open(config_path, "r") as jsonfile:
        data = json.load(jsonfile)
    
    keys = data['Summary'].keys()
    key_array = []
    for key in keys:
        key_array.append(key)
        #print(key)
        
    # get ras and dec for field list
    ra, dec = get_ra_dec(camera, field_ids)
    
    # convert to radians
    for i in range(len(ra)):
        ra[i] = deg_to_rad(ra[i])
        
    for i in range(len(dec)):
        dec[i] = deg_to_rad(dec[i])
        
    # make array of exposure start times
    #duration_seconds = (stop-start)*24*60*60
    n_exp = len(field_ids)*(n_repeat_req+1)
    exp_arr = np.linspace(start, stop, n_exp)
    # print('exp', exp_arr)

    
    # repeat blockof requests
    while n_repeat_req > 0:
        ra.extend(ra)
        dec.extend(dec)
        field_ids.extend(field_ids)
        
        n_repeat_req -=1
    

    # get alt and az from coordinates and time
    alt, az = get_alt_az(exp_arr, ra*u.radian, dec*u.radian)
        
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
    save_df["validStart"] = start
    save_df["validStop"] = stop
    save_df["visitTime"] = exptime
    save_df["visitExpTime"] = exptime
    save_df["expDate"] = np.floor(start)
    save_df["expMJD"] = exp_arr
    save_df["filter"] = filt
    save_df["dither"] = dither
    save_df["azimuth"] = az
    save_df["altitude"] = alt
    save_df["fieldID"] = field_ids
    save_df["subprogram"] = subprogram

    # save
    sqlite_table = "Summary"
    
    save_df.to_sql(sqlite_table, sqlite_connection, if_exists='replace', index=False)
    sqlite_connection.close()
    
f_list = [240940, 240941, 240942, 240943, 240944, 240945, 240946, 242289, 242290, 242291, 242292, 242293, 242294, 242295, 242296, 243640, 243641, 243642, 243643, 243644, 243645, 243646, 243647, 244992, 244993, 244994, 244995, 244996, 244997, 244998, 246345, 246346, 246347, 246348, 246349, 246350, 246351, 247698, 247699, 247700, 247701, 247702, 247703, 247704, 247705]
exptime = 30
n_repeat_req = 1
start = 59648.47916
stop = start + (len(f_list)*(n_repeat_req+1)*exptime / (24*60*60))
filt = 'r'
dither = 'N'    
#save_path = 'sqlite:////home/winter/data/schedules/ToO/HighPriority/'
save_path = 'sqlite:///'
config_path = '../../wsp/config/scheduleconfig.json'
subprogam = "neutrino_followup"
camera = "SUMMER"

make_fieldid_request(camera, save_path, config_path, subprogam, f_list, exptime, n_repeat_req, start, stop, filt, dither)
    
