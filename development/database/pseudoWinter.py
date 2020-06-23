"""
A simulator of the actual Winter instrument
Implements the Controller and Scheduler classes to simulate reception
of schedule database and uses ObsWriter to log "data" into a new sqlite db.
"""

import ObsWriter

class Controller():

    def __init__(self, mode, config_file, base_directory):
        """
        Basically a knockoff of the real controller, uses an infinite loop
        to keep the program running. For future tests may enable other modes. 
        """
        self.base_directory = base_directory

        if mode not in [0,1,2]:
            raise IOError("'" + str(mode) + "' is note a valid operation mode")

        if mode in [0]:
            # Robotic Observing Mode
            try:

                self.schedule = Schedule(base_directory = self.base_directory, date = 'today')
                self.writer = ObsWriter.ObsWriter('testData', self.base_directory) #the ObsWriter initialization
                while True:
                    try:
                        print(self.schedule.getCurrentObs())
                        imagePath = "fakepath/etc/image.fits"
                        self.writer.log_observation(self.schedule.getCurrentObs(), imagePath)
                        self.schedule.gotoNextObs()

                    except:
                        print("errors in the use of schedule or writer")
                        break
            except:
                print('failed to initialize schedule or writer')


import sqlalchemy as db

class Schedule():

    def __init__(self, base_directory, date = 'today'):
        """
        Open databases and find out where we are in the schedule.
        Once finished, self.currentObs contains info about current task

        The db access code is very similar to what is in Winter_Sim. Some methods are
        declared but not imlemented. In production they will most likely be implemented to
        provide full functionality.
        """
        self.base_directory = base_directory
        self.schedulefile = base_directory + '/1_night_test.db'
        self.engine = db.create_engine('sqlite:///' + self.schedulefile)
        self.conn = self.engine.connect()
        print("connected")

        # This block queries the database for all rows
        metadata = db.MetaData()
        summary = db.Table('Summary', metadata, autoload=True, autoload_with=self.engine)
        self.result = self.conn.execute(db.select([summary]))
        print("succesfully queried")

        # The fetchone method grabs the first row in the result of the query and stores it as currentObs
        self.currentObs = self.result.fetchone()
        print("got one: ")

    def makeObsLog(self):
        pass

    def logCurrentObs(self):
        pass

    def getCurrentObs(self):
        return self.currentObs

    def gotoNextObs(self):
        """
        Moves down a line in the database.
        When there are no more lines fetchone returns None and we know we've finished
        """
        self.currentObs = self.result.fetchone()
        if self.currentObs == None:
            self.result.close()
            self.conn.close()




if __name__ == '__main__':
    # The main method allows this module to be imported by other files
    pass
