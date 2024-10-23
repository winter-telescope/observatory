"""Code for logging observations to a sqlite database."""

import os.path
from collections import defaultdict
import uuid
import numpy as np
import pandas as pd
import sqlalchemy as db
from sqlalchemy import create_engine
import astropy.coordinates as coord
import pathlib
from astropy.time import Time
from datetime import datetime
import astropy.units as u
import astroplan.moon
import psycopg
import os
import yaml
from .Fields import Fields
from .utils import *
from .constants import VALIDITY_WINDOW_MJD, DITHER, BASE_DIR, FILTER_ID_TO_NAME, EXPOSURE_TIME, READOUT_TIME
from .constants import WINTER_FILTERS
from .configuration import SchedulerConfiguration, QueueConfiguration

wsp_path  = os.path.join(os.getenv("HOME"), 'WINTER_GIT', 'observatory', 'wsp')

auth_config_file  = wsp_path + '/credentials/authentication.yaml'
auth_config  = yaml.load(open(auth_config_file) , Loader = yaml.FullLoader)

class ObsLogger(object):

    def __init__(self, log_name, survey_start_time = Time('2018-01-01'),
            output_path = BASE_DIR+'../sims/',
            clobber = False):
        self.log_name = log_name
        self.survey_start_time = survey_start_time
        self.prev_obs = None
        self.mjd_tonight = None
        self.moon_illumination_tonight = None
        
        # W
        now = datetime.now()
        now_str = now.strftime('%Y%m%d') # give the name a more readable date format
        
        file_dir = output_path + 'schedules'
        file_path = file_dir + '/nightly_' + now_str + '.db'
        file_link_path = output_path + 'nightly_schedule.lnk'
        
        # create the data directory if it doesn't exist already
        pathlib.Path(file_dir).mkdir(parents = True, exist_ok = True)
        
        self.engine = create_engine('sqlite:///'+os.path.join(file_path))

        self.conn = self.engine.connect()
        #self.create_fields_table(clobber=clobber)
        self.create_pointing_log(clobber=clobber)
        
        # W
        #history_path = '../../wsp/demoRelational.db'
        #self.historyengine = create_engine('sqlite:///'+os.path.join(history_path))
        #self.ihistoryengine = create_engine('sqlite:///'+output_path,f'WINTER_ObsLog.db')
        #print("HISTORY FILE: {}".format(output_path))
        #self.historyengine = create_engine('sqlite:///'+output_path+f'WINTER_ObsLog.db') #NPL did this change on 2-16-21
        #self.history = pd.read_sql('Observation', self.historyengine)
        
        try:
            # Get history from Caltech database 
            conn = psycopg.connect('dbname=winter user='+str(auth_config['drp']['USERNAME'])+' password='+str(auth_config['drp']['PASSWORD'])+
                           ' host='+str(auth_config['drp']['HOSTNAME']))

            cur = conn.cursor()

            command = '''SELECT exposures.progname, exposures.fieldid, exposures.ra, exposures.dec,
                    exposures.fid, exposures."expmjd", exposures."exptime",exposures.airmass,
                    programs.progid, programs.progname, programs.progtitle FROM exposures INNER JOIN programs ON
                    programs.progname=exposures.progname; '''

            cur.execute(command)

            res = cur.fetchall()
    
            self.history = pd.DataFrame(res, columns=['puid', 'fieldid', 'ra', 'dec', 'fid', 'expMJD',
                                        'ExpTime', 'airmass', 'progid', 'progname', 'progtitle'])
        except Exception as e:
            print("Failed to grab history because of:", e)
            self.history = pd.DataFrame( columns=['puid', 'fieldid', 'ra', 'dec', 'fid', 'expMJD',
                                        'ExpTime', 'airmass', 'progid', 'progname', 'progtitle'])
        print("History:", self.history)
        # rename progID to propID for scheduler
        if 'progid' in self.history.columns:
            self.history.rename(columns = {'progid':'propID'}, inplace = True)
        # rename progName to subprogram 
        if 'progname' in self.history.columns:
            self.history.rename(columns = {'progname':'subprogram'}, inplace = True)
        # rename ra and dec keywords from history as needed
        if 'ra' in self.history.columns:
            self.history.rename(columns = {'ra':'fieldRA'}, inplace = True)
        if 'dec' in self.history.columns:
            self.history.rename(columns = {'dec':'fieldDec'}, inplace = True)
        # rename other keywords
        if 'fieldid' in self.history.columns:
            self.history.rename(columns = {'fieldid':'fieldID'}, inplace = True)
        if 'fid' in self.history.columns:
            self.history.rename(columns = {'fid':'filter'}, inplace = True)
            self.history['filter'] = self.history['filter'].map(FILTER_ID_TO_NAME)
        if 'ExpTime' in self.history.columns:
            self.history.rename(columns = {'ExpTime':'visitExpTime'}, inplace = True)
    
            
        
        self.log_tonight = pd.read_sql('Summary', self.engine)
        
        # make a symbolic link (symlink) to the file
        print(f'trying to create link at {file_link_path} to {file_path}')

        try:
            os.symlink(file_path, file_link_path)
        except FileExistsError:
            print('deleting existing symbolic link')
            os.remove(file_link_path)
            os.symlink(file_path, file_link_path)

    def create_fields_table(self, clobber=True):

        if clobber:
            # Drop table if it exists
            try:
                self.conn.execute("""DROP TABLE Field""")
            except:
                pass

        # If the table doesn't exist, create it
        insp = db.inspect(self.engine)
        table_exists = insp.has_table('Field')
        if not table_exists:
        #if not self.engine.dialect.has_table(self.engine, 'Field'): 

            self.conn.execute("""
            CREATE TABLE Field(
            fieldID   INTEGER PRIMARY KEY,
            fieldFov  REAL,
            fieldRA   REAL,
            fieldDec  REAL,
            fieldGL   REAL,
            fieldGB   REAL,
            fieldEL   REAL,
            fieldEB   REAL
            )""")

            f = Fields()
            df = f.fields.reset_index()
            df.rename(columns={'field_id': 'fieldID',
                               'ra': 'fieldRA',
                               'dec': 'fieldDec',
                               'l': 'fieldGL',
                               'b': 'fieldGB',
                               'ecliptic_lon': 'fieldEL',
                               'ecliptic_lat': 'fieldEB'}, inplace=True)
            df.set_index(['fieldID'], inplace=True)
            df['fieldFov'] = 0.00 # ignore for now 

            df_min = df[['fieldFov','fieldRA', 'fieldDec', 'fieldGL', 'fieldGB',
                'fieldEL', 'fieldEB']]

            # (circumscribed) field diameter in degrees
            df_min.to_sql('Field', self.engine, if_exists='replace')

    def create_pointing_log(self, clobber=True):
        
        if clobber:
            # Drop table if it exists
            try:
                self.conn.execute("""DROP TABLE Summary""")
            except:
                pass

        # If the table doesn't exist, create it
        insp = db.inspect(self.engine)
        table_exists = insp.has_table('Summary')
        if not table_exists:
        #if not self.engine.dialect.has_table(self.engine, 'Summary'): 
            
            # create table
            self.conn.execute("""
            CREATE TABLE Summary(
            obsHistID          INTEGER PRIMARY KEY,
            requestID          INTEGER,
            progID             INTEGER,
            progName           TEXT,
            progTitle          TEXT,
            fieldID            INTEGER,
            raDeg              REAL,
            decDeg             REAL,
            filter             TEXT,
            expDate            INTEGER,
            expMJD             REAL,
            validStart         REAL,
            validStop          REAL, 
            ditherNumber       INTEGER,
            bestDetector       INTEGER,
            night              INTEGER,
            visitTime          REAL,
            visitExpTime       REAL,
            FWHMgeom           REAL,
            FWHMeff            REAL,
            airmass            REAL,
            filtSkyBright      REAL,
            lst                REAL,
            altitude           REAL,
            azimuth            REAL,
            dist2Moon          REAL,
            solarElong         REAL,
            moonRA             REAL,
            moonDec            REAL,
            moonAlt            REAL,
            moonAZ             REAL,
            moonPhase          REAL,
            sunAlt             REAL,
            sunAz              REAL,
            slewDist           REAL,
            slewTime           REAL,
            fiveSigmaDepth     REAL,
            totalRequestsTonight INTEGER,
            metricValue        REAL,
            progPI             TEXT,
            observed           INTEGER
            )""")

    def log_pointing(self, state, request, queues):

        record = {}
        # don't use request_id here, but
        # let sqlite create a unique non-null key
        #record['obsHistID'] = request['request_id']
        # give request id its own column
        record['observed'] = 0 # initialize to 0
        record['requestID'] = request['request_id']
        record['progID'] = request['target_program_id']
        record['progName'] = request['target_subprogram_name'] 
        
        for qname, q in queues.items():
            for program in q.observing_programs:
                if program.subprogram_name == request['target_subprogram_name']:
                    pi = program.program_pi
                    record['progPI'] = program.program_pi
                    record['progTitle'] = program.subprogram_title
                    record['ditherNumber'] = program.dither
                    record['bestDetector'] = program.best_detector
        
        record['fieldID'] = request['target_field_id']
        record['raDeg'] = request['target_ra']
        record['decDeg'] = request['target_dec']
