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
from datetime import datetime
import numpy as np
import shlex
import astropy.coordinates
import astropy.time 
import astropy.units as u
import threading


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

# GLOBAL VARS

# load the config
CONFIG_FILE = wsp_path + '/config/config.yaml'
CONFIG = utils.loadconfig(CONFIG_FILE)
LOGGER = logging_setup.setup_logger(wsp_path, CONFIG)

#redefine the argument parser so it exits nicely and execptions are handled better

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
        
        except Exception as e:
            '''
            Exceptions are already handled by the argument parser
            so do nothing here.
            '''
            msg = (f'wintercmd: Could not execute command {func.__name__}: {e}')
            LOGGER.info(msg)
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
    
    
    def __init__(self, base_directory, config, state, mirror_cover, daemonlist, telescope, dome, chiller, pdu1, logger, viscam, ccd):
        # init the parent class
        #super().__init__()
        super(Wintercmd, self).__init__()
        
        # things that define the command line prompt
        self.intro = 'Welcome to wintercmd, the WINTER Command Interface'
        self.prompt = 'wintercmd: '
        
        # grab some useful inputs
        self.state = state
        self.daemonlist = daemonlist
        self.telescope = telescope
        self.dome = dome
        self.chiller = chiller
        self.pdu1 = pdu1
    
        self.base_directory = base_directory
        self.config = config
        self.logger = logger
        self.viscam = viscam
        self.ccd = ccd
        self.mirror_cover = mirror_cover
        self.defineParser()
    
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
                                    action = None,
                                    type = float,
                                    help = '<ra_hours> <dec_degs>')
        self.getargs()
        ra = self.args.position[0]
        dec = self.args.position[1]
        self.telescope.mount_goto_ra_dec_j2000(ra_hours = ra, dec_degs = dec)
        
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
            #print('entering loop')
            time.sleep(self.config['cmd_status_dt'])
            timestamp = datetime.utcnow().timestamp()
            dt = (timestamp - start_timestamp)
            #print(f'wintercmd: wait time so far = {dt}')
            if dt > timeout:
                raise TimeoutError(f'command timed out after {timeout} seconds before completing')
            self.logger.info(f'wintercmd (thread {threading.get_ident()}: count = {self.state["count"]}')
            self.logger.info(f'wintercmd (thread {threading.get_ident()}: mount_is_slewing: {self.state["mount_is_slewing"]}')
            self.logger.info(f'wintercmd (thread {threading.get_ident()}: alt_dist_to_target: {self.state["mount_alt_dist_to_target"]}')
            self.logger.info(f'wintercmd (thread {threading.get_ident()}: az_dist_to_target: {self.state["mount_az_dist_to_target"]}')
            self.logger.info('')
            stop_condition = ( (not self.state['mount_is_slewing']) & (abs(self.state['mount_az_dist_to_target']) < 0.1) & (abs(self.state['mount_alt_dist_to_target']) < 0.1))

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
        timeout = 2000.0
        # wait for the telescope to stop moving before returning
        # create a buffer list to hold several samples over which the stop condition must be true
        n_buffer_samples = self.config.get('cmd_satisfied_N_samples')
        stop_condition_buffer = [(not condition) for i in range(n_buffer_samples)]

        # get the current timestamp
        start_timestamp = datetime.utcnow().timestamp()
        while True:
            #print('entering loop')
            time.sleep(self.config['cmd_status_dt'])
            timestamp = datetime.utcnow().timestamp()
            dt = (timestamp - start_timestamp)
            #print(f'wintercmd: wait time so far = {dt}')
            if dt > timeout:
                raise TimeoutError(f'command timed out after {timeout} seconds before completing')
            dist = ( (alt - self.state["mount_alt_deg"])**2 + (az - self.state["mount_az_deg"])**2 )**0.5
            self.logger.info(f'wintercmd (thread {threading.get_ident()}: count = {self.state["count"]}')
            self.logger.info(f'wintercmd (thread {threading.get_ident()}: mount_is_slewing: {self.state["mount_is_slewing"]}')
            self.logger.info(f'wintercmd (thread {threading.get_ident()}: alt_dist_to_target: {self.state["mount_alt_dist_to_target"]}')
            self.logger.info(f'wintercmd (thread {threading.get_ident()}: az_dist_to_target: {self.state["mount_az_dist_to_target"]}')
            self.logger.info(f'wintercmd (thread {threading.get_ident()}: dist_to_target: {dist} deg')
            self.logger.info('')
            
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
        #TODO: untested
        """
        self.defineCmdParser('save the current pointing model to the specified file')
        self.cmdparser.add_argument('filename',
                                    nargs = 1,
                                    action = None,
                                    help = '<filepath>')
        
        self.getargs()
        filename = self.args.filename[0]
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
    def do_focusLoop(self):
        """
        Runs a focus loop for a given filter by taking a set of images and collecting the relative
        size of objects in the image. Will collimate mirror at optimal position.
        
        """
        
        self.defineCmdParser('retrieve whether or not a plot will be displayed based on img fwhm')
        self.cmdparser.add_argument('plot',
                                    nargs = 1,
                                    action = None,
                                    help = '<position_steps>')
        
        self.getargs()
        
        plotting = False
        
        if self.args.plot[0] == "plot":
            plotting = True
            print('I am plotting this time!')
        
        images = []
        
        current_filter = self.config['focus_loop_param']['current_filter']
        loop = summerFocusLoop.Focus_loop(current_filter, self.config)
        
        filter_range = loop.return_Range()
        
        
        system = 'ccd'
        '''
        try:
            for dist in filter_range:
                Collimate and take exposure
                self.telescope.focuser_goto(target = dist)
                time.sleep(2)
                self.ccd_do_exposure()
                time.sleep(2)
                images.append(loop.return_Path())
        except Exception as e:
            msg = f'wintercmd: could not set up {system} due to {e.__class__.__name__}, {e}'
            print(msg)
           ''' 
        #images_16 = loop.fits_64_to_16(self, images, filter_range)
        images = ['/home/winter/data/images/20210730/SUMMER_20210729_225354_Camera0.fits','/home/winter/data/images/20210730/SUMMER_20210729_225417_Camera0.fits','/home/winter/data/images/20210730/SUMMER_20210729_225438_Camera0.fits','/home/winter/data/images/20210730/SUMMER_20210729_225500_Camera0.fits','/home/winter/data/images/20210730/SUMMER_20210729_225521_Camera0.fits','/home/winter/data/images/20210730/SUMMER_20210729_225542_Camera0.fits','/home/winter/data/images/20210730/SUMMER_20210729_225604_Camera0.fits']
        
        system = 'focuser'
        
        try:
            #find the ideal focuser position
            print('Focuser re-aligning at %s microns'%(filter_range[0]))
            self.telescope.focuser_goto(target = filter_range[0])
            med_values = loop.rate_images(images)
            focuser_pos = filter_range[med_values.index(min(med_values))]

            print('Focuser_going to final position at %s microns'%(focuser_pos))
            self.telescope.focuser_goto(target = focuser_pos)
            if plotting:
                loop.plot_focus_curve()

        except FileNotFoundError:
            print("You are trying to modify a catalog file or an image with no stars")
            pass

        except Exception as e:
            msg = f'wintercmd: could not set up {system} due to {e.__class__.__name__}, {e}'
            print(msg)
        
        return focuser_pos
            
    @cmd
    def m2_focuser_enable(self):
        """
        Created: NPL 2-4-21
        """
        self.defineCmdParser('enable the m2 focus motor')
        self.telescope.focuser_enable()
    
    @cmd
    def m2_focuser_disable(self):
        """
        Created: NPL 2-4-21
        """
        self.defineCmdParser('disable the m2 focus motor')
        self.telescope.focuser_disable()
    
    @cmd
    def m2_focuser_goto(self):
        """
        Created: NPL 2-4-21
        """
        self.defineCmdParser('send M2 focuser to specified position in steps')
        self.cmdparser.add_argument('position',
                                    nargs = 1,
                                    action = None,
                                    help = '<position_steps>')
        
        self.getargs()
        target = self.args.position[0]
        self.telescope.focuser_goto(target = target)
    
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
        self.logger.info(f'wintercmd rotator_goto_mech: target = {target}, type(target) = {type(target)}')
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
            #print('entering loop')
            time.sleep(self.config['cmd_status_dt'])
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
            #print('entering loop')
            time.sleep(self.config['cmd_status_dt'])
            timestamp = datetime.utcnow().timestamp()
            dt = (timestamp - start_timestamp)
            #print(f'wintercmd: wait time so far = {dt}')
            if dt > timeout:
                raise TimeoutError(f'command timed out after {timeout} seconds before completing')
            
            stop_condition = (self.telescope.state['wrap_check_enabled'] )
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
            
            stop_condition = (self.state['rotator_is_slewing'] == False) & (np.abs(rotator_field_angle_norm - target_norm) < 0.05)
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
        timeout = 100.0
        # wait for the telescope to stop moving before returning
        # create a buffer list to hold several samples over which the stop condition must be true
        n_buffer_samples = self.config.get('cmd_satisfied_N_samples')
        stop_condition_buffer = [(not condition) for i in range(n_buffer_samples)]

        # get the current timestamp
        start_timestamp = datetime.utcnow().timestamp()
        while True:
            #print('entering loop')
            time.sleep(self.config['cmd_status_dt'])
            timestamp = datetime.utcnow().timestamp()
            dt = (timestamp - start_timestamp)
            #print(f'wintercmd: wait time so far = {dt}')
            if dt > timeout:
                raise TimeoutError(f'command timed out after {timeout} seconds before completing')
            
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
        
        
        
        self.getargs()
            # this is what happens when called from the cmd line. otherwise include az so it can be called internally
        az = np.float(self.args.azimuth[0])
        sigcmd = signalCmd('GoTo', az)
        self.dome.newCommand.emit(sigcmd)
        
        #self.logger.info(f'self.state["dome_az_deg"] = {self.state["dome_az_deg"]}, type = {type(self.state["dome_az_deg"])}')
        #self.logger.info(f'az = {az}, type = {type(az)}')
        
        ## Wait until end condition is satisfied, or timeout ##
        condition = True
        timeout = 300
        # create a buffer list to hold several samples over which the stop condition must be true
        n_buffer_samples = self.config.get('cmd_satisfied_N_samples')
        stop_condition_buffer = [(not condition) for i in range(n_buffer_samples)]

        # get the current timestamp
        start_timestamp = datetime.utcnow().timestamp()
        while True:
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
        """# wait until the dome is homed.
        #TODO add a timeout
        n_buffer_samples = self.config.get('cmd_satisfied_N_samples')
        stop_condition_buffer = [True for i in range(n_buffer_samples)]
        while True:
            #self.logger.info(f'STOP CONDITION BUFFER = {stop_condition_buffer}')
            time.sleep(self.config['cmd_status_dt'])
            stop_condition = ( (self.state['dome_status'] == self.config['Dome_Status_Dict']['Dome_Status']['STOPPED']) and (np.abs(self.state['dome_az_deg'] - az ) < 0.5 ) )
            # do this in 2 steps. first shift the buffer forward (up to the last one. you end up with the last element twice)
            stop_condition_buffer[:-1] = stop_condition_buffer[1:]
            # now replace the last element
            stop_condition_buffer[-1] = stop_condition
            
            if all(entry == True for entry in stop_condition_buffer):
                break
        self.logger.info('wintercmd: dome homing complete')"""
        
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
        sigcmd = signalCmd('GoTo', az)
        self.dome.newCommand.emit(sigcmd)
        
        """# wait until the dome is homed.
        #TODO add a timeout
        n_buffer_samples = self.config.get('cmd_satisfied_N_samples')
        stop_condition_buffer = [True for i in range(n_buffer_samples)]
        
        while True:
            #self.logger.info(f'wintercmd: dome_go_home  STOP CONDITION BUFFER = {stop_condition_buffer}')
            time.sleep(self.config['cmd_status_dt'])
            stop_condition = ( (self.state['dome_status'] == self.config['Dome_Status_Dict']['Dome_Status']['STOPPED']) and (np.abs(self.state['dome_az_deg'] - az ) < 0.5 ) )
            # do this in 2 steps. first shift the buffer forward (up to the last one. you end up with the last element twice)
            stop_condition_buffer[:-1] = stop_condition_buffer[1:]
            # now replace the last element
            stop_condition_buffer[-1] = stop_condition
            
            if all(entry == True for entry in stop_condition_buffer):
                break
        """
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
        
    @cmd
    def dome_tracking_off(self):
        """ created: NPL 6-12-21 
        turn on tracking so that dome follows telescope
        """
        self.defineCmdParser('stop making dome track telescope')
        sigcmd = signalCmd('TrackingOff')
        self.dome.newCommand.emit(sigcmd)
    
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
    
    @cmd
    def pdu_on(self):
        """
        created: NPL 6-7-21
        
        this turns on a channel on the specified PDU
        
        call: pdu_on 1 8, turns on ch 8 on pdu 1

        """
        
        self.defineCmdParser('execute routine from specified text file. default path is wsp/routines')
        self.cmdparser.add_argument('channel',
                                    nargs = 2,
                                    action = None,
                                    help = "<pdu_num> <chan_num>")
        self.getargs()
        pdu_num = self.args.channel[0]
        chan_num = self.args.channel[1]
        
        # send the on command
        if pdu_num == 1:
            self.pdu1.on(chan_num)
   
    @cmd
    def pdu_off(self):
        """
        created: NPL 6-7-21
        
        this turns on a channel on the specified PDU
        
        call: pdu_on 1 8, turns on ch 8 on pdu 1

        """
        
        self.defineCmdParser('execute routine from specified text file. default path is wsp/routines')
        self.cmdparser.add_argument('channel',
                                    nargs = 2,
                                    action = None,
                                    help = "<pdu_num> <chan_num>")
        self.getargs()
        pdu_num = self.args.channel[0]
        chan_num = self.args.channel[1]
        
        # send the on command
        if pdu_num == 1:
            self.pdu1.on(chan_num)
             
    
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
            self.roboThread.restartRoboSignal.emit()
    
    @cmd
    def robo_do_currentObs(self):
        self.defineCmdParser('do the current observation')
        self.roboThread.do_currentObs_Signal.emit()
        
    @cmd
    def robo_do_exposure(self):
        self.defineCmdParser('tell the robotic operator to take an image with the camera')
        self.roboThread.doExposureSignal.emit()
        
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
                           obstype = 'altaz',
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
                           obstype = 'radec',
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
                           obstype = 'object',
                           target = obj,
                           tracking = 'auto',
                           field_angle = 'auto')
        
        self.roboThread.newCommand.emit(sigcmd)
    
    @cmd
    def robo_remakePointingModel(self):
        self.defineCmdParser('start the robotic operator')
        
        sigcmd = signalCmd('remakePointingModel')
        self.roboThread.newCommand.emit(sigcmd)
        
        
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
        if self.promptThread and self.execThread:
            self.promptThread.stop()
            self.execThread.stop()
        
        # try to shut down the ccd camera client
        try:
            self.parse('ccd_shutdown_client')
            time.sleep(1)
        except Exception as e:
            print(f'could not shut down ccd camera client. {type(e)}: {e}')
        
        # try to shut down the ccd camera server
        """try:
            self.parse('ccd_killServer')
            time.sleep(1)
        except Exception as e:
            print(f'could not shut down ccd camera huaso server. {type(e)}: {e}')"""
        
        #sys.exit()#sigint_handler()
        
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
        QtCore.QCoreApplication.quit()

##### Mirror cover commands ####
        
    @cmd
    def mirror_cover_connect(self):
        self.defineCmdParser('Connect to mirror cover server')
        self.mirror_cover.sendreceive("connect")
        
    @cmd
    def mirror_cover_open(self):
        self.defineCmdParser('Open mirror cover')
        self.mirror_cover.sendreceive("beginopen")
        
    @cmd
    def mirror_cover_close(self):
        self.defineCmdParser('Close mirror cover')
        self.mirror_cover.sendreceive("beginclose")

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
        self.viscam.send_shutter_command(shutter_cmd)

    @cmd
    def command_filter_wheel(self):
        self.defineCmdParser('Command viscam filter wheel')
                  
        self.cmdparser.add_argument('fw_cmd',
              nargs = 1,
              action = None,
              help = '<fw_cmd_int>')

        self.getargs()
        fw_cmd = self.args.fw_cmd[0]
        self.viscam.send_filter_wheel_command(fw_cmd)
        
        
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
        timeout = 15
        # create a buffer list to hold several samples over which the stop condition must be true
        n_buffer_samples = self.config.get('cmd_satisfied_N_samples')
        stop_condition_buffer = [(not condition) for i in range(n_buffer_samples)]

        # get the current timestamp
        start_timestamp = datetime.utcnow().timestamp()
        while True:
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
        sigcmd = signalCmd('doExposure')
        self.ccd.newCommand.emit(sigcmd)
        
        self.logger.info(f'wintercmd: running ccd_do_exposure in thread {threading.get_ident()}')
        
        ## Wait until end condition is satisfied, or timeout ##
        condition = True
        timeout = self.state['ccd_exposureTimeout'] + 10
        # create a buffer list to hold several samples over which the stop condition must be true
        
        
        #n_buffer_samples = self.config.get('cmd_satisfied_N_samples')
        # Change this to trigger on 1 True sample, since the flag is on for a short time and may get skipped
        n_buffer_samples = 1
        stop_condition_buffer = [(not condition) for i in range(n_buffer_samples)]

        # get the current timestamp
        start_timestamp = datetime.utcnow().timestamp()
        while True:
            time.sleep(self.config['cmd_status_dt'])
            timestamp = datetime.utcnow().timestamp()
            dt = (timestamp - start_timestamp)
            #print(f'wintercmd: wait time so far = {dt}')
            if dt > timeout:
                raise TimeoutError(f'command timed out after {timeout} seconds before completing')
            
            stop_condition = ( (self.state['ccd_doing_exposure'] == False) & (self.state['ccd_image_saved_flag']))
            self.logger.info(f'count = {self.state["count"]}')
            self.logger.info(f'wintercmd: ccd_doing_exposure = {self.state["ccd_doing_exposure"]}, ccd_image_saved_flag = {self.state["ccd_image_saved_flag"]}')
            self.logger.info('')
            # do this in 2 steps. first shift the buffer forward (up to the last one. you end up with the last element twice)
            stop_condition_buffer[:-1] = stop_condition_buffer[1:]
            # now replace the last element
            stop_condition_buffer[-1] = stop_condition
            
            if all(entry == condition for entry in stop_condition_buffer):
                self.logger.info(f'wintercmd: finished the do exposure method without timing out :)')
                break 
        
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
        
    @cmd
    def total_startup(self):
        try:
            self.dome_takecontrol()
        except Exception:
            print('Could not take control of dome')
        try:
            self.mount_connect()
            self.mount_tracking_off()
            self.mount_az_on()
            self.mount_alt_on()
            self.dome_tracking_off()
            self.mount_home()
            self.parse('rotator_enable')
            self.parse('rotator_home')
            self.m2_focuser_enable()
            self.mirror_cover_connect()
            self.mirror_cover_open()
            self.dome_go_home()
            self.waitForCondition('mount_is_slewing', 0)
        except Exception:
            print('Problem during connection phase')
        try:
            self.dome_open()
        except Exception:
            print('Could not open dome')
    
    @cmd
    def total_shutdown(self):
        try:
            self.mount_tracking_off()
            self.dome_tracking_off()
            self.mount_home()
            self.dome_go_home()
            self.mirror_cover_close()
            time.sleep(20)
        except Exception:
            print('Could not go home')
        try:
            #self.ccd_tec_stop()
            self.waitForCondition('mount_is_slewing', 0)
        except Exception:
            print('Failed before mount stopped slewing')
        try:
            self.rotator_home()
            time.sleep(10)
            self.rotator_disable()
        except Exception:
            print('Failed in disabling rotator')
        try:
            self.mount_alt_off()
            self.mount_az_off()
            self.m2_focuser_disable()
            self.dome_close()
            time.sleep(20)
            self.dome_givecontrol()
        except Exception:
            print('Failed during closing and disabling step')

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
