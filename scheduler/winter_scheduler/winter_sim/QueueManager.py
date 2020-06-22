"""Queue classes."""

import os
from collections import defaultdict
from datetime import datetime
import logging
import numpy as np
import pandas as pd
import astropy.coordinates as coord
import astropy.units as u
from astropy.time import Time, TimeDelta
import astroplan
from .Fields import Fields
#from .SkyBrightness import SkyBrightness, FakeSkyBrightness
from .magnitudes import W_limiting_mag
from .optimize import request_set_optimize, slot_optimize, tsp_optimize, night_optimize
from .cadence import enough_gap_since_last_obs
from .constants import W_loc, P48_loc, PROGRAM_IDS, FILTER_IDS, TIME_BLOCK_SIZE
from .constants import EXPOSURE_TIME, READOUT_TIME, FILTER_CHANGE_TIME, slew_time
from .constants import PROGRAM_BLOCK_SEQUENCE, LEN_BLOCK_SEQUENCE, MAX_AIRMASS
from .constants import BASE_DIR
from .utils import approx_hours_of_darkness
from .utils import skycoord_to_altaz, seeing_at_pointing
from .utils import altitude_to_airmass, airmass_to_altitude, RA_to_HA, HA_to_RA
from .utils import scalar_len, nightly_blocks, block_index, block_index_to_time
from .utils import block_use_fraction
from .utils import airglow_by_altitude

class QueueEmptyError(Exception):
    """Error class for when the nightly queue has no more fields"""
    pass


