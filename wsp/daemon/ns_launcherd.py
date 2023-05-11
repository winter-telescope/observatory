#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu May 11 13:02:49 2023

ns_launcherd.py

Pyro5 nameserver launcher 

@author: winter
"""

import sys
import getopt
import Pyro5.nameserver


args = sys.argv[1:]
print(f'args = {args}')

options = "n:"
long_options = ["ns_host:"]
arguments, values = getopt.getopt(args, options, long_options)
# checking each argument
print()
print(f'It is me! The nameserver launcher! Woo!')
print(f'arguments = {arguments}')
for currentArgument, currentValue in arguments:
    if currentArgument in ("-n", "--ns_host"):
        ns_host = currentValue
        print(f'ns_launcherd: launching Pyro5 nameserver at host: {ns_host}')
        # launch the nameserver daemon
        Pyro5.nameserver.start_ns_loop(host = ns_host)


print('nameserver launcher is finished?')