from datetime import datetime

import astropy.units as u
import numpy as np
from astropy.coordinates import AltAz, Angle, EarthLocation, SkyCoord
from astropy.time import Time


def get_rotator_mech_angle(
    site,
    target_ra_j2000_hours,
    target_dec_j2000_deg,
    target_field_angle,
    obstime=None,
    port=1,
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
    """

    if obstime is None:
        obstime = Time(datetime.utcnow(), location=site)

    j2000_ra = target_ra_j2000_hours * u.hour
    j2000_dec = target_dec_j2000_deg * u.deg
    j2000_coords = SkyCoord(ra=j2000_ra, dec=j2000_dec, frame="icrs")

    ra_deg = j2000_coords.ra.deg

    if port == 1:
        parity = 1
    elif port == 2:
        parity = -1
    else:
        raise ValueError("Invalid port number")

    # lat = astropy.coordinates.Angle(self.config['site']['lat'])
    # lon = astropy.coordinates.Angle(self.config['site']['lon'])
    # height = self.config['site']['height'] * u.Unit(self.config['site']['height_units'])

    frame = AltAz(obstime=obstime, location=site)
    local_coords = j2000_coords.transform_to(frame)
    target_alt = local_coords.alt.deg
    target_az = local_coords.az.deg

    dec = target_dec_j2000_deg * np.pi / 180.0
    lst = obstime.sidereal_time("mean").rad
    if verbose:
        print(
            f"lst = {obstime.sidereal_time('mean').to_string(unit = u.hour, sep = ':')}"
        )
    hour_angle = lst - ra_deg * np.pi / 180.0
    if verbose:
        print(f"hour_angle (rad) = {hour_angle}")
    if hour_angle < -1 * np.pi:
        hour_angle += 2 * np.pi
    if hour_angle > np.pi:
        hour_angle -= 2 * np.pi

    if verbose:
        print(f"hour_angle (rad) = {hour_angle}")
        print(
            f"hour_angle = {Angle(hour_angle*u.rad).to_string(unit = u.hour, sep = ':')}"
        )
    lat = site.lat.rad

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
    ]

    possible_target_mech_angles = [
        float(target_field_angle - parallactic_angle - parity * target_alt)
        for target_field_angle in possible_target_field_angles
    ]
    if verbose:
        print(f"Possible rotator mech angles: {possible_target_mech_angles}")
    messages = [
        "No rotator wrap predicted",
        "Rotator wrapping < min, adjusting by -360 deg.",
        "Rotator wrapping > max, adjusting by +360 deg.",
    ]

    if verbose:
        print("\n##########################################")
    for ind, possible_target_mech_angle in enumerate(possible_target_mech_angles):
        target_mech_angle = possible_target_mech_angle
        # if the target mech angle is within the range (-360, 360) then break, else try the next option
        if -360.0 < target_mech_angle < 360.0:
            if verbose:
                print(messages[ind])
                print(f"Adjusted field angle --> {target_field_angle}")
                print(f"New target mech angle = {target_mech_angle}")
            break

    if verbose:
        print("##########################################")

    return target_mech_angle


def get_rotator_field_angle(
    site,
    target_ra_j2000_hours,
    target_dec_j2000_deg,
    target_mech_angle,
    port=1,
    obstime=None,
    verbose=False,
):
    """
    Inverse of get_rotator_mech_angle.

    Given a mechanical angle, compute a field angle that, after applying
    cable-wrap constraints, is consistent with the input mechanical angle.

    The underlying geometry is:
        mech_angle = field_angle - parallactic_angle - alt

    so:

        field_angle = mech_angle + parallactic_angle + alt
    """

    if obstime is None:
        obstime = Time(datetime.utcnow(), location=site)

    if port == 1:
        parity = 1
    elif port == 2:
        parity = -1
    else:
        raise ValueError("Invalid port number")

    # Convert target RA/Dec to a SkyCoord
    j2000_ra = target_ra_j2000_hours * u.hour
    j2000_dec = target_dec_j2000_deg * u.deg
    j2000_coords = SkyCoord(ra=j2000_ra, dec=j2000_dec, frame="icrs")

    # Transform to local AltAz
    frame = AltAz(obstime=obstime, location=site)
    local_coords = j2000_coords.transform_to(frame)
    target_alt = local_coords.alt.deg

    # Compute sidereal time, hour angle, parallactic angle
    dec_rad = target_dec_j2000_deg * np.pi / 180.0
    lst_rad = obstime.sidereal_time("mean").rad
    hour_angle = lst_rad - j2000_coords.ra.rad
    # Force hour_angle into [-pi, +pi]
    if hour_angle < -np.pi:
        hour_angle += 2.0 * np.pi
    if hour_angle > np.pi:
        hour_angle -= 2.0 * np.pi

    lat_rad = site.lat.rad
    parallactic_angle = (
        np.arctan2(
            np.sin(hour_angle),
            np.tan(lat_rad) * np.cos(dec_rad) - np.sin(dec_rad) * np.cos(hour_angle),
        )
        * 180.0
        / np.pi
    )

    # Solve for the naive field angle from the input mech angle:
    naive_field_angle = target_mech_angle + parallactic_angle + parity * target_alt

    # Next, apply cable-wrap logic to find the best field angle that
    # remains consistent with the *input mech angle* while adjusting +/- 360
    # as needed. The "consistency" equation is:
    #
    #   target_mech_angle == field_angle - parallactic_angle - target_alt
    #
    # So for each candidate field_angle in [naive, naive +/- 360],
    # we check if the resulting mech angle matches the user’s input
    # (i.e., within some small tolerance), and then also if that
    # candidate field angle is in an allowed range if you desire.

    possible_field_angles = [
        naive_field_angle,
        naive_field_angle - 360.0,
        naive_field_angle + 360.0,
    ]

    # We'll see which candidate is the best. For instance,
    # we might want the final field angle in [-360..+360], or
    # just whichever is "closest" to naive_field_angle.
    chosen_field_angle = None
    tolerance = 1e-6  # deg (or as appropriate)

    if verbose:
        print(f"Naive field angle: {naive_field_angle:.3f} deg")
        print("Possible field angles:", possible_field_angles)

    for candidate in possible_field_angles:
        # Recompute the implied mech angle from candidate
        implied_mech_angle = candidate - parallactic_angle - target_alt
        # Compare with the user-supplied mechanical angle
        if abs(implied_mech_angle - target_mech_angle) < tolerance:
            # Also optionally check if candidate is in some range
            if -360.0 < candidate < 360.0:
                chosen_field_angle = candidate
                break

    if chosen_field_angle is None:
        # If none matched the tolerance or range, pick naive anyway
        # (or you can pick whichever of possible_field_angles is closest)
        chosen_field_angle = naive_field_angle

    if verbose:
        print(f"Final chosen field angle: {chosen_field_angle:.3f} deg")

    return chosen_field_angle


if __name__ == "__main__":

    SITE_LATITUDE = "33d21m21.6s"
    SITE_LONGITUDE = "-116d51m46.8s"
    SITE_HEIGHT = 1706  # meters
    SITE = EarthLocation(lat=SITE_LATITUDE, lon=SITE_LONGITUDE, height=SITE_HEIGHT)

    target_ra_j2000_hours = 14
    target_dec_j2000_deg = 76.0

    # Port 1
    target_field_angle = 245
    obstime = Time(datetime(2024, 12, 17, 17, 17, 7, 503155), location=SITE)
    actual_mech_angle = 42
    pred_mech_angle = get_rotator_mech_angle(
        SITE,
        target_ra_j2000_hours,
        target_dec_j2000_deg,
        target_field_angle,
        obstime=obstime,
        verbose=True,
    )
    print(
        f"PORT 1: Predicted mech angle {pred_mech_angle:.1f} is off from actual {actual_mech_angle:.1f} by {pred_mech_angle - actual_mech_angle:.1f} deg"
    )

    pred_field_angle = get_rotator_field_angle(
        SITE,
        target_ra_j2000_hours,
        target_dec_j2000_deg,
        actual_mech_angle,
        obstime=obstime,
        verbose=True,
    )
    print(
        f"PORT 1: Predicted field angle {pred_field_angle:.1f} is off from actual {target_field_angle:.1f} by {pred_field_angle - target_field_angle:.1f} deg"
    )

    # Port 2
    print()
    print()
    target_field_angle = 295
    print(Time.now())
    obstime = Time(datetime(2024, 12, 17, 19, 3, 15, 310288), location=SITE)
    obstime = None
    actual_mech_angle = 211.93
    pred_mech_angle = get_rotator_mech_angle(
        SITE,
        target_ra_j2000_hours,
        target_dec_j2000_deg,
        target_field_angle,
        port=2,
        obstime=obstime,
        verbose=True,
    )
    print(
        f"PORT 2: Predicted mech angle {pred_mech_angle:.1f} is off from actual {actual_mech_angle:.1f} by {pred_mech_angle - actual_mech_angle:.1f} deg"
    )

    pred_field_angle = get_rotator_field_angle(
        SITE,
        target_ra_j2000_hours,
        target_dec_j2000_deg,
        actual_mech_angle,
        obstime=obstime,
        port=2,
        verbose=True,
    )
    print(
        f"PORT 2: Predicted field angle {pred_field_angle:.1f} is off from actual {target_field_angle:.1f} by {pred_field_angle - target_field_angle:.1f} deg"
    )