class QueueManager(object):

    def __init__(self, queue_name, queue_configuration, rp=None, fields=None):

        self.logger = logging.getLogger(__name__)

        # queue name (useful in Scheduler object when swapping queues)
        self.queue_name = queue_name

        # list of ObservingPrograms
        self.observing_programs = queue_configuration.build_observing_programs()

        # defaults to handle time-windowed queues
        self.is_TOO = False
        self.validity_window = None

        # Hack for greedy queues
        self.requests_in_window = True

        if 'validity_window_mjd' in queue_configuration.config:
            window = queue_configuration.config['validity_window_mjd']
            if window is not None:
                assert(len(window) == 2)
                self.set_validity_window_mjd(window[0], window[1])
            else:
                self.validity_window = None
        else:
            self.validity_window = None

        # flag to check if assign_nightly_requests has been called tonight
        self.queue_night = None

        # block on which the queue parameters were calculated
        self.queue_slot = None

        # number allowed requests by subprogram tonight 
        # (dict of (program_id, subprogram_name))
        self.requests_allowed = {}

        # the queue itself
        self.queue = pd.DataFrame()

        # should we only consider fields from one program in a given
        # observing block?  
        # CURRENTLY NOT IMPLEMENTED.
        self.block_programs = False

        if rp is None:
            # initialize an empty RequestPool
            self.rp = RequestPool()
        else:
            self.rp = rp

        if fields is None:
            self.fields = Fields()
        else:
            self.fields = fields

        # self.Sky = SkyBrightness()

    def is_valid(self, time):
        if self.validity_window is None:
            return True

        window_start = self.validity_window[0]
        window_stop = self.validity_window[1]

        return window_start <= time <= window_stop

    def validity_window_mjd(self):
        if self.validity_window is None:
            return None

        return [self.validity_window[0].mjd, self.validity_window[1].mjd]

    def set_validity_window_mjd(self, window_start, window_stop):
        """Set the time at which this queue can run.

        Parameters
        ----------
        window_start : `float` 
            Modified Julian Date start time
        window_stop : `float` 
            Modified Julian Date end time
        """

        if window_start >= window_stop:
            raise ValueError("validity window start time must be less than end time")
        # rough sanity checks
        if window_start <= Time('2017-01-01').mjd:
            raise ValueError(f"MJD likely out of range: {window_start}")
        if window_stop >= Time('2030-01-01').mjd:
            raise ValueError(f"MJD likely out of range: {window_stop}")

        self.validity_window = [Time(window_start,format='mjd'),
            Time(window_stop,format='mjd')]

    def compute_block_use(self):
        """Returns a dictionary with the fraction of blocks used by the queue,
        assuming observing starts at the beginning of the validity window"""
        

        if self.validity_window is None:
            raise ValueError('All blocks are valid')

        start_block = block_index(self.validity_window[0])
        obs_start_time = Time(self.validity_window[0],format='mjd')

        # greedy queues have no len until they have assignments made, so 
        # just use the validity window
        if len(self.queue) == 0:
            stop_block = block_index(self.validity_window[1])
            obs_end_time = self.validity_window[1]

        else:
            # with no weather, we start at the start of the window 
            if 'n_repeats' in self.queue.columns:
                n_obs = np.sum(self.queue.n_repeats)
                exp_time = np.sum(self.queue.exposure_time * self.queue.n_repeats)
            else:
                n_obs = len(self.queue)
                exp_time = np.sum(self.queue.exposure_time)
            obs_time = (exp_time * u.second) + n_obs * READOUT_TIME
            obs_end_time = self.validity_window[0] + obs_time

            stop_block = block_index(obs_end_time)
            # below breaks if the window is longer than the observations
            #stop_block = block_index(self.validity_window[1])

        assert obs_end_time > obs_start_time

        # compute fraction of the blocks used by the queue
        block_use = defaultdict(float)

        for block in np.arange(start_block, stop_block+1):

            block_use[block] = block_use_fraction(block, obs_start_time,
                                                  obs_end_time)

        return block_use

    def add_observing_program(self, observing_program):
        self.observing_programs.append(observing_program)

    def assign_nightly_requests(self, current_state, obs_log, 
            time_limit = 30 * u.second, block_use = defaultdict(float),
            timed_obs_count = defaultdict(int)):
        # clear previous request pool
        self.rp.clear_all_request_sets()
        # set number of allowed requests by program.
        self.determine_allowed_requests(current_state['current_time'],
                obs_log, timed_obs_count = timed_obs_count)

        for program in self.observing_programs:

            request_sets = program.assign_nightly_requests(
                current_state['current_time'], self.fields,
                obs_log, block_programs=self.block_programs)
            for rs in request_sets:
                self.rp.add_request_sets(rs['program_id'], 
                            rs['subprogram_name'], rs['program_pi'],
                            rs['field_ids'], rs['filter_ids'], 
                            rs['intranight_gap'],
                            rs['exposure_time'],
                            rs['total_requests_tonight'])

        if (len(self.rp.pool) <= 0): # W
            raise QueueEmptyError("Started night with no valid observations")

        assert(len(self.rp.pool) > 0)

        # any specific tasks needed)
        self._assign_nightly_requests(current_state, 
                time_limit = time_limit, block_use = block_use)

        # mark that we've set up the pool for tonight
        self.queue_night = np.floor(current_state['current_time'].mjd) 


    def adjust_program_exposures_tonight(self, obs_log, mjd_start, mjd_stop):
        """Use past history to adjust the number of exposures per program tonight.
        
        Counts exposures from the start of the month and equalizes any excess
        over NIGHTS_TO_REDISTRIBUTE or the number of nights to the end of 
        the month, whichever is less."""
        
        obs_count_by_program = obs_log.count_equivalent_obs_by_program(
                mjd_range = [mjd_start, mjd_stop])
        # drop engineering/commissioning
        obs_count_by_program = obs_count_by_program[
                obs_count_by_program['program_id'] != 0]
        obs_count_by_program.set_index('program_id', inplace=True)

        # if there are no observations, add zeros
        for program_id in PROGRAM_IDS:
            if program_id != 0:
                if program_id not in obs_count_by_program.index:
                    obs_count_by_program.loc[program_id] = 0

        total_obs = np.sum(obs_count_by_program['n_obs'])

        # infer the program fractions from the subprograms
        target_program_fractions = {propid:0 for propid in PROGRAM_IDS 
                if propid != 0}
        for op in self.observing_programs:
            target_program_fractions[op.program_id] = \
                    op.program_observing_time_fraction

        target_program_fractions = pd.Series(target_program_fractions) 
        target_program_fractions.index.name = 'program_id'
        target_program_fractions.name = 'target_fraction'

        target_program_nobs = target_program_fractions * total_obs
        target_program_nobs.name = 'target_program_nobs'

        # note that this gives 0 in case of no observations, as desired
        # have to do the subtraction backwords because of Series/DataFrame 
        # API nonsense
        delta_program_nobs = \
                -1*obs_count_by_program.subtract(target_program_nobs,
                    axis=0)

        NIGHTS_TO_REDISTRIBUTE = 5
        time = Time(mjd_stop,format='mjd')
        dtnow = time.to_datetime()
        if dtnow.month != 12:
            next_month_start_mjd = Time(datetime(dtnow.year,dtnow.month+1,1),
                    scale='utc').mjd
        else:
            next_month_start_mjd = Time(datetime(dtnow.year+1,1,1),
                    scale='utc').mjd
        nights_left_this_month = np.round(next_month_start_mjd - time.mjd)

        if nights_left_this_month > NIGHTS_TO_REDISTRIBUTE:
            divisor = NIGHTS_TO_REDISTRIBUTE
        else:
            divisor = nights_left_this_month
            if divisor == 0:
                divisor = 1

        delta_program_nobs /= divisor

        delta_program_nobs = np.round(delta_program_nobs).astype(int)

        return delta_program_nobs
        



    def determine_allowed_requests(self, time, obs_log, 
            timed_obs_count = defaultdict(int)):
        """Use count of past observations and expected observing time fractions
        to determine number of allowed requests tonight.
        
        Exclude observations already planned in timed queues."""

        self.requests_allowed = {}

        # rather than using equivalent obs, might be easier to work in 
        # exposure time directly?
        
        # enforce program balance on a monthly basis
        dtnow = time.to_datetime()
        month_start_mjd = Time(datetime(dtnow.year,dtnow.month,1),
                scale='utc').mjd
        
        delta_program_exposures_tonight = self.adjust_program_exposures_tonight(
            obs_log, month_start_mjd, time.mjd)
        
        self.logger.info(f'Change in allowed exposures: {delta_program_exposures_tonight}')
        self.logger.info(f'Number of timed observations: {timed_obs_count}')

        dark_time = approx_hours_of_darkness(time)
        
        # calculate subprogram fractions excluding list queues and TOOs
        scheduled_subprogram_sum = defaultdict(float)
        for op in self.observing_programs:
            if len(op.field_ids) > 0:
                scheduled_subprogram_sum[op.program_id] += \
                        op.subprogram_fraction

        for op in self.observing_programs:

            
            program_time_tonight = (
                dark_time * op.program_observing_time_fraction +  
                (delta_program_exposures_tonight.loc[op.program_id,'n_obs'] 
                - timed_obs_count[op.program_id]) * (EXPOSURE_TIME+READOUT_TIME))
            subprogram_time_tonight = (
                program_time_tonight * op.subprogram_fraction / 
                scheduled_subprogram_sum[op.program_id])

            n_requests = (subprogram_time_tonight.to(u.min) / 
                    op.time_per_exposure().to(u.min)).value[0]
            n_requests = np.round(n_requests).astype(np.int)

            self.requests_allowed[(op.program_id, 
                op.subprogram_name)] = n_requests

        for key, n_requests in self.requests_allowed.items():
            if n_requests < 0:
                self.requests_allowed[key] = 0

        self.logger.info(self.requests_allowed)

    def next_obs(self, current_state, obs_log, time_limit = 30 * u.second):
        """Given current state, return the parameters for the next request"""
        # don't store the telescope state locally!

        # check that assign_nightly_requests has been called tonight.
        if self.queue_type != 'list':
            if np.floor(current_state['current_time'].mjd) != self.queue_night:
                self.assign_nightly_requests(current_state, obs_log)

        # define functions that actually do the work in subclasses
        next_obs = self._next_obs(current_state, obs_log,time_limit = time_limit)

        # check if we have a disallowed observation, and reject it:
        if next_obs['target_limiting_mag'] < 0:
            self.remove_requests(next_obs['request_id'])
            next_obs = self.next_obs(current_state, obs_log)

        next_obs['queue_name'] = self.queue_name

        return next_obs

    def update_queue(self, current_state, obs_log, **kwargs):
        """Recalculate queue"""

        # define functions that actually do the work in subclasses
        return self._update_queue(current_state, obs_log)

    def remove_requests(self, request_id):
        """Remove a request from both the queue and the request set pool"""

        # define functions that actually do the work in subclasses
        return self._remove_requests(request_id)

    def compute_limiting_mag(self, df, time, filter_id=None):
        """compute limiting magnitude based on sky brightness and seeing"""

        # copy df so we can edit the filter id if desired
        if filter_id is not None:
            df = df.copy()
            df['filter_id'] = filter_id

        # compute inputs for sky brightness
        sc = coord.SkyCoord(df['ra'], df['dec'], frame='icrs', unit='deg')
        sun = coord.get_sun(time)
        sun_altaz = skycoord_to_altaz(sun, time)
        moon = coord.get_moon(time, location=W_loc)
        moon_altaz = skycoord_to_altaz(moon, time)
        df.loc[:, 'moonillf'] = astroplan.moon.moon_illumination(time)
        
        # WORKING AROUND BUG in moon distance!!!!  171110
        df.loc[:, 'moon_dist'] = moon.separation(sc).to(u.deg).value
        df.loc[:, 'moonalt'] = moon_altaz.alt.to(u.deg).value
        df.loc[:, 'sunalt'] = sun_altaz.alt.to(u.deg).value

        # check if the sun is up anywhere and break things if it isn't
        if np.sum(df['sunalt'] > -6) != 0:
            raise ValueError('Some pointings outside six-degree twilight!')

        # compute sky brightness
        # only have values for reasonable altitudes (set by R20_absorbed...)
        wup = df['altitude'] >= airmass_to_altitude(MAX_AIRMASS) 
        df.loc[wup, 'sky_brightness'] = airglow_by_altitude(\
                                        altitude = df.loc[wup,'altitude'],
                                        filter_id = df.loc[wup,'filter_id'])

        # compute seeing at each pointing
        df.loc[wup, 'seeing'] = seeing_at_pointing(df.loc[wup,'altitude'])

        df.loc[wup, 'limiting_mag'] = W_limiting_mag(EXPOSURE_TIME, 
            df.loc[wup, 'seeing'],
            df.loc[wup, 'sky_brightness'],
            filter_id = df.loc[wup,'filter_id'],
            altitude = df.loc[wup,'altitude'])
       
        

        # renormalize limiting mags to the R-band range so we maintain 
        # the causal structure with airmass, etc. but can get i-band scheduled
        
        # bright time limiting mags (from PTF-trained model--see 170930 notes
        # and plot_sky_brightness_model.ipynb)
        mlim_bright_g = 19.9
        mlim_bright_r = 20.1
        mlim_bright_i = 19.5
        dm_g = (21.9-19.9)
        dm_r = (21.5-20.1)
        dm_i = (20.9-19.5)

