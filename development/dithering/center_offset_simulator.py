import logging
from datetime import datetime

import astropy.coordinates
import astropy.time
import astropy.units as u
import numpy as np

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
                    "x_pixel": 1000,  # 600, #987, #600
                    "y_pixel": 550,  # 530, #570, #530
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


class mini_alertHandler(object):
    def __init__(self, logger=None):
        self.logger = logger

    def slack_log(self, msg, group=None):
        pass
        # if self.logger is None:
        #    print(msg)
        # else:
        #    self.logger.log(level=logging.INFO, msg=msg)


class mini_ephem(object):

    def __init__(
        self, base_directory, config, ns_host=None, logger=None, verbose=False
    ):
        self.base_directory = base_directory
        self.config = config
        self.ns_host = ns_host
        self.logger = logger
        self.verbose = verbose

        # default value for bad query
        self.default = -888
        self.default_timestamp = datetime(1970, 1, 1, 0, 0).timestamp()

        # set up site
        lat = astropy.coordinates.Angle(self.config["site"]["lat"])
        lon = astropy.coordinates.Angle(self.config["site"]["lon"])
        self.height_m = self.config["site"]["height"]
        height = self.height_m * u.Unit(self.config["site"]["height_units"])

        self.site = astropy.coordinates.EarthLocation(lat=lat, lon=lon, height=height)


