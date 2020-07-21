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
import json


class ObsWriter():
    """
    Heavily inspired by obsLogger.py in winter_sim and by code in the schedule.py file in WSP
    """

    def __init__(self, log_name, base_directory, survey_start_time = Time('2018-01-01'), clobber = False):
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
        self.base_directory = base_directory
        self.survey_start_time = survey_start_time
        self.prev_obs = None
        try:
            self.engine = db.create_engine('sqlite:///' + f'./{self.log_name}.db')
        except:
            print(sys.exc_info()[0]) # used to print error messages from sqlalchemy, delete later
        self.logger.debug('made new engine')
        self.conn = self.engine.connect()
        self.logger.debug('opened new connection')

        # Initialize database structure from json file.
        #Note: Change to accept path argument instead of hardcoding
        with open("dataconfig.json") as json_data_file:
            self.dbStructure = json.load(json_data_file)

        self.create_tables(clobber=clobber)


    def printDBStructure(self):
        print(f'Creating database as follows:')
        for table in self.dbStructure:
            print(f'Table: {table}')
            for column in self.dbStructure[table]:
                print(f'    Field: {column} {self.dbStructure[table][column]}')

    def generateDBCommands(self):
        self.logger.debug("generating commands")
        self.sqlCommands = {}
        for table in self.dbStructure:
            command = f'CREATE TABLE {table}('
            for column in self.dbStructure[table]:
                colDict = self.dbStructure[table][column]
                command += f'\n{column} {colDict["type"].upper()}{" PRIMARY KEY" if colDict.get("primaryKey") else ""},'
            command = command[:len(command)-1] + "\n)"
            self.sqlCommands[table]={"createCommand": command}

    def create_tables(self, clobber=False):

        if clobber:
            try:
                self.conn.execute("""DROP TABLE Observation""")
                self.conn.execute("""DROP TABLE Field""")
                self.conn.execute("""DROP TABLE Night""")
            except:
                pass

        self.generateDBCommands()

        for table in self.sqlCommands:

            if not self.engine.dialect.has_table(self.engine, table):
                try:
                    self.conn.execute(self.sqlCommands[table]["createCommand"])
                except:
                    self.logger.error('create failed', exc_info=True )

    def populateFieldsTable(self):
        path = os.getcwd() + '/1_night_test.db'
        scheduleEngine = db.create_engine('sqlite:///' + path)
        scheduleConn = scheduleEngine.connect()
        self.logger.debug('copying fields table from schedule...')

        fields = db.Table('Field', db.MetaData(), autoload=True, autoload_with=scheduleEngine)
        self.logger.debug('got table')
        try:
            result = scheduleConn.execute(db.select([fields]))
        except Exception as e:
            self.logger.error('query failed', exc_info=True )

        self.logger.debug('got result ')

        for row in result:
            print(f'{row}')

    def getPrimaryKey(self, tableName):
        table = self.dbStructure[tableName]
        for key in table:
            if 'primaryKey' in table[key]:
                return key


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
        self.logger.debug('separating data')
        # fieldData, nightData, obsData = separate_data_dict(record)
        try:
            separatedData = self.separate_data_dict(record)
        except:
            self.logger.error('separation failed', exc_info=True )
        print(f'{separatedData}')
        self.logger.debug('separated data')

        fieldData = separatedData['Field']
        obsData = separatedData['Observation']
        nightData = separatedData['Night']

        for table in separatedData:
            try:
                dbTable = db.Table(table, db.MetaData(), autoload=True, autoload_with=self.engine)
                primaryKey = self.getPrimaryKey(table)
                exists = self.conn.execute(dbTable.select().where(dbTable.c[primaryKey] == separatedData[table][primaryKey])).fetchone()
            except Exception as e:
                self.logger.error('query failed', exc_info=True )
            if exists is None:
                try:
                    record_row = pd.DataFrame(separatedData[table], index=[uuid.uuid4().hex])
                    record_row.to_sql(table, self.conn, index=False, if_exists='append')
                    self.logger.debug(f'Inserted {table} Row: {separatedData[table]}')
                except:
                    self.logger.error('insert failed:', exc_info=True )
            else:
                self.logger.debug('did not insert because the row already existed in the database')

    def separate_data_dict(self, dataDict):
        separatedData = {}
        for table in self.dbStructure:
            tableData = {}
            for column in self.dbStructure[table]:
                if column in dataDict:
                    tableData[column] = dataDict[column]
                elif "altNames" in self.dbStructure[table][column]:
                    altNames = self.dbStructure[table][column]["altNames"]
                    for name in altNames:
                        if name in dataDict:
                            tableData[column] = dataDict[name]
                elif "default" in self.dbStructure[table][column]:
                    tableData[column] = self.dbStructure[table][column]["default"]
                else:
                    tableData[column] = None
                    ## Maybe catch a lack of a value in this function rather than waiting for it to be an issue later.
            separatedData[table] = tableData
        return separatedData


