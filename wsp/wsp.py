#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
wsp: the WINTER Supervisor Program

This file is part of wsp

# PURPOSE #
This program is the top-level control loop which runs operations for the
WINTER instrument. 



"""
import time
import matplotlib.pyplot as plt
import numpy as np
from telescope import telescope

# Now try to connect to the telescope using the module

pwi4 = telescope.PWI4(host = "thor", port = 8220)



while True:
    s = pwi4.status()
    time.sleep(2)
    if s.mount.is_connected:
        print("Mount is connected")
        break
    else:
        print("Mount is not connected")
        print("Connecting to Mount...")
        s = pwi4.mount_connect()
        time.sleep(2)
        
        
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
    if opt == "0":
        print("You chose option 0, good for you!")
    elif opt == "1":
        print("You chose option 1, good for you!")
    elif opt == "2":
        print("You chose option 1, good for you!")
    elif opt == "3":
        break
    else:
        print("Please choose a valid option:") 


 


