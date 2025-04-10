from datetime import datetime

import astropy.coordinates
import astropy.time
import astropy.units as u
import numpy as np


class Rotator:
    def __init__(self, config, camname = 'summer'):
        self.config = config
        # set up site
        lat = astropy.coordinates.Angle(self.config["site"]["lat"])
        lon = astropy.coordinates.Angle(self.config["site"]["lon"])
        height = self.config["site"]["height"] * u.Unit(
            self.config["site"]["height_units"]
        )

        self.site = astropy.coordinates.EarthLocation(lat=lat, lon=lon, height=height)
        self.camname = camname
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
            obstime = astropy.time.Time(datetime.utcnow(), location=self.site)

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
            self.site
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
    
if __name__ == "__main__":

    config = {
        "site":{
            # lat/lon. expects a format that can be read with astropy.coordinates.Angle()
                "lat": '33d21m21.6s',
                "lon": '-116d51m46.8s',
                # height (site altitude). height is a number, units are something that can be parsed with astropy.units.Unit()
                "height": 1706,
                "height_units": 'm',
                "timezone": 'America/Los_Angeles',
            },
        "telescope": {
            "rotator": {
                "summer": {
                    "rotator_field_angle_zeropoint": 155.0,
                    "rotator_home_degs": -25.0,
                    "rotator_max_degs": 120.0,
                    "rotator_min_degs": -120.0,
                },
        },
    }}

    rotator = Rotator(config)
    ra, dec = "4:29:19", "43:54:23"
    ra_hours = astropy.coordinates.Angle(ra, unit=u.hour).value
    dec_deg = astropy.coordinates.Angle(dec, unit=u.deg).value
    target_field_angle = 155.0
    obstime = astropy.time.Time(datetime.utcnow(), location=rotator.site)
    rotator.get_safe_rotator_angle(ra_hours, dec_deg, target_field_angle, obstime, verbose=True)
    