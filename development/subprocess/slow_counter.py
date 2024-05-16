#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Mar 14 12:50:43 2024

@author: nlourie
"""

import time
import sys
import getopt
a = 0


def count_and_print(n):
    print(f'counting up to {n} seconds!')
    for i in range(n):
        print(i)
        if i>0:
            time.sleep(1)
        if i>10:
            a = 500/0
        

if __name__ == '__main__':
    

    
    argumentList = sys.argv[1:]
    
    # set the defaults
    verbose = False
    num_to_count = 0
    
    # Options
    options = "vn:"
     
    # Long options
    long_options = ["verbose", "num"]
    
    
     
    try:
        # Parsing argument
        #print(f'argumentList = {argumentList}')
        arguments, values = getopt.getopt(argumentList, options, long_options)
        #print(f'arguments: {arguments}')
        #print(f'values: {values}')
        # checking each argument
        for currentArgument, currentValue in arguments:
     
            if currentArgument in ("-v", "--verbose"):
                verbose = True
            
            elif currentArgument in ("-n", "--num"):
                num_to_count = int(currentValue)
                 

                
    except getopt.error as err:
        # output error, and return with an error code
        print(str(err))
        
    # do the counting!
    count_and_print(num_to_count)