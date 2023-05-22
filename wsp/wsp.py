#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
wsp: the WINTER Supervisor Program

This file is part of wsp

# PURPOSE #
This program is the top-level control loop which runs operations for the
WINTER instrument.



"""

# system packages
import sys
import os
import numpy as np
import time
from PyQt5 import uic, QtCore, QtGui, QtWidgets
import yaml
import signal
from pathlib import Path
import getopt

# add the wsp directory to the PATH
wsp_path = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(1, wsp_path)
print(f'wsp: wsp_path = {wsp_path}')

# winter modules
#from power import power
#from telescope import pwi4
#from telescope import telescope
#from command import commandServer_multiClient
#from housekeeping import easygetdata
from control import systemControl
from utils import utils
from utils import logging_setup
#######################################################################
# Captions and menu options for terminal interface
linebreak = '\n \033[34m####################################################################################'
caption1 = '\n\t\033[32mWSP - The WINTER Supervisor Program'
caption2 = '\n\t\033[32mPlease Select an Operating Mode:'
captions = [caption1, caption2]
main_opts= dict({'R': 'Robotic schedule File Mode',
            'I': 'Instrument-only Mode',
            'M':'Manual Mode',
            'Q': 'Exit'})

logo = []
logo.append('__      _____ _ __             _  _')
logo.append("\ \ /\ / / __| '_ \           | )/ )")
logo.append(" \ V  V /\__ \ |_) |       \ /|//,' __")
logo.append('  \_/\_/ |___/ .__/        (")(_)-=()))=-')
logo.append("             | |              (\\\\")
logo.append("             |_|  ")



# Logo Credit: https://ascii.co.uk/art/wasp


big_m = []
big_m.append('88888b     d88888')
big_m.append('888888b   d888888') 
big_m.append('8888888b.d8888888') 
big_m.append('88888Y88888P88888') 
big_m.append('88888 Y888P 88888') 
big_m.append('88888  Y8P  88888') 
big_m.append('88888   "   88888') 
big_m.append('88888       88888') 

big_r = []
big_r.append('8888888888b.')
big_r.append('888888888888b.')
big_r.append('88888   Y8888b') 
big_r.append('88888    88888') 
big_r.append('88888   d8888P') 
big_r.append('888888888P"')  
big_r.append('88888 T8888b')   
big_r.append('88888  T8888b')  
big_r.append('88888   T8888b')

big_i = []
big_i.append('8888888888888 ')
big_i.append('8888888888888 ')
big_i.append('    88888     ')
big_i.append('    88888     ')
big_i.append('    88888     ')
big_i.append('    88888     ')
big_i.append('8888888888888 ')
big_i.append('8888888888888 ')

big_letter = dict({'m' : big_m, 'r' : big_r, 'i':big_i})
#########################################################################
def numbered_menu(captions, options):
    """Creates menu for terminal interface
       inputs:
           list captions: List of menu captions
           list options: List of menu options
       outputs:
           int opt: Integer corresponding to menu option chosen by user"""

    print(linebreak)
    for logo_line in logo:
        print('     ',logo_line)
    print ('\t' + captions[0])
    print(linebreak)
    for i in range(len(options)):
        if (i < 9):
            print( '\t' +  '\033[32m' + str(i) + ' ..... ' '\033[0m' +  options[i] + '\n')
    print ('\t' + captions[1] + '\n')
    for i in range(len(options)):
        if (i >= 9):
            print ('\t' +  '\033[32m' + str(i) + ' ..... ' '\033[0m' +  options[i] + '\n')
    opt = input().strip()
    return opt

def printlogo():
    print(linebreak)
    for logo_line in logo:
        print('     ',logo_line)
    print ('\t' + captions[0])
    print(linebreak)

def dict_menu(captions, options):
    """Creates menu for terminal interface
       inputs:
           list captions: List of menu captions
           dict options: List of menu options
       outputs:
           int opt: Integer corresponding to menu option chosen by user
           list allowed_opts: list of all the lowercase menu opptions allowed to be chosen
           """
           
    printlogo()
    allowed_opts = []
    for key in options.keys():
        print( '\t' +  '\033[32m' + key + ' ..... ' '\033[0m' +  options[key] + '\n')
        allowed_opts.append(key.lower())
    print ('\t' + captions[1] + '\n')
    
    opt = input().strip().lower()
    return opt,allowed_opts

#########################################################################


def sigint_handler(*args):
    """Handler for the SIGINT signal."""
    print('exiting.')
    sys.stderr.write('\r')
    QtCore.QCoreApplication.quit()

if __name__ == "__main__":
    signal.signal(signal.SIGINT, sigint_handler)
    app = QtCore.QCoreApplication(sys.argv)
    
    mode = None
    

    # GET ANY COMMAND LINE ARGUMENTS
    args = sys.argv[1:]
    print(f'wsp.py: args = {args}')

    options = "rimvn:"
    long_options = ["robo", "instrument", "manual", "verbose", "ns_host=", 
                    "smallchiller", "sunsim", "domesim", "dometest"]
    arguments, values = getopt.getopt(args, options, long_options)
    # checking each argument
    print()
    print(f'wsp.py: Parsing sys.argv...')
    print(f'wsp.py: arguments = {arguments}')
    print(f'wsp.py: values = {values}')
    for currentArgument, currentValue in arguments:
        if currentArgument in ("-r", "--robo"):
            mode = 'r'
        
        elif currentArgument in ("-i", "--instrument"):
            mode = 'i'
        
        elif currentArgument in ("-m", "--manual"):
            mode = 'm'
            
        
    modes = dict()
    modes.update({'r' : "Entering [R]obotic schedule file mode (will initiate observations!)"})
    modes.update({'i' : "Entering [I]nstrument mode: initializing instrument subsystems and waiting for commands"})
    modes.update({'m' : "Entering fully [M]anual mode: initializing all subsystems and waiting for commands"})
    
    opts = arguments
    
    printlogo()
    print()
    for line in big_letter[mode]:
        print('\t\t\t\t',line)
    print('\033[32m >>>> ', modes[mode])
    print()
    print(linebreak)
    print('\033[32m')
    
    '''
    #print(f'args = {args}')
    
    if len(args)<1:
        pass
    
    # parse the mode
    elif len(args) >= 1:
       
        mode_arg = args[0]
        opts = args[1:]
        
        if mode_arg in modes.keys():
            # remove the dash when passing the option
            mode = mode_arg.replace('-','')
            printlogo()
            print()
            if mode == 'm':
                for line in big_letter[mode]:
                    print('\t\t\t\t',line)
            print('\033[32m >>>> ', modes[mode_arg])
            print()
            print(linebreak)
            print('\033[32m')
            
        else:
            print(f'Invalid mode {mode_arg}')
        
        
        
    """else:
        print('Too many options specified.')"""
    '''
    # load the config
    config_file = wsp_path + '/config/config.yaml'
    config = utils.loadconfig(config_file)
    # set up the logger
    logger = logging_setup.setup_logger(wsp_path, config)
    
    # START UP THE CONTROL SYSTEM
    
    # If an option was specified from the command line, then use that
    if not mode is None:
        #print(f'Starting WSP with mode = {mode}, opts = {opts}')
        
        winter = systemControl.control(mode = mode, config = config, base_directory = wsp_path, logger = logger, opts = opts)
    '''
    # If no option was specified, then start up the text user interface
    else:
        try:
            while True:
                opt,allowed_opts = dict_menu(captions,main_opts)
                if opt in allowed_opts:
                    if opt == "r":
                        print ("Entering [R]obotic schedule file mode (will initiate observations!)")
                    elif opt == "i":
                        print("Entering [I]nstrument mode: initializing instrument subsystems and waiting for commands")
                    elif opt == "m":
                        print("Entering fully [M]anual mode: initializing all subsystems and waiting for commands")
                    # Reset Color of Text
                    print('\033[0m')
                    winter = systemControl.control(mode = opt, config = config, base_directory = wsp_path, logger = logger)
    
                    break
    
                elif opt == "q":
                    print("Killing WSP...",'\033[0m')
                    sys.exit()
                    break
                else:
                    print("Please choose a valid option:")
        except KeyboardInterrupt:
            pass


    # instatiate the control (ie main) class
    #TODO port this to the real systemControl instead
    #winter = systemControl_threaded.control(mode = int(opt), config = config, base_directory = wsp_path, logger = logger)

    """
    # Run the interpreter every so often to catch SIGINT
    timer = QtCore.QTimer()
    timer.start(500)
    timer.timeout.connect(lambda: None)
    """
    '''
    sys.exit(app.exec_())
    