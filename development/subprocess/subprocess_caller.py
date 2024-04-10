#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Mar 14 12:50:42 2024

@author: nlourie
"""
import sys
import subprocess
import shlex
import getopt




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
        

    # RUN THE COUTER IN A SUBPROCESS
    
    pythonpath = "python"
    cmd = f"{pythonpath} slow_counter.py -n {num_to_count}"
    
    # run the test daemon
    args = shlex.split(cmd)
    
    
    # print(f'Launching program in non-blocking call with subprocess.Popen')
    # p_testd = subprocess.Popen(args, shell = False)
    # pid = p_testd.pid
    # print(f'Test Daemon Running in PID {pid}')
    
    print()
    print('Launching program in blocking call with subprocess.run')
    
    try:
        p_testd = subprocess.run(args, shell = False, check = True, capture_output=True)
    
        print(f'-> Successfully ran the counter in a subprocess!')
    
    except subprocess.CalledProcessError as e:
        print(f'-> Error running subprocess: {e}')
    
    #if not daemon_list is None:
    #    daemon_list.add_daemon('test_daemon', pid)
    
    #print()
    print('PROGRAM COMPLETE')
    print()