#        wg = df['filter_id'] == 1
#        if np.sum(wg):
#            df.loc[wg,'limiting_mag'] = \
#                (df.loc[wg,'limiting_mag'] - mlim_bright_g) * dm_r/dm_g \
#                + mlim_bright_r
#
#        wi = df['filter_id'] == 3
#        if np.sum(wi):
#            df.loc[wi,'limiting_mag'] = \
#               (df.loc[wi,'limiting_mag'] - mlim_bright_i) * dm_r/dm_i \
#                + mlim_bright_r 

        # assign a very bright limiting mag to the fields that are down 
        # so the metric goes to zero
        df.loc[~wup, 'limiting_mag'] = -99

        # assign a very bright limiting mag to the fields within 20 degrees of
        # the moon 
        wmoon = df['moon_dist'] < 20
        df.loc[wmoon, 'limiting_mag'] = -99

        # need to check the Hour Angle at both the start and the end of the
        # block, since we don't know the exact time it will be observed

        # time is provided at the block midpoint

        ha_vals = RA_to_HA(df['ra'].values*u.degree, 
                time - TIME_BLOCK_SIZE/2.)
        # for limits below, need ha-180-180
        ha_vals = ha_vals.wrap_at(180.*u.degree)
        ha = pd.Series(ha_vals.to(u.degree), index=df.index, name='ha')

        ha_vals_end = RA_to_HA(df['ra'].values*u.degree, 
                time + TIME_BLOCK_SIZE/2.)
        # for limits below, need ha-180-180
        ha_vals_end = ha_vals_end.wrap_at(180.*u.degree)
        ha_end = pd.Series(ha_vals_end.to(u.degree), index=df.index, name='ha')

        # lock out TCS limits
        
        # Reed limits |HA| to < 5.95 hours (most relevant for circumpolar
        # fields not hit by the airmass cut)
        # whalimit = np.abs(ha) >= (5.95 * u.hourangle).to(u.degree).value
        # whalimit_end = np.abs(ha_end) >= (5.95 * u.hourangle).to(u.degree).value
        # df.loc[whalimit | whalimit_end, 'limiting_mag'] = -99

        # 1) HA < -17.6 deg && Dec < -22 deg is rejected for both track & stow because of interference with FFI.
        # w1 = (ha <= -17.6) & (df['dec'] <= -22)
        # w1_end = (ha_end <= -17.6) & (df['dec'] <= -22)
        # df.loc[w1 | w1_end, 'limiting_mag'] = -99

        # West of HA -17.6 deg, Dec < -45 deg is rejected for tracking because of the service platform in the south.  
        # w2 = (ha >= -17.6) & (df['dec'] <= -45)
        # w2_end = (ha_end >= -17.6) & (df['dec'] <= -45)
        # df.loc[w2 | w2_end, 'limiting_mag'] = -99

        # fabs(HA) > 3 deg is rejected for Dec < -46 to protect the shutter "ears".  
        # w3 = (np.abs(ha) >= 3.) & (df['dec'] <= -46)
        # w3_end = (np.abs(ha_end) >= 3.) & (df['dec'] <= -46)
        # df.loc[w3 | w3_end, 'limiting_mag'] = -99

        # dec > 87.5 is rejected
        # w4 = (df['dec'] > 87.5)
        # df.loc[w4, 'limiting_mag'] = -99

        return df['limiting_mag'], df['sky_brightness']

    def return_queue(self):
        """Return queue values, ordered in the expected sequence if possible"""

        queue = self._return_queue()

        cols = ['field_id','filter_id','exposure_time','program_id',
                'subprogram_name','ra','dec','ordered']
        if self.queue_type == 'gurobi':
            cols.append('slot_start_time')

        return queue.loc[:,cols]