#        record['fieldRA'] = np.radians(request['target_ra'])
#        record['fieldDec'] = np.radians(request['target_dec'])
#        record['altitude'] = np.radians(request['target_alt'])
#        record['azimuth'] = np.radians(request['target_az'])

        record['filter'] = FILTER_ID_TO_NAME[request['target_filter_id']]
        # times are recorded at start of exposure
        exposure_start = state['current_time'] - \
            request['target_exposure_time']
        # see note in utils.py
        exposure_start.delta_ut1_utc = 0.

        record['expDate'] = (exposure_start - self.survey_start_time).sec
        record['expMJD'] = exposure_start.mjd
        record['validStart'] = exposure_start.mjd - (VALIDITY_WINDOW_MJD/2)
        record['validStop'] = exposure_start.mjd + (VALIDITY_WINDOW_MJD/2)
        
        # check default dither  prefernce
        # TODO make this program specific
        # if request['target_filter_id'] in WINTER_FILTERS:
        #     record['dither'] = DITHER[0]
        # else:
        #     record['dither'] = DITHER[1]

        record['night'] = np.floor((exposure_start - self.survey_start_time).jd
                                   ).astype(np.int)
        record['visitTime'] = request[
            'target_exposure_time'].to(u.second).value
        record['visitExpTime'] = request[
            'target_exposure_time'].to(u.second).value

        # compute some values we will need
        sc = coord.SkyCoord(np.radians(record['raDeg']) * u.radian,
                            np.radians(record['decDeg']) * u.radian)
        altaz = skycoord_to_altaz(sc, exposure_start)

        if 'current_zenith_seeing' in state:
            pointing_seeing = seeing_at_pointing(altaz.alt.value)
            record['FWHMgeom'] = pointing_seeing
            record['FWHMeff'] = pointing_seeing

        record['airmass'] = altaz.secz.value
        record['filtSkyBright'] = request['target_sky_brightness']
        # despite the docs, it seems lst is stored as radians
        record['lst'] = np.radians(exposure_start.sidereal_time('apparent').to(
            u.hourangle).value/24.*360.)
        record['altitude'] = altaz.alt.value
        record['azimuth'] = altaz.az.value
        '''
        # W trying to get the simulations to run faster
        # Spending about 5 min per night recording moon and sun position
        # TODO: uncomment for production code
        
        record['dist2Moon'] = 0.
        record['solarElong'] = 0.
        record['moonRA'] = 0.
        record['moonDec'] = 0.
        record['moonAlt'] = 0.
        record['moonAZ'] = 0.
        record['moonPhase'] = 0.
        record['sunAlt'] = 0.
        record['sunAz'] = 0.
        
        ''' 
        sun = coord.get_sun(exposure_start)
        sun_altaz = skycoord_to_altaz(sun, exposure_start)
        moon = coord.get_moon(exposure_start, W_loc)
        moon_altaz = skycoord_to_altaz(moon, exposure_start)

        # WORKING AROUND a bug in sc.separation(moon)!
        moon_sc = coord.SkyCoord(moon.ra,moon.dec)
        record['dist2Moon'] = moon.separation(sc).to(u.radian).value
        record['solarElong'] = sun.separation(sc).to(u.deg).value
        record['moonRA'] = moon.ra.to(u.radian).value
        record['moonDec'] = moon.dec.to(u.radian).value
        record['moonAlt'] = moon_altaz.alt.to(u.radian).value
        record['moonAZ'] = moon_altaz.az.to(u.radian).value

        # store tonight's mjd so that we can avoid recomputing moon
        # illumination, which profiling shows is weirdly expensive
        if np.floor(exposure_start.mjd) != self.mjd_tonight:
            self.moon_illumination_tonight = astroplan.moon.moon_illumination(
                # Don't use P48_loc to avoid astropy bug:
                # https://github.com/astropy/astroplan/pull/213
                # exposure_start, P48_loc) * 100.
                exposure_start) * 100.
            self.mjd_tonight = np.floor(exposure_start.mjd)

        record['moonPhase'] = self.moon_illumination_tonight

        record['sunAlt'] = sun_altaz.alt.to(u.radian).value
        record['sunAz'] = sun_altaz.az.to(u.radian).value
        
        if self.prev_obs is not None:
            sc_prev = coord.SkyCoord(np.radians(self.prev_obs['raDeg']) * u.radian,
                                     np.radians(self.prev_obs['decDeg']) * u.radian)
            record['slewDist'] = sc.separation(sc_prev).to(u.radian).value
            record['slewTime'] = (record['expDate'] -
                                  (self.prev_obs['expDate'] +
                                      self.prev_obs['visitTime']))
        record['fiveSigmaDepth'] = request['target_limiting_mag']

        # ztf_sim specific keywords!
        record['totalRequestsTonight'] = \
            request['target_total_requests_tonight']
        record['metricValue'] = request['target_metric_value']
        

        record_row = pd.DataFrame(record,index=[uuid.uuid1().hex])

        # append to our local history DataFrame
        # note that the index here will change when reloaded from the db
        self.log_tonight = self.log_tonight.append(record_row, sort=False)

        # write to the database
        record_row.to_sql('Summary', self.conn, index=False, if_exists='append')

