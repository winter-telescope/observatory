# Import following modules
from pywebio.input import *
from pywebio.output import *
from pywebio.session import *
from pywebio import start_server
import re

from make_timed_request import make_timed_request
from make_untimed_request import make_untimed_request
from utils import up_tonight
import astropy.units as u
from astropy.time import Time, TimeDelta
import numpy as np

import yaml
from astroplan import Observer
import datetime
import pytz
from astropy.coordinates import SkyCoord
import sys

env = "PRODUCTION"

if env == "PRODUCTION":
    too_path = '/home/winter/data/schedules/ToO/high_priority/'
    req_path = '/home/winter/data/schedules/requests/'
    wsp_path = '../../wsp'
    sys.path.insert(0, '../../wsp')
    from alerts import alert_handler

else:
    save_path = ''
  
# For checking Email, whether Valid or not.
regex = '^(\w|\.|\_|\-)+[@](\w|\_|\-|\.)+[.]\w{2,3}$'
  


    
def check_time_sensitive(data):

        
    # for checking Email
    if not (re.search(regex, data['email'])):
        return ('email', 'Invalid email!')
      

def check_time_insensitive(data):

        
    # for checking Email
    if not (re.search(regex, data['email'])):
        return ('email', 'Invalid email!')
    
    # for checking spaces in program name
    if (re.search(r"\s", data['prog_name'])):
        return ('prog_name', 'Program name cannot have spaces!')
    

      