if __name__ == '__main__':
    # used to make this file importable
    pass

# def loadObslog(self):
#     try:
#         # Try to load the observation log for tonight
#         if os.path.isfile(self.obslogfile):
#             print(" found obslog for tonight")
#             # found an obslog. read it in and get the request ID from the last line
#             log = utils.readcsv(self.obslogfile,skiprows = 2)
#
#
#             # the get the most recent line and request
#             lastrequestID = int(log['requestID'][-1])
#             lastobsHistID = int(log['obsHistID'][-1])
#
#
#             try:
#                 # see if the most recent requestID is in the schedule file
#                 #   MUST match the requestID and the obshistID
#                 # Need to make the lists numpy arrays to do the comparison
#                 #TODO is this the best place/time to make them numpy arrays?
#                 requestID_nparr = np.array(self.schedule['requestID'])
#                 obsHistID_nparr = np.array(self.schedule['obsHistID'])
#                 index = np.where((requestID_nparr == lastrequestID) & (obsHistID_nparr == lastobsHistID) )
#                 # there's a leftover empty element from the where, something like index = (array([14]),)
#                 index = index[0]
#
#                 # if there are multiple places that match the last logged line, then restart schedule
#                 if len(index)>1:
#                     print(" reduncancy in rank of last observation. Starting from top")
#                     self.currentScheduleLine = 0
#                 else:
#                     index = int(index)
#
#                     # if the index is the index of the last line, then need special handling:
#                     if index >= self.schedule[''][-1]:
#                         # all the items in the schedule have been completed!
#                         if self.forceRestart:
#                             #if we're forcing a restart, then start again
#                             self.currentScheduleLine = 0
#                         else:
#                             print(f" All items in the schedule have been observed. Exiting...")
#                             self.currentScheduleLine = -1
#                             return
#                     # make the current line the next line after the last logged line
#                     print(f' Found the last logged obs in line {index} of the schedule! Starting schedule at line {index+1}')
#                     self.currentScheduleLine = self.schedule[''][index] + 1
#             except:
#                 print(" couldn't match last obs line with schedule")
#
#
#         else:
#             print(" could not find obslog for tonight. making one...")
#             self.makeObslog()
#     except:
#         print(" could not verify the obslog status!")
# def makeObslog(self):
#     # Make a new obslog
#     # Never overwrite stuff in the log, only append!
#     file = open(self.obslogfile,'a')
#     date_obj = datetime.strptime(self.date,'%Y%m%d')
#     now_obj  = datetime.utcnow()
#
#     calitz = pytz.timezone('America/Los_Angeles')
#     cali_now = datetime.now(calitz)
#
#     file.write(f"# WINTER Observation Log for the night of {date_obj.strftime('%Y-%m-%d')}\n")
#     file.write(f"# Created: {now_obj.strftime('%Y-%m-%d %H:%M:%S')} UTC / {cali_now.strftime('%Y-%m-%d %H:%M:%S')} Palomar Time\n")
#     file.write(f"Time,\t")
#     selected_keys = ['obsHistID','requestID','propID','fieldID','fieldRA','fieldDec','filter','altitude','azimuth']
#     #for key in  self.schedule.keys():
#     for key in selected_keys:
#         file.write(f"{key},\t")
#     file.write("\n")
#     file.close()
#
# def logCurrentObs(self):
#     # log the current observation
#     # if we're at the end of the schedule file don't log the observation
#     if self.currentScheduleLine == -1:
#         print(' all scheduled items completed, nothing to add to log')
#         pass
#     else:
#         now_obj  = datetime.utcnow()
#         file = open(self.obslogfile,'a')
#         #file.write(f" new observation made at {now_obj.strftime('%Y-%m-%d %H:%M:%S')} UTC")
#         self.observed_timestamp = int(datetime.timestamp(now_obj))
#         file.write(f'{self.observed_timestamp},\t')
#         #for val in self.currentObs.values():
#         selected_keys = ['obsHistID','requestID','propID','fieldID','fieldRA','fieldDec','filter','altitude','azimuth']
#         for key in selected_keys:
#             val = self.schedule[key][self.currentScheduleLine]
#             file.write(f"{val},\t")
#         file.write("\n")
#         file.close()
