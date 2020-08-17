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
wsp_path = os.getcwd()
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

#######################################################################
# Captions and menu options for terminal interface
linebreak = '\n \033[34m#######################################################################'
caption1 = '\n\t\033[32mWSP - The WINTER Supervisor Program'
caption2 = '\n\t\033[32mPlease Select an Operating Mode:'
captions = [caption1, caption2]
main_opts= ['Schedule File Mode',\
            'Start with Housekeeping(temporary debugging)',\
            'Manual Mode',\
            'Exit']
logo = []
logo.append('__      _____ _ __             _  _')
logo.append("\ \ /\ / / __| '_ \           | )/ )")
logo.append(" \ V  V /\__ \ |_) |       \ /|//,' __")
logo.append('  \_/\_/ |___/ .__/        (")(_)-=()))=-')
logo.append("             | |              (\\\\")
logo.append("             |_|  ")

# Logo Credit: https://ascii.co.uk/art/wasp
#########################################################################
def menu(captions, options):
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

    night = utils.night()
    logger = utils.setup_logger(wsp_path, night, logger_name = 'logtest')
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
            opt = menu(captions,main_opts)
            if opt in ["0","1","2"]:
                if opt == "0":
                    print ("Entering robotic schedule file mode!")
                elif opt == "1":
                    print("Initializing systems and waiting for further commands")
                elif opt == "2":
                    print("Entering fully manual mode and waiting for commands")

                winter = systemControl_threaded.control(mode = int(opt), config = config, base_directory = wsp_path, logger = logger)

                # break

            elif opt == "3":
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