class mini_roboOperator(object):
    def __init__(self, config=None, camname=None, logger=None):
        self.logger = logger
        self.config = config
        self.camname = camname
        self.running = True
        self.ephem = mini_ephem(
            base_directory=None,
            config=self.config,
            ns_host=None,
            logger=None,
            verbose=False,
        )
        self.alertHandler = mini_alertHandler()

        # set up some default values
        self.ok_to_observe = True
        self.target_ra_j2000_hours = None
        self.target_dec_j2000_deg = None
        self.target_alt = None
        self.target_az = None
        self.target_field_angle = None
        self.target_mech_angle = None

    def log(self, msg, level=logging.INFO, silent=True):
        msg = f"roboOperator: {msg}"
        if silent is False:
            if self.logger is None:
                print(msg)
            else:
                self.logger.log(level=level, msg=msg)
        else:
            pass

    def check_ok_to_observe(self, logcheck=False):
        self.ok_to_observe = True
        if logcheck:
            self.log("okay to observe check passed")
        return

    def is_rotator_mech_angle_possible(
        self, predicted_rotator_mechangle, rotator_min_degs, rotator_max_degs
    ):
        return (predicted_rotator_mechangle > rotator_min_degs) and (
            predicted_rotator_mechangle < rotator_max_degs
        )

    def get_safe_rotator_angle(
        self,
        ra_hours,
        dec_deg,
        target_field_angle,
        obstime=None,
        verbose=False,
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

        if obstime is None:
            obstime = astropy.time.Time(datetime.utcnow(), location=self.ephem.site)

        self.target_ra_j2000_hours = ra_hours
        self.target_dec_j2000_deg = dec_deg

        j2000_ra = self.target_ra_j2000_hours * u.hour
        j2000_dec = self.target_dec_j2000_deg * u.deg
        j2000_coords = astropy.coordinates.SkyCoord(
            ra=j2000_ra, dec=j2000_dec, frame="icrs"
        )

        ra_deg = j2000_coords.ra.deg

        # lat = astropy.coordinates.Angle(self.config['site']['lat'])
        # lon = astropy.coordinates.Angle(self.config['site']['lon'])
        # height = self.config['site']['height'] * u.Unit(self.config['site']['height_units'])

        site = (
            self.ephem.site
        )  # astropy.coordinates.EarthLocation(lat = lat, lon = lon, height = height)
        frame = astropy.coordinates.AltAz(obstime=obstime, location=site)
        local_coords = j2000_coords.transform_to(frame)
        self.target_alt = local_coords.alt.deg
        self.target_az = local_coords.az.deg

        dec = dec_deg * np.pi / 180.0
        lst = obstime.sidereal_time("mean").rad
        hour_angle = lst - ra_deg * np.pi / 180.0
        if hour_angle < -1 * np.pi:
            hour_angle += 2 * np.pi
        if hour_angle > np.pi:
            hour_angle -= 2 * np.pi

        lat = astropy.coordinates.Angle(self.config["site"]["lat"]).rad

        parallactic_angle = (
            np.arctan2(
                np.sin(hour_angle),
                np.tan(lat) * np.cos(dec) - np.sin(dec) * np.cos(hour_angle),
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

        possible_target_mech_angles = [
            (target_field_angle - parallactic_angle - self.target_alt)
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
            print("\n##########################################")
        for ind, possible_target_mech_angle in enumerate(possible_target_mech_angles):
            if self.is_rotator_mech_angle_possible(
                predicted_rotator_mechangle=possible_target_mech_angle,
                rotator_min_degs=self.config["telescope"]["rotator"][self.camname][
                    "rotator_min_degs"
                ],
                rotator_max_degs=self.config["telescope"]["rotator"][self.camname][
                    "rotator_max_degs"
                ],
            ):
                self.target_mech_angle = possible_target_mech_angle
                self.target_field_angle = possible_target_field_angles[ind]
                if verbose:
                    print(messages[ind])
                    print(f"Adjusted field angle --> {self.target_field_angle}")
                    print(f"New target mech angle = {self.target_mech_angle}")
                break
        if verbose:
            print("##########################################")

        return self.target_field_angle, self.target_mech_angle

    def get_center_offset_coords(
        self,
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

        print(f"get_center_offset_coords: pa = {pa}")

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
            x_pixel = self.config["observing_parameters"][self.camname][
                "best_position"
            ]["x_pixel"]
            y_pixel = self.config["observing_parameters"][self.camname][
                "best_position"
            ]["y_pixel"]

        else:
            # invalid offset typefocus_loop_param
            self.log(f"invalid offset type selected, defaulting to no offset")
            return ra_hours, dec_deg
        # where does the center of pointing land by default
        base_pointing_x_pixel = self.config["observing_parameters"][self.camname][
            "base_position"
        ]["x_pixel"]
        base_pointing_y_pixel = self.config["observing_parameters"][self.camname][
            "base_position"
        ]["y_pixel"]

        # what is the shape of the detector?
        x_pixels = self.config["observing_parameters"][self.camname]["x_pixels"]
        y_pixels = self.config["observing_parameters"][self.camname]["y_pixels"]

        if self.camname == "winter":

            # get the board id of the best detector
            board_id = self.config["observing_parameters"][self.camname][
                "best_position"
            ]["board_id"]

            y_board_id_mapping = {4: 0, 2: 0, 3: 1, 0: 1, 1: 2, 5: 2}

            x_board_id_mapping = {4: 1, 2: 0, 3: 1, 0: 0, 1: 1, 5: 0}

            if board_id in [1, 3, 4]:
                x_pixel = x_pixels - x_pixel
                y_pixel = y_pixels - y_pixel

            base_pointing_board = self.config["observing_parameters"][self.camname][
                "base_position"
            ]["board_id"]

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

        pixel_scale_arcsec = self.config["observing_parameters"][self.camname][
            "pixscale"
        ]

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
            x_offset_deg * np.cos(np.deg2rad(pa))
            - y_offset_deg * np.sin(np.deg2rad(pa))
        )
        # nate changed the multiplier for the parity below:
        dec_offset = (-(1**parity)) * (
            x_offset_deg * np.sin(np.deg2rad(pa))
            + y_offset_deg * np.cos(np.deg2rad(pa))
        )

        self.log(f"calculated field offsets:")
        self.log(f"ra_offset = {ra_offset*60} arcmin")
        self.log(f"dec_offset = {dec_offset*60} arcmin")

        # convert RA to deg
        ra_deg = ra_hours * 15.0
        new_base_ra_deg = ra_deg + ra_offset / np.cos(
            np.deg2rad(dec_deg)
        )  # changing viraj's minus sign to plus sign

        # convert back to hours
        new_base_ra_hours = new_base_ra_deg / 15.0

        # calculate the new dec
        new_base_dec_deg = (
            dec_deg + dec_offset
        )  # changing viraj's minus sign to plus sign

        return new_base_ra_hours, new_base_dec_deg, ra_offset * 60, dec_offset * 60

    def do_observation(
        self,
        targtype,
        target=None,
        tracking="auto",
        field_angle="auto",
        obstype="TEST",
        comment="",
        obsmode="SCHEDULE",
        offset="best",
        obstime=None,
    ):
        """
        A GENERIC OBSERVATION FUNCTION

        INPUTS:
            targtype: description of the observation type. can be any ONE of:
                'schedule'  : observes whatever the current observation in the schedule queue is
                                - exposure time and other parameters are set according to the current obs from the schedule file

                'altaz'     : observes the specified target = (alt_degs, az_degs):
                                - exposure time is NOT set, whatever the current time is set to is used
                                - tracking is turned on by default
                                - if tracking is on, field angle is set to config['telescope']['rotator_field_angle_zeropoint']
                'radec'     : observes the specified target = (ra_j2000_hours, dec_j2000_deg)
                                - exposure time is NOT set, whatever the current time is set to is used
                                - tracking is turned on by default
                                - if tracking is on, field angle is set to config['telescope']['rotator_field_angle_zeropoint']

            in all cases a check is done to make sure that:
                - it is okay to observe (eg dome/weather/sun/etc status)
                - there are no ephemeris bodies (from the tracked list) within the field of view margins

        """
        # the observation has not been completed
        self.observation_completed = False

        # tag the context for any error messages
        context = "do_observation"

        self.log(
            f"doing observation: targtype = {targtype}, target = {target}, tracking = {tracking}, field_angle = {field_angle}"
        )
        #### FIRST MAKE SURE IT'S OKAY TO OBSERVE ###
        self.check_ok_to_observe(logcheck=True)
        self.log(
            f"self.running = {self.running}, self.ok_to_observe = {self.ok_to_observe}"
        )

        # TODO Uncomment this, for now it's commented out so that we can test with the dome closed
        # NPL 7-28-21

        if self.ok_to_observe:
            pass
        else:

            return

        # set the obsmode
        self.obsmode = obsmode.upper()

        # if observation mode is manual, reset all the header values

        ### Validate the observation ###
        # just make it lowercase to avoid any case issues
        targtype = targtype.lower()
        # set the target type
        self.targtype = targtype

        # set the obstype
        self.obstype = obstype

        # now check that the target is appropriate to the observation type
        if targtype == "altaz":
            try:
                # make sure it's a tuple
                assert (
                    type(target) is tuple
                ), f"for {targtype} observation, target must be a tuple. got type = {type(target)}"

                # make sure it's the right length
                assert (
                    len(target) == 2
                ), f"for {targtype} observation, target must have 2 coordinates. got len(target) = {len(target)}"

                # make sure they're floats
                assert (type(target[0]) is float) & (
                    type(target[0]) is float
                ), f"for {targtype} observation, target vars must be floats"
            except Exception as e:
                self.log(f"Problem while vetting observation: {e}")
            # get the target alt and az
            self.target_alt = target[0]
            self.target_az = target[1]
            msg = f"Observing [{obstype}] Target @ (Alt, Az) = {self.target_alt:0.2f}, {self.target_az:0.2f}"
            self.alertHandler.slack_log(msg, group=None)

            self.log(
                f"target: (alt, az) = {self.target_alt:0.2f}, {self.target_az:0.2f}"
            )
            try:
                # calculate the nominal target ra and dec
                alt_object = astropy.coordinates.Angle(self.target_alt * u.deg)
                az_object = astropy.coordinates.Angle(self.target_az * u.deg)
                if obstime is None:
                    if self.sunsim:
                        obstime_mjd = self.ephem.state.get("mjd", 0)
                        obstime = astropy.time.Time(
                            obstime_mjd, format="mjd", location=self.ephem.site
                        )
                    else:
                        obstime = astropy.time.Time(
                            datetime.utcnow(), location=self.ephem.site
                        )

                altaz = astropy.coordinates.SkyCoord(
                    alt=alt_object,
                    az=az_object,
                    location=self.ephem.site,
                    obstime=obstime,
                    frame="altaz",
                )
                j2000 = altaz.transform_to("icrs")
                self.target_ra_j2000_hours = j2000.ra.hour
                self.target_dec_j2000_deg = j2000.dec.deg
                ra_deg = j2000.ra.deg
                msg = f"target: (ra, dec) = {self.target_ra_j2000_hours:0.1f}, {self.target_dec_j2000_deg:0.1f}"
                self.log(msg)
            except Exception as e:
                self.log(f"badness getting target nominal ra/dec: {e}")

            if tracking.lower() == "auto":
                tracking = True
            else:
                pass
        elif targtype == "radec":
            try:
                self.log(f"vetting target: {target}, targtype = {targtype}")
                # make sure it's a tuple
                assert (
                    type(target) is tuple
                ), f"for {targtype} observation, target must be a tuple. got type = {type(target)}"

                # make sure it's the right length
                assert (
                    len(target) == 2
                ), f"for {targtype} observation, target must have 2 coordinates. got len(target) = {len(target)}"

                # make sure they're floats
                # self.log(f'Targ[0]: val = {target[0]}, type = {type(target[0])}')
                assert (type(target[0]) is float) & (
                    type(target[1]) is float
                ), f"for {targtype} observation, target vars must be floats"
            except Exception as e:
                self.log(f"Problem while vetting observation: {e}")
            # get the target RA (hours) and DEC (degs)
            self.target_ra_j2000_hours = target[0]
            self.target_dec_j2000_deg = target[1]

            msg = f"Observing [{obstype}] Target @ (RA, DEC) = {self.target_ra_j2000_hours:0.2f}, {self.target_dec_j2000_deg:0.2f}"
            self.alertHandler.slack_log(msg, group=None)

            # j2000_coords = astropy.coordinates.SkyCoord.from_name(obj, frame = 'icrs')
            j2000_ra = self.target_ra_j2000_hours * u.hour
            j2000_dec = self.target_dec_j2000_deg * u.deg
            j2000_coords = astropy.coordinates.SkyCoord(
                ra=j2000_ra, dec=j2000_dec, frame="icrs"
            )

            ra_deg = j2000_coords.ra.deg

            if obstime is None:
                if self.sunsim:
                    obstime_mjd = self.ephem.state.get("mjd", 0)
                    obstime = astropy.time.Time(
                        obstime_mjd, format="mjd", location=self.ephem.site
                    )
                else:
                    obstime = astropy.time.Time(
                        datetime.utcnow(), location=self.ephem.site
                    )

            # lat = astropy.coordinates.Angle(self.config['site']['lat'])
            # lon = astropy.coordinates.Angle(self.config['site']['lon'])
            # height = self.config['site']['height'] * u.Unit(self.config['site']['height_units'])
            # site = astropy.coordinates.EarthLocation(lat = lat, lon = lon, height = height)
            frame = astropy.coordinates.AltAz(obstime=obstime, location=self.ephem.site)
            local_coords = j2000_coords.transform_to(frame)
            self.target_alt = local_coords.alt.deg
            self.target_az = local_coords.az.deg

        elif targtype == "object":
            # do some asserts
            # TODO
            self.log(f"handling object observations")
            # set the comment on the fits header
            # self.log(f'setting qcomment to {target}')
            # self.qcomment = target
            self.log(f"setting targetName to {target}")
            self.targetName = target
            # make sure it's a string
            if not (type(target) is str):
                self.log(
                    f"for object observation, target must be a string object name, got type = {type(target)}"
                )
                return

            try:
                obj = target

                j2000_coords = astropy.coordinates.SkyCoord.from_name(obj, frame="icrs")

                self.target_ra_j2000_hours = j2000_coords.ra.hour
                self.target_dec_j2000_deg = j2000_coords.dec.deg
                ra_deg = j2000_coords.ra.deg

                if obstime is None:
                    if self.sunsim:
                        obstime_mjd = self.ephem.state.get("mjd", 0)
                        obstime = astropy.time.Time(
                            obstime_mjd, format="mjd", location=self.ephem.site
                        )
                    else:
                        obstime = astropy.time.Time(
                            datetime.utcnow(), location=self.ephem.site
                        )
                lat = astropy.coordinates.Angle(self.config["site"]["lat"])
                lon = astropy.coordinates.Angle(self.config["site"]["lon"])
                height = self.config["site"]["height"] * u.Unit(
                    self.config["site"]["height_units"]
                )

                site = astropy.coordinates.EarthLocation(
                    lat=lat, lon=lon, height=height
                )
                frame = astropy.coordinates.AltAz(obstime=obstime, location=site)
                local_coords = j2000_coords.transform_to(frame)
                self.target_alt = local_coords.alt.deg
                self.target_az = local_coords.az.deg

                msg = f"Doing [{obstype}] observation of {target} @ (RA, DEC) = ({self.target_ra_j2000_hours:0.2f}, {self.target_dec_j2000_deg:0.2f})"
                msg += f", (Alt, Az) = ({self.target_alt:0.2f}, {self.target_az:0.2f})"
                self.alertHandler.slack_log(msg, group=None)

            except Exception as e:
                self.log(f"error getting object coord: {e}")

        else:
            # we shouldn't ever get here because of the upper asserts
            return

        self.log(f"vetting field angle: {field_angle}")
        # handle the field angle
        if field_angle.lower() == "auto":
            # self.target_field_angle = self.config['telescope'] # this is wrong :D will give 155 instead of 65
            self.target_field_angle = self.config["telescope"]["rotator"]["winter"][
                "rotator_field_angle_zeropoint"
            ]
        else:
            self.target_field_angle = field_angle

        self.log("getting correct field angle to stay within rotator limits")

        try:

            self.target_field_angle, self.target_mech_angle = (
                self.get_safe_rotator_angle(
                    ra_hours=self.target_ra_j2000_hours,
                    dec_deg=self.target_dec_j2000_deg,
                    target_field_angle=self.target_field_angle,
                    obstime=obstime,
                    verbose=True,
                )
            )
            print(f"target_field_angle = {self.target_field_angle}")
            print(f"target_mech_angle  = {self.target_mech_angle}")

        except Exception as e:
            self.log(f"error calculating field and mechanical angles: {e}")

        # adjust the pointing center based on the offset
        self.log(
            f"calculating the new coordinates to center the field with offset type: {offset}"
        )
        try:
            # pass self.target_field_angle, the one that it chooses, and pass that to PA in the get_center_offset_coords function
            (
                self.target_ra_j2000_hours,
                self.target_dec_j2000_deg,
                ra_offset_arcmin,
                dec_offset_arcmin,
            ) = self.get_center_offset_coords(
                ra_hours=self.target_ra_j2000_hours,
                dec_deg=self.target_dec_j2000_deg,
                pa=self.target_field_angle
                - self.config["telescope"]["rotator"]["winter"][
                    "rotator_field_angle_zeropoint"
                ],
                offsettype=offset,
            )
            # return the field angle and ra/dec offsets
            return (
                self.target_field_angle,
                self.target_mech_angle,
                ra_offset_arcmin,
                dec_offset_arcmin,
            )

        except Exception as e:
            self.log(f"error calculating new pointing center offset: {e}")
            return


if __name__ == "__main__":

    print("Testing the get_safe_rotator_angle function")
    print("=========================================")

    robo = mini_roboOperator(config=config, camname="winter")
    # test the get_safe_rotator_angle function

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

    obstime_mjd = 60774.50935656831

    obstime = astropy.time.Time(obstime_mjd, format="mjd", location=robo.ephem.site)

    field_angle_zp = config["telescope"]["rotator"]["winter"][
        "rotator_field_angle_zeropoint"
    ]

    for target_name, values in targets.items():
        print()
        j2000_coords = astropy.coordinates.SkyCoord.from_name(target_name, frame="icrs")
        target = (j2000_coords.ra.hour, j2000_coords.dec.deg)

        # dispatch a fake observation
        pred_field_angle, pred_mech_angle, ra_offset_arcmin, dec_offset_arcmin = (
            robo.do_observation(
                targtype="radec",
                target=target,
                tracking="auto",
                field_angle="auto",
                obstype="TEST",
                comment="",
                obsmode="SCHEDULE",
                offset="best",
                obstime=obstime,
            )
        )

        # print the results
        print("------------------------------------------")
        print(f"target: {target_name}")

        print(
            f"field angle: predicted = {pred_field_angle}, actual = {values['field_angle']:.2f}"
        )
        print(
            f"ra_offset: predicted = {ra_offset_arcmin:.2f} arcmin, actual={values['offset']['best_center'][0]:.2f}"
        )
        print(
            f"dec_offset: predicted = {dec_offset_arcmin:.2f} arcmin, actual={values['offset']['best_center'][1]:.2f}"
        )
        print("------------------------------------------")
