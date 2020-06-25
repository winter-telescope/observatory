"""
Code for logging observations to a sqlite database
"""

import sqlalchemy as db
import uuid
from astropy.time import Time
import os
import sys
import pandas as pd
import logging


class ObsWriter():
    """
    Heavily inspired by obsLogger.py in winter_sim and by code in the schedule.py file in WSP
    """

    def __init__(self, log_name, output_path, survey_start_time = Time('2018-01-01'), clobber = False):
        """
        Initialize an observation logger by opening a database connection for the night.
        Creates an empty table to write observations to.
        """

        #set up logging
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        fh = logging.FileHandler('pseudoLog.log', mode='a')
        format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        fh.setFormatter(format)
        self.logger.addHandler(fh)

        self.log_name = log_name
        self.survey_start_time = survey_start_time
        self.prev_obs = None
        try:
            self.engine = db.create_engine('sqlite:///' + f'./{self.log_name}.db')
        except:
            print(sys.exc_info()[0]) # used to print error messages from sqlalchemy, delete later
        self.logger.debug('made new engine')
        self.conn = self.engine.connect()
        self.logger.debug('opened new connection')

        self.create_obs_log(clobber=clobber)

    def create_obs_log(self, clobber=True):

        try:
            self.conn.execute("""DROP TABLE Datalog""")
        except:
            pass

        if not self.engine.dialect.has_table(self.engine, 'Datalog'):
            # create table

            self.conn.execute("""
            CREATE TABLE Datalog(
            obsHistID            INTEGER PRIMARY KEY,
            requestID            INTEGER,
            propID               INTEGER,
            fieldID              INTEGER,
            fieldRA              REAL,
            fieldDec             REAL,
            filter               TEXT,
            expDate              INTEGER,
            expMJD               REAL,
            night                INTEGER,
            visitTime            REAL,
            visitExpTime         REAL,
            FWHMgeom             REAL,
            FWHMeff              REAL,
            airmass              REAL,
            filtSkyBright        REAL,
            lst                  REAL,
            altitude             REAL,
            azimuth              REAL,
            dist2Moon            REAL,
            solarElong           REAL,
            moonRA               REAL,
            moonDec              REAL,
            moonAlt              REAL,
            moonAZ               REAL,
            moonPhase            REAL,
            sunAlt               REAL,
            sunAz                REAL,
            slewDist             REAL,
            slewTime             REAL,
            fiveSigmaDepth       REAL,
            totalRequestsTonight INTEGER,
            metricValue          REAL,
            subprogram           TEXT,
            pathToFits           TEXT
            )""")


    def log_observation(self, data, image):
        """
        Take in data and a file path and combine them into a row that can be saved to our database.
        data is None checks for the condition that we've finished reading the schedule for tonight
        """
        if data is None:
            self.conn.close()
            self.engine.close()
            return
        record = dict(data)
        record['pathToFits'] = image
        try:
            record_row = pd.DataFrame(record,index=[uuid.uuid4().hex])
            # the uuid4 method doesnt use identifying info to make IDS. Maybe should be looked into more at some point.
            record_row.to_sql('Datalog', self.conn, index=False, if_exists='append')
            self.logger.debug(f'Inserted Row: {record}')
        except Exception as e:
            self.logger.error('query failed', exc_info=True )

if __name__ == '__main__':
    # used to make this file importable
    pass
