#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Feb 13 15:07:59 2024

Center offset testing ground


@author: nlourie

"""

import os
import sys
from datetime import datetime

import astropy.coordinates
import astropy.time
import astropy.units as u
import numpy as np

# # add the wsp directory to the PATH
# wsp_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),'wsp')
# # switch to this when ported to wsp
# #wsp_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# sys.path.insert(1, wsp_path)
# #print(f'wsp_path = {wsp_path}')

# from utils import utils
# # load the config
# config_file = wsp_path + '/config/config.yaml'
# config = utils.loadconfig(config_file)

# minimum working config file except for standalone running
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
                    "x_pixel": 800,  # 600, #987, #600
                    "y_pixel": 500,  # 530, #570, #530
                },
                "base_position": {
                    "board_id": 0,
                    "x_pixel": 1788,  # 1900, #1788
                    "y_pixel": 533,  # 449, #533
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


camname = "winter"


def log(x):
    print(x)


def get_center_offset_coords(
    ra_hours: float,
    dec_deg: float,
    pa: float = 90.0,
    offsettype="best",
):
    """
    Calculate the pointing ra/dec required to put the desired ra/dec at the given pixel
    position of the given board.
    :param ra: ra of the target in hours
    :param dec: dec of the target in degrees
    :param pa: where is north with respect to top of detector, positive (same as target_field_angle)
    is counter-clockwise
    :return: new_base_ra required for the board pointing
    :return: new_base_dec required for the board pointing
    """

    if (offsettype is None) or (offsettype.lower() == "none"):
        # just return the input parameters
        return ra_hours, dec_deg

    elif offsettype == "center":
        # NPL 2/13/24: it seems like no offset is actually properly aligned
        # and the below stuff isn't putting it in the center, either bc
        # the math is wrong, or bc the coordinates are incorrect.
        # x_pixel = 0
        # y_pixel = 0
        return ra_hours, dec_deg

    elif offsettype == "best":
        # what is the pixel where the observation should be centered on the best detector?
        # x_pixel: x pixel position on requested board. This assumes the X pixel value
        # when an individual board image is opened in DS9. Default is slightly lower of center.
        x_pixel = config["observing_parameters"][camname]["best_position"]["x_pixel"]
        y_pixel = config["observing_parameters"][camname]["best_position"]["y_pixel"]

    else:
        # invalid offset type
        log(f"invalid offset type selected, defaulting to no offset")
        return ra_hours, dec_deg
    # where does the center of pointing land by default
    base_pointing_x_pixel = config["observing_parameters"][camname]["base_position"][
        "x_pixel"
    ]
    base_pointing_y_pixel = config["observing_parameters"][camname]["base_position"][
        "y_pixel"
    ]

    # what is the shape of the detector?
    x_pixels = config["observing_parameters"][camname]["x_pixels"]
    y_pixels = config["observing_parameters"][camname]["y_pixels"]

    if camname == "winter":

        # get the board id of the best detector
        board_id = config["observing_parameters"][camname]["best_position"]["board_id"]

        y_board_id_mapping = {4: 0, 2: 0, 3: 1, 0: 1, 1: 2, 5: 2}

        x_board_id_mapping = {4: 1, 2: 0, 3: 1, 0: 0, 1: 1, 5: 0}

        if board_id in [1, 3, 4]:
            x_pixel = x_pixels - x_pixel
            y_pixel = y_pixels - y_pixel

        base_pointing_board = config["observing_parameters"][camname]["base_position"][
            "board_id"
        ]

        base_board_x = x_board_id_mapping[base_pointing_board]
        base_board_y = y_board_id_mapping[base_pointing_board]
        requested_board_x = x_board_id_mapping[board_id]
        requested_board_y = y_board_id_mapping[board_id]

        # Calculate the offset in pixels from the base pointing
        x_offset_pixels = (
            (requested_board_x - base_board_x) * x_pixels
            + x_pixel
            - base_pointing_x_pixel
        )
        y_offset_pixels = (
            (requested_board_y - base_board_y) * y_pixels
            + y_pixel
            - base_pointing_y_pixel
        )

    else:
        # eg, for summer or any normal non mosaic focal plane
        x_offset_pixels = x_pixel - base_pointing_x_pixel
        y_offset_pixels = y_pixel - base_pointing_y_pixel

    pixel_scale_arcsec = config["observing_parameters"][camname]["pixscale"]

    # Calculate the offset in arcseconds
    x_offset_arcsec = x_offset_pixels * pixel_scale_arcsec
    y_offset_arcsec = y_offset_pixels * pixel_scale_arcsec

    # Calculate the offset in degrees
    x_offset_deg = x_offset_arcsec / 3600.0  # * np.cos(np.deg2rad(dec))
    y_offset_deg = y_offset_arcsec / 3600.0

    # Calculate the new ra/dec at the base pointing if the requested coordinates
    # need to be at the requested pixels, using the offset and PA,
    # but with astronomy parity
    # For WINTER: parity = 1
    # Note: viraj points out this might have to be flipped for SUMMER
    parity = 1
    ra_offset = (-(1**parity)) * (
        x_offset_deg * np.cos(np.deg2rad(pa)) - y_offset_deg * np.sin(np.deg2rad(pa))
    )
    # nate changed the multiplier for the parity below:
    dec_offset = (-(1**parity)) * (
        x_offset_deg * np.sin(np.deg2rad(pa)) + y_offset_deg * np.cos(np.deg2rad(pa))
    )

    log(f"calculated field offsets:")
    log(f"ra_offset  = {ra_offset*60:.2f} arcmin")
    log(f"dec_offset = {dec_offset*60:.2f} arcmin")

    # convert RA to deg
    ra_deg = ra_hours * 15.0
    new_base_ra_deg = ra_deg + ra_offset / np.cos(
        np.deg2rad(dec_deg)
    )  # changing viraj's minus sign to plus sign

    # convert back to hours
    new_base_ra_hours = new_base_ra_deg / 15.0

    # calculate the new dec
    new_base_dec_deg = dec_deg + dec_offset  # changing viraj's minus sign to plus sign

    return new_base_ra_hours, new_base_dec_deg


def is_rotator_mech_angle_possible(
    predicted_rotator_mechangle, rotator_min_degs, rotator_max_degs
):
    return (predicted_rotator_mechangle > rotator_min_degs) and (
        predicted_rotator_mechangle < rotator_max_degs
    )


def get_safe_rotator_angle(
    ra_hours, dec_deg, target_field_angle, obstime=None, verbose=False
):
    """
    takes in the target field angle, and then returns a field angle and
    mechanical angle pair that corresponds to the best safe rotator
    position within the allowed cable wrap range. Evaluates these 5
    choices (ranked best to worst):
        1. target field angle
        2. target field angle - 360 deg
        3. target field angle + 360 deg
        4. target field angle - 180 deg
        5. target field angle + 180 deg

    """

    lat = astropy.coordinates.Angle(config["site"]["lat"])
    lon = astropy.coordinates.Angle(config["site"]["lon"])
    height = config["site"]["height"] * u.Unit(config["site"]["height_units"])

    site = astropy.coordinates.EarthLocation(lat=lat, lon=lon, height=height)

    if obstime is None:
        obstime = astropy.time.Time(datetime.utcnow(), location=site)

    target_ra_j2000_hours = ra_hours
    target_dec_j2000_deg = dec_deg

    j2000_ra = target_ra_j2000_hours * u.hour
    j2000_dec = target_dec_j2000_deg * u.deg
    j2000_coords = astropy.coordinates.SkyCoord(
        ra=j2000_ra, dec=j2000_dec, frame="icrs"
    )

    ra_deg = j2000_coords.ra.deg

    frame = astropy.coordinates.AltAz(obstime=obstime, location=site)
    local_coords = j2000_coords.transform_to(frame)
    target_alt = local_coords.alt.deg
    target_az = local_coords.az.deg

    # lat = astropy.coordinates.Angle(config['site']['lat']).rad
    dec = dec_deg * np.pi / 180.0
    lst = obstime.sidereal_time("mean").rad
    hour_angle = lst - ra_deg * np.pi / 180.0
    if hour_angle < -1 * np.pi:
        hour_angle += 2 * np.pi
    if hour_angle > np.pi:
        hour_angle -= 2 * np.pi

    # print(f'hour_angle = {hour_angle}')
    # print(f'lat = {lat}')
    # print(f'dec = {dec}')

    parallactic_angle = (
        np.arctan2(
            np.sin(hour_angle),
            np.tan(lat.rad) * np.cos(dec) - np.sin(dec) * np.cos(hour_angle),
        )
        * 180
        / np.pi
    )

    possible_target_field_angles = [
        target_field_angle,
        target_field_angle - 360.0,
        target_field_angle + 360.0,
        target_field_angle - 180.0,
        target_field_angle + 180.0,
    ]

    # print(f'parallactic angle = {parallactic_angle}')
    # print(f'target_field_angle = {target_field_angle}')
    # print(f'target_alt = {target_alt}')
    # print(f'possible_target_field_angles = {possible_target_field_angles}')
    possible_target_mech_angles = [
        (target_field_angle - parallactic_angle - target_alt)
        for target_field_angle in possible_target_field_angles
    ]

    messages = [
        "No rotator wrap predicted",
        "Rotator wrapping < min, adjusting by -360 deg.",
        "Rotator wrapping > max, adjusting by +360 deg.",
        "Rotator wrapping < min, adjusting by -180 deg.",
        "Rotator wrapping > max, adjusting by +180 deg.",
    ]

    if verbose:
        print("##########################################")
    for ind, possible_target_mech_angle in enumerate(possible_target_mech_angles):
        if is_rotator_mech_angle_possible(
            predicted_rotator_mechangle=possible_target_mech_angle,
            rotator_min_degs=config["telescope"]["rotator"][camname][
                "rotator_min_degs"
            ],
            rotator_max_degs=config["telescope"]["rotator"][camname][
                "rotator_max_degs"
            ],
        ):
            target_mech_angle = possible_target_mech_angle
            target_field_angle = possible_target_field_angles[ind]
            if verbose:
                print(messages[ind])
                print(f"Adjusted field angle --> {target_field_angle}")
                print(f"New target mech angle = {target_mech_angle}")
            break
    if verbose:
        print("##########################################")
        print()

    return target_field_angle, target_mech_angle


# obstime_mjd = 60353.152

# obj = 'aldebaran'

# offset test, 4/9/24 6:38a Eastern
obstime_mjd = 60774.443
obj = "deneb"
obj = "dubhe"
obj = "kochab"
obj = "hr6322"
obj = "altair"
print()
print(f"Object: {obj}")
j2000_coords = astropy.coordinates.SkyCoord.from_name(obj, frame="icrs")
j2000_ra_hours = j2000_coords.ra.hour
j2000_dec_deg = j2000_coords.dec.deg

lat = astropy.coordinates.Angle(config["site"]["lat"])
lon = astropy.coordinates.Angle(config["site"]["lon"])
height = config["site"]["height"] * u.Unit(config["site"]["height_units"])

site = astropy.coordinates.EarthLocation(lat=lat, lon=lon, height=height)
obstime = astropy.time.Time(obstime_mjd, format="mjd", location=site)

frame = astropy.coordinates.AltAz(obstime=obstime, location=site)
local_coords = j2000_coords.transform_to(frame)
local_alt_deg = local_coords.alt.deg
local_az_deg = local_coords.az.deg


# now calculate the offsets


# get_center_offset_coords(ra_hours = j2000_ra_hours, dec_deg = j2000_dec_deg,
#                         pa = 0, offsettype = 'best')

target_ra_j2000_hours = j2000_ra_hours
target_dec_j2000_deg = j2000_dec_deg
field_angle_zp = config["telescope"]["rotator"]["winter"][
    "rotator_field_angle_zeropoint"
]


target_field_angle, target_mech_angle = get_safe_rotator_angle(
    ra_hours=target_ra_j2000_hours,
    dec_deg=target_dec_j2000_deg,
    target_field_angle=field_angle_zp,
    obstime=obstime,
    verbose=True,
)

pa_goal = target_field_angle - field_angle_zp

target_ra_j2000_hours, target_dec_j2000_deg = get_center_offset_coords(
    ra_hours=target_ra_j2000_hours,
    dec_deg=target_dec_j2000_deg,
    pa=pa_goal,
    offsettype="best",
)