#        # convert nan to SQL NULL. might be smarter to just replace the
#        # insertion method below with something smarter (pd.to_sql?)
#        for k,v in record.items():
#            try:
#                if np.isnan(v):
#                    record[k] = 'NULL'
#            except TypeError:
#                continue
#
#        # use placeholders to create the INSERT query
#        columns = ', '.join(list(record.keys()))
#        placeholders = '{' + '}, {'.join(list(record.keys())) + '}'
#        query = 'INSERT INTO Summary ({}) VALUES ({})'.format(
#            columns, placeholders)
#        query_filled = query.format(**record)
#        self.conn.execute(query_filled)


        # save record for next obs
        self.prev_obs = record

    def _mjd_filter_history(self, mjd_range):
        """If mjd_range is not `None`, return a dataframe for the provided range"""

        if mjd_range is not None:
            assert mjd_range[0] <= mjd_range[1]
            w = ((self.history['expMJD'] >= mjd_range[0]) & 
                  (self.history['expMJD'] <= mjd_range[1])) 
            hist = self.history[w]
        else:
            hist = self.history

        return hist

    def _equivalent_obs(self, grp):
        """Given a dataframe groupby object, convert to equivalent standard obserations
        Returns a dict with keys determined by the group"""

        total_exposure_time = grp['visitExpTime'].agg(np.sum)
        count_nobs = grp['fieldID'].agg(len) # how many observations in a program

        # add readout overhead (but not slew)
        total_time = total_exposure_time + count_nobs * READOUT_TIME.to(u.second).value
        count_equivalent = np.round(total_time/(EXPOSURE_TIME + READOUT_TIME).to(u.second).value).astype(int).to_dict()

        # make this a defaultdict so we get zero values for new programs
        return defaultdict(int, count_equivalent)


    def count_equivalent_obs_by_program(self, mjd_range = None):
        """Count of number of equivalent standard exposures by program."""
        

        hist = self._mjd_filter_history(mjd_range)

        grp = hist.groupby(['propID'])

        s = pd.Series(self._equivalent_obs(grp))
        s.index.name = 'program_id'
        s.name = 'n_obs'
        s = s.reset_index()
        return s

    def count_equivalent_obs_by_subprogram(self, mjd_range = None):
        """Count of number of equivalent standard exposures by program and subprogram."""

        hist = self._mjd_filter_history(mjd_range)

        grp = hist.groupby(['propID','subprogram'])

        s = pd.Series(self._equivalent_obs(grp))
        s.index.names = ['program_id','subprogram']
        s.name = 'n_obs'
        s = s.reset_index()
        return s

    def count_equivalent_obs_by_program_night(self, mjd_range = None):
        """Count of number of equivalent standard exposures by program, subprogram, and night."""

        hist = self._mjd_filter_history(mjd_range)

        grp = hist.groupby(['propID','night'])

        s = pd.Series(self._equivalent_obs(grp))
        s.index.names = ['program_id','night']
        s.name = 'n_obs'
        s = s.reset_index()
        return s

    def count_total_obs_by_subprogram(self, mjd_range = None):
        """Count of observations by program and subprogram.
        
        Returns a dict with keys (program_id, subprogram_name)"""

        hist = _mjd_filter_history(mjd_range)

        grp = hist.groupby(['propID','subprogram'])

        count = grp['fieldID'].agg(len).to_dict()

        s = pd.Series(defaultdict(int, count))
        s.index.names = ['program_id','night']
        s.name = 'n_obs'
        s = s.reset_index()
        return s

    def select_last_observed_time_by_field(self,
            field_ids = None, filter_ids = None, 
            program_ids = None, subprogram_names = None, 
            mjd_range = None):

        # start with "True" 
        w = self.history['expMJD'] > 0

        if field_ids is not None:
            w &= self.history['fieldID'].apply(lambda x: x in field_ids)

        if filter_ids is not None:
            filter_names = [FILTER_ID_TO_NAME[fi] for fi in filter_ids]
            w &= self.history['filter'].apply(lambda x: 
                    x in filter_names)

        if program_ids is not None:
            w &= self.history['propID'].apply(lambda x: 
                    x in program_ids)

        if subprogram_names is not None:
            w &= self.history['subprogram'].apply(lambda x: 
                    x in subprogram_names)

        if mjd_range is not None:
            assert mjd_range[0] <= mjd_range[1]
            w &= ((self.history['expMJD'] >= mjd_range[0]) & 
                  (self.history['expMJD'] <= mjd_range[1])) 

        # note that this only returns fields that have previously 
        # been observed under these constraints!
        return self.history.loc[
                w,['fieldID','expMJD']].groupby('fieldID').agg(np.max)

    def select_n_obs_by_field(self,
            field_ids = None, filter_ids = None, 
            program_ids = None, subprogram_names = None, 
            mjd_range = None):

        # start with "True" 
        w = self.history['expMJD'] > 0

        if field_ids is not None:
            w &= self.history['fieldID'].apply(lambda x: x in field_ids)

        if filter_ids is not None:
            filter_names = [FILTER_ID_TO_NAME[fi] for fi in filter_ids]
            w &= self.history['filter'].apply(lambda x: 
                    x in filter_names)

        if program_ids is not None:
            w &= self.history['propID'].apply(lambda x: 
                    x in program_ids)

        if subprogram_names is not None:
            w &= self.history['subprogram'].apply(lambda x: 
                    x in subprogram_names)

        if mjd_range is not None:
            assert mjd_range[0] <= mjd_range[1]
            w &= ((self.history['expMJD'] >= mjd_range[0]) & 
                  (self.history['expMJD'] <= mjd_range[1])) 

        # note that this only returns fields that have previously 
        # been observed!   
        grp =  self.history.loc[
                w,['fieldID','expMJD']].groupby('fieldID')
        nobs = grp['expMJD'].agg(len)
        nobs.name = 'n_obs'

        return nobs

    def return_obs_history(self, time):
        """Return one night's observation history"""

        mjd_range = [np.floor(time.mjd), np.floor(time.mjd)+1.]
        w = ((self.history['expMJD'] >= mjd_range[0]) & 
                  (self.history['expMJD'] <= mjd_range[1])) 
        return self.history.loc[w, 
                ['propID', 'fieldID',
                    'fieldRA', 'fieldDec', 'filter', 'expMJD', 'visitExpTime',
                    'airmass', 'subprogram']]

