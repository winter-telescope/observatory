#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Aug 13 11:22:35 2021

@author: winter
"""
import argparse
import shlex

cmdparser = argparse.ArgumentParser('tell the robotic operator to execute an observation')
        
# argument to hold the target type
cmdparser.add_argument('targtype',
                            nargs = 1,
                            action = None,
                            type = str,
                            choices = ['altaz', 'radec', 'object'],
                            )

# argument to hold the coordinates/location of the target
cmdparser.add_argument('target',
                            action = None,
                            type = str,
                            nargs = '*',
                            help = '<target> {<target>}')

# argument to hold the observation type
group = cmdparser.add_mutually_exclusive_group()
group.add_argument('-s',    '--science',   action = 'store_true', default = False)
group.add_argument('-d',    '--dark',      action = 'store_true', default = False)
group.add_argument('-f',    '--flat',      action = 'store_true', default = False)
group.add_argument('-foc',  '--focus',     action = 'store_true', default = False)
group.add_argument('-t',    '--test',      action = 'store_true', default = False)
group.add_argument('-b',    '--bias',      action = 'store_true', default = False)
group.add_argument('-p',    '--pointing',  action = 'store_true', default = False)



#%%

#argv = 'robo_observe object "M51" -f'

argv = 'robo_observe -f'
      
arglist= shlex.split(argv)[1:]


args = cmdparser.parse_args(arglist)

#print(f'parsed args = {args}')


if args.science:
    obstype = 'SCIENCE'
elif args.dark:
    obstype = 'DARK'
elif args.flat:
    obstype = 'FLAT'
elif args.focus:
    obstype = 'FOCUS'
elif args.bias:
    obstype = 'BIAS'
elif args.test:
    obstype = 'TEST'
elif args.pointing:
    obstype = 'POINTING'

print(f'OBSTYPE = {obstype}')

#%%
state = dict({'mount_alt_deg' : 234, 'mount_az_deg' : 255})

qcomment = f"(Alt, Az) = ({state['mount_alt_deg']:0.1f}, {state['mount_az_deg']:0.1f})"
# this works:
#split = shlex.split('"(Alt, Az) = (234.0, 255.0)"')
split = shlex.split(f'"{qcomment}"')
print(split)
#%%

while False:
    try:
        argv = input('enter cmd: ')
        
        arglist= shlex.split(argv)[1:]
    
    
        args = cmdparser.parse_args(arglist)
        
        print(f'parsed args = {args}')
    except KeyboardInterrupt:
        break