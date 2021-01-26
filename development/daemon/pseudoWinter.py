"""
A simulator of the actual Winter instrument
Implements the Controller and Scheduler classes to simulate reception
of schedule database and uses ObsWriter to log "data" into a new sqlite db.
"""
import logging
import time
import Pyro5.client


class Controller():

    def __init__(self, mode, config_file, base_directory):
        """
        Basically a knockoff of the real controller, uses an infinite loop
        to keep the program running. For future tests may enable other modes.
        """
        #set up logging
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        fh = logging.FileHandler('pseudoLog.log', mode='w')
        format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        fh.setFormatter(format)
        self.logger.addHandler(fh)
        self.logger.debug("created logger in Controller class")


        self.base_directory = base_directory

        if mode not in [0,1,2]:
            raise IOError("'" + str(mode) + "' is note a valid operation mode")

        if mode in [0]:
            # Robotic Observing Mode
            try:

                self.schedule = Schedule(base_directory = self.base_directory, date = 'today')
                self.schedule.loadSchedule(currentTime=0)
                try:
                    self.weather = Pyro5.client.Proxy("PYRONAME:weather")
                    self.weather.startWeather()
                    self.logger.error('weather connect succesful')
                except Exception as e:
                    self.logger.error('weather connect failed', exc_info=True )

                counter = 0
                while True and counter <= 12:
                    try:
                        safe = self.weather.weather_safe()
                        print("Weather Safe: " + str(safe))
                        if safe:
                            print(self.schedule.getCurrentObs())
                            self.schedule.gotoNextObs()

                        time.sleep(5)
                        counter +=1
                    except:
                        print("errors in the use of schedule or writer")
                        break
                self.weather.shutdownWeather()
            except:
                print('failed to initialize schedule or writer')

import sqlalchemy as db

class Schedule():

    def __init__(self, base_directory, date = 'today'):
        """
        sets up logging and opens connection to the database. Does
        not actually access any data yet.
        """

        #set up logging
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        fh = logging.FileHandler('pseudoLog.log', mode='a')
        format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        fh.setFormatter(format)
        self.logger.addHandler(fh)

        self.base_directory = base_directory
        self.schedulefile = base_directory + '/1_night_test.db'
        self.engine = db.create_engine('sqlite:///' + self.schedulefile)
        self.conn = self.engine.connect()
        self.logger.error(str('successfully connected to db at ' + self.schedulefile))


    def loadSchedule(self, currentTime=0, startFresh=False):
        """
        Load the schedule starting at the currentTime.
        ### Note: At the moment currentTime is a misnomer, we are selecting by the IDs of the observations
        since the schedule database does not include any time information. Should change this to
        actually refer to time before deployment.
        """
        metadata = db.MetaData()

        try:
            summary = db.Table('Summary', metadata, autoload=True, autoload_with=self.engine)
            self.logger.error('starting to load schedule')
        except Exception as e:
            self.logger.error('load summary failed', exc_info=True)
        #Query the database starting at the correct time of night
        try:
            self.result = self.conn.execute(summary.select().where(summary.c.obsHistID >= currentTime))
            self.logger.debug('successfully queried db')
        except Exception as e:
            self.logger.error('query failed', exc_info=True )

        # The fetchone method grabs the first row in the result of the query and stores it as currentObs
        self.currentObs = dict(self.result.fetchone())
        self.logger.debug('popped first result')

    def makeObsLog(self):
        #Moving to ObsWriter Class, the functionality should be separate
        pass

    def logCurrentObs(self):
        #Moving to ObsWriter Class, the functionality should be separate
        pass

    def getCurrentObs(self):
        """
        Returns the observation that the telescope should be making at the current time
        """
        return self.currentObs

    def gotoNextObs(self):
        """
        Moves down a line in the database.
        When there are no more lines fetchone returns None and we know we've finished
        """
        self.currentObs = dict(self.result.fetchone())
        if self.currentObs == None:
            self.result.close()
            self.conn.close()




if __name__ == '__main__':
    # The main method allows this module to be imported by other files
    pass
