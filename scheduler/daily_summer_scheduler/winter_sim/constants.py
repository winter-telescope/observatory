"""Constants."""

import os
import inspect
import numpy as np
from astropy.time import Time
import astropy.coordinates as coords
import astropy.units as u
import astroplan

BASE_DIR = os.path.dirname(os.path.abspath(inspect.getfile(
                inspect.currentframe()))) + '/'


# W
# height is in meters ABOVE SEA LEVEL 
P48_loc = coords.EarthLocation(lat=coords.Latitude('33d21m26.35s'),
                               lon=coords.Longitude('-116d51m32.04s'),
                               height=1707.)

W_loc = coords.EarthLocation(lat=coords.Latitude('33d21m25.5s'),
                              lon=coords.Longitude('-116d51m58.4s'),
                              height=1696.)

# use UTC only
#P48_Observer = astroplan.Observer(location=P48_loc)
W_Observer = astroplan.Observer(location=W_loc)


# W
# Dome specs from ICD
# not sure what 'axis' the telescope specs are along
# what is a slew time constant??? 0.50 
# TODO, dome doesn't need to move for every pointing

#NPL 9-14-21: added the 'settle' parameter for each axis
W_slew_pars = {
    'ha': {'coord': 'ra', 
           'accel': 7.00 * u.deg * u.second**(-2.),
           'decel': 7.00 * u.deg * u.second**(-2.),
           'vmax': 15.00 * u.deg / u.second,   
           'settle': 1 * u.second
           },
    'dec': {'coord': 'dec', 
            'accel': 7.00 * u.deg * u.second**(-2.),
            'decel': 7.00 * u.deg * u.second**(-2.),
            'vmax': 15.00 * u.deg / u.second,
            'settle' : 1 * u.second
            },
    'dome': {'coord': 'az', 
             'accel': 1.2 * u.deg * u.second**(-2.),
             'decel': 1.2 * u.deg * u.second**(-2.),
             'vmax': 3.3 * u.deg / u.second,
             'settle' : 10.0 * u.second
             }}

"""
# estimated drivetime
# this is from a study of a bunch of moves, move_time = delta_az/effective_speed = lag_time
effective_speed = 3.33 #deg/sec
lag_time = 9.0 #seconds
drivetime = np.abs(dist_to_go)/effective_speed + lag_time# total time to move




"""



# HA and Dec from http://www.oir.caltech.edu/twiki_oir/bin/view/Palomar/ZTF/TelescopeSpecifications v5
# Dome estimate from Jeff Z email, 9/21/15
# goals info from Jeff Z email, 12/12/16
# Ha/Dec from Telescope Drive Performance Assessment v1.2; dome estimate from
# Jeff Z. email, 9/27/17
#P48_slew_pars = {
#    'ha': {'coord': 'ra', 'accel': 0.4 * u.deg * u.second**(-2.),
#           'decel': 0.4 * u.deg * u.second**(-2.),
#           'vmax': 2.5 * u.deg / u.second},
#    'dec': {'coord': 'dec', 'accel': 0.5 * u.deg * u.second**(-2.),
#            'decel': 0.5 * u.deg * u.second**(-2.),
#            'vmax': 3.0 * u.deg / u.second},
#    'dome': {'coord': 'az', 'accel': 0.5 * u.deg * u.second**(-2.),
#             'decel': 0.5 * u.deg * u.second**(-2.),
#             'vmax': 3. * u.deg / u.second}}


c=29979245800.0 #cm/s

class Sensor:
    def __init__(self, name='AP1121', rn=43.0, dark=113.0, nx=640, ny=512, pitch=15): 
        self.name  = name
        self.rn    = rn
        self.dark  = dark
        self.nx    = nx
        self.ny    = ny
        self.pitch = pitch
        self.pred_zp = [24.13, 24.66, 24.05]

class Camera:
    def __init__(self, name='WINTER', Dtel=1.0, pixscale=1.08):
        self.name=name
        self.pixscale=pixscale
        self.sensor=Sensor(name='AP1020', rn=45.0, dark=125.0, nx=1920, ny=1080, pitch=15) # edit
        self.Dtel=Dtel
        
class Site:
    def __init__(self, name='Palomar'):
        self.name      = 'Palomar'
        self.sky      = [17.4, 15.85, 14.2] # mag / sq arcsec in VEGA at zenith
        self.medseeing = 1.1 * (0.62 / 1.1)**(1./5.)  # arcsec FWHM, scale IR


SNR = 5.
EXPOSURE_TIME = 150. * u.second
#READOUT_TIME = 2.1 * u.second
READOUT_TIME = 40 * u.second #NPL 9-14-21 based on actual delay times with SUMMER
# note: actual readout time to finish reading out and saving and validating ~15 s
#       actual overhead on a 30 second exposure is ~50 seconds including saving and dome/mount moves
#       since dome move has 10 second settle time, make "readout time" 40 seconds
#READOUT_TIME = 0. * u.second # W
#FILTER_CHANGE_TIME = 135. * u.second ZTF
FILTER_CHANGE_TIME = 5. * u.second # W #NPL changed to 5 from 10 for SUMMER
SETTLE_TIME = 1. * u.second

MAX_AIRMASS = 3.0 # for W (2.5 for ZTF)

TIME_BLOCK_SIZE = 30. * u.min

PROGRAM_NAME_TO_ID = {'engineering': 0, 
                      'WINTER':1, 'SUMMER': 2, 'Palomar': 3, 'collaboration' :4 }
PROGRAM_NAMES = list(PROGRAM_NAME_TO_ID.keys())
PROGRAM_ID_TO_NAME = {v: k for k, v in list(PROGRAM_NAME_TO_ID.items())}
PROGRAM_IDS = list(PROGRAM_ID_TO_NAME.keys())

PROGRAM_BLOCK_SEQUENCE = [1, 2, 1, 2, 3]
LEN_BLOCK_SEQUENCE = len(PROGRAM_BLOCK_SEQUENCE)

FILTER_NAME_TO_ID = {'g': 1, 'r': 2, 'i': 3}
FILTER_NAMES = list(FILTER_NAME_TO_ID.keys())
FILTER_ID_TO_NAME = {v: k for k, v in list(FILTER_NAME_TO_ID.items())}
FILTER_IDS = list(FILTER_ID_TO_NAME.keys())

#PIXEL_SCALE = 1.006  # arcsec/pixel (ZTF)
PIXEL_SCALE = 0.46  # arcsec/pixel W, from proposal, double check

#VALIDITY_WINDOW_MINUTES = 2.0
VALIDITY_WINDOW_MINUTES = 3.0 * (EXPOSURE_TIME.value/60) # EXPOSURE_TIME is in seconds. this ensures that there's overlap in entries
VALIDITY_WINDOW_MJD = VALIDITY_WINDOW_MINUTES / (24*60) # 24*60 minutes per day

DITHER = 'Y'

def slew_time(axis, angle):
    vmax = W_slew_pars[axis]['vmax']
    acc = W_slew_pars[axis]['accel']
    dec = W_slew_pars[axis]['decel']
    settle = W_slew_pars[axis]['settle']

    t_acc = vmax / acc
    t_dec = vmax / dec
    slew_time = 0.5 * (2. * angle / vmax + t_acc + t_dec)
    w = 0.5 * vmax * (t_acc + t_dec) >= angle
    slew_time[w] = np.sqrt(2 * angle[w] * (1. / acc + 1. / dec))

    wnonzero = slew_time > 0
    #slew_time[wnonzero] += SETTLE_TIME
    slew_time[wnonzero] += settle
    return slew_time 
