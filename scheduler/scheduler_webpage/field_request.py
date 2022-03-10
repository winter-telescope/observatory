# web page to request specific fields be added to
# the nightly schedule 

import pandas as pd
import numpy as np

# pip install pywebio
import pywebio
from pywebio.input import input, FLOAT
from pywebio.output import put_text
from pywebio import start_server


import tornado.ioloop
import tornado.web
from pywebio.platform.tornado import webio_handler

import astropy.units as u
from astropy.time import Time, TimeDelta
from astropy.coordinates import SkyCoord, EarthLocation, AltAz
import astropy.coordinates as coords
import astroplan

# define location of Wallace Observatory
W_loc = coords.EarthLocation(lat=coords.Latitude('33d21m25.5s'),
                              lon=coords.Longitude('-116d51m58.4s'),
                              height=1696.)

W_Observer = astroplan.Observer(location=W_loc)


# get alt and az of observations
# in decimal degrees
def get_alt_az(times, ra, dec):
    loc = SkyCoord(ra=ra, dec=dec, frame='icrs')
    time = Time(times, format='mjd')         
    altaz = loc.transform_to(AltAz(obstime=time,location=W_loc))
    degs = SkyCoord(altaz.az, altaz.alt, frame='icrs')
    #print('altaz'  , altaz)
    alt_array = degs.dec.degree
    az_array = degs.ra.degree
    
    return (alt_array, az_array)

ra = 0.2*u.radian
dec = 1.2*u.radian
times = [59610.1, 59610.11, 59610.12]
alt, az = get_alt_az(times, ra, dec)
print('result', alt, az)

#degs = SkyCoord(az, alt, frame='icrs')
#print(degs.ra.degree)
#aa = degs.ra
#print(degs, aa.degrees)

# what is up (above altitude 20 deg) in a given night?
# date in MJD (median Julian Date), e.g. 59480 (Sept 23)
# ra (right ascension) in hours, minutes, seconds, e.g. '+19h50m41s'
# dec (declination) in hours, minutes, seconds, e.g. '+08d50m58s'
def up_tonight(time, ra, dec):
    loc = SkyCoord(ra=ra, dec=dec, frame='icrs')
    time = Time(time, format='mjd') 
    sun_rise = W_Observer.sun_rise_time(time, which="previous") 
    sun_set = W_Observer.sun_set_time(time, which="next") 
    night =(sun_set.jd-sun_rise.jd)
    if night >= 1:
        # if next day, subtract a day
        dt = np.linspace(sun_set.jd, sun_set.jd+(night-1), 100)
    else:
        dt = np.linspace(sun_set.jd, sun_set.jd+(night), 100)
        
    altaz = loc.transform_to(AltAz(obstime=Time(dt, format='jd'),location=W_loc))
    d = {'time': dt, 'alt': altaz.alt}
    df = pd.DataFrame(data=d)
    df = df[df['alt']>=20] # can change limiting altitude here 
    try:
        time_up = df['time'].iloc[-1] - df['time'].iloc[0]
    except:
        time_up = 0
     
    if time_up > 0:
        start = Time(df['time'].iloc[0], format='jd').isot
        end = Time(df['time'].iloc[-1], format='jd').isot
        is_available = 'Object is up between UTC ' + str(start)+ ' and ' + str(end)
        avail_bool = True
    else:
        is_available = 'Object is not up'
        avail_bool = False
        
    
    return (avail_bool, is_available)



def time_insesnitive_requests():
    info = pywebio.input_group("Group inputs", [
     input('Username', name='username'),
     input('Password', name='pass')])
    
    pywebio.radio("Gender", options=['Male', 'Female'])





def bmi():
    height = input("Your Height(cm)：", type=FLOAT)
    weight = input("Your Weight(kg)：", type=FLOAT)

    BMI = weight / (height / 100) ** 2

    top_status = [(14.9, 'Severely underweight'), (18.4, 'Underweight'),
                  (22.9, 'Normal'), (27.5, 'Overweight'),
                  (40.0, 'Moderately obese'), (float('inf'), 'Severely obese')]

    for top, status in top_status:
        if BMI <= top:
            put_text('Your BMI: %.1f, category: %s' % (BMI, status))
            break



# class MainHandler(tornado.web.RequestHandler):
#     def get(self):
#         self.write("Hello, world")

# if __name__ == "__main__":
#     application = tornado.web.Application([
#         (r"/", MainHandler),
#         (r"/bmi", webio_handler(bmi)),  # bmi is the same function as above
#     ])
#     application.listen(port=8886, address='localhost')
#     tornado.ioloop.IOLoop.current().start()



### backend 
def rad_to_deg(x):
    return x * 180 / np.pi

camera_field_size = 0.26112 /2

git_path = '../daily_summer_scheduler/data/'

field_filename = git_path + 'SUMMER_fields.txt'
summer_fields = pd.read_csv(field_filename,
            names=['field_id','ra','dec','ebv','l','b',
                'ecliptic_lon', 'ecliptic_lat', 'number'],
            sep='\s+',usecols=['field_id','ra','dec', 'l','b', 
                'ecliptic_lon', 'ecliptic_lat'],index_col='field_id',
            skiprows=1)

def get_field_ids(ras, decs, units="degrees"):
    field_list = []
    
    lists = [ras, decs]
    if len(set(map(len, lists))) not in (0, 1):
        raise ValueError('RA and Dec lists are not the same length')
    
    for ra, dec in zip(ras, decs):
        if units=="radians":
            ra_degs = rad_to_deg(ra)
            dec_degs = rad_to_deg(dec)
        else:
            ra_degs = ra
            dec_degs = dec
            
        # sort dec
        dec_sort = summer_fields.iloc[((summer_fields['dec']-dec_degs).abs() <= camera_field_size).values]
        #print(dec_sort)
        
        # sort ra
        ra_sort = dec_sort.iloc[((dec_sort['ra']-ra_degs).abs() <= camera_field_size).values]
        #print(ra_sort)
        
        field_num = ra_sort.index[0]
        field_list.append(field_num)
        
    return field_list
        
        
# fl = get_field_ids([0,2,3], [1,2,3], "degrees")
# print(fl)

# if __name__ == '__main__':
#     start_server(time_insesnitive_requests, port=80)
    
# program_data = {"program_name": "collaboration",
#  		 "active_months": "all"
    
#     }
# 'intranight_half_width_min'
# # add optional arguments
# if len(data['intranight_gap_min']) != 0:
#     program_data['intranight_gap_min'] =int(data['intranight_gap_min'])
    
# if len(data['intranight_half_width_min']) != 0:
#     program_data['intranight_half_width_min'] =int(data['intranight_half_width_min'])

# print(program_data)
# program_data['test'] =[1,2,3]

# print(program_data)


buf = b'abcd000123abcd'

new = buf.split(b'abcd')
print(new)