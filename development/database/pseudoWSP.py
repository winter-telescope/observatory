"""
A simulated Winter Supervisor Program
Receives a Schedule db and commands the psuedoWinter instrument
Logs "data" returned by the instrument simulator
"""
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# system packages
import sys
import os
import numpy as np
import time

# add the wsp directory to the PATH
wsp_path = os.getcwd()
# sys.path.insert(1, wsp_path)

# winter modules
import pseudoWinter
# from power import power
# from telescope import pwi4
# from telescope import telescope
# from control import systemControl
# from command import commandServer_multiClient

# This is a test function to make sure commands are being parsed
def printphrase(phrase = 'default phrase'):
    printed_phrase = f"I'm Printing the Phrase: {phrase}"
    print(printed_phrase)
    return printed_phrase

def home_the_thing():
    winter.telescope_home()


#######################################################################
# Captions and menu options for terminal interface
linebreak = '\n \033[34m#######################################################################'+  '\033[32m'
caption1 = '\n\t\033[32mWSP - A Pseudo WINTER Supervisor Program'+  '\033[32m'
caption2 = '\n\t\033[32mPlease Select an Operating Mode:'+  '\033[32m'
captions = [caption1, caption2]
main_opts= ['Test Schedule File Mode',\
            'Get Ready and Wait',\
            'Manual Mode',\
            'Exit']
logo = []
logo.append('__      _____ _ __             _  _')
logo.append("\ \ /\ / / __| '_ \           | )/ )")
logo.append(" \ V  V /\__ \ |_) |       \ /|//,' __")
logo.append('  \_/\_/ |___/ .__/        (")(_)-=()))=-')
logo.append("             | |              (\\\\")
logo.append("             |_|  "+  '\033[32m')

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
global winter
try:
    while True:
        opt = menu(captions,main_opts)
        if opt in ["0","1","2"]:
            if opt == "0":
                print ("Entering test robotic schedule file mode!")
            elif opt == "1":
                print("Initializing systems and waiting for further commands")
            elif opt == "2":
                print("Entering fully manual mode and waiting for commands")

            winter = pseudoWinter.Controller(mode = int(opt), config_file = '',base_directory = wsp_path)
            print(wsp_path)
            cmd = ''
            cmd = input('Please Enter a Command: ')

            if cmd == 'quit':
                print("Killing WSP..." +  '\033[0m')
                break # get out of the outer while loop
        elif opt == "3":
            print("Killing WSP..." +  '\033[0m')
            break
        else:
            print("Please choose a valid option:")
except KeyboardInterrupt:
    pass