class GurobiQueueManager(QueueManager):

    def __init__(self, queue_name, queue_configuration, **kwargs):
        super().__init__(queue_name, queue_configuration, **kwargs)
        self.block_obs_number = 0
        self.queue_type = 'gurobi'

    def _assign_nightly_requests(self, current_state, 
            time_limit = 30.*u.second, block_use = defaultdict(float)): 
        self._assign_slots(current_state, time_limit = time_limit, 
                block_use = block_use)

    def _next_obs(self, current_state, obs_log, time_limit = 30.*u.second):
        """Select the highest value request."""

        # do the slot assignment at the beginning of the night 
        # (or if the queue is empty, which should be unusual)

        # if we've entered a new block, solve the TSP to sequence the requests
        if (block_index(current_state['current_time'])[0] != self.queue_slot):
            self._sequence_requests_in_block(current_state, time_limit = time_limit)

        if (len(self.queue_order) == 0):
            raise QueueEmptyError("Ran out of observations this block.") 
        
        idx = self.queue_order[0]
        row = self.queue.loc[idx]
        
        if self.queue_slot in self.filter_by_slot:
            filter_id = int(self.filter_by_slot[self.queue_slot])
        else:
            raise QueueEmptyError("No requests in this slot!")
        # W
        filter_id = row['filter_id']
        request_id = row['req_id']
        
        next_obs = {'target_field_id': int(row['field_id']),
            'target_ra': row['ra'],
            'target_dec': row['dec'],
            'target_filter_id': filter_id,
            'target_program_id': int(row['program_id']),
            'target_subprogram_name': row['subprogram_name'],
            'target_program_pi': row['program_pi'],
            'target_exposure_time': row['exposure_time'] * u.second,
            'target_sky_brightness': 
                    self.block_sky_brightness.loc[request_id,self.queue_slot][filter_id],
            'target_limiting_mag': 
                    self.block_lim_mags.loc[request_id,self.queue_slot][filter_id],
            'target_metric_value':  
                    self.block_slot_metric.loc[request_id,self.queue_slot][filter_id],
            'target_total_requests_tonight': int(row['total_requests_tonight']),
            'request_id': request_id }

#            'target_sky_brightness': self.queue.ix[idx].sky_brightness,
#            'target_limiting_mag': self.queue.ix[idx].limiting_mag,
#            'target_metric_value':  self.queue.ix[idx].value,
#            'target_request_number_tonight':

        # TEMPORARY workaround to enable multiple observing times in one
        # subprogram
        #if (row['subprogram_name'] == 'ZUDS') and (filter_id == 3):
        #    next_obs['target_exposure_time'] = 90 * u.second

        return next_obs

    def _slot_metric(self, limiting_mag):
        """Calculate metric for assigning fields to slots.

        penalizes volume for both extinction (airmass) and fwhm penalty
        due to atmospheric refraction, plus sky brightness from
        moon phase and distance
        == 1 for 21st mag."""

        metric = 10.**(0.6 * (limiting_mag - 21)) 
        # print("Gurobi metric", metric)
        # lock out -99 limiting mags even more aggressively
        return metric.where(limiting_mag > 0, -0.99)

    def _assign_slots(self, current_state, time_limit = 30*u.second, 
            block_use = defaultdict(float)):
        """Assign requests in the Pool to slots"""

        # check that the pool has fields in it
        if len(self.rp.pool) == 0:
            raise QueueEmptyError("No fields in pool")

        # join with fields so we have the information we need
        # make a copy so rp.pool and self.queue are not linked
        df = self.rp.pool.join(self.fields.fields, on='field_id').copy()

        # calculate limiting mag by block.  uses the block midpoint time
        blocks, times = nightly_blocks(current_state['current_time'], 
            time_block_size=TIME_BLOCK_SIZE)

        # remove the excluded blocks, if any.  Could do this in optimize.py
        # but it makes the optimization problem unneccesarily bigger
        # don't demand 100% of the block is used: tiny fractions lead to
        # infeasible models
        exclude_blocks = [b for (b,v) in block_use.items() if v > 0.95]

        self.logger.debug(f'Excluding completely filled blocks {exclude_blocks}')

        if len(exclude_blocks):
            cut_blocks = np.setdiff1d(blocks, exclude_blocks)
            cut_times = block_index_to_time(cut_blocks, 
                    current_state['current_time'], where='mid')
            blocks, times = cut_blocks, cut_times

        lim_mags = {}
        sky_brightnesses = {}
        for bi, ti in zip(blocks, times):
            if 'altitude' in df.columns:
                df.drop('altitude', axis=1, inplace=True)
            if 'azimuth' in df.columns:
                df.drop('azimuth', axis=1, inplace=True)
            # use pre-computed blocks
            df_alt = self.fields.block_alt[bi]
            df_alt.name = 'altitude'
            df = df.join(df_alt, on='field_id')
            df_az = self.fields.block_az[bi]
            df_az.name = 'azimuth'
            df = df.join(df_az, on='field_id')
            for fid in FILTER_IDS:
                df_limmag, df_sky = \
                    self.compute_limiting_mag(df, ti, filter_id = fid)
                lim_mags[(bi, fid)] = df_limmag
                sky_brightnesses[(bi, fid)] = df_sky

        # this results in a MultiIndex on the *columns*: level 0 is block,
        # level 1 is filter_id.  df_metric.unstack() flattens it
        self.block_lim_mags = pd.DataFrame(lim_mags)
        self.block_sky_brightness = pd.DataFrame(sky_brightnesses)
        self.block_slot_metric = self._slot_metric(self.block_lim_mags)

        # count the number of observations requested by filter
        df['n_reqs_tot'] = 0
        for fid in FILTER_IDS:
            df['n_reqs_{}'.format(fid)] = \
                df.filter_ids.apply(lambda x: np.sum([xi == fid for xi in x]))
            df['n_reqs_tot'] += df['n_reqs_{}'.format(fid)] 

        # prepare the data for input to gurobi
        #import shelve
        #s = shelve.open('tmp_vars.shelf')
        #s['block_lim_mags'] = self.block_lim_mags
        #s['block_slot_metric'] = self.block_slot_metric
        #s['df'] = df
        #s.close()

        # select request_sets for the night
