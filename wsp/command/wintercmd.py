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
import datetime
import numpy as np

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
        except Exception as e:
            """
            Exceptions are already handled by the argument parser
            so do nothing here.
            """
            print('Could not execute command: ', e)

            pass
    return wrapper_cmd


class Wintercmd(object):


    def __init__(self, config, telescope, logger):
        # init the parent class
        super().__init__()

        # things that define the command line prompt
        self.intro = 'Welcome to wintercmd, the WINTER Command Interface'
        self.prompt = 'wintercmd: '

        # subclass some useful inputs
        self.telescope = telescope

        self.config = config
        self.logger = logger
        self.defineParser()

    def parse(self,argv = None):

        # parse_args defaults to [1:] for args, but you need to
        # exclude the rest of the args too, or validation will fail

        if argv is None:
            self.argv = sys.argv[1:]
            if len(self.argv) < 1:
                   #self.argv = ['-h']
                   pass
        else:
            self.argv = argv.split(' ')

        self.logger.debug(f'self.argv = {self.argv}')

        self.command = self.parser.parse_args(self.argv[0:1]).command
        #print(f'cmdarg = {cmdarg}')
        self.arglist = self.argv[1:]
        #self.command = cmdarg.command
        self.logger.debug(f'command = {self.command}')

        if not hasattr(self, self.command):
            if self.command == '':
                pass
            else:
                self.logger.warning('Unrecognized command: {self.command}')
                self.parser.print_help()

                #sys.exit(1)
                pass
        # use dispatch pattern to invoke method with same name
        else:
            try:
                getattr(self, self.command)()
            except Exception as e:
                self.logger.warning(f'Could not execute command {self.command}')
                self.logger.debug(e)

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


    @cmd
    def commit(self):
        self.defineCmdParser(description='Record changes to the repository')
        # prefixing the argument with -- means it's optional
        self.cmdparser.add_argument('--amend', action='store_true')
        self.getargs()
        self.logger.info('Running git commit, amend=%s' % self.args.amend)



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

    @cmd
    def mount_disconnect(self):
        self.defineCmdParser('disconnect from telescope mount')
        self.telescope.mount_disconnect()

    @cmd
    def mount_az_on(self):
        self.defineCmdParser('turn on az motor')
        self.telescope.mount_enable(0)

    @cmd
    def mount_az_off(self):
        self.defineCmdParser('turn off az motor')
        self.telescope.mount_disable(0)

    @cmd
    def mount_alt_on(self):
        self.defineCmdParser('turn on alt motor')
        self.telescope.mount_enable(1)

    @cmd
    def mount_alt_off(self):
        self.defineCmdParser('turn off alt motor')
        self.telescope.mount_disable(1)

    @cmd
    def mount_stop(self):
        self.defineCmdParser('STOP TELESCOPE MOTION')
        self.telescope.mount_stop()

    @cmd
    def mount_home(self):
        self.defineCmdParser('point telescope mount to home position')
        alt_degs = (self.config['telescope_home']['alt_degs'])
        az_degs = self.config['telescope_home']['az_degs']
        self.logger.info(f'slewing to home: ALT = {alt_degs}, AZ = {az_degs}')
        self.telescope.mount_goto_alt_az(alt_degs = alt_degs, az_degs = az_degs)

    @cmd
    def mount_shutdown(self):
        # self.mount_home()
        # time.sleep(0.5)
        # self.mount_az_off()
        # time.sleep(0.5)
        # self.mount_alt_off()
        # time.sleep(0.5)
        # self.mount_disconnect()

        # possible alternate structure: Probably won't work
        alt_degs = (self.config['telescope_home']['alt_degs'])
        az_degs = self.config['telescope_home']['az_degs']
        self.logger.info(f'slewing to home: ALT = {alt_degs}, AZ = {az_degs}')
        self.telescope.mount_goto_alt_az(alt_degs = alt_degs, az_degs = az_degs)
        self.telescope.mount_disable(0)
        self.telescope.mount_disable(1)



    @cmd
    def quit(self):
        """Quits out of Interactive Mode."""

        print('Good Bye!')
        if self.promptThread and self.execThread:
            self.promptThread.stop()
            self.execThread.stop()

        sys.exit()#sigint_handler()

class ManualCmd(Wintercmd):

    def __init__(self, config, telescope, logger):
        super().__init__(config, telescope, logger)
        self.prompt = 'wintercmd(M): '

    @cmd
    def mount_goto_alt_az(self):
        """Usage: goto_alt_az <alt> <az>"""
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



class ScheduleCmd(Wintercmd):

    def __init__(self, config, telescope, logger):
        super().__init__(self, config, telescope, logger)
        self.prompt = 'wintercmd(S): '

    @cmd
    def LIGO_alert(self):
        self.defineCmdParser('change to the LIGO observing schedule')
        pass

    @cmd
    def use_nightly_schedule(self):
        self.defineCmdParser('set the schedule file read to the nightly plan')
        pass

    @cmd
    def resume_schedule(self):
        self.defineCmdParser('resume scheduled observations')
        if self.execThread:
            self.execThread.start()

    @cmd
    def pause_schedule(self):
        self.defineCmdParser('interrupt scheduled observations')
        if self.execThread:
            self.execThread.stop()
