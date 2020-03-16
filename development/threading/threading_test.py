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


def thread_function(name,num):
    print(f"Thread {name}: starting")
    for i in range(num):
        print(f"Thread {name}: count = {i+1}")
        time.sleep(1)
    print(f"Thread {name}: finishing")
    
if __name__ == "__main__":
    
    
    print() 
    daemonize1 = False
    if daemonize1:
        print("RUNNING THREAD 1 AS A DAEMON")
    else:
        print("NOT RUNNING THREAD 1 AS A DAEMON")
    daemonize2 = True
    if daemonize2:
        print("RUNNING THREAD 2 AS A DAEMON")
    else:
        print("NOT RUNNING THREAD 2 AS A DAEMON")
                
        
    print("Main    : before creating thread")
    t1 = threading.Thread(target=thread_function, args=(1,5),daemon = daemonize1)
    t2 = threading.Thread(target=thread_function, args=(2,10),daemon = daemonize2)

    print("Main    : before running thread")
    t1.start()
    t2.start()
    
    print("The name of t1 is:", t1)
    
    print("Main    : wait for the thread to finish")
    print("Joining t1 to Main:")
    t1.join()
    #print("Joining t2 to Main:")
    #t2.join()
    print("Main    : all done")
    print()

    










"""
# Same code as above but with logging instead of printing:


import threading
import numpy as np
import time
import logging


def thread_function(name,num):
    logging.info(f"Thread {name}: starting")
    for i in range(num):
        logging.info(f"Thread {name}: count = {i+1}")
        time.sleep(1)
    logging.info(f"Thread {name}: finishing")
    
if __name__ == "__main__":
    format = "%(asctime)s: %(message)s"
    logging.basicConfig(format=format, level=logging.INFO,
                        datefmt="%H:%M:%S")
    
    logging.info('') 
    daemonize1 = False
    if daemonize1:
        logging.info("RUNNING THREAD 1 AS A DAEMON")
    else:
        logging.info("NOT RUNNING THREAD 1 AS A DAEMON")
    daemonize2 = True
    if daemonize2:
        logging.info("RUNNING THREAD 2 AS A DAEMON")
    else:
        logging.info("NOT RUNNING THREAD 2 AS A DAEMON")
                
        
    logging.info("Main    : before creating thread")
    t1 = threading.Thread(target=thread_function, args=(1,5),daemon = daemonize1)
    t2 = threading.Thread(target=thread_function, args=(2,10),daemon = daemonize2)

    logging.info("Main    : before running thread")
    t1.start()
    t2.start()
    logging.info("Main    : wait for the thread to finish")
    # x.join()
    logging.info("Main    : all done")
    logging.info('')

"""