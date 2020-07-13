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
import cmd
import time
import queue
from docopt import docopt, DocoptExit

from schema import Schema, And, Or, Use, SchemaError

from PyQt5 import uic, QtCore, QtGui, QtWidgets
#from PyQt5.QtWidgets import QMessageBox


import traceback
import signal


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

def docopt_cmd(func):
    """
    This decorator is used to simplify the try/except block and pass the result
    of the docopt parsing to the called action.
    """
    def fn(self, arg):
        try:
            opt = docopt(fn.__doc__, arg)
            
        except DocoptExit as e:
            # The DocoptExit is thrown when the args do not match.
            # We print a message to the user and the usage block.

            print('Invalid Command!')
            print(e)
            return

        except SystemExit:
            # The SystemExit exception prints the usage for --help
            # We do not need to do the print here.

            return

        return func(self, opt)

    fn.__name__ = func.__name__
    fn.__doc__ = func.__doc__
    fn.__dict__.update(func.__dict__)
    return fn

class Wintercmd(cmd.Cmd):
    
    
    
    
    def __init__(self, telescope):
        # init the parent class
        super().__init__()
        
        # things that define the command line prompt
        self.intro = 'Welcome to wintercmd, the WINTER Command Interface'
        self.prompt = 'wintercmd: '
        
        # subclass some useful inputs
        self.telescope = telescope
        
        # define the types and error messages for the arguments
        self.schema = Schema({'<int>' : Use(int, error = '<int> must be integer')})
    
    def argcheck(self, arg):
        
        try:
            arg = self.schema.validate(arg)
            return True
        except SchemaError as e:
            print('Argument Type Error: ',e)
            print(__doc__)
            return False
        
    @docopt_cmd
    def do_count(self,arg):
        """usage: count <int>"""
        if self.argcheck(arg):
            num = int(arg['<int>'])
            print(f'counting seconds up to {num}:')
            i = 0
            while i < num:
                print(f'   count = {i}')
                i+=1
                time.sleep(1)
    
    @docopt_cmd
    def do_xyzzy(self, arg):
        
        """Usage: xyzzy"""
        print('nothing happened.')

    
    @docopt_cmd
    def do_plover(self,arg):
        """Usage: plover <int>"""
        #print('args = ',arg)
        if self.argcheck(arg):
            print(type(arg['<int>']))
            print(f"plover: {arg['<int>']}")

    @docopt_cmd
    def do_goto_alt_az(self,arg):
        """Usage: goto_alt_az <alt> <az>"""
        #print('args = ',arg)
        alt = arg['<alt>']
        az = arg['<az>']
        self.telescope.goto_alt_az(alt = alt, az = az)
        
    def do_quit(self, arg):
        """Quits out of Interactive Mode."""

        print('Good Bye!')
        sys.exit()
        

#%% Test Stuff
class Telescope(object):
    def __init__(self):
        # this is just a sample class for testing
        self.alt = 0.0
        self.az = 0.0
        self.home()
    
    def home(self):
        print('telescope: homing telescope')
    
    def get_status(self):
        print(f'telescope: ALT = {self.alt}, AZ = {self.az}')
        
    def goto_alt_az(self,alt,az):
        print(f"Slewing to ALT = {alt}, AZ = {az}")
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
            
            # emit signal that command has been received
            self.newcmd.emit(cmd)
            
class cmd_executor(QtCore.QThread):           
    """
    This is a thread which handles the command queue, takes commands
    from the command line "cmd_prompt" thread or from the server thread.
    The command queue is a prioritied FIFO queue and each item from the queue
    is executed in a QRunnable worker thread.
    """
    def __init__(self,telescope,wintercmd):
        super().__init__()
        
        # set up the threadpool
        self.threadpool = QtCore.QThreadPool()
        
        # create the winter command object
        #self.wintercmd = Wintercmd(telescope)
        self.wintercmd = wintercmd
        
        # set up the command prompt
        #self.cmdprompt = cmd_prompt(telescope,self.wintercmd)
        
        # create the command queue
        self.queue = queue.PriorityQueue()
        
        # connect the command interfaces to the executor
        #self.cmdprompt.newcmd.connect(self.add_to_queue)
        
        # start the thread
        self.start()
    
            
    
    def add_to_queue(self,cmd):
        print(f"adding cmd to queue: {cmd}")
        self.queue.put((1,cmd))
        
    def execute(self,cmd):
        """
        Execute the command in a worker thread
        """
        print(f'executing command {cmd}')
        try:
            worker = Worker(self.wintercmd.onecmd, cmd)
            #self.wintercmd.onecmd(cmd)
            self.threadpool.start(worker)
        except Exception as e:
            print(f'could not execute {cmd}: {e}')
    def run(self):
       # if there are any commands in the queue, execute them!
       print('waiting for commands to execute')
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
        
        # init some test stuff
        self.telescope = Telescope()
        
        # parse the command interface
        
        self.opt = docopt(__doc__, ['-i'])
        print(__doc__)
        
        # init the command object
        self.wintercmd = Wintercmd(self.telescope)
        
        
        
        # init the cmd executor
        self.cmdexecutor = cmd_executor(self.telescope, self.wintercmd)
        
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

if __name__ == "__main__":
    app = QtCore.QCoreApplication(sys.argv)

    
    mainthread = main()

    signal.signal(signal.SIGINT, sigint_handler)

    # Run the interpreter every so often to catch SIGINT
    timer = QtCore.QTimer()
    timer.start(500) 
    timer.timeout.connect(lambda: None) 

    sys.exit(app.exec_())

        
        
        