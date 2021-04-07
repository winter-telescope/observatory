#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
commandParser

This file is part of wsp

# PURPOSE #
This program handles the parsing and execution of commands sent to the WINTER
telescope. Commands are added to a priority FIFO queue and executed in
a threadpool of worker threads.


"""


import sys
import time
import queue
import argparse
from PyQt5 import uic, QtCore, QtGui, QtWidgets
import traceback
import signal
import logging
import os
import datetime
import numpy as np



class WorkerSignals(QtCore.QObject):
    '''
    Defines the signals available from a running worker thread.

    In this example we've defined 5 custom signals:
        finished signal, with no data to indicate when the task is complete.
        error signal which receives a tuple of Exception type, Exception value and formatted traceback.
        result signal receiving any object type from the executed function.

    Supported signals are:

    finished
        No data

    error
        `tuple` (exctype, value, traceback.format_exc() )

    result
        `object` data returned from processing, anything

    progress
        `int` indicating % progress
    '''
    started = QtCore.pyqtSignal()
    finished = QtCore.pyqtSignal()
    error    = QtCore.pyqtSignal(tuple)
    result   = QtCore.pyqtSignal(object)
    progress = QtCore.pyqtSignal(int)

class Worker(QtCore.QRunnable):
    '''
    Worker thread

    Inherits from QRunnable to handler worker thread setup, signals and wrap-up.

    :param callback: The function callback to run on this worker thread. Supplied args and
                     kwargs will be passed through to the runner.
    :type callback: function
    :param args: Arguments to pass to the callback function
    :param kwargs: Keywords to pass to the callback function

    '''

    def __init__(self, fn, *args, **kwargs): # Now the init takes any function and its args
        #super(Worker, self).__init__() # <-- this is what the tutorial suggest
        super().__init__() # <-- This seems to work the same. Not sure what the difference is???
        # Store constructor arguments (re-used for processing)
        self.fn = fn
        self.args = args
        self.kwargs = kwargs

        # This is a new bit: subclass an instance of the WorkerSignals class:
        self.signals = WorkerSignals()





    @QtCore.pyqtSlot()
    def run(self):
        '''
        Initialise the runner function with passed args, kwargs.

        Did some new stuff here since ex6.
        Now it returns an exception if the try/except doesn't work
        by emitting the instances of the self.signals QObject

        '''

        # Retrieve args/kwargs here; and fire processing using them
        try:
            self.signals.started.emit()
            result = self.fn(
                *self.args, **self.kwargs
            )
        except:
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.signals.error.emit((exctype, value, traceback.format_exc()))
        else:
            self.signals.result.emit(result)  # Return the result of the processing
        finally:
            self.signals.finished.emit()  # Done


class cmd_request(object):
    """
    A cmd_request object is generated each time a user tries to execute a
    command, either by typing into the local command prompt or externally from
    a network connection.

    The cmd_request object contains the specified command argument, which
    should be one of the cmd entries in wintercmd if it is to be successful,
    the priority level of the command (set variously in the code depending on
    who is the sender), as well as information about the requester,
    namely their ip address, port.
    """
    def __init__(self, cmd, request_addr, request_port, priority = 'low'):
        try:
            self.cmd = cmd
            self.request_addr = request_addr
            self.request_port = request_port
            self._priority_dict_ = dict({'low'      : 4,
                                         'med'      : 3,
                                         'medium'   : 3,
                                         'high'     : 2,
                                         'sudo'     : 1})
            self.priority = priority
            self.priority_num = self._priority_dict_.get(self.priority,4)
        except:
            try:
                print(f'invalid command request {cmd} (priority {priority} from user at [{request_addr} : {request_port}]')
                #TODO log it
            except:
                print('invalid command request!')
                #TODO log it

class cmd_prompt(QtCore.QThread):
    """
    This is a dedicated thread which just listens for commands from the terminal
    and then sends any received command out to be executed in a worker thread
    """
    # define a signal which will emit when a new command is received
    #newcmd = QtCore.pyqtSignal(str)
    newcmd = QtCore.pyqtSignal(object) #not just a str, now has more info

    def __init__(self,telescope,wintercmd):
        super().__init__()

        self.wintercmd = wintercmd
        self.wintercmd.promptThread = self
        self.telescope = telescope
        self.running = False
        self.start()

    def stop(self):
        self.running = False
        ## TODO: Anything else that needs to happen before stopping the thread

    def run(self):
        self.running = True
        self.getcommands()

    def getcommands(self):
        print(f'commandparser: running command console in thread {self.currentThread()}')
        while self.running:
            # listen for an incoming command
            cmd = input(self.wintercmd.prompt)
            # don't do anyting if the command is just whitespace:
            if cmd.isspace() or ( cmd == ''):
                pass
            else:
                # create a command request object
                new_cmd_request = cmd_request(cmd = cmd,
                                              request_addr = 'localhost',
                                              request_port = 'terminal',
                                              priority = 'medium')
                # emit signal that command has been received
                #self.newcmd.emit(cmd) #old system where just the command was passed
                self.newcmd.emit(new_cmd_request)


class cmd_executor(QtCore.QThread):
    """
    This is a thread which handles the command queue, takes commands
    from the command line "cmd_prompt" thread or from the server thread.
    The command queue is a prioritied FIFO queue and each item from the queue
    is executed in a QRunnable worker thread.
    """
    def __init__(self,telescope,wintercmd,logger, listener=None):
        super().__init__()

        # set up the threadpool
        self.threadpool = QtCore.QThreadPool()

        # create the winter command object
        #self.wintercmd = Wintercmd(telescope)
        self.wintercmd = wintercmd
        self.wintercmd.execThread = self
        self.logger = logger
        self.listener = listener

        # set up the command prompt
        #self.cmdprompt = cmd_prompt(telescope,self.wintercmd)

        # create the command queue
        self.queue = queue.PriorityQueue()

        # connect the command interfaces to the executor
        #self.cmdprompt.newcmd.connect(self.add_to_queue)

        # start the thread
        self.start()

   
    
   


    def add_cmd_request_to_queue(self,cmdrequest):
        # adds a command request object directly to the queue
        
        self.logger.debug(f"adding cmd to queue: {cmdrequest.cmd}, from user at {cmdrequest.request_addr}|{cmdrequest.request_port}")
        #self.queue.put((1,cmd))
        self.queue.put((cmdrequest.priority_num, cmdrequest.cmd))
        
    def add_cmd_to_queue(self, cmd, request_addr = 'localhost', request_port = 'robo', priority = 'medium'):
        # adds a command to the queue by creating a command object.
        # cmd is either the actual string, eg 'dome_close', or a list of command strings (eg a routine)
        cmdrequest = cmd_request(cmd = cmd,
                              request_addr = request_addr,
                              request_port = request_port,
                              priority = priority)
        
        if (type(cmd) is list) or (type(cmd) is np.ndarray):
            # the cmd is a list
            self.logger.info(f"adding cmd list from user at {cmdrequest.request_addr}|{cmdrequest.request_port}")
        else:
            self.logger.info(f"adding cmd to queue: {cmdrequest.cmd}, from user at {cmdrequest.request_addr}|{cmdrequest.request_port}")
        
        self.queue.put((cmdrequest.priority_num, cmdrequest.cmd))
    
    def dispatch_single_command(self, cmd):
        try:
            worker = Worker(self.wintercmd.parse,cmd)
            #self.wintercmd.onecmd(cmd)
            ## for the moment the following lines commented, since we are not interrupting for commands without pausing schedule
            # if self.listener:
            #     worker.signals.finished.connect(self.listener.start)
            self.threadpool.start(worker)
        except Exception as e:
            print(f'could not execute {cmd}: {e}')
    
    
    
    def dispatch_command_list(self, cmd):
        # if cmd is a list of commands, then we do them one at a time in a single worker thread
        try:
            worker = Worker(self.wintercmd.parse_list,cmd)
            
            self.threadpool.start(worker)
        except Exception as e:
            print(f'could not execute {cmd}: {e}')
            
    
    def execute(self,cmd):
        """
        Execute the command in a worker thread
        """
        self.logger.debug(f'executing command {cmd}')
        
        if (type(cmd) is list) or (type(cmd) is np.ndarray):
            # the cmd is a list. execute the list sequentially in a single worker thread
            self.dispatch_command_list(cmd)
        else:
            # the cmd is a singleton. exceture it in its own worker thread
            self.dispatch_single_command(cmd)

    def stop(self):
        self.running = False
        ## TODO: Anything else that needs to happen before stopping the thread

    def run(self):
        self.running = True
        # if there are any commands in the queue, execute them!
        self.logger.debug('waiting for commands to execute')
        print(f'commandparser: running command queue manager in thread {self.currentThread()}')
        while self.running:
           if not self.queue.empty():
               priority, cmd = self.queue.get()
               self.execute(cmd)

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
