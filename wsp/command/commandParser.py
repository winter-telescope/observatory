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




class cmd_prompt(QtCore.QThread):
    """
    This is a dedicated thread which just listens for commands from the terminal
    and then sends any received command out to be executed in a worker thread
    """
    # define a signal which will emit when a new command is received
    newcmd = QtCore.pyqtSignal(str)
    
    def __init__(self,telescope,wintercmd):
        super().__init__()
        
        self.wintercmd = wintercmd
        self.telescope = telescope
        self.start()
        
    def run(self):
        self.getcommands()
    
    def getcommands(self):
        while True:
            # listen for an incoming command
            cmd = input(self.wintercmd.prompt)
            # don't do anyting if the command is just whitespace:            
            if cmd.isspace() or ( cmd == ''):
                pass
            else:
                # emit signal that command has been received
                self.newcmd.emit(cmd)

            
class cmd_executor(QtCore.QThread):           
    """
    This is a thread which handles the command queue, takes commands
    from the command line "cmd_prompt" thread or from the server thread.
    The command queue is a prioritied FIFO queue and each item from the queue
    is executed in a QRunnable worker thread.
    """
    def __init__(self,telescope,wintercmd,logger):
        super().__init__()
        
        # set up the threadpool
        self.threadpool = QtCore.QThreadPool()
        
        # create the winter command object
        #self.wintercmd = Wintercmd(telescope)
        self.wintercmd = wintercmd
        self.logger = logger
        
        # set up the command prompt
        #self.cmdprompt = cmd_prompt(telescope,self.wintercmd)
        
        # create the command queue
        self.queue = queue.PriorityQueue()
        
        # connect the command interfaces to the executor
        #self.cmdprompt.newcmd.connect(self.add_to_queue)
        
        # start the thread
        self.start()
    
            
    
    def add_to_queue(self,cmd):
        self.logger.debug(f"adding cmd to queue: {cmd}")
        self.queue.put((1,cmd))
        
    def execute(self,cmd):
        """
        Execute the command in a worker thread
        """
        self.logger.debug(f'executing command {cmd}')
        try:
            worker = Worker(self.wintercmd.parse,cmd)
            #self.wintercmd.onecmd(cmd)
            self.threadpool.start(worker)
        except Exception as e:
            print(f'could not execute {cmd}: {e}')
            
    def run(self):
       # if there are any commands in the queue, execute them!
       self.logger.debug('waiting for commands to execute')
       while True:
           if not self.queue.empty():
               priority, cmd = self.queue.get()
               self.execute(cmd)
