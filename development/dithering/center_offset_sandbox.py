#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Apr 15 08:59:21 2025

@author: nlourie
"""
import numpy as np
import astropy.coordinates
import astropy.time
import astropy.units as u
import matplotlib.pyplot as plt
from center_offset_simulator import mini_ephem





targets = dict(
    {
        "deneb": {
            "offset": {"best_center": (-32, 16), "best_side": (-45, 16)},
            "rising": True,
            "field_angle": 65.0,
        },
        "dubhe": {
            "offset": {"best_center": (-32, 19), "best_side": (-50, 19)},
            "rising": False,
            "field_angle": 65.0,
        },
        "kochab": {
            "offset": {"best_center": (75, -23.5), "best_side": (105, -23.5)},
            "rising": False,
            "field_angle": 245.0,
        },
         "hr6322": {
            "offset": {"best_center": (135, -25), "best_side": (200, -25)},
            "rising": False,
            "field_angle": 245.0,
         },
        "altair": {
            "offset": {"best_center": (-21, 14), "best_side": (-30, 14)},
            "rising": None,
            "field_angle": 65.0,
        },
    }
)

config = dict(
    {
        "observing_parameters": {
            "winter": {
                "dithers": {
                    "ditherNumber": 10,
                    "ditherMinStep_as": 10,
                    "ditherMaxStep_as": 15,
                },
                "best_position": {
                    "board_id": 4,
                    "addr" : "pc",
                    "x_pixel": 1000,  # 600, #987, #600
                    "y_pixel": 540,  # 530, #570, #530
                },
                "base_position": {
                    "board_id": 0,
                    "addr" : "sb",
                    #"x_pixel": 1788,  # 1900, #1788
                    #"y_pixel": 533,  # 449, #533
                    "x_pixel": 1828,
                    "y_pixel":784,
                    "north-up":{
                        "addr" : "sb",
                        "x_pixel" : 1687,
                        "y_pixel" : 384,
                        },
                    "north-down":{
                        "addr" : "sb",
                        "x_pixel" : 1828,
                        "y_pixel" : 784,
                        },
                    "default":{
                        "addr" : "sb",
                        "x_pixel" : 1756,
                        "y_pixel" : 584,
                        }
                    
                },
                "pixscale": 1.11,
                "x_pixels": 1984,
                "y_pixels": 1096,
            }
        },
        "site": {
            # lat/lon. expects a format that can be read with astropy.coordinates.Angle()
            "lat": "33d21m21.6s",
            "lon": "-116d51m46.8s",
            # height (site altitude). height is a number, units are something that can be parsed with astropy.units.Unit()
            "height": 1706,
            "height_units": "m",
            "timezone": "America/Los_Angeles",
        },
        "telescope": {
            "rotator": {
                "winter": {
                    "rotator_field_angle_zeropoint": 65.0,
                    "rotator_home_degs": 65.5,
                    "rotator_max_degs": 120.0,
                    "rotator_min_degs": -90.0,
                }
            },
        },
    }
)

""" For kochab:
##########################################
Rotator wrapping > max, adjusting by +180 deg.
Adjusted field angle --> 245.0
New target mech angle = 71.73940629887889
##########################################
target_field_angle = 245.0
target_mech_angle  = 71.73940629887889
get_center_offset_coords: pa = 180.0
------------------------------------------
target: kochab
field angle: predicted = 245.0, actual = 245.00
ra_offset: predicted = 21.83 arcmin, actual=75.00
dec_offset: predicted = -20.04 arcmin, actual=-23.50
------------------------------------------
"""
""" from do_observation:
pa=self.target_field_angle
- self.config["telescope"]["rotator"]["winter"][
    "rotator_field_angle_zeropoint"
]
"""


target_name = "kochab"

errRA_arr = np.array([])
errDec_arr = np.array([])

for target_name, values in targets.items(): 
    print()
    
    print("=======================================================")
    
    print(f"target = {target_name}:")
    print("-------------------------------------------------------")
    
    target_field_angle = targets[target_name]["field_angle"]
    print(f"target_field_angle = {target_field_angle}")
    
    meas_offset = targets[target_name]["offset"]["best_center"]
    
    j2000_coords = astropy.coordinates.SkyCoord.from_name(target_name, frame="icrs")
    target = (j2000_coords.ra.hour, j2000_coords.dec.deg)
    
    
    obstime_mjd = 60774.50935656831
    ephem = mini_ephem(base_directory=None, config=config)
    obstime = astropy.time.Time(obstime_mjd, format="mjd", location=ephem.site)
    camname = "winter"
    
    frame = astropy.coordinates.AltAz(obstime=obstime, location=ephem.site)
    local_coords = j2000_coords.transform_to(frame)
    target_alt = local_coords.alt.deg
    target_az = local_coords.az.deg
    
    print(f"target RA/Dec (h,deg)    = ({j2000_coords.ra.hour:.2f}, {j2000_coords.dec.deg:.2f})")
    print(f"target Alt/Az (deg, deg) = ({target_alt:.2f}, {target_az:.2f} deg")
    
    
    
    
    
    
    
    # this gets calculated by get_safe_rotator_angle
    
    pa = target_field_angle - config["telescope"]["rotator"]["winter"]["rotator_field_angle_zeropoint"]+90
    print(f"pa wrt to north -> east= {pa:.2f}")
    # note that this is angle wrt north -> east
    
    # convert to delta angle wrt north up
    pa = pa - 90
    print(f"pa wrt to north -> up = {pa:.2f}")
    
    # base offsets
    base_offsets = {"sa" : (1,2),
                    "sb" : (1,1),
                    "sc" : (0,1),
                    "pc" : (0,2),
                    "pb" : (0,1),
                    "pa" : (0,0)}
    
    # specific example for kochab eg FLIPPED: target field angle = 245
    
    # detector width in x and y in pixels
    wx = config["observing_parameters"][camname]["x_pixels"]
    wy = config["observing_parameters"][camname]["y_pixels"]
    
    ## calculate the final goal center
    addr_f = config["observing_parameters"][camname]["best_position"]["addr"]
    # start with detector coords (eg matching DS9): (xd, yd)
    xd_f = config["observing_parameters"][camname]["best_position"]["x_pixel"]
    yd_f = config["observing_parameters"][camname]["best_position"]["y_pixel"]
    
    # calcualte camera-oriented coords: (xc, yc)
    # coordinate transformation req'd if on the starboard side
    if "s" in addr_f:
        xc_f = wx - xd_f
        yc_f = wy - yd_f
    else:
        xc_f = xd_f
        yc_f = yd_f
        
    # now calculate mosaic coords: (xm, ym)
    xm_f = base_offsets[addr_f][0]*wx + xc_f
    ym_f = base_offsets[addr_f][1]*wy + yc_f
    print(f"final location (xm_f, ym_f) = ({xm_f}, {ym_f})")
    
    
    # now calculate the mosaic coords of the start position
    
    # we need a case to handle the offsets because it's not the same in north-up as north-down
    
    # if we near pa = 0: north-up
    if abs(pa) <= 10:
        orientation = "north-up"
    elif abs(pa-180) <= 10:
        orientation = "north-down"
    else:
        orienation = "default"
        
    # Override to see if we can handle common location
    orientation = "default"
    print(f"orientation = {orientation}")
    addr_0 = config["observing_parameters"][camname]["base_position"][orientation]["addr"]
    xd_0 = config["observing_parameters"][camname]["base_position"][orientation]["x_pixel"]
    yd_0 = config["observing_parameters"][camname]["base_position"][orientation]["y_pixel"]
    if "s" in addr_0:
        xc_0 = wx - xd_0
        yc_0 = wy - yd_0
    else:
        xc_0 = xd_0
        yc_0 = yd_0
    # now calculate mosaic coords: (xm, ym)
    xm_0 = base_offsets[addr_0][0]*wx + xc_0
    ym_0 = base_offsets[addr_0][1]*wy + yc_0
    print(f"starting location (xm_0, ym_0) = ({xm_0}, {ym_0})")
    
    
    # Now calcualte the offsets:
    delta_xm = xm_f - xm_0
    delta_ym = ym_f - ym_0
    
    print(f"raw pixel offsets (dxm, dym) = ({delta_xm}, {delta_ym})")
    
    
    
    # convert to viraj's names:
    x_offset_pixels = delta_xm
    y_offset_pixels = delta_ym
    
    
    
    
    
    
    # now we need to rotate the pixel offsets by the position angle
    parity = 1
    delta_xm = parity * (delta_xm * np.cos(np.deg2rad(pa)) - delta_ym * np.sin(np.deg2rad(pa)))
    delta_ym = parity * (delta_xm * np.sin(np.deg2rad(pa)) + delta_ym * np.cos(np.deg2rad(pa)))
    
    
    print(f"rotated pixel offsets (dxm, dym) = ({delta_xm:.0f}, {delta_ym:.0f})")
    
    
    pixel_scale_arcsec = config["observing_parameters"][camname]["pixscale"]
    
    
    
    # now we need to calculate the actual offsets to move the telescope to the specified location
    
    start = j2000_coords
    offset_ra = delta_xm * (pixel_scale_arcsec/60.0) * u.arcmin
    offset_dec = delta_ym * (pixel_scale_arcsec/60.0) * u.arcmin
    
    end = start.spherical_offsets_by(offset_ra, offset_dec)
    # calculate the literal difference required by PWI4 mount_offset
    ra_delta_arcmin = end.ra.arcmin - start.ra.arcmin
    dec_delta_arcmin = end.dec.arcmin - start.dec.arcmin
    
    print()
    print(f"calc (dRA, dDec) = ({ra_delta_arcmin:.1f}, {dec_delta_arcmin:.1f}) arcmin")
    
    print(f"meas (dRA, dDec) = ({meas_offset[0]:.1f}, {meas_offset[1]:.1f}) arcmin")
    err_ra = ra_delta_arcmin - meas_offset[0]
    err_dec = dec_delta_arcmin - meas_offset[1]
    
    # update the arrays to plot
    errRA_arr = np.append(errRA_arr, err_ra)
    errDec_arr = np.append(errDec_arr, err_dec)
    
    err_mag = np.sqrt(err_ra**2 + err_dec**2)
    
    if err_mag < 5.0:
        quality = "GOOD"
    else:
        quality = "BAD"
    
    print()
    print(f"err  (dRA, dDec) = ({err_ra:.1f}, {err_dec:.1f}) arcmin")
    print(f"err magnitude    = {err_mag:.1f} arcmin --> {quality}")
    print("=======================================================")
    

# now plot the results
plt.figure()
plt.plot(errRA_arr, errDec_arr, 'o')
plt.xlabel('Error in RA (arcmin)')
plt.ylabel("Error in Dec (arcmin)")
    
    














