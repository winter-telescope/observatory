#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
wintercmd: the WINTER command interface

Usage:
    wintercmd goto_alt_az <alt> <az>
    wintercmd plover <int>
    wintercmd xyzzy
    wintercmd count <int>
    wintercmd (-i | --interactive)
    wintercmd (-h | --help | --version)

Options:
    -i, --interactive  Interactive Mode
    -h, --help  Show this screen and exit.
"""


"""
This is based on the 'interactive_example.py' sample script
provided in the docopt examples:
    https://github.com/docopt/docopt/blob/master/examples/interactive_example.py

How does it work?
The script relies primarily on two modules:
    docopt:
        this parses the input which can come from argv when calling
        the script, or from the terminal entry in the interactive mode
    cmd:
        this is a simple implementation of a command line command interface.
        It has a backend that treats cmd.Cmd objects as an interpreter, which has
        a prompt, a header, and a bunch of associated functions which *must*
        all start with "do_". For example, "do_thing" is read as a command that
        is called through the interface by entering "thing". We also use the
        continuous prompt loop .cmdloop() method which runs an infinite loop
        that gets input and parses the input.
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
from math import fmod
from datetime import datetime
import numpy as np
import shlex
import astropy.coordinates
import astropy.time 
import astropy.units as u
import threading
import pandas as pd
import yaml
import sqlite3 as sql
import requests
from astropy.coordinates import SkyCoord
import warnings
import subprocess
import pathlib

# add the wsp directory to the PATH
wsp_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(1, wsp_path)

print(f'wintercmd: wsp_path = {wsp_path}')

# winter modules
from command import commandParser
from utils import logging_setup
from utils import utils
from daemon import daemon_utils
from focuser import summerFocusLoop
from alerts import alert_handler
#from viscam.web_request import short_circ
from control.roboOperator import TargetError
# GLOBAL VARS

# load the config
CONFIG_FILE = wsp_path + '/config/config.yaml'
CONFIG = utils.loadconfig(CONFIG_FILE)
LOGGER = logging_setup.setup_logger(wsp_path, CONFIG)

#redefine the argument parser so it exits nicely and execptions are handled better

class WrapError(Exception):
    pass

