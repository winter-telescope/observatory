#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jul  6 16:36:42 2020

argparse demos from the official documentations:
    https://docs.python.org/3/library/argparse.html#sub-commands


@author: nlourie
"""

import argparse
import sys

def foo(args):
    print(args.x * args.y)
    
def bar(args):
    print(args.z)
    
def fartNtimes(args):
    N = args.N[0]
    print(f'Farting {N} times:')
    for i in range(N):
        print(f'fart {i+1}/{N}')
    
def goto_alt_az(args):
    alt = args.coords[0]
    az = args.coords[1]
    print(f'SLEWING TO ALT = {alt}, AZ = {az}')
    
# create the top-level parser

parser = argparse.ArgumentParser(description = 'Demo Command Parser')
#parser.print_help()

# add subparsers
subparsers = parser.add_subparsers()

# add an argument
cmd1 = subparsers.add_parser('fartNtimes', help = 'print fart N times')
cmd1.add_argument('N',nargs = 1,type=int, help = 'number of times to print fart')
cmd1.set_defaults(func = fartNtimes)

cmd2 = subparsers.add_parser('goto_alt_az', help = 'Slew to Alt Az')
cmd2.add_argument('coords', nargs = 2, type = float, help = 'coords to point to')
cmd2.set_defaults(func = goto_alt_az)

if len(sys.argv) <= 1:
    sys.argv.append('--help')


args = parser.parse_args()#['fartNtimes','3'])
#print(f'args = {args}')

# Run the appropriate function (in this case showtop20 or listapps)
args.func(args)