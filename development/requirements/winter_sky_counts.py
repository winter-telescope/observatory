#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Sep 12 11:45:08 2023

@author: frostig
"""

import numpy as np

## Constants

# define the site
sky_options = [15.85, 15.4, 15.1, 15.55] # J-band in VEGA mag/arcsec^2 for Chile, 
                                               # Palomar 2007, Palomar 2020, PGIR 2020

# conversion_gain in e-/count
conversion_gain = 2.5 

# pixel scale 
pix_scale = 1.1 # arcsec/pix
 
# number of lens surfaces
n_surf = 24

# mirror, corrector surfaces, QE
M1_eff       = 0.945
M2_eff       = 0.942
M3_eff       = 0.883
corrector    = 0.99**6
measured_telescope = M1_eff * M2_eff * M3_eff * corrector
InGaAs_eff   = 0.80

# detector QE, instrument surfaces, telescope mirrors
winter_thru_J = InGaAs_eff * (.99)**(n_surf)*measured_telescope

## Different ways to calculate WINTER's zerpoint

# Option 1: Scaling from WIRC
winter_area = np.pi*(50)**2 -  np.pi*(50*0.47)**2 # 0.611 m^2
p200_area = np.pi*(254)**2 -  np.pi*(50)**2 # 1 meter secondary obscuration -> 19.4m^2

# wirc data 
# from https://sites.astro.caltech.edu/palomar/observer/200inchResources/sensitivities.html
wirc_thru = .17
vega_corr_J = 0.91
wirc_zp_J = 24.6 + vega_corr_J  
winter_zp_J_wirc = wirc_zp_J + 2.5*np.log10(winter_area/p200_area) + 2.5*np.log10(winter_thru_J/wirc_thru) 
print(f"WINTER J zeropoint scaled from WIRC: {winter_zp_J_wirc:5.2f}")

# Option 2: first principles calculation
h = 6.67*10**(-27) #ergs-s
c= 2.998*10**(10) # cm/s

lam_J = 1.25*10**(-4) #cm
n_J = 1 / winter_thru_J
del_nu_J = 5.8* 10**(13) #Hz

F_J = n_J*(1/del_nu_J) * (h*c/lam_J) * 1/winter_area
winter_zp_J_fp = -2.5*np.log10(F_J) -48.6 +.05
print(f"WINTER J zeropoint from first principles: {winter_zp_J_fp:5.2f}")

# Option 3: scaled from the prototype instrument
proto_dtel  = 2.5
winter_dtel = 1.0
proto_zp_J = 25.27
proto_thru = 0.96**12 * 0.85**2 * 0.8
winter_zp_J_proto = proto_zp_J + 5*np.log10(winter_dtel/proto_dtel)  + 2.5*np.log10(winter_thru_J/proto_thru) 
print(f"WINTER J zeropoint scaled from the prototype: {winter_zp_J_proto:5.2f}")

## functions:

def zenith_angle_to_airmass(zenith_angle):
    return 1. / np.cos(np.radians(zenith_angle)) # Plane-parallel atmos

def altitude_to_airmass(altitude):
    za = 90. - altitude  
    return zenith_angle_to_airmass(za)

def vega_to_AB(mag_vega, filter_id=1):
    # http://www.astronomy.ohio-state.edu/~martini/usefuldata.html
    offset= [0.634, 0.91, 1.39]
    return mag_vega + offset[filter_id]

def airglow_by_altitude(altitude=90., sky_bg=0, filter_id=1):
    zenith_airglow = vega_to_AB(sky_options[sky_bg], filter_id)
    # http://www.gemini.edu/sciops/instruments/gmos/AirglowSPIE.pdf
    slope = [-0.77, -0.61, -0.80]
    const = zenith_airglow - slope[filter_id]*1 # find const from airmass 1
    X = altitude_to_airmass(altitude)
    airglow = slope[filter_id]*X + const
    return airglow

def sky_electrons_per_pixel(mag_per_sq_arcsec, zeropoint="pred", filter_id=1):
    # returns electrons per pixel per second
    # area of one pixel in arcsec^2.
    pixarea = pix_scale**2.
    mag_per_pix = mag_per_sq_arcsec - 2.5 * np.log10(pixarea)
    # use predicted zeropoint or scale from prototype
    if zeropoint == "pred":
        R_sky = 1* 10**(0.4*(winter_zp_J_fp-mag_per_pix))
    elif zeropoint == "proto":
        R_sky = 1* 10**(0.4*(winter_zp_J_proto-mag_per_pix))
        #print(camera.zeropoint[filter_id])
    elif zeropoint == "wirc":
        R_sky = 1* 10**(0.4*(winter_zp_J_wirc-mag_per_pix))
    return R_sky

def sky_counts(exposure_time, sky_bg=0, zeropoint="pred", filter_id=1, altitude=90., pixels = 1., gain=conversion_gain):
    sky_brightness = airglow_by_altitude(altitude, sky_bg, filter_id)
    sky_counts  = sky_electrons_per_pixel(sky_brightness, zeropoint, filter_id) * exposure_time * pixels / gain
    return sky_counts

sky_counts_wirc = sky_counts(1, sky_bg=0, zeropoint="wirc", filter_id=1, altitude=90., pixels = 1., gain=conversion_gain)
sky_counts_pred = sky_counts(1, sky_bg=0, zeropoint="pred", filter_id=1, altitude=90., pixels = 1., gain=conversion_gain)
sky_counts_proto = sky_counts(1, sky_bg=0, zeropoint="proto", filter_id=1, altitude=90., pixels = 1., gain=conversion_gain)

print(f"Projected sky counts / sec with zeropoint scaled from wirc: {sky_counts_wirc:5.2f}")
print(f"Projected sky counts / sec with zeropoint from first principles: {sky_counts_pred:5.2f}")
print(f"Projected sky counts / sec with zeropoint scaled from proto: {sky_counts_proto:5.2f}")
