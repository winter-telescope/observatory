#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Mar 11 16:49:35 2020


Python Built-in threading test script

@author: nlourie
"""


import threading
import numpy as np
import time
import sys
import os
from concurrent.futures import ThreadPoolExecutor


def thread_function(name,num):
    #num = 5
    print()
    print(f"Thread {name}: starting")
    for i in range(num):
        print(f"Thread {name}: count = {i+1}")
        time.sleep(1)
    
    print(f"\nThread {name}: finishing\n")
    
def printword():
    word_to_print = input("Enter a word to parrot back: ")
    if word_to_print == 'quit':
        print(">>>>>>>>>>>>>>>>>>>>>> QUITTING <<<<<<<<<<<<<<<<<<<<<<<<<<<<<")
        os._exit(1)
    else:
        print("Parrot says: ",word_to_print)
    
if __name__ == "__main__":
    
    print("Main:   Before starting executor")
    with ThreadPoolExecutor(max_workers = 3) as executor:
        # if you pass an arg to a function that doesn't take args,then a silent
        # error occurs
        
        #executor.map(thread_function,['a','b','c'],[2,5,15])
        
        executor.submit(thread_function, 'a',10)
        executor.submit(thread_function, 'b',20)
        executor.submit(printword)
        
        
        

        
    print("\nMain:   Finished\n")

    
