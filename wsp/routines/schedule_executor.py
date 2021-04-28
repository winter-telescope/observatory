#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ported over from its original home in commandParser

@author: allan garcia-zych
"""


import time
from PyQt5 import uic, QtCore, QtGui, QtWidgets
import datetime
import numpy as np



class schedule_executor(QtCore.QThread):
    """
    This is a thread which handles the tracking and execution of the scheduled observations for the robotic execution
    modes of WINTER's operation.
    """

    # define useful signals
    changeSchedule = QtCore.pyqtSignal(object)
    newcmd = QtCore.pyqtSignal(object)

    def __init__(self, config, state, telescope, wintercmd, schedule, writer, logger):
        super().__init__()
        self.config = config
        self.state = state
        self.telescope = telescope
        self.wintercmd = wintercmd
        self.wintercmd.scheduleThread = self
        self.schedule = schedule
        self.schedule.scheduleExec = self
        self.writer = writer
        self.logger = logger
        self.lastSeen = -1
        self.currentALT = 0
        self.currentAZ = 0
        self.running = False
        self.schedulefile_name = None
        # if the changeSchedule signal is caught, set up a new schedule
        self.changeSchedule.connect(self.setup_new_schedule)

        # load the dither list
        self.dither_alt, self.dither_az = np.loadtxt(self.schedule.base_directory + '/' + self.config['dither_file'], unpack = True)
        # convert from arcseconds to degrees
        self.dither_alt *= (1/3600.0)
        self.dither_az  *= (1/3600.0)

    def getSchedule(self, schedulefile_name):
        self.schedule.loadSchedule(schedulefile_name, self.lastSeen+1)

    def interrupt(self):
        self.schedule.currentObs = None

    def stop(self):
        self.running = False
        #TODO: Anything else that needs to happen before stopping the thread

    def setup_new_schedule(self, schedulefile_name):
        """
        This function handles the initialization needed to start observing a
        new schedule. It is called when the changeSchedule signal is caught,
        as well as when the thread is first initialized.
        """

        print(f'scheduleExecutor: setting up new schedule from file >> {schedulefile_name}')

        if self.running:
            self.stop()

        self.schedulefile_name = schedulefile_name

    def get_data_to_log(self):
        data = {}
        for key in self.schedule.currentObs:
            if key in ("visitTime", "altitude", "azimuth"):
                data.update({f'{key}Scheduled': self.schedule.currentObs[key]})
            else:
                data.update({key: self.schedule.currentObs[key]})
        data.update({'visitTime': self.waittime, 'altitude': self.alt_scheduled, 'azimuth': self.az_scheduled})
        return data
    #def observe(self):


    def run(self):
        '''
        This function must contain all of the database manipulation code to remain threadsafe and prevent
        exceptions from being raised during operation
        '''
        self.running = True
        #print(f'scheduleExecutor: running scheduleExec in thread {self.currentThread()}')

        #print(f'scheduleExecutor: attempting to load schedulefile_name = {self.schedulefile_name}')
        if self.schedulefile_name is None:
            # NPL 9-21-20: put this in for now so that the while loop in run wouldn't go if the schedule is None
            self.schedule.currentObs = None

        else:
            #print(f'scheduleExecutor: loading schedule file [{self.schedulefile_name}]')
            # code that sets up the connections to the databases
            self.getSchedule(self.schedulefile_name)
            self.writer.setUpDatabase()

        while self.schedule.currentObs is not None and self.running:
            #print(f'scheduleExecutor: in the observing loop!')
            self.lastSeen = self.schedule.currentObs['obsHistID']
            self.current_field_alt = float(self.schedule.currentObs['altitude'])
            self.current_field_az = float(self.schedule.currentObs['azimuth'])

            for i in range(len(self.dither_alt)):
                # step through the prescribed dither sequence
                dither_alt = self.dither_alt[i]
                dither_az = self.dither_az[i]
                print(f'Dither Offset (alt, az) = ({dither_alt}, {dither_az})')
                self.alt_scheduled = self.current_field_alt + dither_alt
                self.az_scheduled = self.current_field_az + dither_az

                #self.newcmd.emit(f'mount_goto_alt_az {self.currentALT} {self.currentAZ}')
                if self.state["ok_to_observe"]:
                    print(f'Observing Dither Offset (alt, az) = ({dither_alt}, {dither_az})')
                    self.telescope.mount_goto_alt_az(alt_degs = self.alt_scheduled, az_degs = self.az_scheduled)
                    # wait for the telescope to stop moving before returning
                    while self.state['mount_is_slewing']:
                       time.sleep(self.config['cmd_status_dt'])
                else:
                    print(f'Skipping Dither Offset (alt, az) = ({dither_alt}, {dither_az})')
                self.waittime = int(self.schedule.currentObs['visitTime'])/len(self.dither_alt)
                ##TODO###
                ## Step through current obs dictionairy and update the state dictionary to include it
                ## append planned to the keys in the obs dictionary, to allow us to use the original names to record actual values.
                ## for now we want to add actual waittime, and actual time.
                #####
                # print(f' Taking a {waittime} second exposure...')
                time.sleep(self.waittime)

                if self.state["ok_to_observe"]:
                    imagename = self.writer.base_directory + '/data/testImage' + str(self.lastSeen)+'.FITS'
                    # self.telescope_mount.virtualcamera_take_image_and_save(imagename)
                    currentData = self.get_data_to_log()
                    # self.state.update(currentData)
                    # data_to_write = {**self.state}
                    data_to_write = {**self.state, **currentData} ## can add other dictionaries here
                    self.writer.log_observation(data_to_write, imagename)

            self.schedule.gotoNextObs()

        if not self.schedulefile_name is None:
            ## TODO: Code to close connections to the databases.
            self.schedule.closeConnection()
            self.writer.closeConnection()