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

def update_logger_path(logger, newpath):
    fmt = "%(asctime)s.%(msecs).03d [%(filename)s:%(lineno)s - %(funcName)s()] %(levelname)s: %(threadName)s: %(message)s"
    datefmt = "%Y-%m-%dT%H:%M:%S"
    formatter = logging.Formatter(fmt,datefmt=datefmt)
    formatter.converter = time.gmtime

    for fh in logger.handlers: logger.removeHandler(fh)
    fh = logging.FileHandler(newpath, mode='a')
    fh.setFormatter(formatter)
    logger.addHandler(fh)

def setup_logger(base_dir, night, logger_name):

    path = base_dir + '/log/' + night

    if os.path.exists(path) == False:
        # use makedirs instead of mkdir because it makes any needed intermediary directories
        os.makedirs(path)
        
    fmt = "%(asctime)s.%(msecs).03d [%(filename)s:%(lineno)s - %(funcName)s()] %(levelname)s: %(threadName)s: %(message)s"
    datefmt = "%Y-%m-%d  %H:%M:%S"

    logger = logging.getLogger(logger_name)
    formatter = logging.Formatter(fmt,datefmt=datefmt)
    formatter.converter = time.gmtime

    fileHandler = logging.FileHandler(path + '/' + logger_name + '.log', mode='a')
    fileHandler.setFormatter(formatter)

    #console = logging.StreamHandler()
    #console.setFormatter(formatter)
    #console.setLevel(logging.INFO)
    
    # add a separate logger for the terminal (don't display debug-level messages)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(fileHandler)
    #logger.addHandler(console)
    
    return logger


def night():
    today = datetime.datetime.utcnow()
    if datetime.datetime.now().hour >= 10 and datetime.datetime.now().hour <= 16:
        today = today + datetime.timedelta(days=1)
    return 'n' + today.strftime('%Y%m%d')


def printWord(word):
    print(f"I'm printing the word: {word}")

#%% ####### pyqt stuff for threading #####



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

#%% #### COMMANDING STUFF #####


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
            #print('Could not execute command: ', e)
            
            pass
    return wrapper_cmd 


class Wintercmd(object):
    
    
    def __init__(self, telescope, logger):
        # init the parent class
        super().__init__()
        
        # things that define the command line prompt
        self.intro = 'Welcome to wintercmd, the WINTER Command Interface'
        self.prompt = 'wintercmd: '
        
        # subclass some useful inputs
        self.telescope = telescope
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
    def goto_alt_az(self):
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
        self.telescope.goto_alt_az(alt = alt, az = az)
    
    @cmd
    def quit(self):
        """Quits out of Interactive Mode."""

        print('Good Bye!')
        sigint_handler()

#%% Test Stuff
class Telescope(object):
    def __init__(self, logger):
        self.logger = logger
        # this is just a sample class for testing
        self.alt = 0.0
        self.az = 0.0
        self.home()
    
    def home(self):
        self.logger.info('telescope: homing telescope')
    
    def get_status(self):
        self.logger.info(f'telescope: ALT = {self.alt}, AZ = {self.az}')
        
    def goto_alt_az(self,alt,az):
        self.logger.info(f"Slewing to ALT = {alt}, AZ = {az}")
        self.alt = alt
        self.az = az
        
#%% Testing
"""        
argv  = sys.argv[1:]
#print('sys.argv[1:] = ',argv)
#print('len(sys.argv[1:]) = ',len(argv))

if len(argv) < 1:
    #print('no inputs')
    argv = ['-i']

opt = docopt(__doc__, argv)
print(__doc__)

        
telescope = Telescope()

wintercmd = Wintercmd(telescope)
print(wintercmd.intro)
cmd = input(wintercmd.prompt)
wintercmd.onecmd(cmd)

"""

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


class main(QtCore.QObject):   

                  
    def __init__(self, parent=None ):            
        super(main, self).__init__(parent)   
        
        #self.thread = self.currentThread()
        #print(f'mainThread: thread ID = {self.thread}')
        
        # start a counter to watch loop execution
        self.index = 0
        
        self.timer = QtCore.QTimer()
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.count)
        self.timer.start()
        
        # set up the logger
        self.base_dir = os.getcwd()
        self.night = night()
        self.logger = setup_logger(self.base_dir, self.night, logger_name = 'logtest')
        
        # init some test stuff
        self.telescope = Telescope(self.logger)
        
        self.wintercmd = Wintercmd(self.telescope, self.logger)
        
        
        # init the cmd executor
        self.cmdexecutor = cmd_executor(self.telescope, self.wintercmd, self.logger)
        
        # init the cmd prompt
        self.cmdprompt = cmd_prompt(self.telescope, self.wintercmd)
        
        # connect the new command signal to the executor
        self.cmdprompt.newcmd.connect(self.cmdexecutor.add_to_queue)
        
        
        
            
    def caught_signal(self,number):
        print(f'main: caught signal {number}') 
    
    
        
    def count(self):
        self.index += 1
        #print(f'main: index = {self.index}')
     
    
        
        
def sigint_handler( *args):
    """Handler for the SIGINT signal."""
    sys.stderr.write('\r')
    
    mainthread.cmdprompt.quit()
    
    mainthread.cmdexecutor.quit()
    
    QtCore.QCoreApplication.quit()
#%%
if __name__ == "__main__":
    app = QtCore.QCoreApplication(sys.argv)

    
    mainthread = main()

    signal.signal(signal.SIGINT, sigint_handler)

    # Run the interpreter every so often to catch SIGINT
    timer = QtCore.QTimer()
    timer.start(500) 
    timer.timeout.connect(lambda: None) 

    sys.exit(app.exec_())

        
        
        