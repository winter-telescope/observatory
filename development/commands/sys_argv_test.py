#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Mar  8 16:44:35 2021

sys argv test

@author: nlourie
"""

import sys

args = sys.argv[1:]
modes = dict()
modes.update({'-r' : "Entering [R]obotic schedule file mode (will initiate observations!)"})
modes.update({'-i' : "Entering [I]nstrument mode: initializing instrument subsystems and waiting for commands"})
modes.update({'-m' : "Entering fully [M]anual mode: initializing all subsystems and waiting for commands"})

#print(f'args = {args}')

if len(args)<1:
    pass

elif len(args) == 1:
   
    arg = args[0]
    
    if arg in modes.keys():
        print(modes[arg])
    else:
        print(f'Invalid mode {arg}')

else:
    print('Too many options specified.')
    