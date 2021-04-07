#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Apr  6 12:55:04 2021


Routine tester

@author: nlourie
"""

import numpy as np

routine_file = 'startup.txt'

routine = np.loadtxt('startup.txt',
                     delimiter = '\n',
                     comments = '#',
                     dtype = str)

for cmd in routine:
    print(f'Executing command: {cmd}')
    