def web_form():  
  
    units_coord = ['RA in hours/minutes/seconds (+19h50m41s); Dec in degrees/minutes/seconds (+08d50m58s)',  'Radians']
    units_time = ['MJD',  'Local Pacific time']
        
    # Ask for initial camera and observation type info
    type_obs = input_group("What sort of request are you submitting?" , [
                        radio("Timing", options=['Time sensitive', 'Time insensitive'], name='timing', required=True),
                        radio("Camera:", options=['WINTER', 'SUMMER'], name = 'camera', required=True)
                        ])
    
    # change filter list based on camera
    if type_obs['camera'] == 'WINTER':
        filters = ['Y',  'J', 'Hs']
    else:
        filters = ['u',  'g']
    
    # time sensitive options
    if type_obs['timing'] == 'Time sensitive':
    
        
        time_sensitive = input_group('Time sensitive observation request', [
                        input('Name', name='name', type=TEXT, required=True, PlaceHolder="Name"),
                        
                        input('Email', name='email', type=TEXT, required=True, PlaceHolder="user@gmail.com"),
                        
                        select(label='Select your units for right ascension and declination', options=units_coord, value='Radians', name='units_coord'),
                        
                        input('Right ascension', name='ra', type=TEXT, required=True, PlaceHolder="5.195 or +19h50m41s"),
                        
                        input('Declination', name='dec', type=TEXT, required=True, PlaceHolder="0.154 or +08d50m58s"),
                        
                        select(label='Select your units for the start and stop time', options=units_time, value='MJD', name='units_time'),
                        
                        input('Start time', name='start_time', type=TEXT, required=True, PlaceHolder="59605.0339 or 2022-01-25 16:55:54.420535"),
                        
                        input('Stop time', name='stop_time', type=TEXT, required=True, PlaceHolder="59605.0339 or 2022-01-25 16:55:54.420535"),
                        
                        input('Exposure time (s)', name='exp', type=FLOAT, required=True, PlaceHolder=""),
                        
                        select(label='Filter', options=filters, value='', name='filters'),
                        
                        radio("Dither", options=['Y', 'N'], name='dither', required=True),
                        
                        ] , validate=check_time_sensitive, cancelable=True)
        
        
    
       
        try:
            # check formatting
            if time_sensitive['units_time'] == 'MJD':
                tonight = np.floor(float(time_sensitive['start_time']))
                start_time = Time(float(time_sensitive['start_time']), format='mjd')
                stop_time = Time(float(time_sensitive['stop_time']), format='mjd')
            else: 
                Pacific = pytz.timezone("PST8PDT")
                # convert iso string to datetime object to astropy time object
                dt = datetime.datetime.fromisoformat(str(time_sensitive['start_time']))
                dt2 = Pacific.localize(datetime.datetime(dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second, dt.microsecond))
                dt3 = dt2.astimezone(pytz.utc)
                start_time = Time(dt3, scale='utc')
                
                dt = datetime.datetime.fromisoformat(str(time_sensitive['stop_time']))
                dt2 = Pacific.localize(datetime.datetime(dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second, dt.microsecond))
                dt3 = dt2.astimezone(pytz.utc)
                stop_time = Time(dt3, scale='utc')
                
                tonight = np.floor(start_time.mjd)
    
            
            if time_sensitive['units_coord'] == 'Radians':
                ra = float(time_sensitive['ra'])*u.radian
                dec = float(time_sensitive['dec'])*u.radian
            else: 
                ra = str(time_sensitive['ra'])
                dec = str(time_sensitive['dec'])
                loc = SkyCoord(ra=ra, dec=dec, frame='icrs')
                ra = loc.ra.radian*u.radian
                dec = loc.dec.radian*u.radian
                
            # make array of exposure start times
            duration_seconds = (stop_time.mjd-start_time.mjd)*24*60*60
            n_exp = int(duration_seconds / time_sensitive['exp'])
            exposures_arr = np.linspace(start_time.mjd, stop_time.mjd, n_exp)
            
            
            # check if target is up tonight
            is_up, str_up = up_tonight(tonight, ra, dec)
                
            
                          
            if is_up == True:
                # make databse 
                make_timed_request(env, ra, dec, time_sensitive['exp'], n_exp,
                                   start_time.mjd, stop_time.mjd,  exposures_arr,
                                   time_sensitive['filters'], time_sensitive['dither'])        
    
                # Display output using popup
                popup("Your target is up on the night requested and your request has been recorded. \n Details will be sent to:",
                  f"Name: {time_sensitive['name']}\
                  \nEmail: {time_sensitive['email']}",
                  closable=True)
                    
                if env == "PRODUCTION":
                        # set up the alert system to post to slack
                    auth_config_file  = wsp_path + '/credentials/authentication.yaml'
                    user_config_file = wsp_path + '/credentials/alert_list.yaml'
                    alert_config_file = wsp_path + '/config/alert_config.yaml'
                    
                    auth_config  = yaml.load(open(auth_config_file) , Loader = yaml.FullLoader)
                    user_config = yaml.load(open(user_config_file), Loader = yaml.FullLoader)
                    alert_config = yaml.load(open(alert_config_file), Loader = yaml.FullLoader)
                    
                    alertHandler = alert_handler.AlertHandler(user_config, alert_config, auth_config)
                    
                    msg = f"Name: {time_sensitive['name']} at email: {time_sensitive['email']} has submitted a timed ToO request. The request has been added to {too_path}. "
                    
                    alertHandler.slack_message_group('scheduler', msg)
                    alertHandler.slack_log(msg, group = None)
                    
            else: 
                popup("Your target is not up on the night requested. Please try again. ",
                  closable=True)
                
                
        except: 
            popup("Something went wrong! \n Try checking your units and try again",
                  closable=True)

    
    else:
        priority_opts = ["oldest: Every night, select the set of fields that has been observed least recently by this sub-program.",
                         "mean_observable_airmass: Select the subset of fields with the lowest mean observable airmass (> MAX_AIRMASS) during the night.",
                         "rotate: rotate between stripes in right ascension.  The number of strips is set by internight_gap_days.",
                         "random: Select a random subset of fields"]
        
        filter_opts = ["sequence: every night, use all filters specified in sequence",
                       "rotate: rotate through the filters specified, with one and only one filter used for all observations per night"]
        
        field_opts = ["List specific RAs and Decs",
                       "Range of RAs and Decs",
                       "Range of Galactic longitude (l) and latitude (b)"]
        
        put_markdown('## Welcome to the WINTER/SUMMER request page for time insensitive requests')
        put_markdown('### Below we explain a few of the options:')
        put_text("Field selections: can either select by listing specific RAs and Decs (enter an array of RAs and Decs in degrees) \n \
                 or by selecting a continuous range in RA/Dec or galactic longitude/latitude (enter a range in degrees \n \
                     like [0,90])")
        put_text("Internight gap (days): Number of days before an observed field should be revisited.  Integer >= 1.")
        put_text("Number of visits per night: Number of images to take per field per night.  Integer >= 1. \n \
                 If you pick 2 filters in sequence, make sure your request >=2.")
        put_text("Intranight gap (minutes): Center of allowed time between exposures in minutes (e.g., 60 minutes)")
        put_text("Intranight half width (minutes): Tolerance on window between exposures during the night.  If the previous exposure \n \
                 of the field occured at T0, the next exposure can occur at any time between T0 + intranight_gap_min  \n \
                     - intranight_half_width_min and T0 + intranight_gap_min + intranight_half_width_min.")
        put_text("Nightly priority: Scheme for selecting a subset of the fields in the total sub-program footprint on any given night.")
        put_text("Filter choice: Option for how to determine what filter(s) to use on a given night for this subprogram.  Currently implemented options include:")
        
        time_insensitive = input_group('Time insensitive observation request', [
                        input('Name', name='name', type=TEXT, required=True, PlaceHolder="Name"),
                        
                        input('Email', name='email', type=TEXT, required=True, PlaceHolder="user@gmail.com"),
                        
                        input('Name of program (no spaces)', name='prog_name', type=TEXT, required=True, PlaceHolder="Spring22_SNe"),
                        
                        # Field selection
                        
                        select(label='How would you like to select fields', options=field_opts, name='field_selection'),
                        
                        #select(label='Select your units for right ascension and declination', options=units_coord, value='Radians', name='units_coord'),
                        
                        input('List of right ascensions (degrees, optional)', name='ra', type=TEXT, required=False, PlaceHolder="[12, 13.33, 14.2, 16.66]"),
                        
                        input('List of declinations (degrees, optional)', name='dec', type=TEXT, required=False, PlaceHolder="[12, 13.33, 14.2, 16.66]"),
                        
                        input('Range of right acensions/galactic longitudes (degrees, optional)', name='ra_cut', type=TEXT, required=False, PlaceHolder="[0,90]"),
                        
                        input('Range of declinations//galactic latitudes (degrees, optional)', name='dec_cut', type=TEXT, required=False, PlaceHolder="[0,90]"),
                        
                        # allowed months?
                        
                        # Exposure time
                        input('Exposure time (s)', name='exp', type=FLOAT, required=True, PlaceHolder=""),
                        
                        
                        # Filters
                        checkbox(label='Filters', options=filters, value='', name='filters'),
                        
                        select(label='Filter choice (optional, if selecting more than one filter)', options=filter_opts, value='filter_choice', name='filter_choice'),
                        
                        ##### need filter sequence
                        
                        # priority
                        select(label='Select nightly priority', options=priority_opts, value='priority', name='priority'),
                        
                        # internight_gap_days
                        input('Internight gap (days)', name='internight_gap_days', type=NUMBER, required=True, PlaceHolder="1"),
                        
                        # n_visits_per_night -- check if correct multiple of others
                        input('Number of visits per night', name='n_visits_per_night', type=NUMBER, required=True, PlaceHolder="1"),
                        
                        # intranight_gap_min (optional)
                        input('Intranight gap (minutes, optional)', name='intranight_gap_min', type=NUMBER, required=False, PlaceHolder="60"),
                        
                        # intranight_half_width_min (optional)
                        input('Intranight half width (minutes, optional)', name='intranight_half_width_min', type=NUMBER, required=False, PlaceHolder="60")
                        
                        ] , validate=check_time_insensitive, cancelable=True)
          
        ret = make_untimed_request(env, type_obs['camera'], time_insensitive, field_opts, filters)
        
        if ret == 1:
            # Display output using popup
            popup("Your request has been recorded. \n Details will be sent to:",
              f"Name: {time_insensitive['name']}\
              \nEmail: {time_insensitive['email']}",
              closable=True)
                
            if env == "PRODUCTION":
                    # set up the alert system to post to slack
                auth_config_file  = wsp_path + '/credentials/authentication.yaml'
                user_config_file = wsp_path + '/credentials/alert_list.yaml'
                alert_config_file = wsp_path + '/config/alert_config.yaml'
                
                auth_config  = yaml.load(open(auth_config_file) , Loader = yaml.FullLoader)
                user_config = yaml.load(open(user_config_file), Loader = yaml.FullLoader)
                alert_config = yaml.load(open(alert_config_file), Loader = yaml.FullLoader)
                
                alertHandler = alert_handler.AlertHandler(user_config, alert_config, auth_config)
                
                msg = f"Name: {time_insensitive['name']} at email: {time_insensitive['email']} has submitted an observing request. The request has been added to {req_path}. "
              
                #alertHandler.email_group('scheduler', 'Schedule config request', msg)
                alertHandler.slack_message_group('scheduler', msg)
                alertHandler.slack_log(msg, group = None)
            
        else:
            popup("Something went wrong! \n Try checking your units and try again",
              closable=True)
        

    
if __name__ == '__main__':
    start_server(web_form, port=8808)
