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

# add the wsp directory to the PATH
wsp_path = os.getcwd()
sys.path.insert(1, wsp_path)

# winter modules
from power import power
from telescope import pwi4
from telescope import telescope
from control import systemControl
from command import commandServer_multiClient

# This is a test function to make sure commands are being parsed 
def printphrase(phrase = 'default phrase'):
    printed_phrase = f"I'm Printing the Phrase: {phrase}"
    print(printed_phrase)
    return printed_phrase

def home_the_thing():
    winter.telescope_home()

       
#######################################################################
# Captions and menu options for terminal interface
linebreak = '\n \033[34m#######################################################################'
caption1 = '\n\t\033[32mWSP - The WINTER Supervisor Program'
caption2 = '\n\t\033[32mPlease Select an Operating Mode:'
captions = [caption1, caption2]
main_opts= ['Schedule File Mode',\
            'Get Ready and Wait',\
            'Manual Mode',\
            'Exit']
#########################################################################
def menu(captions, options):
    """Creates menu for terminal interface
       inputs:
           list captions: List of menu captions
           list options: List of menu options
       outputs:
           int opt: Integer corresponding to menu option chosen by user"""
    print(linebreak)
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
while True:
    opt = menu(captions,main_opts)
    if opt in ["0","1","2"]:
        print("You chose option ",opt, " good for you!")
        winter = systemControl.control(mode = int(opt), config_file = '',base_directory = wsp_path)
        break
    elif opt == "3":
        print("Killing WSP...")
        break
    else:
        print("Please choose a valid option:") 


while True:
    try:
        eval(input('Please Enter a Command: '))
        
    except KeyboardInterrupt:
        break
    except:
        print('Command did not work.')