#        self.request_sets_tonight, dft = request_set_optimize(
#            self.block_slot_metric, df, self.requests_allowed,
#            time_limit = time_limit)
#
#        if len(self.request_sets_tonight) == 0:
#           raise QueueEmptyError("No request sets selected!")
#
#        # optimize assignment into slots
#        df_slots = slot_optimize(
#            self.block_slot_metric.loc[self.request_sets_tonight], 
#            df.loc[self.request_sets_tonight], self.requests_allowed,
#            time_limit = time_limit)

        self.request_sets_tonight, df_slots, dft = night_optimize(
            self.block_slot_metric, df, self.requests_allowed,
            time_limit = time_limit, block_use = block_use)

        grp = df_slots.groupby('slot')
        print('grp', grp.head())
        
        # W 
        self.queued_requests_by_slot = grp.apply(np.array)
        self.filter_by_slot = \
            grp['metric_filter_id'].apply(lambda x: np.unique(x)[0])
            
        print('queued', self.queued_requests_by_slot)
        print('old', grp['request_id'].apply(list))

        # self.queued_requests_by_slot = grp['request_id'].apply(list)
        # self.filter_by_slot = \
        #    grp['metric_filter_id'].apply(lambda x: np.unique(x)[0])

        # rework to dump output
        df_slots['scheduled'] = True
        dft.set_index(['request_id','slot','metric_filter_id'],inplace=True)
        df_slots.set_index(['request_id','slot','metric_filter_id'],inplace=True)
        dft = dft.join(df_slots,how='outer')
        dft['scheduled'] = dft['scheduled'].fillna(False)
        dft.reset_index(inplace=True)

        dft = pd.merge(dft,df[['field_id']],
            left_on='request_id', right_index=True)

        n_requests_scheduled = np.sum(dft['scheduled'])
        total_metric_value = np.sum(dft['scheduled']*dft['metric'])
        avg_metric_value = total_metric_value / n_requests_scheduled

        tot_avail_requests_bysubprogram = \
                df.groupby(['program_id','subprogram_name'])['n_reqs_tot'].agg(np.sum)
        tot_avail_requests_bysubprogram.name = 'available'

        # use self.requests_allowed and join this all up

        nscheduled_requests_bysubprogram = \
                dft.loc[dft['scheduled'],['program_id','subprogram_name']].groupby(['program_id','subprogram_name']).agg(len)
        nscheduled_requests_bysubprogram.name = 'scheduled'

        # reformat requests_allowed for joining
        mux = pd.MultiIndex.from_tuples(self.requests_allowed.keys(),
                names = ['program_id','subprogram_name'])
        df_allowed = pd.DataFrame(list(self.requests_allowed.values()),
                index=mux,columns=['allowed'])

        df_summary = df_allowed.join(tot_avail_requests_bysubprogram).join(nscheduled_requests_bysubprogram)
        self.logger.info(df_summary)

        self.logger.info(f'{n_requests_scheduled} requests scheduled')
        self.logger.info(f'{total_metric_value:.2f} total metric value; ' 
               f'{avg_metric_value:.2f} average per request')

        # this is not ideal for 
        tnow = current_state['current_time']
        yymmdd = tnow.iso.split()[0][2:].replace('-','')
        solution_outfile = f'{BASE_DIR}/../sims/gurobi_solution_{yymmdd}.csv'

        before_noon_utc = (tnow.mjd - np.floor(tnow.mjd)) < 0.5
        
        # avoid clobbering the solution file with restarts after observing has
        # completed
        # if before_noon_utc or (not os.path.exists(solution_outfile)):
            # dft.drop(columns=['Yrtf']).to_csv(solution_outfile)

    def _sequence_requests_in_block(self, current_state, time_limit = 30.*u.second):
        """Solve the TSP for requests in this slot"""

        self.queue_slot = block_index(current_state['current_time'])[0]

        # raise an error if there are missing blocks--potentially due to
        # excluded blocks
        if self.queue_slot not in self.queued_requests_by_slot.index:
            raise QueueEmptyError(f"Current block {self.queue_slot} is not stored")

        # retrieve requests to be observed in this block
        req_list = self.queued_requests_by_slot.loc[self.queue_slot]
        # W
        req_df = pd.DataFrame(req_list, columns=['slot', 'filter_id', 'field_id'])
        
        # request_set ids should be unique per block
        # assert( (len(set(req_list)) == len(req_list) ) )

        if np.all(np.isnan(req_df['filter_id'].tolist())):
            raise QueueEmptyError("No requests assigned to this block")

        # W
        idx = req_df['field_id'].tolist()
        filter_list = req_df['filter_id'].tolist()
        
        # reconstruct
        df = self.rp.pool.loc[idx].join(self.fields.fields, on='field_id').copy()
        az = self.fields.block_az[self.queue_slot]
        df = df.join(az, on='field_id')
        # W
        df.index.name = 'req_id'
        df.reset_index(inplace=True)
        df = df.join(req_df, rsuffix='_req_id')

        # now prepend the CALSTOW positoin so we can minimize slew from
        # filter exchanges 
        # Need to use current HA=0
        # print("START", HA_to_RA(0, current_state['current_time']).to(u.degree).value)
        df_blockstart = pd.DataFrame({'ra':HA_to_RA(0,
            current_state['current_time']).to(u.degree).value,
            'dec':-48.,'azimuth':180.},index=[0])
        df_fakestart = pd.concat([df_blockstart,df],sort=True)

        # compute overhead time between all request pairs
        
        # compute pairwise slew times by axis for all pointings
        slews_by_axis = {}
        def coord_to_slewtime(coord, axis=None):
            c1, c2 = np.meshgrid(coord, coord)
            dangle = np.abs(c1 - c2)
            angle = np.where(dangle < (360. - dangle), dangle, 360. - dangle)
            return slew_time(axis, angle * u.deg)
        
        # compute pairwise filter exchange times
        filter_overheads = {}
        def filter_exchange(fid):
            test_list = list(fid)
            time_arr = []
            for i in test_list:
                new_arr = []
                for j in test_list:
                    if i == j:
                        new_arr.append(0)
                    else:
                        new_arr.append(FILTER_CHANGE_TIME.value)
                time_arr.append(new_arr)   
            return time_arr

        slews_by_axis['dome'] = coord_to_slewtime(
            df_fakestart['azimuth'], axis='dome')
        slews_by_axis['dec'] = coord_to_slewtime(
            df_fakestart['dec'], axis='dec')
        slews_by_axis['ra'] = coord_to_slewtime( 
            df_fakestart['ra'], axis='ha')
         # W
        filter_overhead = filter_exchange(df_fakestart['filter_id'])*u.s

        maxradec = np.maximum(slews_by_axis['ra'], slews_by_axis['dec'])
        maxslews = np.maximum(slews_by_axis['dome'], maxradec)
        # impose a penalty on zero-length slews (which by construction
        # in this mode are from different programs)
        wnoslew = maxslews == 0
        maxslews[wnoslew] = READOUT_TIME * 10.
        # W, for WINTER, readout time is zero
        # maxslews[wnoslew] = 10. * u.second
        # W
        slew_overhead = np.maximum(maxslews, READOUT_TIME)
        overhead_time = slew_overhead + filter_overhead
        
        tsp_order, tsp_overhead_time = tsp_optimize(overhead_time.value,
                                                    time_limit = time_limit)

        # remove the fake starting point.  tsp_optimize always starts with
        # the first observation in df, which by construction is our fake point,
        # so we can simply cut it off.
        tsp_order = tsp_order[1:]
        assert(0 not in tsp_order)

        # tsp_order is 0-indexed from overhead time, so I need to
        # reconstruct the request_id
        self.queue_order = df_fakestart.index.values[tsp_order]
         # W
        self.req_queue_order = df_fakestart.req_id.values[tsp_order]
        self.queue = df

    def _remove_requests(self, request_set_id):
        """Remove a request from both the queue and the pool.
        
        Note that gurobi queue uses request_set_id to index."""

        # should be the topmost item
        assert (self.req_queue_order[0] == request_set_id)
        # W, reindexing 
        row = self.queue.loc[self.queue_order[0]]
        row_filter = row['filter_id']
        self.queue = self.queue.drop(self.queue_order[0])
        self.queue_order = self.queue_order[1:]
        self.req_queue_order = self.req_queue_order[1:]

        # row = self.queue.loc[request_set_id]
        # self.queue = self.queue.drop(request_set_id)
        # (past slot assignments are still in self.queued_requests_by_slot)
        # (we will only reuse the RequestPool if we do recomputes)
        self.rp.remove_request(request_set_id, 
                row_filter)

    def _return_queue(self):

        # start by setting up the current slot
        if len(self.queue) > 0:
            queue = self.queue.loc[self.queue_order].copy()
            queue.loc[:,'ordered'] = True
            queue.loc[:,'slot_start_time'] = block_index_to_time(
                    self.queue_slot, Time.now(), where='start').iso
        else:
            # before the night starts, the queue is empty
            queue = self.queue.copy()

        # now loop over upcoming slots, ensuring they are sorted (should be)
        slots = self.queued_requests_by_slot.index.values
        slots = np.sort(slots)

        for slot in slots:
            if (self.queue_slot is not None):
                if slot <= self.queue_slot:
                    continue
            slot_requests = self.queued_requests_by_slot.loc[slot]
 
            idx = pd.Index(slot_requests)
            # reconstruct
            df = self.rp.pool.loc[idx].join(self.fields.fields, on='field_id').copy()
            df.loc[:,'filter_id'] = self.filter_by_slot[slot]
            df.loc[:,'ordered'] = False
            df.loc[:,'slot_start_time'] = block_index_to_time(slot,
                    Time.now(), where='start').iso
            queue = queue.append(df)
        

        return queue


