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

        self.create_tables(clobber=clobber)

    def create_tables(self, clobber=False):

        if clobber:
            try:
                self.conn.execute("""DROP TABLE Observation""")
                self.conn.execute("""DROP TABLE Field""")
                self.conn.execute("""DROP TABLE Night""")
            except:
                pass

        if not self.engine.dialect.has_table(self.engine, 'Observation'):
            # create table

            self.conn.execute("""
            CREATE TABLE Observation(
            obsHistID            INTEGER PRIMARY KEY,
            fieldID              INTEGER,
            filter               TEXT,
            night                INTEGER,
            visitTime            REAL,
            visitExpTime         REAL,
            airmass              REAL,
            filtSkyBright        REAL,
            fiveSigmaDepth       REAL,
            dist2Moon            REAL,
            progID               INTEGER,
            subprogram           TEXT,
            pathToFits           TEXT
            )""")


        if not self.engine.dialect.has_table(self.engine, 'Field'):
            # create table

            self.conn.execute("""
            CREATE TABLE Field(
            fieldID            INTEGER PRIMARY KEY,
            rightAscension            REAL,
            declination               REAL
            )""")



        if not self.engine.dialect.has_table(self.engine, 'Night'):
            # create table

            self.conn.execute("""
            CREATE TABLE Night(
            nightID            INTEGER PRIMARY KEY,
            avgTemp            Real,
            moonPhase          TEXT
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

        #separate provided data into table friendly chunks
        self.logger.error('separating data')
        fieldData, nightData, obsData = separate_data_dict(record)
        self.logger.error('separated data')

        #append to Field table if necessary

        #append to Night table if necessary

        #append to Observation Table
        try:
            record_row = pd.DataFrame(obsData,index=[uuid.uuid4().hex])
            # the uuid4 method doesnt use identifying info to make IDS. Maybe should be looked into more at some point.
            record_row.to_sql('Observation', self.conn, index=False, if_exists='append')
            self.logger.debug(f'Inserted Row: {record}')
        except Exception as e:
            self.logger.error('query failed', exc_info=True )

def separate_data_dict(dataDict):
    fieldData = {'fieldID': dataDict['fieldID'], 'rightAscension': dataDict['fieldRA'], 'declination': dataDict['fieldDec']}
    nightData = {'nightID': dataDict['night'], 'avgTemp': -314, 'moonPhase': dataDict['moonPhase']}
    obsData = {}
    obsFields = ['obsHistID', 'fieldID', 'filter', 'night', 'visitTime', 'visitExpTime', 'airmass', \
    'filtSkyBright', 'fiveSigmaDepth', 'dist2Moon', 'subprogram', 'pathToFits' ]
    for field in obsFields:
        obsData[field] = dataDict[field]
    obsData['progID'] = dataDict['propID']

    return fieldData, nightData, obsData

if __name__ == '__main__':
    # used to make this file importable
    pass
