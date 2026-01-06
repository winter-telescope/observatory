#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon May 22 14:54:47 2023

FITS Header Creator

Takes in metadata, typically a state dictionary from WSP, and produces 
a full FITS header

@author: winter
"""
import logging
import os
import sys
from datetime import datetime

import astropy.coordinates
import astropy.io.fits as fits
import astropy.units as u
import numpy as np
import Pyro5.core
import Pyro5.server
from astropy.time import Time

# add the wsp directory to the PATH
wsp_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(1, wsp_path)
print(f"telescope: wsp_path = {wsp_path}")

from utils import utils


def log(logger, msg, level=logging.INFO):
    if logger is None:
        print(msg)
    else:
        logger.log(level=level, msg=msg)


def GetHeader(config, state, imageinfo, logger=None):

    # state is the WSP housekeeping state metadata
    # imageinfo is specific information about the image

    """
    Things expected in image info:
        - exptime
        - imname
        -

    """

    # state should be the housekeeping state of the full observatory

    # make an empty header LIST: EACH ENTRY WILL BE A  object
    header = list()

    # populate the header. this would be better done driven by a config file
    camname = imageinfo.get("camname", "")

    ###### BASIC PARAMETERS ######
    header.append(("OBSTYPE", imageinfo.get("imtype", ""), "Observation Type"))
    header.append(
        (
            "OBSMODE",
            state.get("obsmode", ""),
            "Observation mode (eg manual/calibration/schedule",
        )
    )
    # add the filename to the header
    header.append(("FILENAME", imageinfo.get("imname", ""), "File name"))
    header.append(("ORIGNAME", imageinfo.get("imname", ""), "Original filename"))
    # add the image readout mode
    header.append(
        ("READOUTM", imageinfo.get("immode", ""), "Image readout mode (eg cds, iwr)")
    )

    ###### TELESCOPE PARAMETERS ######
    # Site lon/lat/height
    header.append(("OBSERVAT", "Palomar Observatory", "Observatory"))
    header.append(("TELESCOP", "WINTER / P39", "Observatory telescope"))
    header.append(
        ("OBSLAT", state.get("site_latitude_degs", ""), "Observatory latitude (deg)")
    )
    header.append(
        ("OBSLON", state.get("site_longitude_degs", ""), "Observatory longitude (deg)")
    )
    header.append(
        ("OBSALT", state.get("site_height_meters", ""), "Observatory altitude (m)")
    )
    header.append(
        ("TELLAT", state.get("mount_latitude_degs", ""), "Telescope latitude (deg)")
    )
    header.append(
        ("TELLON", state.get("mount_longitude_degs", ""), "Telescope longitude (deg)")
    )
    header.append(
        ("TELALT", state.get("mount_height_meters", ""), "Telescope altitude (m)")
    )

    # mirror cover status
    header.append(
        ("MIRCOVER", state.get("mirror_cover_state_str", ""), "Mirror cover status")
    )

    # target RA/DEC

    # RA
    ra_hours = state.get("mount_ra_j2000_hours", 0)
    ra_obj = astropy.coordinates.Angle(ra_hours * u.hour)
    # recasting to get rid of any numpy type objects for passing through the pyro server
    header.append(
        (
            "RA",
            str(ra_obj.to_string(unit=u.deg, sep=":")),
            "Requested right ascension (deg:m:s)",
        )
    )
    header.append(("RADEG", ra_obj.deg, "Requested right ascension (deg)"))

    # DEC
    dec_deg = state.get("mount_dec_j2000_deg", 0)
    dec_obj = astropy.coordinates.Angle(dec_deg * u.deg)
    header.append(
        (
            "DEC",
            str(dec_obj.to_string(unit=u.deg, sep=":")),
            "Requested declination (deg:m:s)",
        )
    )
    header.append(("DECDEG", dec_obj.deg, "Requested declination (deg)"))

    header.append(
        (
            "TELRA",
            str(ra_obj.to_string(unit=u.deg, sep=":")),
            "Telescope right ascension (deg:m:s)",
        )
    )
    header.append(
        (
            "TELDEC",
            str(dec_obj.to_string(unit=u.deg, sep=":")),
            "Telescope declination (deg:m:s)",
        )
    )

    # Alt and Az
    header.append(("AZIMUTH", state.get("mount_az_deg", ""), "Telescope azimuth (deg)"))
    header.append(
        ("ALTITUDE", state.get("mount_alt_deg", ""), "Telescope altitude (deg)")
    )
    header.append(
        ("ELVATION", state.get("mount_alt_deg", ""), "Telescope elevation (deg)")
    )
    # airmass
    z = float((90 - state.get("mount_alt_deg", 0)) * np.pi / 180.0)
    airmass = 1 / np.cos(z)
    header.append(("AIRMASS", airmass, "Airmass"))
    header.append(("DOME_AZ", state.get("dome_az_deg", ""), "Dome azimuth (deg)"))

    header.append(
        ("FOCPOS", state.get("focuser_position", ""), "Focuser position (micron)")
    )
    header.append(
        (
            "ROTMECH",
            state.get("rotator_mech_position", ""),
            "Rotator mechanical angle (deg)",
        )
    )
    header.append(
        ("ROTFIELD", state.get("rotator_field_angle", ""), "Rotator field angle (deg)")
    )

    ###### SCHEDULE PARAMETERS ######
    ### obsHistID
    header.append(
        ("OBHISTID", state.get("robo_obsHistID", ""), "obsHistID: line in schedulefile")
    )
    ### raDeg
    # handled already as RA
    ### decDeg
    # handled already as DEC
    ### filter
    # handled already as FILTER
    # visitExpTime
    header.append(
        (
            "VEXPTIME",
            state.get("robo_visitExpTime", ""),
            "Total target visit exposure time (s)",
        )
    )
    ###priority
    # not implemented
    ### ProgPI
    header.append(("PROGPI", state.get("programPI", ""), "schedule program ID"))
    ### progID
    header.append(("PROGID", state.get("robo_programID", ""), "schedule program PI"))
    ### progName
    header.append(("PROGNAME", state.get("programName", ""), "schedule program name"))
    ### validStart
    header.append(
        ("VALSTART", state.get("robo_validStart", ""), "schedule valid start (MJD)")
    )
    ### validStop
    header.append(
        ("VALSTOP", state.get("robo_validStop", ""), "schedule valid start (MJD)")
    )

    ### observed
    ### maxAirmass
    header.append(
        ("MXAIRMAS", state.get("robo_maxAirmass", ""), "scheduled max airmass")
    )

    ### ditherNumber
    header.append(
        ("NUMDITHS", state.get("robo_num_dithers", ""), "total number of dithers")
    )
    header.append(
        (
            "DITHNUM",
            state.get("robo_dithnum", ""),
            "this dither number (eg 1 out of total of 5)",
        )
    )
    header.append(
        ("DITHSTEP", state.get("robo_ditherStepSize", ""), "dither step size")
    )
    ### fieldID
    header.append(("FIELDID", state.get("robo_fieldID", ""), "Field ID number"))
    ### targName
    header.append(("TARGNAME", state.get("targetName", ""), "target name"))
    ### scheduleName
    header.append(("SCHDNAME", state.get("scheduleName", ""), "schedule file name"))
    ### scheduleType
    header.append(
        (
            "SCHDTYPE",
            state.get("scheduleType", ""),
            "schedule type (eg nightly or target)",
        )
    )
    ### qcomment
    header.append(
        ("QCOMMENT", state.get("qcomment", ""), "Queue comment (general comment)")
    )
    # try:
    #     objra = astropy.coordinates.Angle(state.get('robo_target_ra_j2000', 0)*u.hour)
    #     objdec = astropy.coordinates.Angle(state.get('robo_target_dec_j2000', 0)*u.deg)
    #     objra_str = str(objra.to_string(unit = u.deg, sep = ':'))
    #     objdec_str = str(objdec.to_string(unit = u.deg, sep = ':'))
    # except Exception as e:
    #     objra_str = ''
    #     objdec_str = ''
    #     log(logger,(f'header creator: could not form object ra/dec strings: {e}'))

    # header.append(('OBJRA', objra_str,     'Object right ascension (deg:m:s)'))
    # header.append(('OBJDEC', objdec_str,   'Object declination (deg:m:s)'))

    header.append(("OBJRA", None, "DEPRECATED - Object RA"))
    header.append(("OBJDEC", None, "DEPRECATED - Object DEC"))

    # Update the headers with the Scheduled Target RA/Dec
    targ_ra_comment = "Target RA (J2000)"
    targ_dec_comment = "Target DEC (J2000)"
    targ_ra_value = None
    targ_dec_value = None
    try:
        # if there is no target ra, don't stuff with garbage (eg -999)
        assert state.get("robo_target_ra_j2000_hours", -999) != -999
        targ_ra = astropy.coordinates.Angle(
            state.get("robo_target_ra_j2000_hours", 0) * u.hour
        )
        targ_dec = astropy.coordinates.Angle(
            state.get("robo_target_dec_j2000_deg", 0) * u.deg
        )

        targ_ra_comment = f"Target RA {targ_ra.to_string(unit = u.hour, sep = ':', precision = 1)} (J2000)"
        targ_dec_comment = f"Target DEC {targ_dec.to_string(unit = u.deg, sep = ':', precision = 1)} (J2000)"
        targ_ra_value = np.round(targ_ra.deg, 6)
        targ_dec_value = np.round(targ_dec.deg, 6)
    except AssertionError:
        # No need to do anything, fallback values will be used
        pass
    except Exception as e:
        log(logger, f"header creator: could not form target ra/dec strings: {e}")
    header.append(("TARGRA", targ_ra_value, targ_ra_comment))
    header.append(("TARGDEC", targ_dec_value, targ_dec_comment))

    # Update the headers with the pointing center RA/Dec
    pointing_ra_comment = "Target RA (J2000)"
    pointing_dec_comment = "Target DEC (J2000)"
    pointing_ra_value = None
    pointing_dec_value = None
    try:
        # if there is no target ra, don't stuff with garbage (eg -999)
        assert state.get("robo_pointing_ra_j2000_hours", -999) != -999
        pointing_ra = astropy.coordinates.Angle(
            state.get("robo_pointing_ra_j2000_hours", 0) * u.hour
        )
        pointing_dec = astropy.coordinates.Angle(
            state.get("robo_pointing_dec_j2000_deg", 0) * u.deg
        )

        pointing_ra_comment = f"Pointing Center RA {pointing_ra.to_string(unit = u.hour, sep = ':', precision = 1)} (J2000)"
        pointing_dec_comment = f"Pointing Center DEC {pointing_dec.to_string(unit = u.deg, sep = ':', precision = 1)} (J2000)"
        pointing_ra_value = np.round(pointing_ra.deg, 6)
        pointing_dec_value = np.round(pointing_dec.deg, 6)
    except AssertionError:
        # No need to do anything, fallback values will be used
        pass
    except Exception as e:
        log(logger, f"header creator: could not form pointing ra/dec strings: {e}")

    header.append(("POINTRA", pointing_ra_value, pointing_ra_comment))
    header.append(("POINTDEC", pointing_dec_value, pointing_dec_comment))
    # target type: altaz, radec, schedule
    header.append(("TARGTYPE", state.get("targtype", ""), "Target Type"))

    ###### FILTER PARAMETERS ######

    # filtername = state.get('filtername', '')
    # filterID = state.get('filterID', '')
    # filterpos = state.get('filterpos', '')

    filterpos = state.get(f"{camname}_fw_filter_pos", "")  # eg 1
    try:
        filterID = config["filter_wheels"][camname]["positions"][filterpos]  # eg. 'r'
        filtername = config["filters"][camname][filterID][
            "name"
        ]  # eg. "SDSS r' (Chroma)"
    except:
        filterID = ""
        filtername = ""

    header.append(("FILTER", filtername, "Filter name"))
    header.append(("FILTERID", filterID, "Filter ID"))
    header.append(("FILPOS", filterpos, "Filter position"))

    ###### CAMERA PARAMETERS #####
    header.append(("INSTRUME", camname, "Instrument name"))
    header.append(
        ("EXPTIME", imageinfo.get("exptime", -1), "Requested exposure time (sec)")
    )

    # MODE_NUM

    ###### TIME PARAMETERS ######
    try:
        # add the image acquisition timestamp to the fits header
        image_starttime_utc = imageinfo.get("imstarttime")
        image_starttime_utc_datetime_object = datetime.strptime(
            image_starttime_utc, "%Y%m%d-%H%M%S-%f"
        )
        image_starttime_utc_object = Time(image_starttime_utc_datetime_object)

        header.append(
            (
                "UTC",
                image_starttime_utc_datetime_object.strftime("%Y%m%d_%H%M%S.%f"),
                "Time of observation ",
            )
        )
        header.append(
            (
                "UTCISO",
                image_starttime_utc_object.iso,
                "Time of observation in ISO format",
            )
        )
        header.append(
            (
                "UTCSHUT",
                image_starttime_utc_datetime_object.strftime("%Y%m%d_%H%M%S.%f"),
                "UTC time shutter open",
            )
        )
        header.append(
            (
                "UTC-OBS",
                image_starttime_utc_datetime_object.strftime("%Y%m%d %H%M%S.%f"),
                "UTC time shutter open",
            )
        )
        header.append(
            (
                "DATE-OBS",
                image_starttime_utc_datetime_object.strftime("%Y%m%d %H%M%S.%f"),
                "UTC date of observation (MM/DD/YY)",
            )
        )
        header.append(
            ("OBSJD", image_starttime_utc_object.jd, "Julian day corresponds to UTC")
        )
        header.append(
            ("OBSMJD", image_starttime_utc_object.mjd, "MJD corresponds to UTC")
        )

    except Exception as e:
        log(logger, f"could not make the time entries: {e}")
        header.append(("UTC", "", "Time of observation "))
        header.append(("UTCISO", "", "Time of observation in ISO format"))
        header.append(("UTCSHUT", "", "UTC time shutter open"))
        header.append(("UTC-OBS", "", "UTC time shutter open"))
        header.append(("DATE-OBS", "", "UTC date of observation (MM/DD/YY)"))
        header.append(("OBSJD", "", "Julian day corresponds to UTC"))
        header.append(("OBSMJD", "", "MJD corresponds to UTC"))
    """
    obstime = Time(self.image_starttime_utc, scale = 'utc', location = self.site)
    lst_obj = obstime.sidereal_time('mean')
    header.append(('OBSLST', lst_obj.to_string(unit = u.deg, sep = ':'),              'Mean LST corresponds to UTC'))
    """

    ###### WEATHER PARAMETERS ######
    # UT_WEATH
    try:

        weather_datetime = datetime.fromtimestamp(state["dome_timestamp"])
        ut_weath = weather_datetime.strftime("%Y-%m-%d %H%M%S.%f")
    except Exception as e:
        log(logger, (f'state["dome_timestamp"] = {state.get("dome_timestamp", "?")}'))
        log(logger, (f"could not get dome time, {e}"))
        ut_weath = ""

    header.append(("UT_WEATH", ut_weath, "UT of weather data"))
    # TEMPTURE
    header.append(
        ("TEMPTURE", state.get("T_outside_pcs", ""), "Outside air temperature (C)")
    )
    # WINDSPD
    header.append(
        ("WINDSPD", state.get("windspeed_average_pcs", ""), "Outside wind speed")
    )
    # WINDDIR
    header.append(
        ("WINDDIR", state.get("wind_direction_pcs", ""), "Outside wind direction (deg)")
    )
    # DEWPOINT
    header.append(("DEWPOINT", state.get("Tdp_outside_pcs", ""), "Dewpoint (C)"))
    # WETNESS
    header.append(
        ("WETNESS", state.get("dome_wetness_status", ""), "Wetness sensor reading")
    )
    # HUMIDITY
    header.append(
        ("HUMIDITY", state.get("rh_outside_pcs", ""), "Relative humidity (%)")
    )
    # PRESSURE
    header.append(
        ("PRESSURE", state.get("pressure_pcs", ""), "Atmospheric pressure, millibars")
    )
    # TELESCOPE TEMPS
    header.append(
        ("TEMPM1", state.get("telescope_temp_m1", ""), "telescope temp M1, C")
    )
    header.append(
        ("TEMPM2", state.get("telescope_temp_m2", ""), "telescope temp M2, C")
    )
    header.append(
        ("TEMPM3", state.get("telescope_temp_m3", ""), "telescope temp M3, C")
    )
    header.append(
        (
            "TEMPAMB",
            state.get("telescope_temp_ambient", ""),
            "telescope temp ambient, C",
        )
    )

    ###### INSTRUMENT MONITOR PARAMETERS ######
    header.append(
        ("TMISCPBT", state.get("T_misc_powerbox", ""), "Misc Power Box Temp (C)")
    )
    header.append(
        (
            "TPBSTAR",
            state.get("T_powerbox_star", ""),
            "Starboard FPA Power Box Temp (C)",
        )
    )
    header.append(
        ("TPBPORT", state.get("T_powerbox_port", ""), "Port FPA Power Box Temp (C)")
    )
    header.append(
        ("TOBSTAR", state.get("T_ob_star", ""), "Optics Box Temp - Starboard (C)")
    )
    header.append(("TOBPORT", state.get("T_ob_port", ""), "Optics Box Temp - Port (C)"))
    header.append(
        ("TOBCENT", state.get("T_ob_center", ""), "Optics Box Temp - Center (C)")
    )
    header.append(("TFPGA", state.get("T_fpga_sb", ""), "FPGA Temp - StarB (C)"))
    header.append(
        ("THXSC", state.get("T_hx_sc", ""), "FPA Heat Exchanger Temp - StarC (C)")
    )
    header.append(
        ("THSNKSA", state.get("T_heatsink_sa", ""), "FPA Heatsink Temp - StarA")
    )
    header.append(
        ("THSNKSB", state.get("T_heatsink_sb", ""), "FPA Heatsink Temp - StarB")
    )
    header.append(
        ("THSNKSC", state.get("T_heatsink_sc", ""), "FPA Heatsink Temp - StarC")
    )
    header.append(
        ("THSNKPA", state.get("T_heatsink_pa", ""), "FPA Heatsink Temp - PortA")
    )
    header.append(
        ("THSNKPB", state.get("T_heatsink_pb", ""), "FPA Heatsink Temp - PortB")
    )
    header.append(
        ("THSNKPC", state.get("T_heatsink_pc", ""), "FPA Heatsink Temp - PortC")
    )

    ###### OTHER PARAMETERS ######
    header.append(("MOONRA", state.get("moon_ra_deg", ""), "Moon J2000.0 R.A. (deg)"))
    header.append(("MOONDEC", state.get("moon_dec_deg", ""), "Moon J2000.0 Dec. (deg)"))
    header.append(
        ("MOONILLF", state.get("moon_illf", ""), "Moon illuminated fraction (frac)")
    )
    header.append(("MOONPHAS", state.get("moon_phase", ""), "Moon phase angle (deg)"))
    header.append(
        (
            "MOONESB",
            state.get("moon_excess_brightness_vband", ""),
            "Moon excess in sky brightness V-band",
        )
    )
    header.append(("MOONALT", state.get("moon_alt", ""), "Moon altitude (deg)"))
    header.append(("MOONAZ", state.get("moon_az", ""), "Moon azimuth (deg)"))
    header.append(("SUNALT", state.get("sun_alt", ""), "Sun altitude (deg)"))
    header.append(("SUNAZ", state.get("sun_az", ""), "Sun azimuth (deg)"))
    header.append(
        (
            "SEEING",
            state.get("fwhm_mean", ""),
            "Seeing measurement: FWHM mean from focusing",
        )
    )

    return header


if __name__ == "__main__":
    logger = None
    try:
        ns = Pyro5.core.locate_ns("192.168.1.10")
        uri = ns.lookup("state")
        p = Pyro5.client.Proxy(uri)
        state = p.GetStatus()
    except Exception as e:
        log(logger, (f"could not get WSP state: {e}"))
        state = {}

    # load the config
    config_file = wsp_path + "/config/config.yaml"
    config = utils.loadconfig(config_file)

    camstate = dict(
        {
            "imname": "WINTERcamera_20230612-001809-576",
            "imstarttime": "20230612-001809-576",
            "imtype": "TEST",
        }
    )
    header = GetHeader(config, state, camstate)

    # header = dict({"DICTKEY" : "DictValue"})

    hdu = fits.PrimaryHDU()

    hdu.data = np.zeros((1080, 1920))

    # Now build the image header. Handle differently if it's passed a dict,
    # or a list of  objects

    if type(header) is list:
        for element in header:

            try:
                log(logger, (element))
                card = fits.Card(*element)
                hdu.header.append(card)
            except Exception as e:
                log(logger, (f"could not add {card[0]} to header: {e}"))
    elif type(header) is dict:
        for key in header:
            try:
                hdu.header[key] = header[key]
            except Exception as e:
                log(logger, (f"could not add {key} to header: {e}"))

    hdu.writeto(os.path.join(os.getenv("HOME"), "data", "test.fits"), overwrite=True)
