"""Routines for working with the ZTF discrete field grid"""

import numpy as np
import pandas as pd
import astropy.coordinates as coord
import astropy.units as u
from astropy.time import Time
from collections import defaultdict
import itertools
from .utils import *
from .constants import BASE_DIR, P48_loc, W_slew_pars, PROGRAM_IDS, FILTER_IDS
from .constants import TIME_BLOCK_SIZE, MAX_AIRMASS, EXPOSURE_TIME, READOUT_TIME
from .constants import slew_time


class Fields(object):
    """Class for accessing field grid."""

    # W change base dir
    #def __init__(self, field_filename=BASE_DIR + '../data/ZTF_Fields.txt'):
    def __init__(self, field_filename=BASE_DIR + '../data/SUMMER_fields.txt'): # W
        self._load_fields(field_filename)
        self.loc = W_loc
        self.current_block_night_mjd = None  # np.floor(time.mjd)
        self.current_blocks = None
        self.block_alt = None
        self.block_az = None
        self.observable_hours = None

    def _load_fields(self, field_filename):
        """Loads a field grid of the format generated by Tom B.
        Expects field_id, ra (deg), dec (deg) columns"""

        df = pd.read_csv(field_filename,
            names=['field_id','ra','dec','ebv','l','b',
                'ecliptic_lon', 'ecliptic_lat', 'number'],
            sep='\s+',usecols=['field_id','ra','dec', 'l','b', 
                'ecliptic_lon', 'ecliptic_lat'],index_col='field_id',
            skiprows=1)


        # drop fields below dec of -36 degrees for speed
        # W
        df = df[df['dec'] >= -35]

        # W Add more
        # label the grid ids
        grid_id_boundaries = \
            {0: {'min':1,'max':99999},
             1: {'min':100001,'max':199999},
             2: {'min':200001,'max':299999},
             3: {'min':300001,'max':700000}}

        # intialize with a bad int value
        df['grid_id'] = 99

        for grid_id, bounds in list(grid_id_boundaries.items()):
            w = (df.index >= bounds['min']) &  \
                    (df.index <= bounds['max'])
            df.loc[w,'grid_id'] = grid_id

        self.fields = df
        self.field_coords = self._field_coords()

    def _field_coords(self, cuts=None):
        """Generate an astropy SkyCoord object for current fields"""
        if cuts is None:
            fields = self.fields
        else:
            fields = self.fields[cuts]
        return coord.SkyCoord(fields['ra'],
                              fields['dec'], frame='icrs', unit='deg')

    def compute_blocks(self, time, time_block_size=TIME_BLOCK_SIZE):
        """Store alt/az for tonight in blocks"""

        # check if we've already computed for tonight:
        block_night = np.floor(time.mjd).astype(np.int)
        if self.current_block_night_mjd == block_night:
            return

        self.current_block_night_mjd = block_night

        blocks, times = nightly_blocks(time, time_block_size=time_block_size)
        self.current_blocks = blocks

        alt_blocks = {}
        az_blocks = {}
        for bi, ti in zip(blocks, times):
            altaz = self.alt_az(ti)
            alt_blocks[bi] = altaz.alt
            az_blocks[bi] = altaz.az

        # DataFrames indexed by field_id, columns are block numbers
        self.block_alt = pd.DataFrame(alt_blocks)
        self.block_az = pd.DataFrame(az_blocks)

        block_airmass = altitude_to_airmass(self.block_alt)
        w = (block_airmass <= MAX_AIRMASS) & (block_airmass >= 1.0)
        # average airmass over the time we're above MAX_AIRMASS
        mean_observable_airmass = block_airmass[w].mean(axis=1)
        mean_observable_airmass.name = 'mean_observable_airmass'
        self.mean_observable_airmass = mean_observable_airmass

    def compute_observability(self, max_airmass=MAX_AIRMASS,
                              time_block_size=TIME_BLOCK_SIZE):
        """For each field_id, use the number of nighttime blocks above max_airmass to compute observability time."""

        min_alt = airmass_to_altitude(max_airmass)

        observable_hours = (self.block_alt >= min_alt.to(u.degree).value).sum(axis=1) * \
            (TIME_BLOCK_SIZE.to(u.hour))
        observable_hours.name = 'observable_hours'
        self.observable_hours = observable_hours

    def alt_az(self, time, cuts=None):
        """return Altitude & Azimuth by field at a given time"""

        if cuts is None:
            index = self.fields.index
            fieldsAltAz = self.field_coords.transform_to(
                coord.AltAz(obstime=time, location=self.loc))
        else:
            # warning: specifying cuts makes this much slower
            index = self.fields[cuts].index
            fieldsAltAz = self._field_coords(cuts=cuts).transform_to(
                coord.AltAz(obstime=time, location=self.loc))

        return pd.DataFrame({'alt': fieldsAltAz.alt, 'az': fieldsAltAz.az},
                            index=index)

    def overhead_time(self, current_state, cuts=None):
        """Calculate overhead time in seconds from current position.
        Also returns current altitude, for convenience.

        cuts is a boolean series indexed by field_id, as generated by
        select_fields """

        if cuts is None:
            fields = self.fields
        else:
            fields = self.fields[cuts]

        df_altaz = self.alt_az(current_state['current_time'], cuts=cuts)
        df = fields.join(df_altaz)

        slews_by_axis = {'readout': READOUT_TIME}
        for axis in ['dome', 'dec', 'ha']:
            if axis == 'dome':
                current_coord = current_state['current_domeaz'].value
            if axis == 'ha':
                # convert to RA for ease of subtraction
                current_coord = HA_to_RA(current_state['current_ha'],
                                         current_state['current_time']).degree
            if axis == 'dec':
                current_coord = current_state['current_dec'].value
            coord = W_slew_pars[axis]['coord']
            dangle = np.abs(df[coord] - current_coord)
            angle = np.where(dangle < (360. - dangle), dangle, 360. - dangle)
            slews_by_axis[axis] = slew_time(axis, angle * u.deg)

        dfslews = pd.DataFrame(slews_by_axis, index=df.index)

        dfmax = dfslews.max(axis=1)
        dfmax = pd.DataFrame(dfmax)
        dfmax.columns = ['overhead_time']

        return dfmax, df_altaz

    def select_fields(self,
                      ra_range=None, dec_range=None,
                      l_range=None, b_range=None,
                      abs_b_range=None,
                      ecliptic_lon_range=None, ecliptic_lat_range=None,
                      grid_id=None,
                      observable_hours_range=None):
        """Select a subset of fields based on their sky positions.

        Each _range keyword takes a list[min, max].
        grid_id is a scalar

        Returns a boolean array indexed by field_id."""

        # start with a boolean True series:
        cuts = (self.fields['ra'] == self.fields['ra'])

        if observable_hours_range is not None:
            # check that we've computed observable_hours
            assert(self.observable_hours is not None)
            fields = self.fields.join(self.observable_hours)
        else:
            fields = self.fields

        range_keys = ['ra', 'dec', 'l', 'b', 'ecliptic_lon', 'ecliptic_lat',
                      'observable_hours']

        assert((b_range is None) or (abs_b_range is None))

        for i, arg in enumerate([ra_range, dec_range, l_range, b_range,
                                 ecliptic_lon_range, ecliptic_lat_range,
                                 observable_hours_range]):
            if arg is not None:
                cuts = cuts & (fields[range_keys[i]] >= arg[0]) & \
                    (fields[range_keys[i]] <= arg[1])

        # easier cuts for Galactic/Extragalactic
        if abs_b_range is not None:
            cuts = cuts & (np.abs(fields['b']) >= abs_b_range[0]) & \
                (np.abs(fields['b']) <= abs_b_range[1])

        scalar_keys = ['grid_id']

        for i, arg in enumerate([grid_id]):
            if arg is not None:
                cuts = cuts & (fields[scalar_keys[i]] == arg)

        return cuts

    def select_field_ids(self, **kwargs):
        """Returns a pandas index"""
        cuts = self.select_fields(**kwargs)
        return self.fields[cuts].index