class GreedyQueueManager(QueueManager):

    def __init__(self, queue_name, queue_configuration, **kwargs):
        super().__init__(queue_name, queue_configuration, **kwargs)
        self.time_of_last_filter_change = None
        self.min_time_before_filter_change = TIME_BLOCK_SIZE
        self.queue_type = 'greedy'

    def _assign_nightly_requests(self, current_state,
            time_limit = 30.*u.second, block_use = defaultdict(float)):
        # initialize the time of last filter change
        if self.time_of_last_filter_change is None:
            self.time_of_last_filter_change = current_state['current_time']

    def _next_obs(self, current_state, obs_log, time_limit = 30.*u.second):
        """Select the highest value request."""

        # since this is a greedy queue, we update the queue after each obs
        # for speed, only do the whole recalculation if we're in a new slot
#        if ((block_index(current_state['current_time'])[0] != self.queue_slot)
#                or (len(self.queue) == 0)):
#            self._update_queue(current_state)
#        else:
#            # otherwise just recalculate the overhead times
#            _ = self._update_overhead(current_state)

        # to get the "on the fly" cadence windows to work I have to 
        # run the whole queue every time right now...
        self._update_queue(current_state, obs_log)

        # in case this wasn't initialized by assign_nightly_requests
        if self.time_of_last_filter_change is None:
            self.time_of_last_filter_change = current_state['current_time']

        # check if filter changes are allowed yet
        if ((current_state['current_time'] - self.time_of_last_filter_change)
                < self.min_time_before_filter_change):
            # only consider observations in the current filter
            queue = self.queue[self.queue['filter_id'] == current_state['current_filter_id']]
            # unless there are no more observations, in which case allow a
            # change
            if len(queue) == 0:
                queue = self.queue
        else:
            # allow filter changes if desired
            queue = self.queue

        # request_id of the highest value request
        # print(np.max(queue.value))
        max_idx = queue.value.idxmax()
        row = queue.loc[max_idx]
 

        next_obs = {'target_field_id': row['field_id'],
            'target_ra': row['ra'],
            'target_dec': row['dec'],
            'target_filter_id': row['filter_id'],
            'target_program_id': row['program_id'],
            'target_subprogram_name': row['subprogram_name'],
            'target_program_pi': row['program_pi'],
            'target_exposure_time': row['exposure_time'] * u.second,
            'target_sky_brightness': row['sky_brightness'],
            'target_limiting_mag': row['limiting_mag'],
            'target_metric_value':  row['value'],
            'target_total_requests_tonight': row['total_requests_tonight'],
            'request_id': max_idx,
            'target_alt': row['altitude'],
            'target_az': row['azimuth']      }

        return next_obs

    def _metric(self, df):
        """Calculate metric for prioritizing fields.

        Penalizes volume for both extinction (airmass) and fwhm penalty
        due to atmospheric refraction, plus sky brightness from
        moon phase and distance, overhead time
        == 1 for 21st mag, 15 sec overhead."""
        