class ArgumentParser(argparse.ArgumentParser):
    '''
    Subclass the exiting/error methods from argparse.ArgumentParser
    so that we can keep it from killing the loop if we want
    '''
    def __init__(self,logger,*args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger = logger

    def exit(self, status=0, message=None):
        if message:
            self._print_message(message, sys.stderr)
        #sys.exit(status)

    def error(self, message):
        """error(message: string)

        Prints a usage message incorporating the message to stderr and
        exits.

        If you override this in a subclass, it should not return -- it
        should either exit or raise an exception.
        """
        #self.logger.warning('Error in command call.')
        self._print_message('Error in command call: \n \t', sys.stderr)
        self.print_usage(sys.stderr)
        #args = {'prog': self.prog, 'message': message}
        #self.exit(2, _('%(prog)s: error: %(message)s\n') % args)

def cmd(func):
    """
    This is a simple wrapper to simplify the try/except statement
    when executing a function in the command list.
    """
    def wrapper_cmd(*args, **kwargs):
        try:
            func(*args, **kwargs)
        
        except TimeoutError as e:
            raise TimeoutError(e)
        except TargetError as e:
            print(f'wintercmd: caught TargetError: (e)')
            raise TargetError(e)
            
        except Exception as e:
            '''
            Exceptions are already handled by the argument parser
            so do nothing here.
            '''
            msg = (f'wintercmd: Could not execute command {func.__name__}: {e}')
            LOGGER.exception(msg)
            #NPL 8-2-21: adding these because some exceptions are getting lost (ie TargetError)
            raise Exception(e)
            
            
            pass
    return wrapper_cmd

class signalCmd(object):
    '''
    this is an object which can pass commands and args via a signal/slot to
    other threads, ideally for daemons
    '''
    def __init__(self, cmd, *args, **kwargs):
        self.cmd = cmd
        self.argdict = dict()
        self.args = args
        self.kwargs = kwargs

#class Wintercmd(object):
class Wintercmd(QtCore.QObject):    
    '''
    Using a QObject so that it can signals. To execute commands 
    from outside this thread let's try using the signal/slot approach.
    '''
    
    # a signal which will be used to signal that cmdParser should execute a new routine
    newRoutine = QtCore.pyqtSignal(object)        

    # a signal which will be used to send a commandRequest directly back to command executor
    newCmdRequest = QtCore.pyqtSignal(object)
    
    
    def __init__(self, base_directory, 
                 config, 
                 state, 
                 alertHandler, 
                 mirror_cover, 
                 daemonlist, 
                 telescope, 
                 dome, 
                 chiller, 
                 labjacks, 
                 powerManager, 
                 logger, 
                 #viscam, 
                 #ccd,
                 #summercamera,
                 #wintercamera,
                 camdict,
                 fwdict,
                 imghandlerdict,
                 ephem,
                 verbose = False):
        # init the parent class
        #super().__init__()
        super(Wintercmd, self).__init__()
        
        # things that define the command line prompt
        self.intro = 'Welcome to wintercmd, the WINTER Command Interface'
        self.prompt = 'wintercmd: '
        # grab some useful inputs
        self.state = state
        self.alertHandler = alertHandler
        self.daemonlist = daemonlist
        self.telescope = telescope
        self.dome = dome
        self.chiller = chiller
        self.labjacks = labjacks
        self.powerManager = powerManager
    
        self.base_directory = base_directory
        self.config = config
        self.logger = logger
        #self.viscam = viscam
        #self.ccd = ccd
        #self.summercamera = summercamera
        #self.wintercamera = wintercamera
        self.camdict = camdict
        self.fwdict = fwdict
        self.imghandlerdict = imghandlerdict
        self.mirror_cover = mirror_cover
        self.ephem = ephem
        
        self.verbose = verbose

        
        self.defineParser()
        
        # NPL 8-24-21: trying to get wintercmd to catch wrap warnings
        self.telescope.signals.wrapWarning.connect(self.raiseWrapError)
        
        # connect the warning from the chiller to shut off the TEC to a handling function
        #self.chiller.TECshutoffCmd.connect(self.handle_chiller_alarm)
        
        # wait QTimer to try to keep responsive instead of 
        
    def raiseWrapError(self):
        msg = f'wintercmd (thread {threading.get_ident()}): caught telescope wrapWarning signal: raising wrap error'
        self.logger.warning(msg)
        #raise WrapError
    
    def throwTimeoutError(self):
        msg = "command took too long to execute!"
        self.logger.warning(msg)
        raise TimeoutError(msg)
    
    def parse(self,argv = None):

        # parse_args defaults to [1:] for args, but you need to
        # exclude the rest of the args too, or validation will fail

        if argv is None:
            self.argv = sys.argv[1:]
            if len(self.argv) < 1:
                   #self.argv = ['-h']
                   pass
        else:
            #self.argv = argv.split(' ')
            # use the shlex module to split up the arguments intelligently, just like sys.argv does
            self.argv = shlex.split(argv)
        self.logger.debug(f'self.argv = {self.argv}')

        self.command = self.parser.parse_args(self.argv[0:1]).command
        #print(f'cmdarg = {cmdarg}')
        self.arglist = self.argv[1:]
        #self.command = cmdarg.command
        #self.logger.debug(f'command = {self.command}')

        if not hasattr(self, self.command):
            if self.command == '':
                pass
            else:
                self.logger.warning(f'Unrecognized command: {self.command}')
                self.parser.print_help()

                #sys.exit(1)
                pass
        # use dispatch pattern to invoke method with same name
        else:
            #### EXECUTE THE FUNCTION ####
            """try:
                getattr(self, self.command)()
            except Exception as e:
                self.logger.warning(f'Could not execute command {self.command}, {e}')
                self.logger.debug(e)"""
                
            # try it without the try/except block. don't want too many otherwise the error handling gets lost
            getattr(self, self.command)()
            
    
    def parse_list(self, cmdlist):
        # assumes each item in the list is a well-formed wintercmd
        try:
            for cmd in cmdlist:
                self.parse(cmd)
        
        except Exception as e:
            self.logger.warning(f'Could not execute command list. Died at {cmd}, Error: {e}')
        
    
    def getargs(self):
        '''
        this just runs the cmdparser and returns the arguments'
        it also checks if the help option ('-h') has been called,
        and then returns a boolean. If help has been called it set self.exit
        to True, otherwise it's false.'
        '''
        #print('arglist = ',self.arglist)

        self.args = self.cmdparser.parse_args(self.arglist)
        #print('args = ',self.args)
        #print('help selected? ','-h' in self.arglist)
        if '-h' in self.arglist:
            self.exit = True
            #print('help True!')
        else:
            self.exit = False
            #print('help False!')


    def defineParser(self, description = None):
        '''
        this creates the base parser which parses the commands
        the usage is grabbef from the documentation, so make sure it's documented
        nicely!
        '''
        self.parser = ArgumentParser(logger = self.logger,
            description=description,
            usage = __doc__)
        self.parser.add_argument('command', help='Subcommand to run')

    def defineCmdParser(self, description = None):
        '''
        this creates or recreates the subparser that parses the arguments
        passed to whtaever the command is
        '''
        self.cmdparser = ArgumentParser(logger = self.logger, description = description)
    
    
    def waitForCondition(self, expression, condition, timeout = 100.0):
        
        print(f'waiting for expression: {expression} to equal condition {condition}...')
        # wait for the telescope to stop moving before returning
        # create a buffer list to hold several samples over which the stop condition must be true
        n_buffer_samples = self.config.get('cmd_satisfied_N_samples')
        stop_condition_buffer = [(not condition) for i in range(n_buffer_samples)]
        
        # get the current timestamp
        start_timestamp = datetime.utcnow().timestamp()
        print(f'start_timestamp = {start_timestamp}')
        while True:
            QtCore.QCoreApplication.processEvents()
            #print('entering loop')
            #self.logger.info(f'STOP CONDITION BUFFER = {stop_condition_buffer}')
            time.sleep(self.config['cmd_status_dt'])
            timestamp = datetime.utcnow().timestamp()
            dt = (timestamp - start_timestamp)
            print(f'wintercmd: wait time so far = {dt}')
            if dt > timeout:
                raise TimeoutError(f'command timed out after {timeout} seconds before completing')
            
            stop_condition = self.state['mount_is_slewing']
            # do this in 2 steps. first shift the buffer forward (up to the last one. you end up with the last element twice)
            stop_condition_buffer[:-1] = stop_condition_buffer[1:]
            # now replace the last element
            stop_condition_buffer[-1] = stop_condition
            
            if all(entry == condition for entry in stop_condition_buffer):
                break    
    
    
    def handle_chiller_alarm(self):
        msg = '### WINTERCMD: GOT ALERT TO SHUT OFF TEC! ###'
        self.alertHandler.slack_log(msg)
        print(msg)
        self.logger.warning(msg)
        self.parse('ccd_tec_stop')
        
    
    @cmd
    def commit(self):
        self.defineCmdParser(description='Record changes to the repository')
        # prefixing the argument with -- means it's optional
        self.cmdparser.add_argument('--amend', action='store_true')
        self.getargs()
        self.logger.info('Running git commit, amend=%s' % self.args.amend)

    @cmd
    def raise_timeout(self):
        self.defineCmdParser(description = "Raise a TimeoutError")
        self.throwTimeoutError()

    @cmd
    def count(self):

        self.defineCmdParser('Count up to specified number in the logger')
        self.cmdparser.add_argument('num',
                                    nargs = 1,
                                    action = None,
                                    type = int,
                                    help = "number to count up to")
        self.getargs()
        #print('self.exit? ',self.exit)
        if self.exit: return

        num = self.args.num[0]
        self.logger.info(f'counting seconds up to {num}:')
        i = 0
        while i < num+1:
            self.logger.info(f'   count = {i}')
            i+=1
            time.sleep(1)

    @cmd
    def xyzzy(self):
        self.defineCmdParser('xyzzy test command')
        """Usage: xyzzy"""
        self.logger.info('nothing happened.')

    @cmd
    def plover(self):
        """Usage: plover <int>"""
        self.defineCmdParser('return the phrase "plover: <num>"')
        self.cmdparser.add_argument('num',
                                    nargs = 1,
                                    action = None,
                                    type = int,
                                    help = 'integer number to plover')
        self.getargs()
        num = self.args.num[0]
        self.logger.info(f"plover: {num}")

    @cmd
    def mount_connect(self):
        self.defineCmdParser('connect to telescope mount')
        self.telescope.mount_connect()

        """        
        time.sleep(self.config.get('cmd_waittime', 1.0))
        while not self.state['mount_is_connected']:
            time.sleep(self.config['cmd_status_dt'])
        
        """
        ## Wait until end condition is satisfied, or timeout ##
        condition = True
        timeout = 5.0
        # wait for the telescope to stop moving before returning
        # create a buffer list to hold several samples over which the stop condition must be true
        n_buffer_samples = self.config.get('cmd_satisfied_N_samples')
        stop_condition_buffer = [(not condition) for i in range(n_buffer_samples)]

        # get the current timestamp
        start_timestamp = datetime.utcnow().timestamp()
        while True:
            QtCore.QCoreApplication.processEvents()
            #print('entering loop')
            time.sleep(self.config['cmd_status_dt'])
            timestamp = datetime.utcnow().timestamp()
            dt = (timestamp - start_timestamp)
            #print(f'wintercmd: wait time so far = {dt}')
            if dt > timeout:
                raise TimeoutError(f'command timed out after {timeout} seconds before completing')
            
            stop_condition = (self.state['mount_is_connected'] == True)
            # do this in 2 steps. first shift the buffer forward (up to the last one. you end up with the last element twice)
            stop_condition_buffer[:-1] = stop_condition_buffer[1:]
            # now replace the last element
            stop_condition_buffer[-1] = stop_condition
            
            if all(entry == condition for entry in stop_condition_buffer):
                break    
        
    @cmd
    def mount_disconnect(self):
        self.defineCmdParser('disconnect from telescope mount')
        self.telescope.mount_disconnect()
        """
        time.sleep(self.config.get('cmd_waittime', 1.0))
        while self.state['mount_is_connected']:
            time.sleep(self.config['cmd_status_dt'])
            
        """
        ## Wait until end condition is satisfied, or timeout ##
        condition = True
        timeout = 5.0
        # wait for the telescope to stop moving before returning
        # create a buffer list to hold several samples over which the stop condition must be true
        n_buffer_samples = self.config.get('cmd_satisfied_N_samples')
        stop_condition_buffer = [(not condition) for i in range(n_buffer_samples)]

        # get the current timestamp
        start_timestamp = datetime.utcnow().timestamp()
        while True:
            QtCore.QCoreApplication.processEvents()
            #print('entering loop')
            time.sleep(self.config['cmd_status_dt'])
            timestamp = datetime.utcnow().timestamp()
            dt = (timestamp - start_timestamp)
            #print(f'wintercmd: wait time so far = {dt}')
            if dt > timeout:
                raise TimeoutError(f'command timed out after {timeout} seconds before completing')
            
            stop_condition = (self.state['mount_is_connected'] == False)
            # do this in 2 steps. first shift the buffer forward (up to the last one. you end up with the last element twice)
            stop_condition_buffer[:-1] = stop_condition_buffer[1:]
            # now replace the last element
            stop_condition_buffer[-1] = stop_condition
            
            if all(entry == condition for entry in stop_condition_buffer):
                break    

    @cmd
    def mount_az_on(self):
        self.defineCmdParser('turn on az motor')
        self.telescope.mount_enable(0)
        
        """
        time.sleep(self.config.get('cmd_waittime', 1.0))
        while not self.state['mount_az_is_enabled']:
            time.sleep(self.config['cmd_status_dt'])
        """
        ## Wait until end condition is satisfied, or timeout ##
        condition = True
        timeout = 5.0
        # wait for the telescope to stop moving before returning
        # create a buffer list to hold several samples over which the stop condition must be true
        n_buffer_samples = self.config.get('cmd_satisfied_N_samples')
        stop_condition_buffer = [(not condition) for i in range(n_buffer_samples)]

        # get the current timestamp
        start_timestamp = datetime.utcnow().timestamp()
        while True:
            QtCore.QCoreApplication.processEvents()
            #print('entering loop')
            time.sleep(self.config['cmd_status_dt'])
            timestamp = datetime.utcnow().timestamp()
            dt = (timestamp - start_timestamp)
            #print(f'wintercmd: wait time so far = {dt}')
            if dt > timeout:
                raise TimeoutError(f'command timed out after {timeout} seconds before completing')
            
            stop_condition = (self.state['mount_az_is_enabled'])
            # do this in 2 steps. first shift the buffer forward (up to the last one. you end up with the last element twice)
            stop_condition_buffer[:-1] = stop_condition_buffer[1:]
            # now replace the last element
            stop_condition_buffer[-1] = stop_condition
            
            if all(entry == condition for entry in stop_condition_buffer):
                break    
        
        
    @cmd
    def mount_az_off(self):
        self.defineCmdParser('turn off az motor')
        self.telescope.mount_disable(0)
        
        """
        time.sleep(self.config.get('cmd_waittime', 1.0))
        while self.state['mount_az_is_enabled']:
            time.sleep(self.config['cmd_status_dt'])
        """
        ## Wait until end condition is satisfied, or timeout ##
        condition = True
        timeout = 5.0
        # wait for the telescope to stop moving before returning
        # create a buffer list to hold several samples over which the stop condition must be true
        n_buffer_samples = self.config.get('cmd_satisfied_N_samples')
        stop_condition_buffer = [(not condition) for i in range(n_buffer_samples)]

        # get the current timestamp
        start_timestamp = datetime.utcnow().timestamp()
        while True:
            QtCore.QCoreApplication.processEvents()
            #print('entering loop')
            time.sleep(self.config['cmd_status_dt'])
            timestamp = datetime.utcnow().timestamp()
            dt = (timestamp - start_timestamp)
            #print(f'wintercmd: wait time so far = {dt}')
            if dt > timeout:
                raise TimeoutError(f'command timed out after {timeout} seconds before completing')
            
            stop_condition = (self.state['mount_az_is_enabled'] == False)
            # do this in 2 steps. first shift the buffer forward (up to the last one. you end up with the last element twice)
            stop_condition_buffer[:-1] = stop_condition_buffer[1:]
            # now replace the last element
            stop_condition_buffer[-1] = stop_condition
            
            if all(entry == condition for entry in stop_condition_buffer):
                break   
        
            
    @cmd
    def mount_alt_on(self):
        self.defineCmdParser('turn on alt motor')
        self.telescope.mount_enable(1)
        """
        time.sleep(self.config.get('cmd_waittime', 1.0))
        while not self.state['mount_az_is_enabled']:
            time.sleep(self.config['cmd_status_dt'])
        """
        ## Wait until end condition is satisfied, or timeout ##
        condition = True
        timeout = 5.0
        # wait for the telescope to stop moving before returning
        # create a buffer list to hold several samples over which the stop condition must be true
        n_buffer_samples = self.config.get('cmd_satisfied_N_samples')
        stop_condition_buffer = [(not condition) for i in range(n_buffer_samples)]

        # get the current timestamp
        start_timestamp = datetime.utcnow().timestamp()
        while True:
            QtCore.QCoreApplication.processEvents()
            #print('entering loop')
            time.sleep(self.config['cmd_status_dt'])
            timestamp = datetime.utcnow().timestamp()
            dt = (timestamp - start_timestamp)
            #print(f'wintercmd: wait time so far = {dt}')
            if dt > timeout:
                raise TimeoutError(f'command timed out after {timeout} seconds before completing')
            
            stop_condition = (self.state['mount_alt_is_enabled'] == True)
            # do this in 2 steps. first shift the buffer forward (up to the last one. you end up with the last element twice)
            stop_condition_buffer[:-1] = stop_condition_buffer[1:]
            # now replace the last element
            stop_condition_buffer[-1] = stop_condition
            
            if all(entry == condition for entry in stop_condition_buffer):
                break   

    @cmd
    def mount_alt_off(self):
        self.defineCmdParser('turn off alt motor')
        self.telescope.mount_disable(1)
        """
        time.sleep(self.config.get('cmd_waittime', 1.0))
        while self.state['mount_alt_is_enabled']:
            time.sleep(self.config['cmd_status_dt'])
        """
        ## Wait until end condition is satisfied, or timeout ##
        condition = True
        timeout = 5.0
        # wait for the telescope to stop moving before returning
        # create a buffer list to hold several samples over which the stop condition must be true
        n_buffer_samples = self.config.get('cmd_satisfied_N_samples')
        stop_condition_buffer = [(not condition) for i in range(n_buffer_samples)]

        # get the current timestamp
        start_timestamp = datetime.utcnow().timestamp()
        while True:
            QtCore.QCoreApplication.processEvents()
            #print('entering loop')
            time.sleep(self.config['cmd_status_dt'])
            timestamp = datetime.utcnow().timestamp()
            dt = (timestamp - start_timestamp)
            #print(f'wintercmd: wait time so far = {dt}')
            if dt > timeout:
                raise TimeoutError(f'command timed out after {timeout} seconds before completing')
            
            stop_condition = (self.state['mount_alt_is_enabled'] == False)
            # do this in 2 steps. first shift the buffer forward (up to the last one. you end up with the last element twice)
            stop_condition_buffer[:-1] = stop_condition_buffer[1:]
            # now replace the last element
            stop_condition_buffer[-1] = stop_condition
            
            if all(entry == condition for entry in stop_condition_buffer):
                break 

    @cmd
    def mount_stop(self):
        self.defineCmdParser('STOP TELESCOPE MOTION')
        self.telescope.mount_stop()

    @cmd
    def mount_home(self):
        self.defineCmdParser('point telescope mount to home position')
        alt_degs = (self.config['telescope']['home_alt_degs'])
        az_degs = self.config['telescope']['home_az_degs']
        self.logger.info(f'slewing to home: ALT = {alt_degs}, AZ = {az_degs}')
        self.telescope.mount_goto_alt_az(alt_degs = alt_degs, az_degs = az_degs)
        
        # wait for the telescope to stop moving before returning
        ## Wait until end condition is satisfied, or timeout ##
        condition = True
        timeout = 200
        # wait for the telescope to stop moving before returning
        # create a buffer list to hold several samples over which the stop condition must be true
        n_buffer_samples = self.config.get('cmd_satisfied_N_samples')
        stop_condition_buffer = [(not condition) for i in range(n_buffer_samples)]

        # get the current timestamp
        start_timestamp = datetime.utcnow().timestamp()
        while True:
            QtCore.QCoreApplication.processEvents()
            #print('entering loop')
            time.sleep(self.config['cmd_status_dt'])
            timestamp = datetime.utcnow().timestamp()
            dt = (timestamp - start_timestamp)
            #print(f'wintercmd: wait time so far = {dt}')
            if dt > timeout:
                raise TimeoutError(f'command timed out after {timeout} seconds before completing')
            
            stop_condition = (self.state['mount_is_slewing'] == False)
            # do this in 2 steps. first shift the buffer forward (up to the last one. you end up with the last element twice)
            stop_condition_buffer[:-1] = stop_condition_buffer[1:]
            # now replace the last element
            stop_condition_buffer[-1] = stop_condition
            
            if all(entry == condition for entry in stop_condition_buffer):
                break 
       
        self.logger.info(f'Telescope Homing complete')
        
    @cmd
    def mount_shutdown(self):

        self.defineCmdParser('shut down the mount safely')
        # always manage the rotator first!
        self.mount_tracking_off()
        self.parse('rotator_home')
        self.mount_home()
        self.mount_az_off()
        self.mount_alt_off()
        self.parse('rotator_disable')
        self.mount_disconnect()


    @cmd
    def mount_startup(self):
        self.defineCmdParser('connect and home the mount')
        self.mount_connect()
        self.mount_tracking_off()
        self.parse('rotator_enable')
        self.parse('rotator_home')
        #time.sleep(self.config['cmd_status_dt'])
        self.mount_az_on()
        #time.sleep(self.config['cmd_status_dt'])
        self.mount_alt_on()
        #time.sleep(self.config['cmd_status_dt'])
        self.mount_home()

    @cmd
    def mount_set_slew_time_constant(self):
        """Usage: mount_set_slew_time_constant <tau>"""
        self.defineCmdParser('set mount slew time constant')
        self.cmdparser.add_argument('tau',
                                    nargs = 1,
                                    action = None,
                                    type = float,
                                    help = '<tau_sec>')
        self.getargs()
        tau = self.args.tau[0]
        self.telescope.mount_set_slew_time_constant(tau)
        
    @cmd
    def mount_find_home(self):
        """Usage: mount_find_home"""
        self.defineCmdParser('find home')
        self.telescope.mount_find_home()
        
    @cmd
    def mount_fans_on(self):
        """Usage: mount_fans_on"""
        self.defineCmdParser('turn on telescope mount fans')
        self.telescope.fans_on()
        
    @cmd
    def mount_fans_off(self):
        """Usage: mount_fans_on"""
        self.defineCmdParser('turn off telescope mount fans')
        self.telescope.fans_off()
    
    @cmd
    def mount_goto_ra_dec_apparent(self):
        """Usage: mount_goto_ra_dec_apparent <ra> <dec>"""
        self.defineCmdParser('move telescope to specified apparent ra/dec')
        self.cmdparser.add_argument('position',
                                    nargs = 2,
                                    action = None,
                                    type = float,
                                    help = '<ra_hours> <dec_degs>')
        self.getargs()
        ra = self.args.position[0]
        dec = self.args.position[1]
        self.telescope.mount_goto_ra_dec_apparent(ra_hours = ra, dec_degs = dec)
        
        
        ## Wait until end condition is satisfied, or timeout ##
        condition = True
        timeout = 60.0
        # wait for the telescope to stop moving before returning
        # create a buffer list to hold several samples over which the stop condition must be true
        n_buffer_samples = self.config.get('cmd_satisfied_N_samples')
        stop_condition_buffer = [(not condition) for i in range(n_buffer_samples)]

        # get the current timestamp
        start_timestamp = datetime.utcnow().timestamp()
        while True:
            QtCore.QCoreApplication.processEvents()
            #print('entering loop')
            time.sleep(self.config['cmd_status_dt'])
            timestamp = datetime.utcnow().timestamp()
            dt = (timestamp - start_timestamp)
            #print(f'wintercmd: wait time so far = {dt}')
            if dt > timeout:
                raise TimeoutError(f'command timed out after {timeout} seconds before completing')
            
            stop_condition = ( (not self.state['mount_is_slewing']) & (abs(self.state['mount_az_dist_to_target']) < 0.1) & (abs(self.state['mount_alt_dist_to_target']) < 0.1))
            # do this in 2 steps. first shift the buffer forward (up to the last one. you end up with the last element twice)
            stop_condition_buffer[:-1] = stop_condition_buffer[1:]
            # now replace the last element
            stop_condition_buffer[-1] = stop_condition
            
            if all(entry == condition for entry in stop_condition_buffer):
                break    
       
        self.logger.info(f'Telescope Move complete')
        
    @cmd
    def mount_goto_ra_dec_j2000(self):
        """Usage: mount_goto_ra_dec_j2000 <ra> <dec>"""
        self.defineCmdParser('move telescope to specified j2000 ra (hours)/dec (deg) ')
        self.cmdparser.add_argument('position',
                                    nargs = 2,
                                    type = str,
                                    action = None,
                                    help = '<ra_hours> <dec_degs>')
        self.getargs()
        ra = self.args.position[0]
        dec = self.args.position[1]
        
        
        # allow the RA and DEC to be specified in multiple ways:
        # this allows you to specify the coords either as: 
        #     ra, dec = '05:34:30.52', '22:00:59.9'
        #     ra, dec = 5.57514, 22.0166            
        ra_obj = astropy.coordinates.Angle(ra, unit = u.hour)
        dec_obj = astropy.coordinates.Angle(dec, unit = u.deg)
        
        ra_hour = ra_obj.hour
        dec_deg = dec_obj.deg
        
        self.telescope.mount_goto_ra_dec_j2000(ra_hours = ra_hour, dec_degs = dec_deg)
        
        ## Wait until end condition is satisfied, or timeout ##
        condition = True
        timeout = 60.0
        # wait for the telescope to stop moving before returning
        # create a buffer list to hold several samples over which the stop condition must be true
        n_buffer_samples = self.config.get('cmd_satisfied_N_samples')
        stop_condition_buffer = [(not condition) for i in range(n_buffer_samples)]

        # get the current timestamp
        start_timestamp = datetime.utcnow().timestamp()
        self.logger.info(f'wintercmd: mount_goto_ra_dec_j2000 running in thread {threading.get_ident()}')
        while True:
            QtCore.QCoreApplication.processEvents()
            #print('entering loop')
            time.sleep(self.config['cmd_status_dt'])
            timestamp = datetime.utcnow().timestamp()
            dt = (timestamp - start_timestamp)
            #print(f'wintercmd: wait time so far = {dt}')
            if dt > timeout:
                raise TimeoutError(f'command timed out after {timeout} seconds before completing')
            """
            self.logger.info(f'wintercmd (thread {threading.get_ident()}: count = {self.state["count"]}')
            self.logger.info(f'wintercmd (thread {threading.get_ident()}: mount_is_slewing: {self.state["mount_is_slewing"]}')
            self.logger.info(f'wintercmd (thread {threading.get_ident()}: alt_dist_to_target: {self.state["mount_alt_dist_to_target"]}')
            self.logger.info(f'wintercmd (thread {threading.get_ident()}: az_dist_to_target: {self.state["mount_az_dist_to_target"]}')
            self.logger.info('')
            """
            az_dist_lim = 3
            alt_dist_lim = 0.5
            stop_condition = ( (not self.state['mount_is_slewing']) & (abs(self.state['mount_az_dist_to_target']) < az_dist_lim) & (abs(self.state['mount_alt_dist_to_target']) < alt_dist_lim))

            # do this in 2 steps. first shift the buffer forward (up to the last one. you end up with the last element twice)
            stop_condition_buffer[:-1] = stop_condition_buffer[1:]
            # now replace the last element
            stop_condition_buffer[-1] = stop_condition
            
            if all(entry == condition for entry in stop_condition_buffer):
                break    
        self.logger.info(f'Telescope Move complete')
    
    def mount_goto_ra_dec_j2000_rad(self):
        """Usage: mount_goto_ra_dec_j2000 <ra> <dec>"""
        self.defineCmdParser('move telescope to specified j2000 ra (rad)/dec (rad) ')
        self.cmdparser.add_argument('position',
                                    nargs = 2,
                                    action = None,
                                    type = float,
                                    help = '<ra_hours> <dec_degs>')
        self.getargs()
        ra_rad = self.args.position[0]
        dec_rad = self.args.position[1]
        
        # convert the ra and dec in radians to ra (hours) and dec (deg)
        ra_hours = astropy.coordinates.Angle(ra_rad * u.rad).hour
        dec_deg = astropy.coordinates.Angle(dec_rad * u.rad).deg
        
        
        self.telescope.mount_goto_ra_dec_j2000(ra_hours = ra_hours, dec_degs = dec_deg)
        
        ## Wait until end condition is satisfied, or timeout ##
        condition = True
        timeout = 60.0
        # wait for the telescope to stop moving before returning
        # create a buffer list to hold several samples over which the stop condition must be true
        n_buffer_samples = self.config.get('cmd_satisfied_N_samples')
        stop_condition_buffer = [(not condition) for i in range(n_buffer_samples)]

        # get the current timestamp
        start_timestamp = datetime.utcnow().timestamp()
        while True:
            QtCore.QCoreApplication.processEvents()
            #print('entering loop')
            time.sleep(self.config['cmd_status_dt'])
            timestamp = datetime.utcnow().timestamp()
            dt = (timestamp - start_timestamp)
            #print(f'wintercmd: wait time so far = {dt}')
            if dt > timeout:
                raise TimeoutError(f'command timed out after {timeout} seconds before completing')
            
            stop_condition = ( (not self.state['mount_is_slewing']) & (abs(self.state['mount_az_dist_to_target']) < 0.1) & (abs(self.state['mount_alt_dist_to_target']) < 0.1))

            # do this in 2 steps. first shift the buffer forward (up to the last one. you end up with the last element twice)
            stop_condition_buffer[:-1] = stop_condition_buffer[1:]
            # now replace the last element
            stop_condition_buffer[-1] = stop_condition
            
            if all(entry == condition for entry in stop_condition_buffer):
                break    
        self.logger.info(f'Telescope Move complete')
    
    
    @cmd
    def mount_goto_object(self):
        """ Usage: mount_goto_object <object_name> """
        # points to an object that is in the astropy object library
        # before slewing makes sure that the altitude and azimuth as viewed from palomar are okay unless its overridden
        self.defineCmdParser('move telescope to object from astropy catalog')
        self.cmdparser.add_argument('object_name',
                                    nargs = 1,
                                    action = None,
                                    type = str,
                                    help = '<object name>')
        
        # ADD AN OPTIONAL PATH COMMAND. 
        self.cmdparser.add_argument('--force', '-f',
                                    action = 'store_true',
                                    help = "<force move?>")
        
        self.getargs()
        #print(f'wintercmd: args = {self.args}')
        
        obj = self.args.object_name[0]
        force = self.args.force
        
        j2000_coords = astropy.coordinates.SkyCoord.from_name(obj, frame = 'icrs')
        j2000_ra_hours = j2000_coords.ra.hour
        j2000_dec_deg = j2000_coords.dec.deg
        
        obstime = astropy.time.Time(datetime.utcnow())
        lat = astropy.coordinates.Angle(self.config['site']['lat'])
        lon = astropy.coordinates.Angle(self.config['site']['lon'])
        height = self.config['site']['height'] * u.Unit(self.config['site']['height_units'])
                                        
        site = astropy.coordinates.EarthLocation(lat = lat, lon = lon, height = height)
        frame = astropy.coordinates.AltAz(obstime = obstime, location = site)
        local_coords = j2000_coords.transform_to(frame)
        local_alt_deg = local_coords.alt.deg
        local_az_deg = local_coords.az.deg
        
        in_view = (local_alt_deg >= self.config['telescope']['min_alt']) & (local_alt_deg <= self.config['telescope']['max_alt'])
        msg_list = [f'wintercmd: request to point to object: {obj} at (RA, DEC) j2000= ({j2000_ra_hours:0.3f} h, {j2000_dec_deg:0.3f} deg)']
        msg_list.append(f'coords in catalog format (RA [h:m:s], DEC [d:am:as]) j2000 = ({j2000_coords.ra.to_string(u.hour, sep = ":")}, {j2000_coords.dec.to_string(u.deg, sep = ":")})')
        msg_list.append(f'Current sky coords as viewed from Palomar: (Alt, Az) = ({local_alt_deg:0.3f} deg, {local_az_deg:0.3f} deg)')
        if in_view:
            msg_list.append(f'Object is in view! Sending mount_goto_j2000 command')
        else:
            if force:
                msg_list.append('Object IS NOT in view, but you said to FORCE OBSERVATION so sending mount_goto_j2000 command')
            else:
                msg_list.append('Object IS NOT in view. Will not execute move command')
        #msg = "\n".join(msg_list)
        for msg in msg_list:
            self.logger.info(msg)
            
        # SEND THE MOVE COMMAND
        cmd = f'mount_goto_ra_dec_j2000 {j2000_ra_hours} {j2000_dec_deg}'
        self.parse(cmd)
    
    
    def mount_dither_arcsec_radec(self):
        """Usage: mount_dither_arcsec_radec <ra_dist_arcsec> <dec_dist_arcsec>"""
        
        self.defineCmdParser('dither the mount by some arcseconds in ra and dec')
        self.cmdparser.add_argument('dist', nargs = 2, type = float, action = None,
                                    help = '<ra_dist_arcsec> <dec_dist_arcsec>')
        
        # optional argument to make the dither relative to the current position rather than to the offset=zero position
        self.cmdparser.add_argument('--relative', '-r',
                                    action = 'store_true',
                                    default = False,
                                    help = "<force move?>")
        self.getargs()
        #print(f'args = {self.args}')
        ra_dist_arcsec = self.args.dist[0]
        dec_dist_arcsec = self.args.dist[1]
        do_relative_offset = self.args.relative
        
        # Get the center coordinates
        ra0_j2000_hours = self.state['mount_ra_j2000_hours']
        dec0_j2000_deg = self.state['mount_dec_j2000_deg']
        
        # Now account for any previous dither/mount offset
        if do_relative_offset:
            ra_center_j2000_hours = ra0_j2000_hours
            dec_center_j2000_deg = dec0_j2000_deg
        else:
            ra_center_j2000_hours = ra0_j2000_hours - self.state["mount_offsets_ra_arcsec_total"]*(1/3600)*(24/360)
            dec_center_j2000_deg = dec0_j2000_deg - self.state["mount_offsets_dec_arcsec_total"]*(1/3600)
        
        start = astropy.coordinates.SkyCoord(ra = ra_center_j2000_hours*u.hour, 
                                             dec = dec_center_j2000_deg*u.deg)
        
        # figure out where to go
        offset_ra = ra_dist_arcsec *u.arcsecond
        offset_dec = dec_dist_arcsec * u.arcsecond
        end = start.spherical_offsets_by(offset_ra, offset_dec)
        #ra_j2000_hours_goal = end.ra.hour
        #dec_j2000_deg_goal = end.dec.deg
        
        # calculate the literal difference required by PWI4 mount_offset
        ra_delta_arcsec = end.ra.arcsecond - start.ra.arcsecond
        dec_delta_arcsec = end.dec.arcsecond - start.dec.arcsecond
        
        if do_relative_offset:
            ra_delta_arcsec_from_current = ra_delta_arcsec 
            dec_delta_arcsec_from_current = dec_delta_arcsec 
        else:
            ra_delta_arcsec_from_current = ra_delta_arcsec - self.state["mount_offsets_ra_arcsec_total"]
            dec_delta_arcsec_from_current = dec_delta_arcsec - self.state["mount_offsets_dec_arcsec_total"]
        # what is the total angular 3d distance to travel?
        sep = start.separation(end)
        
        # calculate the target alt/az
        obstime_mjd = self.ephem.state.get('mjd',0)
        obstime = astropy.time.Time(obstime_mjd, format = 'mjd', \
                                    location=self.ephem.site)
        frame = astropy.coordinates.AltAz(obstime = obstime, location = self.ephem.site)
        local_end_coords = end.transform_to(frame)
        goal_alt = local_end_coords.alt.deg
        goal_az = local_end_coords.az.deg
        
        
        if True:
            if do_relative_offset:
                self.logger.info('executing RELATIVE dither with respect to current mount position')
            else:
                self.logger.info('executing ABSOLUTE dither with respect to the zero-offset mount position')
            self.logger.info(f'executing dither: RA Dist = {ra_dist_arcsec:.6f}, Dec Dist = {dec_dist_arcsec:.6f}')
            self.logger.info(f'executing dither: RA Dist = {ra_dist_arcsec:.6f}, Dec Dist = {dec_dist_arcsec:.6f}')
            self.logger.info(f'literal differences to pass to PWI4 mount_offset')
            self.logger.info(f'ra delta   = {ra_delta_arcsec:>10.6f} arcsec ({ra_delta_arcsec/60.0:>6.3f} arcmin)')
            self.logger.info(f'dec delta = {dec_delta_arcsec:>10.6f} arcsec ({dec_delta_arcsec/60.0:>6.3f} arcmin)')
            
            self.logger.info(f'Alt/Az Coords: Current --> Finish')
            self.logger.info(f'Alt : {self.state["mount_alt_deg"]:>10.6f} --> {goal_alt:>10.6f} (deg)')
            self.logger.info(f'Az : {self.state["mount_az_deg"]:>10.6f} --> {goal_az:>10.6f} (deg)')

            self.logger.info(f'RA/Dec Coords: Start --> Finish')
            self.logger.info(f'ra : {start.ra.hour:>10.6f} --> {end.ra.hour:>10.6f} (hour)')
            self.logger.info(f'dec: {start.dec.deg:>10.6f} --> {end.dec.deg:>10.6f} (deg)')
            self.logger.info(f'separation = {sep.arcsecond:0.6f} arcsec')
        
        if ra_dist_arcsec != 0.0:
            self.parse(f'mount_offset ra add_arcsec {ra_delta_arcsec_from_current:.3f}')
        
        time.sleep(0.5)
        if dec_dist_arcsec != 0.0:
            self.parse(f'mount_offset dec add_arcsec {dec_delta_arcsec_from_current:.3f}')
        
        # now check to make sure it got to the right place
        if goal_alt < 35:
            threshold_arcsec = 5.0 # 1.0 #NPL 8-16-22: increased this to handle times where there is more rms pointing jitter, noticed this when pointing ~20 deg alt
        else:
            #threshold_arcsec = 1.0
            threshold_arcsec = 5.0 # 1.0 #NPL 6-27-23: increased to work with larger dithers (eg 600")
        # wait for the dist to target to be low and the ra/dec near what they're meant to be
        ## Wait until end condition is satisfied, or timeout ##
        condition = True
        timeout = 10.0
        # wait for the telescope to stop moving before returning
        # create a buffer list to hold several samples over which the stop condition must be true
        n_buffer_samples = self.config.get('cmd_satisfied_N_samples')
        stop_condition_buffer = [(not condition) for i in range(n_buffer_samples)]

        # get the current timestamp
        start_timestamp = datetime.utcnow().timestamp()
        while True:
            QtCore.QCoreApplication.processEvents()
            #print('entering loop')
            time.sleep(self.config['cmd_status_dt'])
            timestamp = datetime.utcnow().timestamp()
            dt = (timestamp - start_timestamp)
            #print(f'wintercmd: wait time so far = {dt}')
            
            #print(f"alt dist to target = {abs(self.state['mount_alt_dist_to_target'])}")
            #print(f"az dist to target  = {abs(self.state['mount_az_dist_to_target'])}")
            dist_to_target_low = ((not self.state['mount_is_slewing'])
                                      and (abs(self.state['mount_az_dist_to_target']) < threshold_arcsec)
                                      and (abs(self.state['mount_alt_dist_to_target']) < threshold_arcsec)
                                  )
           
            ra_dist_hours = abs(self.state['mount_ra_j2000_hours'] - end.ra.hour)
            ra_dist_arcsec = ra_dist_hours * (360/24.0) * 3600.0
            #print(f'ra dist to target = {ra_dist_arcsec:.2f} arcsec')
            ra_in_range = (ra_dist_arcsec < threshold_arcsec)
            
            dec_dist_deg = abs(self.state['mount_dec_j2000_deg'] - end.dec.deg)
            dec_dist_arcsec = dec_dist_deg * 3600.0
            #print(f'dec dist to target = {dec_dist_arcsec:.2f} arcsec')
            dec_in_range = (dec_dist_arcsec < threshold_arcsec)
            
            stop_condition = (dist_to_target_low and ra_in_range and dec_in_range)
            
            # do this in 2 steps. first shift the buffer forward (up to the last one. you end up with the last element twice)
            stop_condition_buffer[:-1] = stop_condition_buffer[1:]
            # now replace the last element
            stop_condition_buffer[-1] = stop_condition
            
            if all(entry == condition for entry in stop_condition_buffer):
                break    
            if dt > timeout:
                msg = f'wintercmd: mount dither timed out after {timeout} seconds before completing: ra_dist_arcsec = {ra_dist_arcsec}, dec_dist_arcsec = {dec_dist_arcsec}, '
                msg += f"dist to target arcsec (alt, az) = ({self.state['mount_az_dist_to_target']}, {self.state['mount_alt_dist_to_target']}"
                self.logger.info(msg)
                self.alertHandler.slack_log(msg)
                raise TimeoutError(f'command timed out after {timeout} seconds before completing')
        self.logger.info(f'Mount Offset complete')
        
    def mount_random_dither_arcsec(self):
        """Usage: mount_random_dither <step>"""        
        self.defineCmdParser("execute a random dither from within a ra-dec circle of radius <step> arcseconds")
        
        self.cmdparser.add_argument('step',
                                    type = float,
                                    action = None,
                                    help = "max dither radius in arcseconds",
                                    )
        self.cmdparser.add_argument('--minstep',
                                    type = float,
                                    nargs = 1,
                                    action = None,
                                    default = 0.0,
                                    help = "min dither radius in arcseconds",
                                    )
        self.getargs()
        
        #boxwidth = self.args.boxwidth
        #ra_dist_arcsec, dec_dist_arcsec = np.random.uniform(-boxwidth/2.0, boxwidth/2.0, 2)
        radius = abs(self.args.step)
        minradius = abs(self.args.minstep)
        
        if minradius >= radius:
            self.logger.info(f'min radius {minradius} is >= radius {radius}. setting to minradius to zero')
        
        
        radius = np.random.uniform(minradius, radius)
        theta = np.random.uniform(0, np.pi)
        ra_dist_arcsec = radius * np.cos(theta)
        dec_dist_arcsec = radius * np.sin(theta)
        
        self.parse(f'mount_dither_arcsec_radec {ra_dist_arcsec} {dec_dist_arcsec}')
        
        
    def mount_offset_arcsec(self):
        """Usage: mount_offset <axis> <arcmin> """
        # this is a handy wrapper around the more complicated mount_offset function below
        
        
        
        self.defineCmdParser('dither the mount in the specified axis by the specified arcminutes')
        self.cmdparser.add_argument('axis',
                                    nargs = 1,
                                    type = str,
                                    choices = ['ra', 'dec'],
                                    action = None,
                                    help = 'axis to dither: ra or dec',
                                    )
        self.cmdparser.add_argument('arcsec',
                                    nargs = 1,
                                    type = float,
                                    action = None,
                                    help = 'arcsec to dither')
        
        self.getargs()
        
        axis = self.args.axis[0]
        arcsec = self.args.arcsec[0]
        #arcsec = arcmin * 60.0
        """
        if axis == 'ra':
            arcmin = arcmin * (1/0.0667) # this is a stupid thing we have to do because the ra offset doesn't work right
        else:
            pass
        
        max_arcmin = 100*
        if arcmin > max_arcmin:
            self.logger.warning(f'wintercmd: MAX DITHER DISTANCE IS {max_arcmin} ARCMIN. RETURNING...')
            return
        """
        cmd = f'mount_offset {axis} add_arcsec {arcsec}'
        
        ra0_j2000_hours = self.state['mount_ra_j2000_hours']
        dec0_j2000_deg = self.state['mount_dec_j2000_deg']
        
        if axis == 'ra':
            delta_ra_hours = (arcsec * (1/60.0/60.0) * (24/360.0))
            delta_dec_deg = 0.0
        elif axis == 'dec':
            delta_ra_hours = 0.0
            delta_dec_deg = (arcsec/60.0/60.0)
        
        #print(f'delta_ra = {delta_ra_hours} hours, delta_dec = {delta_dec_deg}')
        ra_j2000_hours_goal = ra0_j2000_hours + delta_ra_hours
        dec_j2000_deg_goal = dec0_j2000_deg + delta_dec_deg
        #print(f'ra: {ra0_j2000_hours} --> {ra_j2000_hours_goal}')
        #print(f'dec: {dec0_j2000_deg} --> {dec_j2000_deg_goal}')
        #threshold_arcmin = 0.5
        threshold_arcsec = 1
        #threshold_hours = threshold_arcsec * (1/3600.0) * (24/360.0)

        # dispatch the command
        self.parse(cmd)
        
        
        # wait for the dist to target to be low and the ra/dec near what they're meant to be
        ## Wait until end condition is satisfied, or timeout ##
        condition = True
        timeout = 60.0
        # wait for the telescope to stop moving before returning
        # create a buffer list to hold several samples over which the stop condition must be true
        n_buffer_samples = self.config.get('cmd_satisfied_N_samples')
        stop_condition_buffer = [(not condition) for i in range(n_buffer_samples)]

        # get the current timestamp
        start_timestamp = datetime.utcnow().timestamp()
        while True:
            QtCore.QCoreApplication.processEvents()
            #print('entering loop')
            time.sleep(self.config['cmd_status_dt'])
            timestamp = datetime.utcnow().timestamp()
            dt = (timestamp - start_timestamp)
            #print(f'wintercmd: wait time so far = {dt}')
            
            #print(f"alt dist to target = {abs(self.state['mount_alt_dist_to_target'])}")
            #print(f"az dist to target  = {abs(self.state['mount_az_dist_to_target'])}")
            dist_to_target_low = ( (not self.state['mount_is_slewing']) & (abs(self.state['mount_az_dist_to_target']) < threshold_arcsec) & (abs(self.state['mount_alt_dist_to_target']) < threshold_arcsec) )
           
            ra_dist_hours = abs(self.state['mount_ra_j2000_hours'] - ra_j2000_hours_goal)
            ra_dist_arcsec = ra_dist_hours * (360/24.0) * 3600.0
            #print(f'ra dist to target = {ra_dist_arcsec:.2f} arcsec')
            ra_in_range = (ra_dist_arcsec < threshold_arcsec)
            
            dec_dist_deg = abs(self.state['mount_dec_j2000_deg'] - dec_j2000_deg_goal)
            dec_dist_arcsec = dec_dist_deg * 3600.0
            #print(f'dec dist to target = {dec_dist_arcsec:.2f} arcsec')
            dec_in_range = (dec_dist_arcsec < threshold_arcsec)
            
            stop_condition = (dist_to_target_low and ra_in_range and dec_in_range)
            
            # do this in 2 steps. first shift the buffer forward (up to the last one. you end up with the last element twice)
            stop_condition_buffer[:-1] = stop_condition_buffer[1:]
            # now replace the last element
            stop_condition_buffer[-1] = stop_condition
            
            if all(entry == condition for entry in stop_condition_buffer):
                break    
            if dt > timeout:
                msg = f'wintercmd: mount dither timed out after {timeout} seconds before completing: ra_dist_arcsec = {ra_dist_arcsec}, dec_dist_arcsec = {dec_dist_arcsec}, '
                msg += f"dist to target arcsec (alt, az) = ({self.state['mount_az_dist_to_target']}, {self.state['mount_alt_dist_to_target']}"
                self.logger.info(msg)
                self.alertHandler.slack_log(msg)
                raise TimeoutError(f'command timed out after {timeout} seconds before completing')
        self.logger.info(f'Mount Offset complete')
    
    @cmd
    def mount_dither(self):
        """Usage: mount_dither <axis> <arcmin> """
        # this is a handy wrapper around the more complicated mount_offset function below
        
        self.defineCmdParser('dither the mount in the specified axis by the specified arcminutes')
        self.cmdparser.add_argument('axis',
                                    nargs = 1,
                                    type = str,
                                    choices = ['ra', 'dec'],
                                    action = None,
                                    help = 'axis to dither: ra or dec',
                                    )
        self.cmdparser.add_argument('arcmin',
                                    nargs = 1,
                                    type = float,
                                    action = None,
                                    help = 'arcminutes to dither')
        
        self.getargs()
        
        axis = self.args.axis[0]
        arcmin = self.args.arcmin[0]
        arcsec = arcmin * 60.0
        
        if axis == 'ra':
            arcmin = arcmin * (1/0.0667) # this is a stupid thing we have to do because the ra offset doesn't work right
        else:
            pass
        
        max_arcmin = 100
        if arcmin > max_arcmin:
            self.logger.warning(f'wintercmd: MAX DITHER DISTANCE IS {max_arcmin} ARCMIN. RETURNING...')
            return
        
        cmd = f'mount_offset {axis} add_arcsec {arcsec}'
        
        ra0_j2000_hours = self.state['mount_ra_j2000_hours']
        dec0_j2000_deg = self.state['mount_dec_j2000_deg']
        
        ra_j2000_hours_goal = ra0_j2000_hours + (arcmin * (1/60.0) * (24/360.0))
        dec_j2000_deg_goal = dec0_j2000_deg + (arcmin/60.0)

        threshold_arcmin = 0.5
        threshold_hours = threshold_arcmin * (1/60.0) * (24/360.0)

        # dispatch the command
        self.parse(cmd)
        
        
        # wait for the dist to target to be low and the ra/dec near what they're meant to be
        ## Wait until end condition is satisfied, or timeout ##
        condition = True
        timeout = 60.0
        # wait for the telescope to stop moving before returning
        # create a buffer list to hold several samples over which the stop condition must be true
        n_buffer_samples = self.config.get('cmd_satisfied_N_samples')
        stop_condition_buffer = [(not condition) for i in range(n_buffer_samples)]

        # get the current timestamp
        start_timestamp = datetime.utcnow().timestamp()
        while True:
            QtCore.QCoreApplication.processEvents()
            #print('entering loop')
            time.sleep(self.config['cmd_status_dt'])
            timestamp = datetime.utcnow().timestamp()
            dt = (timestamp - start_timestamp)
            #print(f'wintercmd: wait time so far = {dt}')
            if dt > timeout:
                raise TimeoutError(f'command timed out after {timeout} seconds before completing')
            
            dist_to_target_low = ( (not self.state['mount_is_slewing']) & (abs(self.state['mount_az_dist_to_target']) < 0.1) & (abs(self.state['mount_alt_dist_to_target']) < 0.1) )
            ra_in_range = ((abs(self.state['mount_ra_j2000_hours']) - ra_j2000_hours_goal) < threshold_hours)
            dec_in_range = ((abs(self.state['mount_dec_j2000_deg']) - dec_j2000_deg_goal) < threshold_arcmin)
            stop_condition = dist_to_target_low & ra_in_range & dec_in_range
            
            # do this in 2 steps. first shift the buffer forward (up to the last one. you end up with the last element twice)
            stop_condition_buffer[:-1] = stop_condition_buffer[1:]
            # now replace the last element
            stop_condition_buffer[-1] = stop_condition
            
            if all(entry == condition for entry in stop_condition_buffer):
                break    
        self.logger.info(f'Mount Dither complete')
    
    @cmd
    def mount_offset(self):
        # this is a monster case structure because of how it's implemented in PWI4
        # Created, NPL 2-2-21, 
        #todo: THIS IS UNTESTED
        """Usage: mount_offset <axis> <action> <value>"""
        self.defineCmdParser('change mount offset for specified axis')

        helptxt = '<axis> <action> <value> where \n'
        helptxt += 'axis is one of [ra, dec, axis0/az, axis1/alt, path]\n'
        helptxt += 'action is one of [reset, stop_rate, add_arcsec, set_rate (arcseconds per seconds)]\n'
        helptxt += 'value is any float, but MUST be specified in all cases. does not matter for reset'
        self.cmdparser.add_argument('offset',
                                    nargs = 3,
                                    action = None,
                                    help = helptxt)
        
        self.getargs()
        # all args are strings
        axis = self.args.offset[0].lower()
        action = self.args.offset[1].lower()
        value = np.float(self.args.offset[2])
        #print(f'axis = {axis}, action = {action}, value = {value}')
        if axis == 'ra':
            if action == 'reset':
                self.telescope.mount_offset(ra_reset = value)
            elif action == 'stop_rate':
                self.telescope.mount_offset(ra_stop_rate = value)
            elif action == 'add_arcsec':
                self.telescope.mount_offset(ra_add_arcsec = value)
            elif action == 'set_rate':
                self.telescope.mount_offset(ra_set_rate_arcsec_per_sec = value)
        elif axis == 'dec':
            if action == 'reset':
                self.telescope.mount_offset(dec_reset = value)
            elif action == 'stop_rate':
                self.telescope.mount_offset(dec_stop_rate = value)
            elif action == 'add_arcsec':
                self.telescope.mount_offset(dec_add_arcsec = value)
            elif action == 'set_rate':
                self.telescope.mount_offset(dec_set_rate_arcsec_per_sec = value)
        elif axis in ['axis0','az']:
            if action == 'reset':
                self.telescope.mount_offset(axis0_reset = value)
            elif action == 'stop_rate':
                self.telescope.mount_offset(axis0_stop_rate = value)
            elif action == 'add_arcsec':
                self.telescope.mount_offset(axis0_add_arcsec = value)
            elif action == 'set_rate':
                self.telescope.mount_offset(axis0_set_rate_arcsec_per_sec = value)
        elif axis in ['axis1','alt']:
            if action == 'reset':
                self.telescope.mount_offset(axis1_reset = value)
            elif action == 'stop_rate':
                self.telescope.mount_offset(axis1_stop_rate = value)
            elif action == 'add_arcsec':
                self.telescope.mount_offset(axis1_add_arcsec = value)
            elif action == 'set_rate':
                self.telescope.mount_offset(axis1_set_rate_arcsec_per_sec = value)
        elif axis == 'path':
            if action == 'reset':
                self.telescope.mount_offset(path_reset = value)
            elif action == 'stop_rate':
                self.telescope.mount_offset(path_stop_rate = value)
            elif action == 'add_arcsec':
                self.telescope.mount_offset(path_add_arcsec = value)
            elif action == 'set_rate':
                self.telescope.mount_offset(path_set_rate_arcsec_per_sec = value)
        elif axis == 'transverse':
            if action == 'reset':
                self.telescope.mount_offset(transverse_reset = value)
            elif action == 'stop_rate':
                self.telescope.mount_offset(transverse_stop_rate = value)
            elif action == 'add_arcsec':
                self.telescope.mount_offset(transverse_add_arcsec = value)
            elif action == 'set_rate':
                self.telescope.mount_offset(transverse_set_rate_arcsec_per_sec = value)
    @cmd
    def mount_goto_alt_az(self):
        """Usage: mount_goto_alt_az <alt> <az>"""
        self.defineCmdParser('move telescope to specified alt/az in deg')
        self.cmdparser.add_argument('position',
                                    nargs = 2,
                                    action = None,
                                    type = float,
                                    help = '<alt_deg> <az_deg>')
        self.getargs()
        alt = self.args.position[0]
        az = self.args.position[1]
        self.telescope.mount_goto_alt_az(alt_degs = alt, az_degs = az)
        
        # estimate timeout
        delta_az_degs = self.state['mount_az_dist_to_target']/3600.0
        delta_alt_degs = self.state['mount_alt_dist_to_target']/3600.0
        
        ## Wait until end condition is satisfied, or timeout ##
        condition = True
        timeout = 60.0
        # wait for the telescope to stop moving before returning
        # create a buffer list to hold several samples over which the stop condition must be true
        n_buffer_samples = self.config.get('cmd_satisfied_N_samples')
        stop_condition_buffer = [(not condition) for i in range(n_buffer_samples)]

        # get the current timestamp
        start_timestamp = datetime.utcnow().timestamp()
        while True:
            QtCore.QCoreApplication.processEvents()
            #print('entering loop')
            time.sleep(self.config['cmd_status_dt'])
            timestamp = datetime.utcnow().timestamp()
            dt = (timestamp - start_timestamp)
            #print(f'wintercmd: wait time so far = {dt}')
            if dt > timeout:
                raise TimeoutError(f'command timed out after {timeout} seconds before completing')
            dist = ( (alt - self.state["mount_alt_deg"])**2 + (az - self.state["mount_az_deg"])**2 )**0.5
            """
            self.logger.info(f'wintercmd (thread {threading.get_ident()}: count = {self.state["count"]}')
            self.logger.info(f'wintercmd (thread {threading.get_ident()}: mount_is_slewing: {self.state["mount_is_slewing"]}')
            self.logger.info(f'wintercmd (thread {threading.get_ident()}: alt_dist_to_target: {self.state["mount_alt_dist_to_target"]}')
            self.logger.info(f'wintercmd (thread {threading.get_ident()}: az_dist_to_target: {self.state["mount_az_dist_to_target"]}')
            self.logger.info(f'wintercmd (thread {threading.get_ident()}: dist_to_target: {dist} deg')
            self.logger.info('')
            """
            stop_condition = ( (not self.state['mount_is_slewing']) & (abs(self.state['mount_az_dist_to_target']) < 0.1) & (abs(self.state['mount_alt_dist_to_target']) < 0.1) & (dist < 0.1))
            # do this in 2 steps. first shift the buffer forward (up to the last one. you end up with the last element twice)
            stop_condition_buffer[:-1] = stop_condition_buffer[1:]
            # now replace the last element
            stop_condition_buffer[-1] = stop_condition
            
            if all(entry == condition for entry in stop_condition_buffer):
                break    
       
        self.logger.info(f'Telescope Move complete')
    
    
    @cmd
    def mount_park(self):
        """
        Created: NPL 2-2-21
        #todo: this is untested
        """
        self.defineCmdParser('park the telescope mount')
        self.telescope.mount_park()
        
        ## Wait until end condition is satisfied, or timeout ##
        condition = True
        timeout = 5.0
        # wait for the telescope to stop moving before returning
        # create a buffer list to hold several samples over which the stop condition must be true
        n_buffer_samples = self.config.get('cmd_satisfied_N_samples')
        stop_condition_buffer = [(not condition) for i in range(n_buffer_samples)]

        # get the current timestamp
        start_timestamp = datetime.utcnow().timestamp()
        while True:
            QtCore.QCoreApplication.processEvents()
            #print('entering loop')
            time.sleep(self.config['cmd_status_dt'])
            timestamp = datetime.utcnow().timestamp()
            dt = (timestamp - start_timestamp)
            #print(f'wintercmd: wait time so far = {dt}')
            if dt > timeout:
                raise TimeoutError(f'command timed out after {timeout} seconds before completing')
            
            stop_condition = (self.state['mount_is_slewing'])
            # do this in 2 steps. first shift the buffer forward (up to the last one. you end up with the last element twice)
            stop_condition_buffer[:-1] = stop_condition_buffer[1:]
            # now replace the last element
            stop_condition_buffer[-1] = stop_condition
            
            if all(entry == condition for entry in stop_condition_buffer):
                break    
        
    @cmd
    def mount_set_park_here(self):
        """
        Make the current alt/az the park position
        Created: NPL 2-4-21
        """
        self.defineCmdParser('set current alt/az to park position')
        self.telescope.mount_set_park_here()
        # wait for the telescope park position to match the request
        # nevermind... that's not in the status dict
    
    @cmd
    def mount_tracking_on(self):
        """
        Created: NPL 2-2-21
        """
        self.defineCmdParser('turn ON the mount sky tracking')
        self.telescope.mount_tracking_on()
        ## Wait until end condition is satisfied, or timeout ##
        condition = True
        timeout = 5.0
        # wait for the telescope to stop moving before returning
        # create a buffer list to hold several samples over which the stop condition must be true
        n_buffer_samples = self.config.get('cmd_satisfied_N_samples')
        stop_condition_buffer = [(not condition) for i in range(n_buffer_samples)]

        # get the current timestamp
        start_timestamp = datetime.utcnow().timestamp()
        while True:
            QtCore.QCoreApplication.processEvents()
            #print('entering loop')
            time.sleep(self.config['cmd_status_dt'])
            timestamp = datetime.utcnow().timestamp()
            dt = (timestamp - start_timestamp)
            #print(f'wintercmd: wait time so far = {dt}')
            if dt > timeout:
                raise TimeoutError(f'command timed out after {timeout} seconds before completing')
            
            stop_condition = (self.state['mount_is_tracking'])
            # do this in 2 steps. first shift the buffer forward (up to the last one. you end up with the last element twice)
            stop_condition_buffer[:-1] = stop_condition_buffer[1:]
            # now replace the last element
            stop_condition_buffer[-1] = stop_condition
            
            if all(entry == condition for entry in stop_condition_buffer):
                break    
    
    @cmd
    def mount_tracking_off(self):
        """
        Created: NPL 2-4-21
        """
        self.defineCmdParser('turn OFF the mount sky tracking')
        self.telescope.mount_tracking_off()
        ## Wait until end condition is satisfied, or timeout ##
        condition = False
        timeout = 5.0
        # wait for the telescope to stop moving before returning
        # create a buffer list to hold several samples over which the stop condition must be true
        n_buffer_samples = self.config.get('cmd_satisfied_N_samples')
        stop_condition_buffer = [(not condition) for i in range(n_buffer_samples)]

        # get the current timestamp
        start_timestamp = datetime.utcnow().timestamp()
        while True:
            QtCore.QCoreApplication.processEvents()
            #print('entering loop')
            time.sleep(self.config['cmd_status_dt'])
            timestamp = datetime.utcnow().timestamp()
            dt = (timestamp - start_timestamp)
            #print(f'wintercmd: wait time so far = {dt}')
            if dt > timeout:
                raise TimeoutError(f'command timed out after {timeout} seconds before completing')
            
            stop_condition = (self.state['mount_is_tracking'])
            # do this in 2 steps. first shift the buffer forward (up to the last one. you end up with the last element twice)
            stop_condition_buffer[:-1] = stop_condition_buffer[1:]
            # now replace the last element
            stop_condition_buffer[-1] = stop_condition
            
            if all(entry == condition for entry in stop_condition_buffer):
                break 
    
    @cmd
    def mount_follow_tle(self):
        """
        Created: NPL 2-4-21
        #TODO: has not been tested
        """
        self.defineCmdParser('track a two line element (TLE) using the standard NORAD format ')
        self.cmdparser.add_argument('tle',
                                    nargs = '+',
                                    action = None,
                                    help = '<tle_line_1> <tle_line_2><tle_line_3> MUST USE QUOTES AROUND EACH LINE')
        self.getargs()
        tle_line_1 = self.args.tle[0]
        tle_line_2 = self.args.tle[1]
        tle_line_3 = self.args.tle[2]
        
        self.telescope.mount_follow_tle(tle_line_1, tle_line_2, tle_line_3)
        #print(f'L1 = {tle_line_1}\nL2 = {tle_line_2}\nL3 = {tle_line_3}')
    
    
    # Didn't port this stuff over yet:
    """
    def mount_radecpath_new(self):
        return self.request_with_status("/mount/radecpath/new")

    def mount_radecpath_add_point(self, jd, ra_j2000_hours, dec_j2000_degs):
        return self.request_with_status("/mount/radecpath/add_point", jd=jd, ra_j2000_hours=ra_j2000_hours, dec_j2000_degs=dec_j2000_degs)

    def mount_radecpath_apply(self):
        return self.request_with_status("/mount/radecpath/apply")

    def mount_custom_path_new(self, coord_type):
        return self.request_with_status("/mount/custom_path/new", type=coord_type)
        
    def mount_custom_path_add_point_list(self, points):
        lines = []
        for (jd, ra, dec) in points:
            line = "%.10f,%s,%s" % (jd, ra, dec)
            lines.append(line)

        data = "\n".join(lines).encode('utf-8')

        postdata = urlencode({'data': data}).encode()

        return self.request("/mount/custom_path/add_point_list", postdata=postdata)

    def mount_custom_path_apply(self):
        return self.request_with_status("/mount/custom_path/apply")
    """
    
    # Pointing Model Stuff
    @cmd
    def mount_model_add_point(self):
        """
        NPL: written 2-4-21
        #TODO: untested
        """
        self.defineCmdParser('add specified j2000 ra/dec position to pointing model')
        self.cmdparser.add_argument('position',
                                    nargs = 2,
                                    action = None,
                                    type = float,
                                    help = '<ra_hours> <dec_degs>')
        self.getargs()
        ra_j2000_hours = self.args.position[0]
        dec_j2000_degs = self.args.position[1]

        self.telescope.mount_model_add_point(ra_j2000_hours, dec_j2000_degs)

    @cmd
    def mount_model_clear_points(self):
        """
        NPL: written 2-4-21
        #TODO: untested
        """
        self.defineCmdParser('clear all points from pointing model')
        self.telescope.mount_model_clear_points()

    @cmd
    def mount_model_save_as_default(self):
        """
        NPL: written 2-4-21
        #TODO: untested
        """
        self.defineCmdParser('save pointing model as default')
        self.telescope.mount_model_save_as_default()
    
    @cmd
    def mount_model_save(self):
        """
        Created: NPL 2-4-21
        Saves to ~/Documents/PlaneWave Instrumenmts/PWI4/Mount
        """
        self.defineCmdParser('save the current pointing model to the specified file')
        self.cmdparser.add_argument('filename',
                                    nargs = 1,
                                    action = None,
                                    help = '<filepath>')
        
        self.getargs()
        filename = self.args.filename[0]
        # make sure the extension is .pxp
        filePath = pathlib.Path(filename)
        extension = filePath.suffix
        if extension != '.pxp':
            filename = filePath.with_suffix('.pxp')
        self.telescope.mount_model_save(filename)

    @cmd
    def mount_model_load(self):
        """
        Created: NPL 2-4-21
        #TODO: untested
        """
        self.defineCmdParser('load the current pointint model from the specified file')
        self.cmdparser.add_argument('filename',
                                    nargs = 1,
                                    action = None,
                                    help = '<filepath>')
        
        self.getargs()
        filename = self.args.filename[0]
        self.telescope.mount_model_load(filename)

    
    # Telescope Focuser Stuff
    
    
    @cmd
    def doFocusLoop(self):
        self.defineCmdParser('do a focus loop with current filter')
        
        # ADD AN OPTIONAL PATH COMMAND. 

        self.cmdparser.add_argument('-c', '--center',
                                    nargs = 1,
                                    action = None,
                                    default = 'here',
                                    help = "<center_of_sweep>")
        
        self.cmdparser.add_argument('-t', '--throw',
                                    nargs = 1,
                                    type = float,
                                    action = None,
                                    default = -1,
                                    help = "<total_throw>")
        
        self.cmdparser.add_argument('-n', '--nsteps',
                                    nargs = 1,
                                    type = int,
                                    default = -1,
                                    action = None,
                                    help = "<number_of_steps>")
        #def do_focusLoop(self, nom_focus = 'last', total_throw = 'default', nsteps = 'default',
        self.getargs()
        
        print(self.args)
        if type(self.args.center) is str:
            center = self.args.center
        else:
            center = float(self.args.center[0])
        if type(self.args.throw) is int:
            throw = self.args.throw
        else:
            throw = self.args.throw[0]
        if type(self.args.nsteps) is int:
            nsteps = self.args.nsteps
        else:
            nsteps = self.args.nsteps[0]
        
        print(f'center = {center}, type(center) = {type(center)}')
        
        if center == 'here':
            center = self.state['focuser_position']
        
        if throw == -1:
            throw = 'default'
        
        if nsteps == -1:
            nsteps = 'default'
        
        
        print(f'running focus loop with center = {center}, throw = {throw}, nsteps = {nsteps}')
        
        
        sigcmd = signalCmd('do_focusLoop', nom_focus = center, total_throw = throw, nsteps = nsteps)

        self.roboThread.newCommand.emit(sigcmd)
    
    @cmd
    def doFocusSeq(self):
        self.defineCmdParser('do a focus sequence on all active filters')
        sigcmd = signalCmd('do_focus_sequence')
        
        self.roboThread.newCommand.emit(sigcmd)
    
    @cmd
    def doFocusLoop_old(self):
        """
        Runs a focus loop for a given filter by taking a set of images and collecting the relative
        size of objects in the image. Will return focus to the optimal position.
        
        """
        
        self.defineCmdParser('retrieve whether or not a plot will be displayed based on img fwhm')
        self.cmdparser.add_argument('--noplot',
                                    action = 'store_true',
                                    default = False,
                                    help = '<position_steps>')
        self.cmdparser.add_argument('--fine',
                                    action = 'store_true',
                                    default = False,
                                    help = '<position_steps>')
        self.cmdparser.add_argument('--roborun',
                                    action = 'store_true',
                                    default = False,
                                    help = '<run_robotic_schedule>')
        self.cmdparser.add_argument('--roboruntest',
                                    action = 'store_true',
                                    default = False,
                                    help = '<run_robotic_schedule>')
        
        self.getargs()
        
        plotting = True
        fine = False
        roborun = False
        
        #print(f'args = {self.args}')
        #print(f'args.noplot = {self.args.noplot}')
        #print(f'args.fine = {self.args.fine}')
        
        if self.args.noplot:
            plotting = False
        else:
            plotting = True
            self.logger.info('wintercmd: doFocusLoop: I am showing a plot this time!')
        
        if self.args.roborun:
            roborun = True
            self.logger.info('wintercmd: doFocusLoop: I will run the robotic schedule when I am finished!')
        else:
            roborun = False
        
        if self.args.roboruntest:
            roboruntest = True
            self.logger.info('wintercmd: doFocusLoop: I will run the robotic schedule IN TEST MODE when I am finished!')
        else:
            roboruntest = False
        
        
        try:
            if self.args.fine:
                fine = True
            else:
                fine = False
                
        except Exception as e:
            self.logger.info(f'wintercmd: could not set fine focus option: {e}')
            fine = False
        images = []
        
        image_log_path = self.config['focus_loop_param']['image_log_path']
        
        current_filter = str(self.state['Viscam_Filter_Wheel_Position'])
        filt_numlist = {'1':'uband','2':'other2','3':'rband','4':'other4','5':'other5','6':'other6'}

        # Run the focus loop on the current filter
        loop = summerFocusLoop.Focus_loop(filt_numlist[current_filter], self.config, fine)
        
        filter_range = loop.return_Range()
        
        system = 'ccd'
        
        self.parse('mount_tracking_on')
        #self.parse('robo_set_obstype FOCUS')
        self.parse('ccd_set_exposure 10')
                
        try:
            for dist in filter_range:
                #Collimate and take exposure
                print(f"Focus image at position {dist}")
                self.telescope.focuser_goto(target = dist)
                time.sleep(2)
                self.parse('ccd_do_exposure')
                time.sleep(15)
                images.append(loop.return_Path())
                self.logger.info("focus image added to list")
                postImage_process = subprocess.Popen(args = ['python','plotLastImg.py'])
                time.sleep(5)
        except Exception as e:
            msg = f'wintercmd: could not set up {system} due to {e.__class__.__name__}, {e}'
            self.logger.warning(msg)
            
        #images_16 = loop.fits_64_to_16(self, images, filter_range)
        #images = ['/home/winter/data/images/20210730/SUMMER_20210729_225354_Camera0.fits','/home/winter/data/images/20210730/SUMMER_20210729_225417_Camera0.fits','/home/winter/data/images/20210730/SUMMER_20210729_225438_Camera0.fits','/home/winter/data/images/20210730/SUMMER_20210729_225500_Camera0.fits','/home/winter/data/images/20210730/SUMMER_20210729_225521_Camera0.fits','/home/winter/data/images/20210730/SUMMER_20210729_225542_Camera0.fits','/home/winter/data/images/20210730/SUMMER_20210729_225604_Camera0.fits']
        try:
            data = {'images': images, 'focuser_pos' : list(filter_range)}
            df = pd.DataFrame(data)
            df.to_csv(image_log_path + 'focusLoop' + self.state['mount_timestamp_utc'] + '.csv')
        
        except Exception as e:
            msg = f'wintercmd: Unable to save files to focus csv due to {e.__class__.__name__}, {e}'
            self.logger.warning(msg)
            
        system = 'focuser'
        
        
        try:
            #find the ideal focuser position
            self.logger.info('Focuser re-aligning at %s microns'%(filter_range[0]))
            self.telescope.focuser_goto(target = filter_range[0])
            loop.rate_images(images)
            #focuser_pos = filter_range[med_values.index(min(med_values))]
            
            xvals, yvals = loop.plot_focus_curve(plotting)
            focuser_pos = xvals[yvals.index(min(yvals))]
            self.logger.info('Focuser_going to final position at %s microns'%(focuser_pos))
            self.telescope.focuser_goto(target = focuser_pos)
                

        except FileNotFoundError as e:
            self.logger.warning(f"You are trying to modify a catalog file or an image with no stars , {e}")
            pass

        except Exception as e:
            msg = f'wintercmd: could not set up {system} due to {e.__class__.__name__}, {e}'
            self.logger.info(msg)
        
        try:
            if plotting:
                auth_config_file  = wsp_path + '/credentials/authentication.yaml'
                user_config_file = wsp_path + '/credentials/alert_list.yaml'
                alert_config_file = wsp_path + '/config/alert_config.yaml'

                auth_config  = yaml.load(open(auth_config_file) , Loader = yaml.FullLoader)
                user_config = yaml.load(open(user_config_file), Loader = yaml.FullLoader)
                alert_config = yaml.load(open(alert_config_file), Loader = yaml.FullLoader)

                alertHandler = alert_handler.AlertHandler(user_config, alert_config, auth_config)
            
                focus_plot = '/home/winter/data/plots_focuser/latest_focusloop.jpg'
                alertHandler.slack_postImage(focus_plot)
        
        except Exception as e:
            msg = f'wintercmd: Unable to post focus graph to slack due to {e.__class__.__name__}, {e}'
            self.logger.warning(msg)
        
        self.parse('mount_tracking_off')
        
        # start the robotic schedule executor when finished?
        if roborun:
            self.parse('robo_run')
            
        elif roboruntest:
            self.parse('robo_run_test')
        
        return focuser_pos
            
    @cmd
    def m2_focuser_enable(self):
        """
        Created: NPL 2-4-21
        """
        self.defineCmdParser('enable the m2 focus motor')
        self.telescope.focuser_enable()
        
        ## Wait until end condition is satisfied, or timeout ##
        condition = True
        timeout = 5
        # create a buffer list to hold several samples over which the stop condition must be true
        n_buffer_samples = self.config.get('cmd_satisfied_N_samples')
        stop_condition_buffer = [(not condition) for i in range(n_buffer_samples)]

        # get the current timestamp
        start_timestamp = datetime.utcnow().timestamp()
        while True:
            QtCore.QCoreApplication.processEvents()
            time.sleep(self.config['cmd_status_dt'])
            timestamp = datetime.utcnow().timestamp()
            dt = (timestamp - start_timestamp)
            #print(f'wintercmd: wait time so far = {dt}')
            if dt > timeout:
                raise TimeoutError(f'unable to enable M2 focuser: command timed out after {timeout} seconds before completing.')
            
            stop_condition = ( (self.state['focuser_is_enabled'] == 1) )
            # do this in 2 steps. first shift the buffer forward (up to the last one. you end up with the last element twice)
            stop_condition_buffer[:-1] = stop_condition_buffer[1:]
            # now replace the last element
            stop_condition_buffer[-1] = stop_condition
            
            if all(entry == condition for entry in stop_condition_buffer):
                self.logger.info(f'wintercmd: successfully enabled M2 focuser')
                break 
    
    @cmd
    def m2_focuser_disable(self):
        """
        Created: NPL 2-4-21
        """
        self.defineCmdParser('disable the m2 focus motor')
        self.telescope.focuser_disable()
        
        ## Wait until end condition is satisfied, or timeout ##
        condition = True
        timeout = 5
        # create a buffer list to hold several samples over which the stop condition must be true
        n_buffer_samples = self.config.get('cmd_satisfied_N_samples')
        stop_condition_buffer = [(not condition) for i in range(n_buffer_samples)]

        # get the current timestamp
        start_timestamp = datetime.utcnow().timestamp()
        while True:
            QtCore.QCoreApplication.processEvents()
            time.sleep(self.config['cmd_status_dt'])
            timestamp = datetime.utcnow().timestamp()
            dt = (timestamp - start_timestamp)
            #print(f'wintercmd: wait time so far = {dt}')
            if dt > timeout:
                raise TimeoutError(f'unable to disable M2 focuser: command timed out after {timeout} seconds before completing.')
            
            stop_condition = ( (self.state['focuser_is_enabled'] == 0) )
            # do this in 2 steps. first shift the buffer forward (up to the last one. you end up with the last element twice)
            stop_condition_buffer[:-1] = stop_condition_buffer[1:]
            # now replace the last element
            stop_condition_buffer[-1] = stop_condition
            
            if all(entry == condition for entry in stop_condition_buffer):
                self.logger.info(f'wintercmd: successfully disabled M2 focuser')
                break 
    
    @cmd
    def m2_focuser_goto(self):
        """
        Created: NPL 2-4-21
        """
        self.defineCmdParser('send M2 focuser to specified position in steps')
        self.cmdparser.add_argument('position',
                                    nargs = 1,
                                    action = None,
                                    type = float,
                                    help = '<position_steps>')
        
        self.getargs()
        target = self.args.position[0]
        self.telescope.focuser_goto(target = target)
        
        ## Wait until end condition is satisfied, or timeout ##
        condition = True
        timeout = 15
        # create a buffer list to hold several samples over which the stop condition must be true
        n_buffer_samples = self.config.get('cmd_satisfied_N_samples')
        stop_condition_buffer = [(not condition) for i in range(n_buffer_samples)]

        # get the current timestamp
        start_timestamp = datetime.utcnow().timestamp()
        while True:
            QtCore.QCoreApplication.processEvents()
            time.sleep(self.config['cmd_status_dt'])
            timestamp = datetime.utcnow().timestamp()
            dt = (timestamp - start_timestamp)
            #print(f'wintercmd: wait time so far = {dt}')
            if dt > timeout:
                raise TimeoutError(f'unable to goto M2 focuser position: requested pos = {target}, actual pos = {self.state["focuser_position"]}, command timed out after {timeout} seconds before completing.')
            
            stop_condition = ( np.abs(self.state['focuser_position'] - target) < 1 )
            # do this in 2 steps. first shift the buffer forward (up to the last one. you end up with the last element twice)
            stop_condition_buffer[:-1] = stop_condition_buffer[1:]
            # now replace the last element
            stop_condition_buffer[-1] = stop_condition
            
            if all(entry == condition for entry in stop_condition_buffer):
                self.logger.info(f'wintercmd: successfully completed M2 focuser goto')
                break 
    
    @cmd
    def m2_focuser_stop(self):
        """
        Created: NPL 2-4-21
        """
        self.defineCmdParser('stop the m2 focus motor')
        self.telescope.focuser_stop()
    
    # Telescope Rotator Stuff
    @cmd
    def rotator_enable(self):
        """
        Created: NPL 2-4-21
        """
        self.defineCmdParser('enable the instrument rotator')
        self.telescope.rotator_enable()
        
        ## Wait until end condition is satisfied, or timeout ##
        condition = True
        timeout = 5.0
        # wait for the telescope to stop moving before returning
        # create a buffer list to hold several samples over which the stop condition must be true
        n_buffer_samples = self.config.get('cmd_satisfied_N_samples')
        stop_condition_buffer = [(not condition) for i in range(n_buffer_samples)]

        # get the current timestamp
        start_timestamp = datetime.utcnow().timestamp()
        while True:
            QtCore.QCoreApplication.processEvents()
            #print('entering loop')
            time.sleep(self.config['cmd_status_dt'])
            timestamp = datetime.utcnow().timestamp()
            dt = (timestamp - start_timestamp)
            #print(f'wintercmd: wait time so far = {dt}')
            if dt > timeout:
                raise TimeoutError(f'command timed out after {timeout} seconds before completing')
            
            stop_condition = (self.state['rotator_is_enabled'])
            # do this in 2 steps. first shift the buffer forward (up to the last one. you end up with the last element twice)
            stop_condition_buffer[:-1] = stop_condition_buffer[1:]
            # now replace the last element
            stop_condition_buffer[-1] = stop_condition
            
            if all(entry == condition for entry in stop_condition_buffer):
                break    
        
        
    @cmd
    def rotator_disable(self):
        """
        Created: NPL 2-4-21
        """
        self.defineCmdParser('disable the instrument rotator')
        self.telescope.rotator_disable()
        
        ## Wait until end condition is satisfied, or timeout ##
        condition = True
        timeout = 5.0
        # wait for the telescope to stop moving before returning
        # create a buffer list to hold several samples over which the stop condition must be true
        n_buffer_samples = self.config.get('cmd_satisfied_N_samples')
        stop_condition_buffer = [(not condition) for i in range(n_buffer_samples)]

        # get the current timestamp
        start_timestamp = datetime.utcnow().timestamp()
        while True:
            QtCore.QCoreApplication.processEvents()
            #print('entering loop')
            time.sleep(self.config['cmd_status_dt'])
            timestamp = datetime.utcnow().timestamp()
            dt = (timestamp - start_timestamp)
            #print(f'wintercmd: wait time so far = {dt}')
            if dt > timeout:
                raise TimeoutError(f'command timed out after {timeout} seconds before completing')
            
            stop_condition = (self.state['mount_az_is_enabled'])
            # do this in 2 steps. first shift the buffer forward (up to the last one. you end up with the last element twice)
            stop_condition_buffer[:-1] = stop_condition_buffer[1:]
            # now replace the last element
            stop_condition_buffer[-1] = stop_condition
            
            if all(entry == condition for entry in stop_condition_buffer):
                break    
        
        
    @cmd
    def rotator_goto_mech(self):
        """
        Created: NPL 2-4-21
        """
        self.defineCmdParser('turn instrument rotator to specified mechanical position')
        self.cmdparser.add_argument('position',
                                    nargs = 1,
                                    action = None,
                                    help = '<target_degs>')
        
        self.getargs()
        target = float(self.args.position[0])
        self.logger.info(f'wintercmd rotator_goto_mech (thread {threading.get_ident()}): target = {target}, type(target) = {type(target)}')
        self.telescope.rotator_goto_mech(target_degs = target)
        
        
        ## Wait until end condition is satisfied, or timeout ##
        condition = True
        timeout = 25.0
        # wait for the telescope to stop moving before returning
        # create a buffer list to hold several samples over which the stop condition must be true
        n_buffer_samples = self.config.get('cmd_satisfied_N_samples')
        stop_condition_buffer = [(not condition) for i in range(n_buffer_samples)]

        # get the current timestamp
        start_timestamp = datetime.utcnow().timestamp()
        while True:
            QtCore.QCoreApplication.processEvents()
            """
            if self.telescope.wrap_status:
                # the rotator is wrapping!
                raise WrapError(f'command rotator_goto_mech exited because rotator is wrapping!')
            """
            #print('entering loop')
            #time.sleep(self.config['cmd_status_dt'])
            QtCore.QThread.msleep(int(self.config['cmd_status_dt']*1000))
            timestamp = datetime.utcnow().timestamp()
            dt = (timestamp - start_timestamp)
            #print(f'wintercmd: wait time so far = {dt}')
            if dt > timeout:
                raise TimeoutError(f'command timed out after {timeout} seconds before completing')
            
            stop_condition = (self.state['rotator_is_slewing'] == False) & (np.abs(self.state['rotator_mech_position'] - target) < 0.05)
            # do this in 2 steps. first shift the buffer forward (up to the last one. you end up with the last element twice)
            stop_condition_buffer[:-1] = stop_condition_buffer[1:]
            # now replace the last element
            stop_condition_buffer[-1] = stop_condition
            
            if all(entry == condition for entry in stop_condition_buffer):
                break 
        self.logger.info(f'wintercmd: rotator move complete')
        
    @cmd
    def rotator_home(self):
        """
        Created: NPL 5-10-21
        Send the rotator to the home position
        """
        angle = self.config['telescope']['rotator_home_degs']
        cmd = f'rotator_goto_mech {angle}'
        self.parse(cmd)
        
    @cmd
    def rotator_wrap_check_enable(self):
        """
        Created: NPL 5-1-21
        Enable the wrap prevention check in the telescope
        """
        self.telescope.enable_wrap_check()
        ## Wait until end condition is satisfied, or timeout ##
        condition = True
        timeout = 5.0
        # wait for the telescope to stop moving before returning
        # create a buffer list to hold several samples over which the stop condition must be true
        n_buffer_samples = self.config.get('cmd_satisfied_N_samples')
        stop_condition_buffer = [(not condition) for i in range(n_buffer_samples)]

        # get the current timestamp
        start_timestamp = datetime.utcnow().timestamp()
        while True:
            QtCore.QCoreApplication.processEvents()
            #print('entering loop')
            time.sleep(self.config['cmd_status_dt'])
            timestamp = datetime.utcnow().timestamp()
            dt = (timestamp - start_timestamp)
            #print(f'wintercmd: wait time so far = {dt}')
            if dt > timeout:
                raise TimeoutError(f'command timed out after {timeout} seconds before completing')
            
            stop_condition = (self.telescope.state['rotator_wrap_check_enabled'] )
            # do this in 2 steps. first shift the buffer forward (up to the last one. you end up with the last element twice)
            stop_condition_buffer[:-1] = stop_condition_buffer[1:]
            # now replace the last element
            stop_condition_buffer[-1] = stop_condition
            
            if all(entry == condition for entry in stop_condition_buffer):
                break 
    
    @cmd
    def rotator_goto_field(self):
        """
        Created: NPL 2-4-21
        """
        self.defineCmdParser('turn instrument rotator to specified field angle')
        self.cmdparser.add_argument('position',
                                    nargs = 1,
                                    action = None,
                                    help = '<target_degs>')
        
        self.getargs()
        target = float(self.args.position[0])
        self.telescope.rotator_goto_field(target_degs = target)
        
        ## Wait until end condition is satisfied, or timeout ##
        condition = True
        timeout = 60.0
        # wait for the telescope to stop moving before returning
        # create a buffer list to hold several samples over which the stop condition must be true
        n_buffer_samples = self.config.get('cmd_satisfied_N_samples')
        stop_condition_buffer = [(not condition) for i in range(n_buffer_samples)]

        # get the current timestamp
        start_timestamp = datetime.utcnow().timestamp()
        while True:
            QtCore.QCoreApplication.processEvents()
            #print('entering loop')
            time.sleep(self.config['cmd_status_dt'])
            timestamp = datetime.utcnow().timestamp()
            dt = (timestamp - start_timestamp)
            #print(f'wintercmd: wait time so far = {dt}')
            if dt > timeout:
                raise TimeoutError(f'command timed out after {timeout} seconds before completing')
                
            # put the angle between 0-360
            rotator_field_angle_norm = np.mod(self.state['rotator_field_angle'], 360)
            target_norm = np.mod(target, 360)
            
            dist = np.mod(np.abs(rotator_field_angle_norm - target_norm), 360.0)
            #self.logger.info(f'rotator dist to target = {dist} deg, field angle (norm) = {rotator_field_angle_norm}, target (norm) = {target_norm}')
            
            stop_condition = ( (self.state['rotator_is_slewing'] == False) & (dist < 1.0) )
            # do this in 2 steps. first shift the buffer forward (up to the last one. you end up with the last element twice)
            stop_condition_buffer[:-1] = stop_condition_buffer[1:]
            # now replace the last element
            stop_condition_buffer[-1] = stop_condition
            
            if all(entry == condition for entry in stop_condition_buffer):
                break 
        self.logger.info(f'wintercmd: rotator move complete')
        
        
    @cmd
    def rotator_offset(self):
        """
        Created: NPL 2-4-21
        """
        self.defineCmdParser('set instrument rotator offset')
        self.cmdparser.add_argument('position',
                                    nargs = 1,
                                    action = None,
                                    help = '<target_degs>')
        
        self.getargs()
        target = self.args.position[0]
        self.telescope.rotator_offset(offset_degs = target)
    
    @cmd
    def rotator_stop(self):
        """
        Created: NPL 2-4-21
        """
        self.defineCmdParser('STOP the instrument rotator')
        self.telescope.rotator_stop()
    
    # M3 STUFF
    @cmd
    def m3_goto(self):
        """
        Created: NPL 2-4-21
        """
        self.defineCmdParser('set instrument rotator offset')
        self.cmdparser.add_argument('position',
                                    nargs = 1,
                                    action = None,
                                    help = '<target_port>')
        
        self.getargs()
        target_port = self.args.position[0]
        self.telescope.m3_goto(target_port = target_port)
    
    @cmd
    def m3_stop(self):
        """
        Created: NPL 2-4-21
        """
        self.defineCmdParser('STOP the M3 rotator')
        self.telescope.m3_stop()
    
    # Dome Commands
    @cmd
    def dome_home(self):
        """
        Created: NPL 3-18-21
        """
        
        self.defineCmdParser('Home the dome')
        
        sigcmd = signalCmd('Home')
        
        self.dome.newCommand.emit(sigcmd)
        

        ## Wait until end condition is satisfied, or timeout ##
        condition = True
        
        # wait for the telescope to stop moving before returning
        # create a buffer list to hold several samples over which the stop condition must be true
        n_buffer_samples = self.config.get('cmd_satisfied_N_samples')
        stop_condition_buffer = [(not condition) for i in range(n_buffer_samples)]

        # get the current timestamp
        start_timestamp = datetime.utcnow().timestamp()
        
        # wait for homing to start
        timeout = 20
        # need to split up the waiting. first we need to wait until the homing actually starts which is a while
        # if we don't wait it tends to return way before the homing actually starts
        while True:
            QtCore.QCoreApplication.processEvents()
            #print('entering loop')
            time.sleep(self.config['cmd_status_dt'])
            timestamp = datetime.utcnow().timestamp()
            dt = (timestamp - start_timestamp)
            #print(f'wintercmd: wait time so far = {dt}')
            if dt > timeout:
                raise TimeoutError(f'dome never started homing! waited {timeout} seconds')
            
            stop_condition = (self.state['dome_status'] == self.config['Dome_Status_Dict']['Dome_Status']['HOMING'])
            # do this in 2 steps. first shift the buffer forward (up to the last one. you end up with the last element twice)
            stop_condition_buffer[:-1] = stop_condition_buffer[1:]
            # now replace the last element
            stop_condition_buffer[-1] = stop_condition
            
            if all(entry == condition for entry in stop_condition_buffer):
                break    
        self.logger.info('wintercmd: dome has started homing routine')
        
        # wait for homing to complete
        timeout = 120.0
        while True:
            QtCore.QCoreApplication.processEvents()
            #print('entering loop')
            time.sleep(self.config['cmd_status_dt'])
            timestamp = datetime.utcnow().timestamp()
            dt = (timestamp - start_timestamp)
            #print(f'wintercmd: wait time so far = {dt}')
            if dt > timeout:
                raise TimeoutError(f'dome homing command timed out after {timeout} seconds before completing')
            
            stop_condition = (self.dome.Home_Status == 'READY') & (self.dome.Dome_Status == 'STOPPED')
            # do this in 2 steps. first shift the buffer forward (up to the last one. you end up with the last element twice)
            stop_condition_buffer[:-1] = stop_condition_buffer[1:]
            # now replace the last element
            stop_condition_buffer[-1] = stop_condition
            
            if all(entry == condition for entry in stop_condition_buffer):
                break    
        self.logger.info('wintercmd: finished homing dome')
        
    @cmd
    def dome_close(self):
        """
        created: NPL 3-18-21
        """
        self.defineCmdParser('Close the dome')
        sigcmd = signalCmd('Close')
        self.dome.newCommand.emit(sigcmd)
        
        ## Wait until end condition is satisfied, or timeout ##
        condition = True
        timeout = 100.0
        # wait for the telescope to stop moving before returning
        # create a buffer list to hold several samples over which the stop condition must be true
        n_buffer_samples = self.config.get('cmd_satisfied_N_samples')
        stop_condition_buffer = [(not condition) for i in range(n_buffer_samples)]

        # get the current timestamp
        start_timestamp = datetime.utcnow().timestamp()
        while True:
            QtCore.QCoreApplication.processEvents()
            #print('entering loop')
            time.sleep(self.config['cmd_status_dt'])
            timestamp = datetime.utcnow().timestamp()
            dt = (timestamp - start_timestamp)
            #print(f'wintercmd: wait time so far = {dt}')
            if dt > timeout:
                raise TimeoutError(f'command timed out after {timeout} seconds before completing')
            
            stop_condition = (self.dome.Shutter_Status == 'CLOSED')
            # do this in 2 steps. first shift the buffer forward (up to the last one. you end up with the last element twice)
            stop_condition_buffer[:-1] = stop_condition_buffer[1:]
            # now replace the last element
            stop_condition_buffer[-1] = stop_condition
            
            if all(entry == condition for entry in stop_condition_buffer):
                break 
        
        
    @cmd
    def dome_open(self):
        """
        created: NPL 3-18-21
        """
        self.defineCmdParser('Open the dome')
        sigcmd = signalCmd('Open')
        self.dome.newCommand.emit(sigcmd)
        
        ## Wait until end condition is satisfied, or timeout ##
        condition = True
        timeout = 100.0
        # wait for the telescope to stop moving before returning
        # create a buffer list to hold several samples over which the stop condition must be true
        n_buffer_samples = self.config.get('cmd_satisfied_N_samples')
        stop_condition_buffer = [(not condition) for i in range(n_buffer_samples)]

        # get the current timestamp
        start_timestamp = datetime.utcnow().timestamp()
        while True:
            QtCore.QCoreApplication.processEvents()
            #print('entering loop')
            time.sleep(self.config['cmd_status_dt'])
            timestamp = datetime.utcnow().timestamp()
            dt = (timestamp - start_timestamp)
            #print(f'wintercmd: wait time so far = {dt}')
            if dt > timeout:
                raise TimeoutError(f'command timed out after {timeout} seconds before completing')
            
            stop_condition = (self.dome.Shutter_Status == 'OPEN')
            # do this in 2 steps. first shift the buffer forward (up to the last one. you end up with the last element twice)
            stop_condition_buffer[:-1] = stop_condition_buffer[1:]
            # now replace the last element
            stop_condition_buffer[-1] = stop_condition
            
            if all(entry == condition for entry in stop_condition_buffer):
                break 
        
        
        
    @cmd
    def dome_stop(self):
        """
        created: NPL 3-18-21
        """
        self.defineCmdParser('Stop the dome')
        sigcmd = signalCmd('Stop')
        self.dome.newCommand.emit(sigcmd)
    
    @cmd
    def dome_takecontrol(self):
        """
        created: NPL 3-18-21
        """
        self.defineCmdParser('Take Remote Control of the Dome')
        sigcmd = signalCmd('TakeControl')
        self.dome.newCommand.emit(sigcmd)
        
        ## Wait until end condition is satisfied, or timeout ##
        condition = True
        timeout = 5.0
        # create a buffer list to hold several samples over which the stop condition must be true
        n_buffer_samples = self.config.get('cmd_satisfied_N_samples')
        stop_condition_buffer = [(not condition) for i in range(n_buffer_samples)]

        # get the current timestamp
        start_timestamp = datetime.utcnow().timestamp()
        while True:
            QtCore.QCoreApplication.processEvents()
            time.sleep(self.config['cmd_status_dt'])
            timestamp = datetime.utcnow().timestamp()
            dt = (timestamp - start_timestamp)
            #print(f'wintercmd: wait time so far = {dt}')
            if dt > timeout:
                raise TimeoutError(f'command timed out after {timeout} seconds before completing')
            
            stop_condition = (self.dome.Control_Status == 'REMOTE')
            # do this in 2 steps. first shift the buffer forward (up to the last one. you end up with the last element twice)
            stop_condition_buffer[:-1] = stop_condition_buffer[1:]
            # now replace the last element
            stop_condition_buffer[-1] = stop_condition
            
            if all(entry == condition for entry in stop_condition_buffer):
                break 
        
    @cmd
    def dome_givecontrol(self):
        """
        created: NPL 3-18-21
        """
        self.defineCmdParser('Give up remote control of the dome')
        sigcmd = signalCmd('GiveControl')
        self.dome.newCommand.emit(sigcmd)
        
        ## Wait until end condition is satisfied, or timeout ##
        condition = True
        timeout = 5.0
        # create a buffer list to hold several samples over which the stop condition must be true
        n_buffer_samples = self.config.get('cmd_satisfied_N_samples')
        stop_condition_buffer = [(not condition) for i in range(n_buffer_samples)]

        # get the current timestamp
        start_timestamp = datetime.utcnow().timestamp()
        while True:
            QtCore.QCoreApplication.processEvents()
            time.sleep(self.config['cmd_status_dt'])
            timestamp = datetime.utcnow().timestamp()
            dt = (timestamp - start_timestamp)
            #print(f'wintercmd: wait time so far = {dt}')
            if dt > timeout:
                raise TimeoutError(f'command timed out after {timeout} seconds before completing')
            
            stop_condition = (self.dome.Control_Status == 'AVAILABLE')
            # do this in 2 steps. first shift the buffer forward (up to the last one. you end up with the last element twice)
            stop_condition_buffer[:-1] = stop_condition_buffer[1:]
            # now replace the last element
            stop_condition_buffer[-1] = stop_condition
            
            if all(entry == condition for entry in stop_condition_buffer):
                break 
    
    @cmd
    def dome_goto(self):
        """
        created: NPL 3-18-21
        """
        self.defineCmdParser('send dome to specified azimuth')
        self.cmdparser.add_argument('azimuth',
                                    nargs = 1,
                                    action = None,
                                    help = '<azimuth_degs>')
        
        self.cmdparser.add_argument('--verbose', '-v',
                                    action = 'store_true',
                                    default = False,
                                    help = 'verbose')
        
        self.getargs()
            # this is what happens when called from the cmd line. otherwise include az so it can be called internally
        az = np.float(self.args.azimuth[0])
        sigcmd = signalCmd('GoTo', az)
        self.dome.newCommand.emit(sigcmd)
        
        verbose = self.args.verbose
        
        # estimated drivetime
        # this is from a study of a bunch of moves, move_time = delta_az/effective_speed = lag_time
        effective_speed = 3.33 #deg/sec
        lag_time = 9.0 #seconds
        
        delta = az - self.state['dome_az_deg']
                
        if np.abs(delta) >= 180.0:
            dist_to_go = 360-np.abs(delta)
        else:
            dist_to_go = np.abs(delta)

            
        drivetime = np.abs(dist_to_go)/effective_speed + lag_time# total time to move
        # now start "moving the dome" it stays moving for an amount of time
            # based on the dome speed and distance to move
        if verbose:
            self.logger.info(f'wintercmd: Estimated Dome Drivetime = {drivetime} s')
        
        #self.logger.info(f'self.state["dome_az_deg"] = {self.state["dome_az_deg"]}, type = {type(self.state["dome_az_deg"])}')
        #self.logger.info(f'az = {az}, type = {type(az)}')
        
        ## Wait until end condition is satisfied, or timeout ##
        condition = True
        nominal_timeout = drivetime * 1.5 # give the drivetime some overhead
        timeout = 300
        
        # create a buffer list to hold several samples over which the stop condition must be true
        n_buffer_samples = self.config.get('cmd_satisfied_N_samples')
        stop_condition_buffer = [(not condition) for i in range(n_buffer_samples)]

        # get the current timestamp
        start_timestamp = datetime.utcnow().timestamp()
        while True:
            QtCore.QCoreApplication.processEvents()
            time.sleep(self.config['cmd_status_dt'])
            timestamp = datetime.utcnow().timestamp()
            dt = (timestamp - start_timestamp)
            #print(f'wintercmd: wait time so far = {dt}')
            if dt > timeout:
                raise TimeoutError(f'command timed out after {timeout} seconds before completing')
            
            
            stop_condition = ( (self.state['dome_status'] == self.config['Dome_Status_Dict']['Dome_Status']['STOPPED']) and (np.abs(self.state['dome_az_deg'] - az ) < 0.5 ) )
            # do this in 2 steps. first shift the buffer forward (up to the last one. you end up with the last element twice)
            stop_condition_buffer[:-1] = stop_condition_buffer[1:]
            # now replace the last element
            stop_condition_buffer[-1] = stop_condition
            
            if all(entry == condition for entry in stop_condition_buffer):
                break 
        
        if dt > nominal_timeout:
            msg = f'Warning: Dome took {dt} s to move but it should have only taken {drivetime} s'
            self.logger.info(msg)
            self.alertHandler.slack_log(msg)
        if verbose:
            self.logger.info(f'wintercmd: actual dome drivetime = {dt} s')
        
    @cmd 
    def dome_go_home(self):
        """
        Created: NPL 4-22-21
        try to slew to the home position.
        if the dome doesn't know where it is, then home the dome first.
        then slew to home position
        """
        self.defineCmdParser('send dome to home azimuth')
        
        # check if the dome is homed
        if self.state['dome_home_status'] == 1:
            self.logger.info('dome is already homed')
            pass
            
        elif self.state['dome_home_status'] == 0:
            self.logger.info('dome needs to be homed')
            # the dome needs to be homed. home it:
            self.dome_home()
        
        # the dome is homed. now slew it:
        az = self.dome.home_az
        self.parse(f'dome_goto {az}')
        
        
        self.logger.info('wintercmd: dome_go_home complete')
        
        
    @cmd
    def dome_set_home(self):
        """ Created: NPL 4-22-21
        
        change the wsp value for the dome home position.
        
        this doesn't communicate anything to the dome, it just updates
        the value of dome.home_az
        """
        
        self.defineCmdParser('update dome home azimuth position')
        self.cmdparser.add_argument('azimuth',
                                    nargs = 1,
                                    action = None,
                                    help = '<azimuth_degs>')
        
        self.getargs()
        az = self.args.azimuth[0]
        sigcmd = signalCmd('SetHome', az)
        self.dome.newCommand.emit(sigcmd)
    
    @cmd
    def dome_tracking_on(self):
        """ created: NPL 6-12-21 
        turn on tracking so that dome follows telescope
        """
        self.defineCmdParser('make dome track telescope')
        sigcmd = signalCmd('TrackingOn')
        self.dome.newCommand.emit(sigcmd)
        
        ## Wait until end condition is satisfied, or timeout ##
        condition = True
        timeout = 5
        # create a buffer list to hold several samples over which the stop condition must be true
        n_buffer_samples = self.config.get('cmd_satisfied_N_samples')
        stop_condition_buffer = [(not condition) for i in range(n_buffer_samples)]

        # get the current timestamp
        start_timestamp = datetime.utcnow().timestamp()
        while True:
            QtCore.QCoreApplication.processEvents()
            time.sleep(self.config['cmd_status_dt'])
            timestamp = datetime.utcnow().timestamp()
            dt = (timestamp - start_timestamp)
            #print(f'wintercmd: wait time so far = {dt}')
            if dt > timeout:
                raise TimeoutError(f'unable to enable dome tracking: command timed out after {timeout} seconds before completing.')
            
            stop_condition = ( (self.state['dome_tracking_status'] == 1) )
            # do this in 2 steps. first shift the buffer forward (up to the last one. you end up with the last element twice)
            stop_condition_buffer[:-1] = stop_condition_buffer[1:]
            # now replace the last element
            stop_condition_buffer[-1] = stop_condition
            
            if all(entry == condition for entry in stop_condition_buffer):
                self.logger.info(f'wintercmd: successfully enabled dome tracking')
                break 
        
    @cmd
    def dome_tracking_off(self):
        """ created: NPL 6-12-21 
        turn on tracking so that dome follows telescope
        """
        self.defineCmdParser('stop making dome track telescope')
        sigcmd = signalCmd('TrackingOff')
        self.dome.newCommand.emit(sigcmd)
        
        ## Wait until end condition is satisfied, or timeout ##
        condition = True
        timeout = 5
        # create a buffer list to hold several samples over which the stop condition must be true
        n_buffer_samples = self.config.get('cmd_satisfied_N_samples')
        stop_condition_buffer = [(not condition) for i in range(n_buffer_samples)]

        # get the current timestamp
        start_timestamp = datetime.utcnow().timestamp()
        while True:
            QtCore.QCoreApplication.processEvents()
            time.sleep(self.config['cmd_status_dt'])
            timestamp = datetime.utcnow().timestamp()
            dt = (timestamp - start_timestamp)
            #print(f'wintercmd: wait time so far = {dt}')
            if dt > timeout:
                raise TimeoutError(f'unable to disable dome tracking: command timed out after {timeout} seconds before completing.')
            
            stop_condition = ( (self.state['dome_tracking_status'] == 0) )
            # do this in 2 steps. first shift the buffer forward (up to the last one. you end up with the last element twice)
            stop_condition_buffer[:-1] = stop_condition_buffer[1:]
            # now replace the last element
            stop_condition_buffer[-1] = stop_condition
            
            if all(entry == condition for entry in stop_condition_buffer):
                self.logger.info(f'wintercmd: successfully disabled dome tracking')
                break 
    
    @cmd
    def chiller_set_setpoint(self):
        """
        created: NPL 3-22-21
        """
        self.defineCmdParser('set the chiller setpoint')
        self.cmdparser.add_argument('temperature',
                                    nargs = 1,
                                    action = None,
                                    help = '<setpoint_celsius>')
        
        self.getargs()
        temp = np.float(self.args.temperature[0]) # remember the args come in as strings!!
        sigcmd = signalCmd('setSetpoint', temp)
        self.chiller.newCommand.emit(sigcmd)
    
    @cmd
    def chiller_write_register(self):
        """
        created: NPL 3-32-21
        allows you to send any value to a register on the approved write list from
        the chiller config
        """
        self.defineCmdParser('write value to register')
        self.cmdparser.add_argument('request',
                                    nargs = 2,
                                    action = None,
                                    help = "<regname> <value>")
        self.getargs()
        regname = self.args.request[0]
        val = np.float(self.args.request[1])
        sigcmd = signalCmd('WriteRegister', register = regname, value = val)
        self.chiller.newCommand.emit(sigcmd)
    
    @cmd
    def chiller_stop(self):
        """
        created: NPL 3-22-21
        """
        self.defineCmdParser('stop the chiller')
        sigcmd = signalCmd('TurnOff')
        self.chiller.newCommand.emit(sigcmd)
        
    @cmd
    def chiller_start(self):
        """
        created: NPL 3-22-21
        """
        self.defineCmdParser('start the chiller')
        sigcmd = signalCmd('TurnOn')
        self.chiller.newCommand.emit(sigcmd)
    
    # FPA 12V Power Switching
    @cmd
    def fpa(self):
        """
        created: NPL 8-11-23
        This will turn on or off the 12V power supplies that power each 
        half of the WINTER focal planes. This is a convenience function that
        makes the power "on" or "off" behave more logically than directly calling
        the labjack dio functions, since for these power supplies, turning
        the digital line "on" turns the power supply off.
        
        call it like this:
            fpa <action> <addr>
            where action is one of ['on', 'off']
            and addr is one of ['port', 'star', ''] where '' corresponds to
            applying the action to all supplies. 
            In the future hopefully we will be able  to pass single channel
            addresses like 'pa' to this function
            
        """
        self.defineCmdParser('turn on or off the 12v power supply for the winter FPAs')
        self.cmdparser.add_argument('action',
                                    nargs = 1,
                                    action = None,
                                    type = str,
                                    choices = ['on', 'off'],
                                    )
        
        self.cmdparser.add_argument('channel',
                                    nargs = 1,
                                    action = None,
                                    type = str,
                                    default = 'all',
                                    )
        
        
        
        self.getargs()
        if self.verbose:
            print(self.args)
        
        action = self.args.action[0]
        
        if action.lower() == 'on':
            lj_action = 'off'
        elif action.lower() == 'off':
            lj_action = 'on'
        else:
            self.logger.info(f'invalid action: {action}. returning')
            return
        
            
        channels = self.args.channel
        
        if self.verbose:
            self.logger.info(f'setting fpa power for {channels} to {action}')
        
        if channels == 'all':
            channels = ['port', 'star']
        
        for channel in channels:
            lj_channel = f'fpa_{channel}'
            self.parse(f'lj_dio {lj_action} {lj_channel}')
            
    # Labjack Power Switching
    @cmd
    def lj_dio(self):
        """
        created: NPL 8-10-23
        
        this turns on a channel on the specified labjack
        
        example calls: 
            lj_dio on LJ0 FIO5
            lj_dio off fpa_port

        """
        
        self.defineCmdParser('send on or off command to labjack digital output')
        
        self.cmdparser.add_argument('action',
                                    nargs = 1,
                                    action = None,
                                    type = str,
                                    choices = ['on', 'off'],
                                    )
        
        self.cmdparser.add_argument('channel',
                                    nargs = '*',
                                    action = None,
                                    type = str,
                                    )
        
        
        
        self.getargs()
        if self.verbose:
            print(self.args)
        
        action = self.args.action[0]
        
        
            
        channel = self.args.channel
        
        if self.verbose:
            print(f'lj command, action = {action}, channel = {channel}')
        
        sigcmd = signalCmd('dio_do', action = action, outlet_specifier = channel)
        self.labjacks.newCommand.emit(sigcmd)
    
    @cmd
    def pdu(self):
        """
        created: NPL 6-7-21
        
        this turns on a channel on the specified PDU
        
        call: pdu_on 1 8, turns on ch 8 on pdu 1

        """
        
        self.defineCmdParser('send command to a pdu')
        
        self.cmdparser.add_argument('action',
                                    nargs = 1,
                                    action = None,
                                    type = str,
                                    choices = ['on', 'off', 'cycle'],
                                    )
        
        self.cmdparser.add_argument('channel',
                                    nargs = '*',
                                    action = None,
                                    type = str,
                                    )
        
        
        
        self.getargs()
        if self.verbose:
            print(self.args)
        
        action = self.args.action[0]
        
        
            
        channel = self.args.channel
        
        if self.verbose:
            print(f'pdu command, action = {action}, channel = {channel}')
        
        sigcmd = signalCmd('pdu_do', action = action, outlet_specifier = channel)
        self.powerManager.newCommand.emit(sigcmd)
         
    @cmd
    def pdu_off(self):
        """
        created: NPL 6-7-21
        
        this turns on a channel on the specified PDU
        
        call: pdu_on 1 8, turns on ch 8 on pdu 1

        """
        
        self.defineCmdParser('turn off specified outlet on specified pdu')
        self.cmdparser.add_argument('channel',
                                    nargs = 2,
                                    #type = int,
                                    action = None,
                                    help = "<pdu_num> <chan_num>")
        self.getargs()
        pdu_num = int(self.args.channel[0])
        chan_num = self.args.channel[1]
        
        # send the off command
        active_pdus = [1,2]
        if pdu_num in active_pdus:
            pduname = f'pdu{pdu_num}'
            
            sigcmd = signalCmd('pdu_off', pduname = pduname, outlet = chan_num)
            self.powerManager.newCommand.emit(sigcmd)
        else:
            self.logger.info(f'right now PDU numbers are hardcoded, and only {active_pdus} are active')
             
    @cmd
    def pdu_cycle(self):
        """
        created: NPL 6-7-21
        
        this turns on a channel on the specified PDU
        
        call: pdu_on 1 8, turns on ch 8 on pdu 1

        """
        
        self.defineCmdParser('cycle specified outlet on specified pdu')
        self.cmdparser.add_argument('channel',
                                    nargs = 2,
                                    type = int,
                                    action = None,
                                    help = "<pdu_num> <chan_num>")
        self.getargs()
        pdu_num = self.args.channel[0]
        chan_num = self.args.channel[1]
        
        # send the off command
        active_pdus = [1,2]
        if pdu_num in active_pdus:
            pduname = f'pdu{pdu_num}'
            
            sigcmd = signalCmd('pdu_cycle', pduname = pduname, outlet = chan_num)
            self.powerManager.newCommand.emit(sigcmd)
        else:
            self.logger.info(f'right now PDU numbers are hardcoded, and only {active_pdus} are active')
    
    @cmd
    def do_routine(self):
        """
        created: NPL 4-7-21
        
        load a txt file that has a list of commands from this file to execute.
        each command should be written the same way as it would be using the terminal,
        and each command should be on its own line.
        
        """
        self.defineCmdParser('execute routine from specified text file. default path is wsp/routines')
        self.cmdparser.add_argument('filename',
                                    nargs = 1,
                                    action = None,
                                    help = "<filename>")
        
        # ADD AN OPTIONAL PATH COMMAND. 
        self.cmdparser.add_argument('--path',
                                    nargs = 1,
                                    action = None,
                                    help = "<filepath>")
        
        self.getargs()
        filename = self.args.filename[0]
        
        # check for the optional --path flag
        # note that I'm following this example from the documentation:
            # see "Introducing Optional Arguments": https://docs.python.org/3/howto/argparse.html
        if self.args.path:
            location = self.args.path[0] + '/'
        else:
            location = self.base_directory + '/routines/'
        
        filepath = location + filename
        
        self.logger.info(f'Attempting to execute routine from: {filepath}')
        
        # Load in the file
        routine = np.loadtxt(filepath,
                     delimiter = '\n',
                     comments = '#',
                     dtype = str)
        
        # Convert the routine from a numpy array to a list (ie a list of commands)
        cmd_list = list(routine)
        
        # Create a cmd Request object
        cmdrequest = commandParser.cmd_request(cmd = cmd_list,
                                               request_addr = 'dunno address',
                                               request_port = 'not sure of port!',
                                               priority = 'low')
        
        # Now signal that we should execute the list of commands
        #self.newRoutine.emit(cmd_list)
        self.newCmdRequest.emit(cmdrequest)
    
    ######## COMMANDS RELATED TO THE ROBOTIC OPERATIONS ########
    
    @cmd
    def load_target_schedule(self):
        """Usage: load_target_schedule <TOO_ScheduleFile.db>"""
        self.defineCmdParser('load in a TOO target schedule file')
        self.cmdparser.add_argument('schedulefile_name',
                                    nargs = 1,
                                    action = None,
                                    type = str,
                                    help = '<target_schedulefile.db>')
        self.getargs()
        schedulefile_name = self.args.schedulefile_name[0]
        # send signal that the schedule executor should swap schedule files
        self.roboThread.changeSchedule.emit(schedulefile_name)
    @cmd
    def load_nightly_schedule(self):
        self.defineCmdParser('load the schedule file for the nightly plan')
        #schedulefile_name = 'nightly'
        schedulefile_name = 'nightly'
        self.roboThread.changeSchedule.emit(schedulefile_name)

    """@cmd
    def schedule_start(self):
        self.defineCmdParser('start/resume scheduled observations')
        if self.scheduleThread:
            self.scheduleThread.start()

    @cmd
    def schedule_pause(self):
        self.defineCmdParser('interrupt scheduled observations')
        if self.scheduleThread:
            self.scheduleThread.stop()"""
            
    @cmd
    def robo_kill(self):
        self.defineCmdParser('kill the robotic operator thread')
        if self.roboThread.isRunning():
            self.roboThread.terminate()
        else:
            pass
    @cmd
    def robo_init(self):
        self.defineCmdParser('init the robotic operator thread')
        if not self.roboThread.isRunning():
            self.roboThread.start()
        
    @cmd
    def robo_run(self):
        self.defineCmdParser('start the robotic operator')
        if self.roboThread.isRunning():
            self.roboThread.restartRoboSignal.emit('auto')
    
    @cmd
    def robo_stop(self):
        self.defineCmdParser('stop/pause the robotic operator')
        if self.roboThread.isRunning():
            sigcmd = signalCmd('stop')
        
            self.roboThread.newCommand.emit(sigcmd)
    
    @cmd
    def robo_run_test(self):
        self.defineCmdParser('start the robotic operator')
        if self.roboThread.isRunning():
            self.roboThread.restartRoboSignal.emit('test')
    
    @cmd
    def robo_do_currentObs(self):
        self.defineCmdParser('do the current observation')
        self.roboThread.do_currentObs_Signal.emit()
    
    @cmd
    def robo_do_calibration(self):
        self.defineCmdParser('do the current observation')

        self.cmdparser.add_argument('-d',    '--dark',      action = 'store_true', default = False)
        self.cmdparser.add_argument('-b',    '--bias',      action = 'store_true', default = False)
        self.cmdparser.add_argument('-f',    '--flat',      action = 'store_true', default = False)

        self.getargs()
        
        if self.args.dark:
            do_darks = True
        else:
            do_darks = False
        if self.args.flat:
            do_flats = True
        else:
            do_flats = False
        if self.args.bias:
            do_bias = True
        else:
            do_bias = False
        
        
        self.logger.info(f'wintercmd: running roboOperator do_calibration with do_flats = {do_flats}, do_darks = {do_darks}, do_bias = {do_bias}')
        
        sigcmd = signalCmd('do_calibration',
                           do_flats = do_flats,
                           do_darks = do_darks, 
                           do_bias = do_bias)
        
        self.roboThread.newCommand.emit(sigcmd)
        
    @cmd
    def robo_do_bias(self):
        self.defineCmdParser('do the bias exposure series')
        sigcmd = signalCmd('do_bias')
        
        self.roboThread.newCommand.emit(sigcmd)
        
    @cmd
    def robo_do_darks(self):
        self.defineCmdParser('do the dark exposure series')
        self.cmdparser.add_argument('-n', '--nimgs',
                                    nargs = 1,
                                    type = int,
                                    default = -1,
                                    action = None,
                                    help = "<number_of_images>")
        self.cmdparser.add_argument('-e', '--exptimes',
                                    nargs = '+',
                                    type = int,
                                    default = [],
                                    action = None,
                                    help = "<exposure_time_list>")
        self.getargs()
        
        # You call this function like this:
            # robo_do_darks -n 3 -e 1 5 10

        
        if type(self.args.nimgs) is int:
            nimgs = self.args.nimgs
        else:
            nimgs = self.args.nimgs[0]
        
        if nimgs == -1:
            nimgs = None
            
        exptimes = self.args.exptimes
        # Set default image mode
        if exptimes == []:
            exptimes = None
        
        sigcmd = signalCmd('do_darks', n_imgs = nimgs, exptimes = exptimes)
        
        self.roboThread.newCommand.emit(sigcmd)
    
    @cmd
    def robo_do_exposure(self):
        self.defineCmdParser('tell the robotic operator to take an image with the camera')
        #self.roboThread.doExposureSignal.emit()
        # argument to hold the coordinates/location of the target
        
        self.cmdparser.add_argument('--comment',
                                    action = None,
                                    type = str,
                                    nargs = 1,
                                    default = 'radec',
                                    help = '<comment> ')
        
        self.cmdparser.add_argument('--noplot',
                                    action = 'store_true',
                                    default = False,
                                    help = '<comment> ')
        
        # argument to hold the observation type
        group = self.cmdparser.add_mutually_exclusive_group()
        group.add_argument('-s',    '--science',   action = 'store_true', default = False)
        group.add_argument('-d',    '--dark',      action = 'store_true', default = False)
        group.add_argument('-f',    '--flat',      action = 'store_true', default = False)
        group.add_argument('-foc',  '--focus',     action = 'store_true', default = False)
        group.add_argument('-t',    '--test',      action = 'store_true', default = False)
        group.add_argument('-b',    '--bias',      action = 'store_true', default = False)
        group.add_argument('-p',    '--pointing',  action = 'store_true', default = False)
        
        self.getargs()
        
        if self.args.science:
            obstype = 'SCIENCE'
        elif self.args.dark:
            obstype = 'DARK'
        elif self.args.flat:
            obstype = 'FLAT'
        elif self.args.focus:
            obstype = 'FOCUS'
        elif self.args.bias:
            obstype = 'BIAS'
        elif self.args.test:
            obstype = 'TEST'
        elif self.args.pointing:
            obstype = 'POINTING'
        else:
            # SET THE DEFAULT
            obstype = 'TEST'
        
        if self.args.noplot:
            postPlot = False
        else:
            postPlot = True
        
        comment = self.args.comment
        
        sigcmd = signalCmd('doExposure',
                               obstype = obstype,
                               postPlot = postPlot,
                               qcomment = comment)
        
        self.roboThread.newCommand.emit(sigcmd)
        
    @cmd
    def robo_take_flat(self):
        self.defineCmdParser('tell the robotic operator to take an image with the camera')
        sigcmd = signalCmd('doExposure',
                               obstype = 'FLAT',
                               postPlot = True,
                               qcomment = 'altaz')
        
        self.roboThread.newCommand.emit(sigcmd)


    @cmd
    def robo_observe(self):
        """Usage: robo_observe <targtype> <target> {<target}"""
        self.defineCmdParser('tell the robotic operator to execute an observation')
        
        # argument to hold the target type
        self.cmdparser.add_argument('targtype',
                                    nargs = 1,
                                    action = None,
                                    type = str,
                                    choices = ['altaz', 'radec', 'object','here'],
                                    )
        
        # argument to hold the coordinates/location of the target
        self.cmdparser.add_argument('target',
                                    action = None,
                                    type = str,
                                    nargs = '*',
                                    help = '<target> {<target>}')
        
        self.cmdparser.add_argument('--comment',
                                    action = None,
                                    type = str,
                                    nargs = 1,
                                    default = 'radec',
                                    help = '<comment> ')
        
        # by default it assumes manual mode. 
        obsmode_group = self.cmdparser.add_mutually_exclusive_group()
        obsmode_group.add_argument('-man', '--manual',      action = 'store_true', default = False)
        obsmode_group.add_argument('--schedule',    action = 'store_true', default = False)
        obsmode_group.add_argument('-cal', '--calibration',    action = 'store_true', default = False)

        # argument to hold the observation type
        group = self.cmdparser.add_mutually_exclusive_group()
        group.add_argument('-s',    '--science',   action = 'store_true', default = False)
        group.add_argument('-d',    '--dark',      action = 'store_true', default = False)
        group.add_argument('-f',    '--flat',      action = 'store_true', default = False)
        group.add_argument('-foc',  '--focus',     action = 'store_true', default = False)
        group.add_argument('-t',    '--test',      action = 'store_true', default = False)
        group.add_argument('-b',    '--bias',      action = 'store_true', default = False)
        group.add_argument('-p',    '--pointing',  action = 'store_true', default = False)
        
        self.getargs()
        
        # obstype
        if self.args.science:
            obstype = 'SCIENCE'
        elif self.args.dark:
            obstype = 'DARK'
        elif self.args.flat:
            obstype = 'FLAT'
        elif self.args.focus:
            obstype = 'FOCUS'
        elif self.args.bias:
            obstype = 'BIAS'
        elif self.args.test:
            obstype = 'TEST'
        elif self.args.pointing:
            obstype = 'POINTING'
        else:
            # SET THE DEFAULT
            obstype = 'TEST'
            
        # obsmode
        if self.args.manual:
            obsmode = 'MANUAL'
        elif self.args.schedule:
            obsmode = 'SCHEDULE'
        elif self.args.calibration:
            obsmode = 'CALIBRATION'
        else:
            # SET THE DEFAULT
            obsmode = 'UNKNOWN'
        
        #print(f'robo_observe: args = {self.args}')
        comment = self.args.comment

        targtype = self.args.targtype[0].lower()
        if targtype == 'altaz':
            targ_coord_1 = float(self.args.target[0])
            targ_coord_2 = float(self.args.target[1])
            sigcmd = signalCmd('do_observation',
                               targtype = targtype,
                               target = (targ_coord_1, targ_coord_2),
                               tracking = 'auto',
                               field_angle = 'auto',
                               obstype = obstype,
                               comment = comment)
        
        elif targtype == 'radec':
            # allow the RA and DEC to be specified in multiple ways:
            # this allows you to specify the coords either as: 
            #     ra, dec = '05:34:30.52', '22:00:59.9'
            #     ra, dec = 5.57514, 22.0166 
            ra = self.args.target[0]
            dec = self.args.target[1]
            
            ra_obj = astropy.coordinates.Angle(ra, unit = u.hour)
            dec_obj = astropy.coordinates.Angle(dec, unit = u.deg)
            
            # note: turning these back to floats instead of numpy.float64 objects to satisfy assert checking in roboOperator
            ra_hour = float(ra_obj.hour)
            dec_deg = float(dec_obj.deg)
            
            sigcmd = signalCmd('do_observation',
                               targtype = targtype,
                               target = (ra_hour, dec_deg),
                               tracking = 'auto',
                               field_angle = 'auto',
                               obstype = obstype,
                               comment = comment,
                               obsmode = obsmode)
        
        elif targtype == 'object':
            obj = self.args.target[0]
            sigcmd = signalCmd('do_observation',
                               targtype = targtype,
                               target = obj,
                               tracking = 'auto',
                               field_angle = 'auto',
                               obstype = obstype,
                               comment = comment,
                               obsmode = obsmode)
        else:
            msg = f'wintercmd: target type not allowed!'
            self.logger.info(msg)
            print(msg)
            
            
        self.roboThread.newCommand.emit(sigcmd)
        
        
        
    @cmd
    def robo_observe_altaz(self):
        """Usage: mount_goto_alt_az <alt> <az>"""
        self.defineCmdParser('tell the robotic operator to execute on observation of the specified alt and az')
        self.cmdparser.add_argument('position',
                                    nargs = 2,
                                    action = None,
                                    type = float,
                                    help = '<alt_deg> <az_deg>')
        
        self.getargs()
        alt = self.args.position[0]
        az = self.args.position[1]
        
        # triggering this: do_observation(self, obstype, target, tracking = 'auto', field_angle = 'auto'):

        sigcmd = signalCmd('do_observation',
                           targtype = 'altaz',
                           target = (alt,az),
                           tracking = 'auto',
                           field_angle = 'auto')
        
        self.roboThread.newCommand.emit(sigcmd)
    
    @cmd
    def robo_observe_radec(self):
        """Usage: robo_observe_radec <ra> <dec>"""
        self.defineCmdParser('move telescope to specified j2000 ra (hours)/dec (deg) ')
        self.cmdparser.add_argument('position',
                                    nargs = 2,
                                    action = None,
                                    type = float,
                                    help = '<ra_hours> <dec_degs>')
        self.getargs()
        ra_j2000_hours = self.args.position[0]
        dec_j2000_degs = self.args.position[1]
        
        target = (ra_j2000_hours,dec_j2000_degs)
        
        # triggering this: do_observation(self, obstype, target, tracking = 'auto', field_angle = 'auto'):

        sigcmd = signalCmd('do_observation',
                           targtype = 'radec',
                           target = target,
                           tracking = 'auto',
                           field_angle = 'auto')
        
        self.roboThread.newCommand.emit(sigcmd)
        
    @cmd
    def robo_observe_object(self):
        """ Usage: mount_goto_object <object_name> """
        # points to an object that is in the astropy object library
        # before slewing makes sure that the altitude and azimuth as viewed from palomar are okay unless its overridden
        self.defineCmdParser('move telescope to object from astropy catalog')
        self.cmdparser.add_argument('object_name',
                                    nargs = 1,
                                    action = None,
                                    type = str,
                                    help = '<object name>')
        
        self.getargs()
        #print(f'wintercmd: args = {self.args}')
        
        obj = self.args.object_name[0]
        self.logger.info(f'setting up observation of object_name = {obj}')
        # triggering this: do_observation(self, obstype, target, tracking = 'auto', field_angle = 'auto'):

        sigcmd = signalCmd('do_observation',
                           targtype = 'object',
                           target = obj,
                           tracking = 'auto',
                           field_angle = 'auto')
        
        self.roboThread.newCommand.emit(sigcmd)
    
    @cmd
    def robo_remakePointingModel(self):
        self.defineCmdParser('start the robotic operator')
        
        self.cmdparser.add_argument('-a', '--append',
                                    action = 'store_true',
                                    default = False,
                                    help = 'append points instead of clearing')
        self.cmdparser.add_argument('-n', '--firstline', 
                                    nargs = 1,
                                    type = int,
                                    default = 0,
                                    help = 'line number of first point to use')
        
        self.getargs()
        print(f'wintercmd: args = {self.args}')
        append = self.args.append
        #firstpoint = self.args.firstline[0]
        firstpoint = self.args.firstline

        
        sigcmd = signalCmd('remakePointingModel',
                           append = append,
                           firstpoint = firstpoint)
        
        self.roboThread.newCommand.emit(sigcmd)
    
    @cmd
    def robo_set_operator(self):
        self.defineCmdParser('record the name of the current operator')
        self.cmdparser.add_argument('operator_name',
                                    nargs = 1,
                                    action = None,
                                    type = str,
                                    help = '<operator name>')
        
        self.getargs()        
        name = self.args.operator_name[0]
        sigcmd = signalCmd('updateOperator',
                           operator_name = name)
        
        self.roboThread.newCommand.emit(sigcmd)
    
    
    @cmd
    def robo_set_observer(self):
        # this is the same as set_operator... just adding flexibility!
        self.defineCmdParser('record the name of the current operator')
        self.cmdparser.add_argument('operator_name',
                                    nargs = 1,
                                    action = None,
                                    type = str,
                                    help = '<operator name>')
        
        self.getargs()        
        name = self.args.operator_name[0]
        sigcmd = signalCmd('updateOperator',
                           operator_name = name)
        
        self.roboThread.newCommand.emit(sigcmd)
    
    @cmd
    def robo_set_qcomment(self):
        self.defineCmdParser('set comment which will be written to QCOMMENT in the fits header')
        self.cmdparser.add_argument('qcomment',
                                    nargs = 1,
                                    action = None,
                                    type = str,
                                    help = '<queue comment>')
        
        self.getargs()        
        qcomment = self.args.qcomment[0]
        sigcmd = signalCmd('updateQComment',
                           qcomment = qcomment)
        
        self.roboThread.newCommand.emit(sigcmd)
        
        condition = True
        timeout = 15
        # create a buffer list to hold several samples over which the stop condition must be true
        n_buffer_samples = self.config.get('cmd_satisfied_N_samples')
        stop_condition_buffer = [(not condition) for i in range(n_buffer_samples)]

        # get the current timestamp
        start_timestamp = datetime.utcnow().timestamp()
        while True:
            QtCore.QCoreApplication.processEvents()
            time.sleep(self.config['cmd_status_dt'])
            timestamp = datetime.utcnow().timestamp()
            dt = (timestamp - start_timestamp)
            #print(f'wintercmd: wait time so far = {dt}')
            if dt > timeout:
                raise TimeoutError(f'command timed out after {timeout} seconds before completing. Requested qcomment = {qcomment}, but it is {self.state["qcomment"]}')
            
            stop_condition = ( (self.state['qcomment'] == qcomment) )
            # do this in 2 steps. first shift the buffer forward (up to the last one. you end up with the last element twice)
            stop_condition_buffer[:-1] = stop_condition_buffer[1:]
            # now replace the last element
            stop_condition_buffer[-1] = stop_condition
            
            if all(entry == condition for entry in stop_condition_buffer):
                self.logger.info(f'wintercmd: qcomment set successfully. Current qcomment = {self.state["qcomment"]}')
                break 
    
    
    @cmd
    def robo_set_obstype(self):
        self.defineCmdParser('set the current observation type (flat, dark, bias, science, etc')
        self.cmdparser.add_argument('obstype',
                                    nargs = 1,
                                    action = None,
                                    type = str,
                                    help = '<observation type>')
        
        self.getargs()        
        obstype = self.args.obstype[0]
        sigcmd = signalCmd('updateObsType',
                           obstype = obstype)
        
        self.roboThread.newCommand.emit(sigcmd)
        
        condition = True
        timeout = 15
        # create a buffer list to hold several samples over which the stop condition must be true
        n_buffer_samples = self.config.get('cmd_satisfied_N_samples')
        stop_condition_buffer = [(not condition) for i in range(n_buffer_samples)]

        # get the current timestamp
        start_timestamp = datetime.utcnow().timestamp()
        while True:
            QtCore.QCoreApplication.processEvents()
            time.sleep(self.config['cmd_status_dt'])
            timestamp = datetime.utcnow().timestamp()
            dt = (timestamp - start_timestamp)
            #print(f'wintercmd: wait time so far = {dt}')
            if dt > timeout:
                raise TimeoutError(f'command timed out after {timeout} seconds before completing. Requested obstype = {obstype}, but it is {self.state["obstype"]}')
            
            stop_condition = ( (self.state['obstype'] == obstype) )
            # do this in 2 steps. first shift the buffer forward (up to the last one. you end up with the last element twice)
            stop_condition_buffer[:-1] = stop_condition_buffer[1:]
            # now replace the last element
            stop_condition_buffer[-1] = stop_condition
            
            if all(entry == condition for entry in stop_condition_buffer):
                self.logger.info(f'wintercmd: obstype set successfully. Current obstype = {self.state["obstype"]}')
                break 
        
        
    # General Shut Down
    @cmd
    def quit(self):
        """Quits out of Interactive Mode."""
        
        self.logger.info('SHUTTING DOWN SYSTEMS SAFELY BEFORE QUITTING')
        self.parse('mount_shutdown')
        
        
        print('Good Bye!')
        if self.promptThread and self.execThread:
            self.promptThread.stop()
            self.execThread.stop()

        #sys.exit()#sigint_handler()
        
        # kill all the daemons
        self.daemonlist.kill_all()
        
        # kill the program
        QtCore.QCoreApplication.quit()
        
    @cmd
    def kill(self):
        """Quits out of Interactive Mode."""
        
        self.logger.info('KILLING WSP WITH NO REGARD FOR SAFETY!')
        
        
        print('Good Bye!')
        try:
            self.promptThread.stop()
        except Exception as e:
            print(f'could not stop promptThread: {e}')
        
        try:
            self.execThread.stop()
        except Exception as e:
            print(f'could not stop cmd executor thread: {e}')
        
        
        """
        #NPL 5-19-23 commenting out
        # try to shut down the ccd camera client
        try:
            self.parse('ccd_shutdown_client')
            time.sleep(1)
        except Exception as e:
            print(f'could not shut down ccd camera client. {type(e)}: {e}')
        """
        
        # try to kill the ccd huaso_server
        # we don't have a path from loacl to remote for this yet.
        
        # kill all the daemons
        self.daemonlist.kill_all()
        
        # kill any dangling instances of huaso_server
        huaso_server_pids = daemon_utils.getPIDS('huaso_server')
        for pid in huaso_server_pids:
            print(f'killing huaso_server instance with PID {pid}')
            os.kill(pid, signal.SIGKILL)
        
        # kill the program
        print(f'Now trying to kill the QCoreApplication...')
        QtCore.QCoreApplication.quit()

##### Mirror cover commands ####
        
    @cmd
    def mirror_cover_connect(self):
        self.defineCmdParser('Connect to mirror cover server')
        self.mirror_cover.sendreceive("connect")
        
        ## Wait until end condition is satisfied, or timeout ##
        condition = True
        timeout = 5
        # create a buffer list to hold several samples over which the stop condition must be true
        n_buffer_samples = self.config.get('cmd_satisfied_N_samples')
        stop_condition_buffer = [(not condition) for i in range(n_buffer_samples)]

        # get the current timestamp
        start_timestamp = datetime.utcnow().timestamp()
        while True:
            QtCore.QCoreApplication.processEvents()
            time.sleep(self.config['cmd_status_dt'])
            timestamp = datetime.utcnow().timestamp()
            dt = (timestamp - start_timestamp)
            #print(f'wintercmd: wait time so far = {dt}')
            if dt > timeout:
                raise TimeoutError(f'unable to connect to mirror cover: command timed out after {timeout} seconds before completing.')
            
            stop_condition = ( (self.state['Mirror_Cover_Connected'] == 1) )
            # do this in 2 steps. first shift the buffer forward (up to the last one. you end up with the last element twice)
            stop_condition_buffer[:-1] = stop_condition_buffer[1:]
            # now replace the last element
            stop_condition_buffer[-1] = stop_condition
            
            if all(entry == condition for entry in stop_condition_buffer):
                self.logger.info(f'wintercmd: successfully connected to mirror cover')
                break 
        
        
    @cmd
    def mirror_cover_open(self):
        self.defineCmdParser('Open mirror cover')
        self.mirror_cover.sendreceive("beginopen")
        
        # NOTE: when OPEN, Mirror_Cover_State == 0
        
        ## Wait until end condition is satisfied, or timeout ##
        condition = True
        timeout = 40 # seems to take between 15-25 seconds
        # create a buffer list to hold several samples over which the stop condition must be true
        n_buffer_samples = self.config.get('cmd_satisfied_N_samples')
        stop_condition_buffer = [(not condition) for i in range(n_buffer_samples)]

        # get the current timestamp
        start_timestamp = datetime.utcnow().timestamp()
        while True:
            QtCore.QCoreApplication.processEvents()
            time.sleep(self.config['cmd_status_dt'])
            timestamp = datetime.utcnow().timestamp()
            dt = (timestamp - start_timestamp)
            #print(f'wintercmd: wait time so far = {dt}')
            if dt > timeout:
                raise TimeoutError(f'unable to open mirror cover: command timed out after {timeout} seconds before completing.')
            
            stop_condition = ( (self.state['Mirror_Cover_State'] == 0) and (self.state['Mirror_Cover_Connected']))
            # do this in 2 steps. first shift the buffer forward (up to the last one. you end up with the last element twice)
            stop_condition_buffer[:-1] = stop_condition_buffer[1:]
            # now replace the last element
            stop_condition_buffer[-1] = stop_condition
            
            if all(entry == condition for entry in stop_condition_buffer):
                self.logger.info(f'wintercmd: successfully opened mirror cover')
                break 
        
        
    @cmd
    def mirror_cover_close(self):
        self.defineCmdParser('Close mirror cover')
        self.mirror_cover.sendreceive("beginclose")
        
        # NOTE: when CLOSED, Mirror_Cover_State == 1
        
        ## Wait until end condition is satisfied, or timeout ##
        condition = True
        timeout = 40 # seems to take between 15-25 seconds
        # create a buffer list to hold several samples over which the stop condition must be true
        n_buffer_samples = self.config.get('cmd_satisfied_N_samples')
        stop_condition_buffer = [(not condition) for i in range(n_buffer_samples)]

        # get the current timestamp
        start_timestamp = datetime.utcnow().timestamp()
        while True:
            QtCore.QCoreApplication.processEvents()
            time.sleep(self.config['cmd_status_dt'])
            timestamp = datetime.utcnow().timestamp()
            dt = (timestamp - start_timestamp)
            #print(f'wintercmd: wait time so far = {dt}')
            if dt > timeout:
                raise TimeoutError(f'unable to close mirror cover: command timed out after {timeout} seconds before completing.')
            
            stop_condition = ( (self.state['Mirror_Cover_State'] == 1) and (self.state['Mirror_Cover_Connected']))
            # do this in 2 steps. first shift the buffer forward (up to the last one. you end up with the last element twice)
            stop_condition_buffer[:-1] = stop_condition_buffer[1:]
            # now replace the last element
            stop_condition_buffer[-1] = stop_condition
            
            if all(entry == condition for entry in stop_condition_buffer):
                self.logger.info(f'wintercmd: successfully closed mirror cover')
                break 

##### TEST VISCAM COMMANDS ####
    @cmd
    def command_viscam_shutter(self):
        self.defineCmdParser('Command viscam shutter')
                  
        self.cmdparser.add_argument('shutter_cmd',
              nargs = 1,
              action = None,
             help = '<shutter_int>')

        self.getargs()
        shutter_cmd = self.args.shutter_cmd[0]
        sigcmd = signalCmd('send_shutter_command', shutter_cmd)
        self.viscam.newCommand.emit(sigcmd)
        #self.viscam.send_shutter_command(shutter_cmd)

    @cmd
    def command_filter_wheel(self):
        self.defineCmdParser('Command viscam filter wheel')
                  
        self.cmdparser.add_argument('fw_pos',
              nargs = 1,
              type = int,
              action = None,
              help = '<fw_pos_int>')

        self.getargs()
        fw_pos = self.args.fw_pos[0]
        
        sigcmd = signalCmd('command_filter_wheel',
                           pos = fw_pos)
        
        self.viscam.newCommand.emit(sigcmd)
        
        #fw_num = int(fw_cmd)
        
        ## Wait until end condition is satisfied, or timeout ##
        condition = True
        timeout = 30 
        # create a buffer list to hold several samples over which the stop condition must be true
        n_buffer_samples = self.config.get('cmd_satisfied_N_samples')
        stop_condition_buffer = [(not condition) for i in range(n_buffer_samples)]

        # get the current timestamp
        start_timestamp = datetime.utcnow().timestamp()
        while True:
            QtCore.QCoreApplication.processEvents()
            time.sleep(self.config['cmd_status_dt'])
            timestamp = datetime.utcnow().timestamp()
            dt = (timestamp - start_timestamp)
            #print(f'wintercmd: wait time so far = {dt}')
            if dt > timeout:
                raise TimeoutError(f'unable to move viscam filter wheel: command timed out after {timeout} seconds before completing.')
            
            stop_condition = ( (self.state['Viscam_Filter_Wheel_Position'] == fw_pos) )
            # do this in 2 steps. first shift the buffer forward (up to the last one. you end up with the last element twice)
            stop_condition_buffer[:-1] = stop_condition_buffer[1:]
            # now replace the last element
            stop_condition_buffer[-1] = stop_condition
            
            if all(entry == condition for entry in stop_condition_buffer):
                self.logger.info(f'wintercmd: successfully completed viscam filter wheel move')
                break 
    
    @cmd
    def ccd_set_exposure(self):
        self.defineCmdParser('Set exposure time in seconds')
        self.cmdparser.add_argument('seconds',
                                    nargs = 1,
                                    action = None,
                                    help = '<exposure_time_seconds>')
        
        self.getargs()
        secs = np.float(self.args.seconds[0]) # remember the args come in as strings!!
        sigcmd = signalCmd('setexposure', secs)
        self.ccd.newCommand.emit(sigcmd)
        
        ## Wait until end condition is satisfied, or timeout ##
        condition = True
        timeout = 10
        # create a buffer list to hold several samples over which the stop condition must be true
        n_buffer_samples = self.config.get('cmd_satisfied_N_samples')
        stop_condition_buffer = [(not condition) for i in range(n_buffer_samples)]

        # get the current timestamp
        start_timestamp = datetime.utcnow().timestamp()
        while True:
            QtCore.QCoreApplication.processEvents()
            time.sleep(self.config['cmd_status_dt'])
            timestamp = datetime.utcnow().timestamp()
            dt = (timestamp - start_timestamp)
            #print(f'wintercmd: wait time so far = {dt}')
            if dt > timeout:
                self.logger.info(f'command timed out after {timeout} seconds before completing. Requested exptime = {secs}, but it is {self.state["ccd_exptime"]}')
                break
            stop_condition = ( (self.state['ccd_exptime'] == secs) )
            # do this in 2 steps. first shift the buffer forward (up to the last one. you end up with the last element twice)
            stop_condition_buffer[:-1] = stop_condition_buffer[1:]
            # now replace the last element
            stop_condition_buffer[-1] = stop_condition
            
            if all(entry == condition for entry in stop_condition_buffer):
                self.logger.info(f'wintercmd: ccd_exptime set successfully. Current Exptime = {self.state["ccd_exptime"]}')
                try_again = False
                break 
            try_again = True
        
        if try_again:
            
            # sometimes it just doesn't take...
            sigcmd = signalCmd('setexposure', secs)
            self.ccd.newCommand.emit(sigcmd)
            
            ## Wait until end condition is satisfied, or timeout ##
            condition = True
            timeout = 10
            # create a buffer list to hold several samples over which the stop condition must be true
            n_buffer_samples = self.config.get('cmd_satisfied_N_samples')
            stop_condition_buffer = [(not condition) for i in range(n_buffer_samples)]

            # get the current timestamp
            start_timestamp = datetime.utcnow().timestamp()
            while True:
                QtCore.QCoreApplication.processEvents()
                time.sleep(self.config['cmd_status_dt'])
                timestamp = datetime.utcnow().timestamp()
                dt = (timestamp - start_timestamp)
                #print(f'wintercmd: wait time so far = {dt}')
                if dt > timeout:
                    raise TimeoutError(f'command timed out after {timeout} seconds before completing. Requested exptime = {secs}, but it is {self.state["ccd_exptime"]}')
                
                stop_condition = ( (self.state['ccd_exptime'] == secs) )
                # do this in 2 steps. first shift the buffer forward (up to the last one. you end up with the last element twice)
                stop_condition_buffer[:-1] = stop_condition_buffer[1:]
                # now replace the last element
                stop_condition_buffer[-1] = stop_condition
                
                if all(entry == condition for entry in stop_condition_buffer):
                    self.logger.info(f'wintercmd: ccd_exptime set successfully. Current Exptime = {self.state["ccd_exptime"]}')
                    break 
        
        
    @cmd
    def ccd_set_tec_sp(self):
        self.defineCmdParser('Set tec setpoint in celsius')
        self.cmdparser.add_argument('degrees',
                                    nargs = 1,
                                    action = None,
                                    help = '<tec_sp_celsius>')
        
        self.getargs()
        degs = np.float(self.args.degrees[0]) # remember the args come in as strings!!
        sigcmd = signalCmd('setSetpoint', degs)
        self.ccd.newCommand.emit(sigcmd)
    
    @cmd
    def ccd_do_exposure(self):
        self.defineCmdParser('Start ccd exposure')
        
        # argument to hold the observation type
        group = self.cmdparser.add_mutually_exclusive_group()
        group.add_argument('-s',    '--science',   action = 'store_true', default = False)
        group.add_argument('-d',    '--dark',      action = 'store_true', default = False)
        group.add_argument('-f',    '--flat',      action = 'store_true', default = False)
        group.add_argument('-foc',  '--focus',     action = 'store_true', default = False)
        group.add_argument('-t',    '--test',      action = 'store_true', default = False)
        group.add_argument('-b',    '--bias',      action = 'store_true', default = False)
        group.add_argument('-p',    '--pointing',  action = 'store_true', default = False)
        
        self.getargs()
        
        if self.args.science:
            obstype = 'SCIENCE'
            dark = False
        elif self.args.dark:
            obstype = 'DARK'
            dark = True
        elif self.args.flat:
            obstype = 'FLAT'
            dark = False
        elif self.args.focus:
            obstype = 'FOCUS'
            dark = False
        elif self.args.bias:
            obstype = 'BIAS'
            dark = True
        elif self.args.test:
            obstype = 'TEST'
            dark = False
        elif self.args.pointing:
            obstype = 'POINTING'
            dark = False
        else:
            # SET THE DEFAULT
            obstype = ''
            dark = False
        
        print(f'wintercmd: obstype = {obstype}, dark = {dark}')
        
        self.logger.info(f'wintercmd: args = {self.args}')
        
        # it the obstype is '' then just leave it be
        if obstype != '':
            self.parse(f'robo_set_obstype {obstype}')

        sigcmd = signalCmd('doExposure',
                               dark = dark)
        
        self.ccd.newCommand.emit(sigcmd)
        
        self.logger.info(f'wintercmd: running ccd_do_exposure in thread {threading.get_ident()}')
        
        ## Wait until end condition is satisfied, or timeout ##
        condition = True
        timeout = self.state['ccd_exposureTimeout'] + 30
        # create a buffer list to hold several samples over which the stop condition must be true
        
        
        #n_buffer_samples = self.config.get('cmd_satisfied_N_samples')
        # Change this to trigger on 1 True sample, since the flag is on for a short time and may get skipped
        n_buffer_samples = 1
        stop_condition_buffer = [(not condition) for i in range(n_buffer_samples)]

        # get the current timestamp
        start_timestamp = datetime.utcnow().timestamp()
        while True:
            QtCore.QCoreApplication.processEvents()
            time.sleep(self.config['cmd_status_dt'])
            
            timestamp = datetime.utcnow().timestamp()
            dt = (timestamp - start_timestamp)
            #print(f'wintercmd: wait time so far = {dt}')
            if dt > timeout:
                raise TimeoutError(f'ccd_do_exposure command timed out after {timeout} seconds before completing')
            
            stop_condition = ( (self.state['ccd_doing_exposure'] == False) & (self.state['ccd_image_saved_flag']))
            #self.logger.info(f'count = {self.state["count"]}')
            #self.logger.info(f'wintercmd: ccd_doing_exposure = {self.state["ccd_doing_exposure"]}, ccd_image_saved_flag = {self.state["ccd_image_saved_flag"]}')
            #self.logger.info(f'wintercmd: stop_condition_buffer = {stop_condition_buffer}')
            #self.logger.info('')
            # do this in 2 steps. first shift the buffer forward (up to the last one. you end up with the last element twice)
            stop_condition_buffer[:-1] = stop_condition_buffer[1:]
            # now replace the last element
            stop_condition_buffer[-1] = stop_condition
            
            if all(entry == condition for entry in stop_condition_buffer):
                self.logger.info(f'wintercmd: finished the do exposure method without timing out :)')
                break 
           
    
    @cmd
    def ccd_do_bias(self):
        """ Do a bias frame """
        self.defineCmdParser('Do a bias frame')
        
        try:
            
            # set the image type to bias
            self.parse('robo_set_obstype BIAS')
            
            lastExptime = self.state['ccd_exptime']
            
            # change the exposure time to zero
            self.parse(f'ccd_set_exposure 0')
            
            # take a bias frame
            self.parse(f'ccd_do_exposure --bias')
            
            # set the exposure time back to what it was before
            self.parse(f'ccd_set_exposure {lastExptime}')
        
        except Exception as e:
            self.logger.info(f'wintercmd: could not take bias frame: {e}')
    
    
    @cmd
    def ccd_tec_start(self):
        self.defineCmdParser('Start ccd tec')
        sigcmd = signalCmd('tecStart')
        self.ccd.newCommand.emit(sigcmd)
        
    @cmd
    def ccd_tec_stop(self):
        self.defineCmdParser('Stop ccd tec')
        sigcmd = signalCmd('tecStop')
        self.ccd.newCommand.emit(sigcmd)
        
    @cmd
    def ccd_shutdown_client(self):
        self.defineCmdParser('shut down the camera client session')
        sigcmd = signalCmd('shutdownCameraClient')
        self.ccd.newCommand.emit(sigcmd)
    
    @cmd
    def ccd_reconnectServer(self):
        self.defineCmdParser('restart the huaso server')
        sigcmd = signalCmd('reconnectServer')
        self.ccd.newCommand.emit(sigcmd)
    
    @cmd
    def ccd_killServer(self):
        self.defineCmdParser('shut down the huaso server')
        sigcmd = signalCmd('killServer')
        self.ccd.newCommand.emit(sigcmd)
    
    ##### FILTER WHEEL API METHODS #####
    
    @cmd
    def fw_home(self):
        self.defineCmdParser('home the filterwheel')

        
        # argument to hold the observation type
        group = self.cmdparser.add_mutually_exclusive_group()
        group.add_argument('-w',    '--winter',      action = 'store_true', default = True)
        group.add_argument('-c',    '--summer',      action = 'store_true', default = False)
        
        self.getargs()

        self.logger.info(f'fw_goto: args = {self.args}')
        
        if self.args.winter:
            fwname = 'winter'
        elif self.args.summer:
            fwname = 'summer'
        
        fw = self.fwdict[fwname]
                
        sigcmd = signalCmd('home')
        
        self.logger.info(f'wintercmd: homing {fw.daemonname}')
        
        fw.newCommand.emit(sigcmd)
    
    @cmd
    def fw_goto(self):
        self.defineCmdParser('send filterwheel to specified position')
        
        self.cmdparser.add_argument('pos',
                                    nargs = 1,
                                    action = None,
                                    type = int,
                                    help = '<position_number>')
        
        # argument to hold the observation type
        group = self.cmdparser.add_mutually_exclusive_group()
        group.add_argument('-w',    '--winter',      action = 'store_true', default = True)
        group.add_argument('-c',    '--summer',      action = 'store_true', default = False)
        
        self.getargs()

        self.logger.info(f'fw_goto: args = {self.args}')
        
        if self.args.winter:
            fwname = 'winter'
        elif self.args.summer:
            fwname = 'summer'
        
        fw = self.fwdict[fwname]
        
        pos = self.args.pos[0]
        
        sigcmd = signalCmd('goToFilter', pos)
        
        self.logger.info(f'wintercmd: sending {fw.daemonname} to positon {pos}')

        fw.newCommand.emit(sigcmd)
        
        ## Wait until end condition is satisfied, or timeout ##
        condition = True
        timeout = 90
        # create a buffer list to hold several samples over which the stop condition must be true
        n_buffer_samples = self.config.get('cmd_satisfied_N_samples')
        stop_condition_buffer = [(not condition) for i in range(n_buffer_samples)]

        # get the current timestamp
        start_timestamp = datetime.utcnow().timestamp()
        while True:
            QtCore.QCoreApplication.processEvents()
            time.sleep(self.config['cmd_status_dt'])
            timestamp = datetime.utcnow().timestamp()
            dt = (timestamp - start_timestamp)
            #print(f'wintercmd: wait time so far = {dt}')
            if dt > timeout:
                raise TimeoutError(f'unable to move filter wheel: command timed out after {timeout} seconds before completing.')
            
            stop_condition = ( (self.state[f'{fwname}_fw_filter_pos'] == pos) )
            # do this in 2 steps. first shift the buffer forward (up to the last one. you end up with the last element twice)
            stop_condition_buffer[:-1] = stop_condition_buffer[1:]
            # now replace the last element
            stop_condition_buffer[-1] = stop_condition
            
            if all(entry == condition for entry in stop_condition_buffer):
                self.logger.info(f'wintercmd: successfully completed filter wheel move')
                break 
        
    
    
    ##### CAMERA API METHODS #####
    @cmd
    def startupCamera(self):
        
        self.defineCmdParser('startup the camera')
        # You call this function like this:
            # startupCamera -n 'pa' --winter
        
        self.cmdparser.add_argument('-n', '--addrs',
                                    nargs = '+',
                                    type = str,
                                    default = None,
                                    action = None,
                                    help = "<sensor_address>")
        
        # argument to hold the observation type
        group = self.cmdparser.add_mutually_exclusive_group()
        group.add_argument('-w',    '--winter',      action = 'store_true', default = True)
        group.add_argument('-c',    '--summer',      action = 'store_true', default = False)
        
        self.getargs()

        self.logger.info(f'startupCamera: args = {self.args}')
        
        if self.args.winter:
            camname = 'winter'
        elif self.args.summer:
            camname = 'summer'
        
        addrs = self.args.addrs
        
        camera = self.camdict[camname]
        
        sigcmd = signalCmd('startupCamera', addrs = addrs)
        
        self.logger.info(f'wintercmd: starting up {camera.daemonname}')
        
        camera.newCommand.emit(sigcmd)
    
    @cmd
    def shutdownCamera(self):
        
        self.defineCmdParser('shutdown the camera')
        
        self.cmdparser.add_argument('-n', '--addrs',
                                    nargs = '+',
                                    type = str,
                                    default = None,
                                    action = None,
                                    help = "<sensor_address>")
        
        # argument to hold the observation type
        group = self.cmdparser.add_mutually_exclusive_group()
        group.add_argument('-w',    '--winter',      action = 'store_true', default = True)
        group.add_argument('-c',    '--summer',      action = 'store_true', default = False)
        
        self.getargs()

        self.logger.info(f'startupCamera: args = {self.args}')
        
        addrs = self.args.addrs
        
        if self.args.winter:
            camname = 'winter'
        elif self.args.summer:
            camname = 'summer'
        
        camera = self.camdict[camname]
        
        sigcmd = signalCmd('shutdownCamera', addrs = addrs)
        
        self.logger.info(f'wintercmd: starting up {camera.daemonname}')
        
        camera.newCommand.emit(sigcmd)
    
    @cmd
    def restartSensorDaemon(self):
        
        self.defineCmdParser('restart the sensor daemon')
        
        self.cmdparser.add_argument('-n', '--addrs',
                                    nargs = '+',
                                    type = str,
                                    default = None,
                                    action = None,
                                    help = "<sensor_address>")
        
        # argument to hold the observation type
        group = self.cmdparser.add_mutually_exclusive_group()
        group.add_argument('-w',    '--winter',      action = 'store_true', default = True)
        group.add_argument('-c',    '--summer',      action = 'store_true', default = False)
        
        self.getargs()

        self.logger.info(f'startupCamera: args = {self.args}')
        
        addrs = self.args.addrs
        
        if self.args.winter:
            camname = 'winter'
        elif self.args.summer:
            camname = 'summer'
        
        camera = self.camdict[camname]
        
        sigcmd = signalCmd('restartSensorDaemon', addrs = addrs)
        
        self.logger.info(f'wintercmd: starting up {camera.daemonname}')
        
        camera.newCommand.emit(sigcmd)
    
    @cmd
    def doExposure(self):
        
        self.defineCmdParser('take an exposure with the camera')
        # argument to hold the camera 
        camgroup = self.cmdparser.add_mutually_exclusive_group()
        camgroup.add_argument('-w',    '--winter',      action = 'store_true', default = False)
        camgroup.add_argument('-c',    '--summer',      action = 'store_true', default = False)
        
        # argument to hold the observation type
        imtypegroup = self.cmdparser.add_mutually_exclusive_group()
        imtypegroup.add_argument('-s',    '--science',   action = 'store_true', default = False)
        imtypegroup.add_argument('-d',    '--dark',      action = 'store_true', default = False)
        imtypegroup.add_argument('-f',    '--flat',      action = 'store_true', default = False)
        imtypegroup.add_argument('-foc',  '--focus',     action = 'store_true', default = False)
        imtypegroup.add_argument('-t',    '--test',      action = 'store_true', default = False)
        imtypegroup.add_argument('-b',    '--bias',      action = 'store_true', default = False)
        imtypegroup.add_argument('-p',    '--pointing',  action = 'store_true', default = False)
                
        # also add a mode argument
        self.cmdparser.add_argument('--mode',
                                    nargs = 1,
                                    action = None,
                                    type = str,
                                    default = '',
                                    help = '<image_mode>')
        
        # add ability to pass in image directory
        self.cmdparser.add_argument('--imdir',
                                    nargs = 1,
                                    action = None,
                                    type = str,
                                    default = '',
                                    help = '<image_directory>')
        
        # add ability to pass in sensor addresses
        self.cmdparser.add_argument('-n', '--addrs',
                                    nargs = 1,
                                    action = None,
                                    type = str,
                                    default = None,
                                    help = '<camera_address_list>')
        
        # add ability to pass in sensor addresses
        self.cmdparser.add_argument('--imname',
                                    nargs = 1,
                                    action = None,
                                    type = str,
                                    default = '',
                                    help = '<image_name>')
        
        self.getargs()
        
        ###### Handle the image TYPE ######
        if self.args.science:
            imtype = 'SCIENCE'
        elif self.args.dark:
            imtype = 'DARK'
        elif self.args.flat:
            imtype = 'FLAT'
        elif self.args.focus:
            imtype = 'FOCUS'
        elif self.args.bias:
            imtype = 'BIAS'
        elif self.args.test:
            imtype = 'TEST'
        elif self.args.pointing:
            imtype = 'POINTING'
        else:
            # SET THE DEFAULT
            imtype = 'TEST'
        
        ###### Handle the image MODE ######
        if type(self.args.mode) is list:
            mode = self.args.mode[0] 
        else:
            mode = self.args.mode
        # Set default image mode
        if mode == '':
            mode = None
        
        ###### Handle the image DIRECTORY ######
        if type(self.args.imdir) is list:
            imdir = self.args.imdir[0]
        else:
            imdir = self.args.imdir
        # set default imdir
        if imdir == '':
            imdir = None
            
        ###### Handle the image DIRECTORY ######
        if type(self.args.imname) is list:
            imname = self.args.imname[0]
        else:
            imname = self.args.imname
        # set default imdir
        if imname == '':
            imname = None
        
        ###### Handle the imager ADDRESSES ######
        addrs = self.args.addrs

        
        self.logger.info(f'wintercmd: doExposure: args = {self.args}')
        self.logger.info(f'wintercmd: imtype = {imtype}, mode = {mode}, imdir = {imdir}, addrs = {addrs}')

        
        if self.args.winter:
            camname = 'winter'
        elif self.args.summer:
            camname = 'summer'
        else:
            camname = 'winter'
        
        camera = self.camdict[camname]
        
        # local_camera expects this:
            #doExposure(self, imdir=None, imname = None, imtype = 'test', addrs = None):

        sigcmd = signalCmd('doExposure', imdir = imdir, imname = imname, imtype = imtype, mode = mode, addrs = addrs)
        
        self.logger.info(f'wintercmd: doing exposure on {camera.daemonname}')
        
        camera.newCommand.emit(sigcmd)
        
        
        
        ## Wait until end condition is satisfied, or timeout ##
        condition = True
        #timeout = self.state[f'{camname}_camera_command_timeout']
        timeout = self.state[f'{camname}_camera_exptime'] + 10.0
        # create a buffer list to hold several samples over which the stop condition must be true
        
        
        n_buffer_samples = self.config.get('cmd_satisfied_N_samples')
        ## Change this to trigger on 1 True sample, since the flag is on for a short time and may get skipped
        #n_buffer_samples = 1
        stop_condition_buffer = [(not condition) for i in range(n_buffer_samples)]

        # get the current timestamp
        start_timestamp = datetime.utcnow().timestamp()
        while True:
            QtCore.QCoreApplication.processEvents()
            time.sleep(self.config['cmd_status_dt'])
            
            timestamp = datetime.utcnow().timestamp()
            dt = (timestamp - start_timestamp)
            #print(f'wintercmd: wait time so far = {dt}')
            if dt > timeout:
                raise TimeoutError(f'doExposure command timed out after {timeout} seconds before completing')
            
            stop_condition = ( (self.state[f'{camname}_camera_doing_exposure'] == False) & 
                              (self.state[f'{camname}_camera_command_pass'] == 1))
           
            # do this in 2 steps. first shift the buffer forward (up to the last one. you end up with the last element twice)
            stop_condition_buffer[:-1] = stop_condition_buffer[1:]
            # now replace the last element
            stop_condition_buffer[-1] = stop_condition
            
            if all(entry == condition for entry in stop_condition_buffer):
                self.logger.info(f'wintercmd: finished the doExposure method without timing out :)')
                break 
        
        
        
    @cmd
    def tecSetSetpoint(self):
        
        self.defineCmdParser('set the TEC setpoint')
        
        self.cmdparser.add_argument('temp',
                                    nargs = 1,
                                    action = None,
                                    default = None, 
                                    type = float,
                                    #required = False,
                                    help = '<temperature_celsius>')
        
        self.cmdparser.add_argument('-n', '--addrs',
                                    nargs = '+',
                                    type = str,
                                    default = None,
                                    action = None,
                                    help = "<sensor_address>")
        
        # argument to hold the observation type
        group = self.cmdparser.add_mutually_exclusive_group()
        group.add_argument('-w',    '--winter',      action = 'store_true', default = True)
        group.add_argument('-c',    '--summer',      action = 'store_true', default = False)
        
        self.getargs()

        self.logger.info(f'tecSetSetpoint: args = {self.args}')
        
        if self.args.winter:
            camname = 'winter'
        elif self.args.summer:
            camname = 'summer'
        
        camera = self.camdict[camname]
        
        if self.args.temp is None:
            temp = None
        else:
            temp = self.args.temp[0]
        addrs = self.args.addrs
        
        sigcmd = signalCmd('tecSetSetpoint', temp, addrs = addrs)
        
        msg = f'wintercmd: setting TEC setpoint on {camera.daemonname}'
        if addrs is not None:
            msg+=f' on addrs = {addrs}'
        else:
            msg+=f' on all addrs'
        self.logger.info(msg)
        
        camera.newCommand.emit(sigcmd)
        
        
    @cmd
    def setDetbias(self):
        
        self.defineCmdParser('set the detector bias')
        
        self.cmdparser.add_argument('detbias',
                                    nargs = 1,
                                    action = None,
                                    default = None, 
                                    type = float,
                                    #required = False,
                                    help = '<voltage>')
        
        self.cmdparser.add_argument('-n', '--addrs',
                                    nargs = '+',
                                    type = str,
                                    default = None,
                                    action = None,
                                    help = "<sensor_address>")
        
        # argument to hold the observation type
        group = self.cmdparser.add_mutually_exclusive_group()
        group.add_argument('-w',    '--winter',      action = 'store_true', default = True)
        group.add_argument('-c',    '--summer',      action = 'store_true', default = False)
        
        self.getargs()

        self.logger.info(f'setDetbias: args = {self.args}')
        
        if self.args.winter:
            camname = 'winter'
        elif self.args.summer:
            camname = 'summer'
        
        camera = self.camdict[camname]
        
        if self.args.detbias is None:
            detbias = None
        else:
            detbias = self.args.detbias[0]
        addrs = self.args.addrs
        
        sigcmd = signalCmd('setDetbias', detbias, addrs = addrs)
        
        msg = f'wintercmd: setting DETBIAS on {camera.daemonname}'
        if addrs is not None:
            msg+=f' on addrs = {addrs}'
        else:
            msg+=f' on all addrs'
        self.logger.info(msg)
        
        camera.newCommand.emit(sigcmd)
        
    @cmd
    def tecSetVolt(self):
        
        self.defineCmdParser('set the TEC voltage')
        
        self.cmdparser.add_argument('voltage',
                                    nargs = 1,
                                    action = None,
                                    type = float,
                                    help = '<tec_voltage>')
        
        self.cmdparser.add_argument('-n', '--addrs',
                                    nargs = '+',
                                    type = str,
                                    default = None,
                                    action = None,
                                    help = "<sensor_address>")
        
        # argument to hold the observation type
        group = self.cmdparser.add_mutually_exclusive_group()
        group.add_argument('-w',    '--winter',      action = 'store_true', default = True)
        group.add_argument('-c',    '--summer',      action = 'store_true', default = False)
        
        self.getargs()

        self.logger.info(f'tecSetVolt: args = {self.args}')
        
        if self.args.winter:
            camname = 'winter'
        elif self.args.summer:
            camname = 'summer'
        
        camera = self.camdict[camname]
        
        voltage = self.args.voltage[0]
        addrs = self.args.addrs
        
        sigcmd = signalCmd('tecSetVolt', voltage, addrs = addrs)
        
        self.logger.info(f'wintercmd: setting TEC voltage on {camera.daemonname} to {voltage} V')
        
        camera.newCommand.emit(sigcmd)
        
    @cmd
    def setExposure(self):
        
        self.defineCmdParser('set the exposure time')
        
        self.cmdparser.add_argument('exptime',
                                    nargs = 1,
                                    action = None,
                                    type = float,
                                    help = '<exptime_seconds>')
        
        self.cmdparser.add_argument('-n', '--addrs',
                                    nargs = '+',
                                    type = str,
                                    default = None,
                                    action = None,
                                    help = "<sensor_address>")
        
        # argument to hold the observation type
        group = self.cmdparser.add_mutually_exclusive_group()
        group.add_argument('-w',    '--winter',      action = 'store_true', default = True)
        group.add_argument('-c',    '--summer',      action = 'store_true', default = False)
        
        self.getargs()

        self.logger.info(f'setExposure: args = {self.args}')
        
        if self.args.winter:
            camname = 'winter'
        elif self.args.summer:
            camname = 'summer'
        
        camera = self.camdict[camname]
        
        exptime = self.args.exptime[0]
        
        addrs = self.args.addrs
        
        sigcmd = signalCmd('setExposure', exptime, addrs = addrs)
        
        self.logger.info(f'wintercmd: setting exposure time on {camera.daemonname}')
        
        camera.newCommand.emit(sigcmd)
        
        ## Wait until end condition is satisfied, or timeout ##
        if addrs is not None:
            #TODO: ditch this and fix the stop condition
            # if we checking specific addresses then we need a different way to assess success
            return
        condition = True
        timeout = 10
        # create a buffer list to hold several samples over which the stop condition must be true
        n_buffer_samples = self.config.get('cmd_satisfied_N_samples')
        stop_condition_buffer = [(not condition) for i in range(n_buffer_samples)]

        # get the current timestamp
        start_timestamp = datetime.utcnow().timestamp()
        while True:
            QtCore.QCoreApplication.processEvents()
            time.sleep(self.config['cmd_status_dt'])
            timestamp = datetime.utcnow().timestamp()
            dt = (timestamp - start_timestamp)
            #print(f'wintercmd: wait time so far = {dt}')
            if dt > timeout:
                self.logger.info(f'command timed out after {timeout} seconds before completing. Requested exptime = {exptime}, but it is {self.state["ccd_exptime"]}')
                break
            
            stop_condition = ( (self.state[f'{camname}_camera_exptime'] == exptime) & 
                              (self.state[f'{camname}_camera_command_pass'] == 1))
            # do this in 2 steps. first shift the buffer forward (up to the last one. you end up with the last element twice)
            stop_condition_buffer[:-1] = stop_condition_buffer[1:]
            # now replace the last element
            stop_condition_buffer[-1] = stop_condition
            
            if all(entry == condition for entry in stop_condition_buffer):
                
                self.logger.info(f'wintercmd: {camname} camera exptime set successfully.')
                try_again = False
                break 
            try_again = True
        
        if try_again:
            pass
            
    
    @cmd
    def tecStart(self):
        
        self.defineCmdParser('start the TEC')
        """
        self.cmdparser.add_argument('coeffs',
                                    nargs = 1,
                                    action = None,
                                    type = list,
                                    default = [],
                                    help = '<exptime_seconds>')
        """
        # argument to hold the observation type
        group = self.cmdparser.add_mutually_exclusive_group()
        group.add_argument('-w',    '--winter',      action = 'store_true', default = True)
        group.add_argument('-c',    '--summer',      action = 'store_true', default = False)
        
        self.cmdparser.add_argument('-n', '--addrs',
                                    nargs = '+',
                                    type = str,
                                    default = None,
                                    action = None,
                                    help = "<sensor_address>")
        
        self.getargs()

        self.logger.info(f'tecStart: args = {self.args}')
        
        if self.args.winter:
            camname = 'winter'
        elif self.args.summer:
            camname = 'summer'
        
        camera = self.camdict[camname]
            
        addrs = self.args.addrs
                
        sigcmd = signalCmd('tecStart', addrs = addrs)
        
        self.logger.info(f'wintercmd: starting TEC on {camera.daemonname}')
        
        camera.newCommand.emit(sigcmd)
        
    @cmd
    def tecStop(self):
            
        self.defineCmdParser('stop the TEC')
        
        
        # argument to hold the observation type
        group = self.cmdparser.add_mutually_exclusive_group()
        group.add_argument('-w',    '--winter',      action = 'store_true', default = True)
        group.add_argument('-c',    '--summer',      action = 'store_true', default = False)
        
        self.cmdparser.add_argument('-n', '--addrs',
                                    nargs = '+',
                                    type = str,
                                    default = None,
                                    action = None,
                                    help = "<sensor_address>")
        
        self.getargs()

        self.logger.info(f'tecStop: args = {self.args}')
        
        if self.args.winter:
            camname = 'winter'
        elif self.args.summer:
            camname = 'summer'
        
        camera = self.camdict[camname]
           
        addrs = self.args.addrs
        
        sigcmd = signalCmd('tecStop', addrs = addrs)
        
        self.logger.info(f'wintercmd: stopping TEC on {camera.daemonname}')
        
        camera.newCommand.emit(sigcmd)
    
    @cmd
    def tecSetCoeffs(self):
        """
        Convenience function for tuning the WINTER sensor PID parameters
        """
        
        self.defineCmdParser('set the TEC PID coeffs')
        
        self.cmdparser.add_argument('coeffs',
                                    nargs = 3,
                                    action = None,
                                    default = None, 
                                    #required = False,
                                    type = float,
                                    help = '<PID_coeffs_Kp_Ki_Kd>')
        
        self.cmdparser.add_argument('-n', '--addrs',
                                    nargs = '+',
                                    type = str,
                                    default = None,
                                    action = None,
                                    help = "<sensor_address>")
        
        # argument to hold the observation type
        group = self.cmdparser.add_mutually_exclusive_group()
        group.add_argument('-w',    '--winter',      action = 'store_true', default = True)
        group.add_argument('-c',    '--summer',      action = 'store_true', default = False)
        
        self.getargs()

        self.logger.info(f'tecSetCoeffs: args = {self.args}')
        
        if self.args.winter:
            camname = 'winter'
        elif self.args.summer:
            camname = 'summer'
        
        camera = self.camdict[camname]
        
        if self.args.coeffs is None:
            Kp = None
            Ki = None
            Kd = None
        else:
            Kp = self.args.coeffs[0]
            Ki = self.args.coeffs[1]
            Kd = self.args.coeffs[2]
        addrs = self.args.addrs
        
        sigcmd = signalCmd('tecSetCoeffs', Kp, Ki, Kd, addrs = addrs)
        
        msg = f'wintercmd: setting TEC PID coefficients on {camera.daemonname}'
        if addrs is not None:
            msg+=f' on addrs = {addrs}'
        else:
            msg+=f' on all addrs'
        self.logger.info(msg)
        
        camera.newCommand.emit(sigcmd)
    
    @cmd
    def killCameraDaemon(self):
            
        self.defineCmdParser('kill the camera daemon')
        
        
        # argument to hold the observation type
        group = self.cmdparser.add_mutually_exclusive_group()
        group.add_argument('-w',    '--winter',      action = 'store_true', default = True)
        group.add_argument('-c',    '--summer',      action = 'store_true', default = False)
        
        
        
        self.getargs()

        self.logger.info(f'Kill camera daemon: args = {self.args}')
        
        if self.args.winter:
            camname = 'winter'
        elif self.args.summer:
            camname = 'summer'
        
        camera = self.camdict[camname]
           
        
        sigcmd = signalCmd('killCameraDaemon')
        
        self.logger.info(f'wintercmd: killCameraDaemon on {camera.daemonname}')
        
        camera.newCommand.emit(sigcmd)
    
    
    ####### End Camera API Methods #######
    
    @cmd
    def checkCamera(self):
        self.defineCmdParser('check the camera')
        
        
        # argument to hold the observation type
        group = self.cmdparser.add_mutually_exclusive_group()
        group.add_argument('-w',    '--winter',      action = 'store_true', default = True)
        group.add_argument('-c',    '--summer',      action = 'store_true', default = False)
        
        
        
        self.getargs()

        self.logger.info(f'check the camera status: args = {self.args}')
        
        if self.args.winter:
            camname = 'winter'
        elif self.args.summer:
            camname = 'summer'
        
        camera = self.camdict[camname]
           
        if camname == 'winter':
            sigcmd = signalCmd('checkWINTERCamera')
            self.roboThread.newCommand.emit(sigcmd)
        else:
            self.logger.info(f'wintercmd: checkCamera only defined for WINTER')
    
    
    @cmd
    def generate_supernovae_db(self):
        self.defineCmdParser('Generate supernovae observation schedule')
        self.cmdparser.add_argument('source', nargs = 1, default = 'ZTF', action = None)
        self.getargs()
        source = self.args.source[0]
        if source == 'Rochester':
            URL = 'https://www.rochesterastronomy.org/sn2021/snlocations.html'
        else:
            URL = 'https://sites.astro.caltech.edu/ztf/bts/explorer.php?f=s&subsample=sn&classstring=Ia&classexclude=&quality=y&purity=y&ztflink=lasair&lastdet=&startsavedate=&startpeakdate=&startra=&startdec=&startz=&startdur=&startrise=&startfade=&startpeakmag=&startabsmag=&starthostabs=&starthostcol=&startb=&startav=&endsavedate=&endpeakdate=&endra=&enddec=&endz=&enddur=&endrise=&endfade=&endpeakmag=19.0&endabsmag=&endhostabs=&endhostcol=&endb=&endav='
        connection = sql.connect("/home/winter/data/schedules/Supernovae.db")
        print("Downloading entries")
        html = requests.get(URL).content
        df_list = pd.read_html(html)
        df = df_list[-1]
        ra = []
        dec = []
        if source == 'Rochester':
            print("Generating Rochester Database")
            for i, j in zip(df["R.A."], df["Decl."]):
                c = SkyCoord(i, j, unit=(u.hourangle, u.deg))
                ra.append(c.ra.radian)
                dec.append(c.dec.radian)
        else:
            print("Generating ZTF Database")
            new_header = [x[1] for x in df.columns]
            df.columns = new_header
            for i, j in zip(df["RA"], df["Dec"]):
                c = SkyCoord(i, j, unit=(u.hourangle, u.deg))
                ra.append(c.ra.radian)
                dec.append(c.dec.radian)
        df.index = df.index + 1
        df.insert(loc=2, column='visitExpTime', value=30)
        df.insert(loc=0, column='fieldRA', value=ra)
        df.insert(loc=1, column='fieldDec', value=dec)
        df.insert(loc=5, column='filter', value="r")
        warnings.filterwarnings("ignore", category=UserWarning)
        df.to_sql('Summary', con=connection, if_exists='replace', index_label = "obsHistID")
        df_2 = pd.DataFrame.from_dict({"Nonsense that is required": [1, 2, 3, 4, 5]})
        df_2.to_sql('Fields', con=connection, if_exists='replace', index_label = "fieldID")
        print("Finished")
    @cmd
    #def total_startup(self):
    def do_startup(self):    
        # NPL 12-15-21: porting this over to roboOperator
        
        
        self.defineCmdParser('start up the observatory and ready it for observations')
        
        # option to startup the cameras
        self.cmdparser.add_argument('--cameras', '-c',
                                    action = 'store_true',
                                    default = False,
                                    help = "<startup_cameras?>")
        
        self.getargs()
        print(f'wintercmd: args = {self.args}')
        
        startup_cameras = self.args.cameras
        
        sigcmd = signalCmd('do_startup', startup_cameras = startup_cameras)
        
        self.roboThread.newCommand.emit(sigcmd)
        
        ## Wait until end condition is satisfied, or timeout ##
        condition = True
        timeout = 300
        # create a buffer list to hold several samples over which the stop condition must be true
        n_buffer_samples = self.config.get('cmd_satisfied_N_samples')
        stop_condition_buffer = [(not condition) for i in range(n_buffer_samples)]

        # get the current timestamp
        start_timestamp = datetime.utcnow().timestamp()
        while True:
            QtCore.QCoreApplication.processEvents()
            time.sleep(self.config['cmd_status_dt'])
            timestamp = datetime.utcnow().timestamp()
            dt = (timestamp - start_timestamp)
            #print(f'wintercmd: wait time so far = {dt}')
            if dt > timeout:
                raise TimeoutError(f'unable to run startup: command timed out after {timeout} seconds before completing.')
            conds = []
            # make sure the observatory ready flag is true
            conds.append(self.state['robo_observatory_ready'] == 1)
            
            # make sure a bunch of other conditions on things that are part of startup are satisfied
            # make sure the dome is near it's park position
            #conds.append(np.abs(self.state['dome_az_deg'] - self.config['dome_home_az_degs']) < 1.0)
            delta_az = np.abs(self.state['dome_az_deg'] - self.config['dome_home_az_degs']) 
            min_delta_az = np.min([360 - delta_az, delta_az])
            conds.append(min_delta_az < 1.0)
            
            # make sure dome tracking is off
            conds.append(self.state['dome_tracking_status'] == False)
            
            
            ### TELESCOPE CHECKS ###
            # make sure mount tracking is off
            conds.append(self.state['mount_is_tracking'] == False)
            
            # make sure the mount is near home
            delta_az = np.abs(self.state['mount_az_deg'] - self.config['telescope']['home_az_degs']) 
            min_delta_az = np.min([360 - delta_az, delta_az])
            conds.append(min_delta_az < 1.0)
            conds.append(np.abs(self.state['mount_alt_deg'] - self.config['telescope']['home_alt_degs']) < 1.0) # home is 45 deg, so this isn't really doing anything
            conds.append(np.abs(self.state['rotator_mech_position'] - self.config['telescope']['rotator_home_degs']) < 1.0) #NPL 12-15-21 these days it sags to ~ -27 from -25
            
            
            stop_condition = all(conds)
            # do this in 2 steps. first shift the buffer forward (up to the last one. you end up with the last element twice)
            stop_condition_buffer[:-1] = stop_condition_buffer[1:]
            # now replace the last element
            stop_condition_buffer[-1] = stop_condition
            
            if all(entry == condition for entry in stop_condition_buffer):
                self.logger.info(f'wintercmd: startup completed successfully')
                print('Startup has finished :-)')

                break 
        
        
    
    @cmd
    def total_shutdown(self):
        # NPL 12-15-21: porting this over to roboOperator
        sigcmd = signalCmd('do_shutdown')
        
        self.roboThread.newCommand.emit(sigcmd)
        
        ## Wait until end condition is satisfied, or timeout ##
        condition = True
        timeout = 300
        # create a buffer list to hold several samples over which the stop condition must be true
        n_buffer_samples = self.config.get('cmd_satisfied_N_samples')
        stop_condition_buffer = [(not condition) for i in range(n_buffer_samples)]

        # get the current timestamp
        start_timestamp = datetime.utcnow().timestamp()
        while True:
            QtCore.QCoreApplication.processEvents()
            time.sleep(self.config['cmd_status_dt'])
            timestamp = datetime.utcnow().timestamp()
            dt = (timestamp - start_timestamp)
            #print(f'wintercmd: wait time so far = {dt}')
            if dt > timeout:
                raise TimeoutError(f'unable to connect to shut down observatory: command timed out after {timeout} seconds before completing.')
            
            stop_condition = ( (self.state['robo_observatory_stowed'] == 1) )
            # do this in 2 steps. first shift the buffer forward (up to the last one. you end up with the last element twice)
            stop_condition_buffer[:-1] = stop_condition_buffer[1:]
            # now replace the last element
            stop_condition_buffer[-1] = stop_condition
            
            if all(entry == condition for entry in stop_condition_buffer):
                self.logger.info(f'wintercmd: successfully shut down observatory')
                print('Shutdown has finished :-)')

                break 
        
        
        """
        try:
            self.mount_tracking_off()
            self.dome_tracking_off()
            self.mount_home()
            self.dome_go_home()
            self.mirror_cover_close()
            self.waitForCondition('dome_home_status', 1)
            self.waitForCondition('mount_is_slewing', False)
        except Exception:
            print('Failed while going home')
        try:
            self.rotator_home()
            self.waitForCondition('rotator_is_slewing', 0)
            self.rotator_disable()
        except Exception:
            print('Failed while disabling rotator')
        try:
            self.mount_alt_off()
            self.mount_az_off()
            self.m2_focuser_disable()
        except Exception:
            print("Failed while disabling mount and focuser")
        try:
            self.dome_close()
            print ('Closing dome')
            time.sleep(20)
            self.dome_givecontrol()
            print('Shutdown has finished :-)')
        except Exception:
            print('Failed during closing step')
        """
    
    @cmd
    def stow_observatory(self):
        """
        this is a smarter version of total_shutdown which figures out what to
        do depending on whether the observatory state is already stowed/ready/etc
        """
        self.defineCmdParser('shut down the observatory and stow it safely')
        
        # option to startup the cameras
        self.cmdparser.add_argument('--cameras', '-c',
                                    action = 'store_true',
                                    default = False,
                                    help = "<shutdown_cameras?>")
        
        self.getargs()
        print(f'wintercmd: args = {self.args}')
        
        
        
        shutdown_cameras = self.args.cameras
        
        
        self.defineCmdParser('stow the observatory')
        sigcmd = signalCmd('stow_observatory', shutdown_cameras = shutdown_cameras)
        
        self.roboThread.newCommand.emit(sigcmd)
    
    
    @cmd
    def total_restart(self):
        self.total_shutdown()
        self.total_startup()
        
    
    
        """
class ManualCmd(Wintercmd):

    def __init__(self, config, state, telescope, logger):
        super().__init__(config, state, telescope, logger)
        self.prompt = 'wintercmd(M): '
        """
    
        


        """
class ScheduleCmd(Wintercmd):

    def __init__(self, config, state, telescope, logger):
        super().__init__(config, state, telescope, logger)
        self.prompt = 'wintercmd(S): '
        """    
