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


# add the wsp directory to the PATH
wsp_path = os.path.dirname(__file__)
sys.path.insert(1, wsp_path)

# winter modules
from power import power
from telescope import pwi4
#from telescope import telescope
from control import systemControl
from command import commandServer_multiClient
from housekeeping import easygetdata
from control import systemControl_threaded
from utils import utils
from utils import logging_setup
#######################################################################
# Captions and menu options for terminal interface
linebreak = '\n \033[34m#######################################################################'
caption1 = '\n\t\033[32mWSP - The WINTER Supervisor Program'
caption2 = '\n\t\033[32mPlease Select an Operating Mode:'
captions = [caption1, caption2]
main_opts= dict({'S': 'Schedule File Mode',
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

def dict_menu(captions, options):
    """Creates menu for terminal interface
       inputs:
           list captions: List of menu captions
           dict options: List of menu options
       outputs:
           int opt: Integer corresponding to menu option chosen by user
           list allowed_opts: list of all the lowercase menu opptions allowed to be chosen
           """
           
    allowed_opts = []
    print(linebreak)
    for logo_line in logo:
        print('     ',logo_line)
    print ('\t' + captions[0])
    print(linebreak)
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

    # load the config
    config_file = wsp_path + '/config/config.yaml'
    config = utils.loadconfig(config_file)
    # get the mode flag
    opt = 0
    #mode = dict({})

    #menu(config)

    # set up the logger

    #night = utils.night()
    #logger = utils.setup_logger(wsp_path, night, logger_name = 'logtest')
    logger = logging_setup.setup_logger(wsp_path, config)
    """
    while True:
        cmd = input('select a mode: ')
        print(f'You selected mode: {cmd}')

        if cmd == 'quit':
            app.quit()
            sys.exit()
    """
    try:
        while True:
            opt,allowed_opts = dict_menu(captions,main_opts)
            if opt in allowed_opts:
                if opt == "s":
                    print ("Entering robotic schedule file mode!")
                elif opt == "i":
                    print("Entering instrument mode: initializing instrument subsystems and waiting for commands")
                elif opt == "m":
                    print("Entering fully manual mode: initializing all subsystems and waiting for commands")

                winter = systemControl_threaded.control(mode = opt, config = config, base_directory = wsp_path, logger = logger)

                break

            elif opt == "q":
                print("Killing WSP...")
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
    sys.exit(app.exec_())