#        return 10.**(0.6 * (df['limiting_mag'] - 21)) / \
#            ((EXPOSURE_TIME.value + df['overhead_time']) /
#             (EXPOSURE_TIME.value + 15.))

        # W
        return 10.**(0.6 * (df['limiting_mag'] - 21)) / \
            ((EXPOSURE_TIME.value + df['overhead_time']) /
             (EXPOSURE_TIME.value + 15.))
        
        


    def _update_overhead(self, current_state, df=None):
        """recalculate overhead values without regenerating whole queue"""

        inplace = df is None

        if inplace:
            # no dataframe supplied, so replace existing self.queue on exit
            df = self.queue
            df.drop(['overhead_time', 'altitude', 'azimuth'], axis=1,
                    inplace=True)

        # compute readout/slew overhead times, plus current alt/az
        df_overhead, df_altaz = self.fields.overhead_time(current_state)

        # nb: df has index request_id, not field_id
        df = pd.merge(df, df_overhead, left_on='field_id', right_index=True)
        df = pd.merge(df, df_altaz, left_on='field_id', right_index=True)
        df.rename(columns={'alt': 'altitude', 'az': 'azimuth'}, inplace=True)

        # add overhead for filter changes
        w = df['filter_id'] != current_state['current_filter_id']
        if np.sum(w):
            df.loc[w, 'overhead_time'] += FILTER_CHANGE_TIME.to(u.second).value

        if inplace:
            df.loc[:, 'value'] = self._metric(df)
            self.queue = df

        return df

    def _update_queue(self, current_state, obs_log):
        """Calculate greedy weighting of requests in the Pool using current
        telescope state only"""

        # store block index for which these values were calculated
        self.queue_slot = block_index(current_state['current_time'])[0]

        # check that the pool has fields in it
        if len(self.rp.pool) == 0:
            raise QueueEmptyError("No fields in pool")

        # join with fields so we have the information we need
        # make a copy so rp.pool and self.queue are not linked
        df_rs = self.rp.pool.join(self.fields.fields, on='field_id').copy()

        # now expand the dataframe of request sets to a dataframe with one
        # row per obs.  
        requests = []   
        for request_set_id, row in df_rs.iterrows():
            rdict = row.to_dict()
            filter_ids = rdict.pop('filter_ids')
            for filter_id in filter_ids:
                ri = rdict.copy()
                ri['filter_id'] = filter_id
                ri['request_set_id'] = request_set_id
                requests.append(ri)
        df = pd.DataFrame(requests)
            
        df = self._update_overhead(current_state, df=df)

        # start with conservative altitude cut;
        # airmass weighting applied naturally below
        # also make a copy because otherwise it retains knowledge of
        # (discarded) previous reference and raises SettingWithCopyWarnings
        df = df.loc[df['altitude'] > 20, :].copy()

        if len(df) == 0:
            raise QueueEmptyError("No fields in queue above altitude cut")

        # if restricting to one program per block, drop other programs
        if self.block_programs:
            current_block_program = PROGRAM_BLOCK_SEQUENCE[
                self.queue_slot % LEN_BLOCK_SEQUENCE]
            df = df.loc[df['program_id'] == current_block_program, :]

        cadence_cuts = enough_gap_since_last_obs(df,
            current_state,obs_log)

        self.requests_in_window = np.sum(cadence_cuts) > 0
        if ~self.requests_in_window:
            self.logging.warning(calc_queue_stats(df, current_state,
                intro="No fields with observable cadence windows.  Queue in progress:"))
            raise QueueEmptyError("No fields with observable cadence windows")
        # also make a copy because otherwise it retains knowledge of
        # (discarded) previous reference and raises SettingWithCopyWarnings
        df = df.loc[cadence_cuts, :].copy()

        # compute airmasses by field_id
        # airmass = zenith_angle_to_airmass(90. - df_alt)
        # airmass.name = 'airmass'
        # df = pd.merge(df, pd.DataFrame(airmass),
        #              left_on='field_id', right_index=True)
        # airmass cut (or add airmass weighting to value below)
        # df = df[(df['airmass'] <= MAX_AIRMASS) & (df['airmass'] > 0)]

        df_limmag, df_sky = self.compute_limiting_mag(df,
                current_state['current_time'])
        df.loc[:, 'limiting_mag'] = df_limmag
        df.loc[:, 'sky_brightness'] = df_sky

        #df_limmag.name = 'limiting_mag'
        #df = pd.merge(df, df_limmag, left_on='field_id', right_index=True)

        df.loc[:, 'value'] = self._metric(df)

        self.queue = df

    def _remove_requests(self, request_id):
        """Remove a request from both the queue and the request pool"""

        row = self.queue.loc[request_id]

        self.queue = self.queue.drop(request_id)
        self.rp.remove_request(row['request_set_id'], row['filter_id'])

    def _return_queue(self):

        if 'value' in self.queue.columns:
            queue = self.queue.sort_values('value',ascending=False).copy()
        else:
            queue = self.queue.copy()

        # we have put these in value order but the sequence can change
        queue['ordered'] = False
        return queue



class ListQueueManager(QueueManager):
    """Simple Queue that returns observations in order."""

    def __init__(self, queue_name, queue_configuration, fields=None, **kwargs):
        self.queue_type = 'list'

        # queue name (useful in Scheduler object when swapping queues)
        self.queue_name = queue_name

        if fields is None:
            self.fields = Fields()
        else:
            self.fields = fields

        # the queue itself
        self.load_list_queue(queue_configuration.config['targets'])

        if 'validity_window_mjd' in queue_configuration.config:
            window = queue_configuration.config['validity_window_mjd']
            if window is not None:
                assert(len(window) == 2)
                assert(window[1] > window[0])
                self.validity_window = [Time(window[0],format='mjd'),
                    Time(window[1],format='mjd')]
            else:
                self.validity_window = None
        else:
            self.validity_window = None
            
        self.is_TOO = queue_configuration.config['targets'][0]['subprogram_name'].startswith('ToO')

    def _assign_nightly_requests(self, current_state,
            **kwargs):
        pass

    def _update_queue(self, current_state, obs_log):
        pass

    def load_list_queue(self, queue_dict_list, append=False):
        """Initialize an ordered queue.

        queue_dict_list is a list of dicts, one per observation"""
        
        df = pd.DataFrame(queue_dict_list)

        # check that major columns are included
        required_columns = ['field_id','program_id', 'subprogram_name',
                'filter_id', 'program_pi']

        for col in required_columns:
            if col not in df.columns:
                raise ValueError(f'Missing required column {col}')


        # by default use field ids alone to specify pointings, 
        # but allow manual ra/dec if needed
        if ('ra' not in df.columns) and ('dec' not in df.columns):
            queue = df.join(self.fields.fields, on='field_id', how='inner').sort_index().copy()
        else:
            queue = df

        # if some of the field ids are bad, there will be missing rows
        if len(queue) != len(df):
            raise ValueError('One or more field ids are malformed: {}'.format(
                df.index.difference(self.fields.fields.index)))

        # add standard keywords if not present
        if 'exposure_time' not in queue.columns:
            queue['exposure_time'] = EXPOSURE_TIME.to(u.second).value
        if 'max_airmass' not in queue.columns:
            queue['max_airmass'] = MAX_AIRMASS
        if 'n_repeats' not in queue.columns:
            queue['n_repeats'] = 1

        if append:
            self.queue = self.queue.append(queue, ignore_index=True)
        else:
            self.queue = queue

    def _next_obs(self, current_state, obs_log, time_limit = 30.*u.second):
        """Return the next observation in the time ordered queue unless it has expired."""

        
        if len(self.queue) == 0:
            raise QueueEmptyError("No more observations in queue!")
        
        # take the next observation in line
        idx = 0

        while True:
            if idx == len(self.queue):
                raise QueueEmptyError("No valid observations in queue!")
            ra = self.queue.iloc[idx].ra
            ha = RA_to_HA(ra * u.degree, current_state['current_time']
                    ).to(u.degree).wrap_at(180.*u.degree).value
            dec = self.queue.iloc[idx].dec
            sc = coord.SkyCoord(ra,dec, unit=u.deg)
            airmass = altitude_to_airmass(
                    skycoord_to_altaz(sc, 
                        current_state['current_time']).alt.to(u.deg).value)
            if airmass >= self.queue.iloc[idx].max_airmass:
                idx += 1
                continue
            # Reed limits |HA| to < 5.95 hours (most relevant for circumpolar
            # fields not hit by the airmass cut)
            if np.abs(ha) >= (5.95 * u.hourangle).to(u.degree).value:
                idx += 1
                continue
            # 1) HA < -17.6 deg && Dec < -22 deg is rejected for both track & stow because of interference with FFI.
            if (ha <= -17.6) & (dec <= -22):
                idx += 1
                continue
             # West of HA -17.6 deg, Dec < -45 deg is rejected for tracking because of the service platform in the south.
            if (ha >= -17.6) & (dec <= -45):
                idx += 1
                continue
             # fabs(HA) > 3 deg is rejected for Dec < -46 to protect the shutter "ears".
            if (np.abs(ha) >= 3.) & (dec <= -46):
                idx += 1
                continue
             # dec > 87.5 is rejected
            if (dec > 87.5):
                idx += 1
                continue

            break

        
        next_obs = {'target_field_id': int(self.queue.iloc[idx].field_id),
            'target_ra': self.queue.iloc[idx].ra,
            'target_dec': self.queue.iloc[idx].dec,
            'target_filter_id': self.queue.iloc[idx].filter_id,
            'target_program_id': int(self.queue.iloc[idx].program_id),
            'target_subprogram_name': self.queue.iloc[idx].subprogram_name,
            'target_program_pi': self.queue.iloc[idx].program_pi,
            'target_exposure_time': self.queue.iloc[idx].exposure_time * u.second,
            'target_sky_brightness': 0.,
            'target_limiting_mag': 0.,
            'target_metric_value':  0.,
            'target_total_requests_tonight': 1,  
            'request_id': self.queue.index[idx]}

        return next_obs

    def _remove_requests(self, request_id):
        """Remove a request from the queue"""

        try:
            if self.queue.loc[request_id,'n_repeats'] > 1:
                self.queue.loc[request_id,'n_repeats'] -= 1
            else:    
                self.queue = self.queue.drop(request_id)
        except Exception:
            self.logger.exception(f'Failure removing request {request_id}')

    def _return_queue(self):

        # by construction the list queue is already in order
        queue = self.queue.copy()
        queue['ordered'] = True
        return queue

class RequestPool(object):

    def __init__(self):
        # initialize empty dataframe to add to
        self.pool = pd.DataFrame()
        pass

    def add_request_sets(self, program_id, subprogram_name, program_pi,
                field_ids, filter_ids, intranight_gap, exposure_time, 
                total_requests_tonight, priority=1):
        """program_ids must be scalar"""

        assert (scalar_len(program_id) == 1) 
        assert (scalar_len(subprogram_name) == 1) 

        n_fields = scalar_len(field_ids)
        if n_fields == 1:
            # see if it's iterable or not
            try:
                iterator = iter(field_ids)
            except TypeError:
                # if not, assume it's a scalar and wrap in a list
                field_ids = [field_ids]

        # build df as a list of dicts
        request_sets = []
        for i, field_id in enumerate(field_ids):
            request_sets.append({
                'program_id': program_id,
                'subprogram_name': subprogram_name,
                'program_pi': program_pi,
                'field_id': field_id,
                'filter_ids': filter_ids.copy(),
                # pandas doesn't play well with astropy quantities, so change
                # back to seconds
                'intranight_gap_min': intranight_gap.to(u.minute).value,
                'exposure_time': exposure_time.to(u.second).value,
                'total_requests_tonight': total_requests_tonight,
                'priority': priority})

        self.pool = self.pool.append(pd.DataFrame(request_sets), 
            ignore_index=True)

    def n_request_sets(self):
        return len(self.pool)

    def remove_request_sets(self, request_set_ids):
        """Remove completed or otherwise unwanted requests by request_id

        request_ids : scalar or list
            requests to drop (index of self.pool)"""
        self.pool = self.pool.drop(request_set_ids)

    def remove_request(self, request_set_id, filter_id):
        """Remove single completed request from a request set. 

        request_set_id: scalar 
            request set to modify (index of self.pool)
        filter_id: scalar
            filter_id of completed observation"""

        rs = self.pool.loc[request_set_id].copy()
        filters = rs['filter_ids']
        # this is another step that shouldn't be necessary...
        filters.remove(filter_id)
        if len(filters) == 0:
            self.remove_request_sets(request_set_id)
        else:
            self.pool.at[request_set_id, 'filter_ids'] =  filters

    def clear_all_request_sets(self):
        self.pool = pd.DataFrame()


# utils for examining inputs

def calc_pool_stats(df, intro=""):
    """

    df = Q.rp.pool"""

    stats_str = intro + "\n"
    stats_str += "\t{} request sets\n".format(len(df))
    stats_str += "\t{} unique fields\n".format(len(set(df.field_id)))
    for prog_id in PROGRAM_IDS:
        w = df.program_id == prog_id
        stats_str += "\tProgram {}:\n".format(prog_id)
        stats_str += "\t\t{} request sets\n".format(np.sum(w))
        stats_str += "\t\t{} unique fields\n".format(
            len(set(df.loc[w, 'field_id'])))
        stats_str += "\t\t{} median requests tonight per field\n".format(
            np.median(df.loc[w, 'total_requests_tonight']))

    return stats_str


def calc_queue_stats(df, current_state, intro=""):
    """

    df = Q.queue"""

    stats_str = intro + "\n"
    stats_str += "\t{} queued requests\n".format(len(df))
    stats_str += "\t{} unique fields\n".format(len(set(df.field_id)))
    for prog_id in PROGRAM_IDS:
        w = df.program_id == prog_id
        stats_str += "\tProgram {}:\n".format(prog_id)

        if np.sum(w) == 0:
            stats_str += "\t\tNo queued requests!\n"
            continue

        stats_str += "\t\t{} requests\n".format(np.sum(w))
        stats_str += "\t\t{} unique fields\n".format(
            len(set(df.loc[w, 'field_id'])))
        walt = w & (df.loc[w, 'altitude'] > 20)
        stats_str += "\t\t{} fields above altitude cut\n".format(
            np.sum(walt))
#        wfirst = walt & (df.loc[walt, 'request_number_tonight'] == 1)
#        stats_str += "\t\t{} requests awaiting first obs tonight\n".format(
#            np.sum(wfirst))

    return stats_str
