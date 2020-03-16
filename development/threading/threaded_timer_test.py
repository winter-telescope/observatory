#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Mar 12 15:16:34 2020

Non-BLocking Timer:
    
    Source: https://stackoverflow.com/questions/474528/what-is-the-best-way-to-repeatedly-execute-a-function-every-x-seconds?rq=1
    Author: MestreLion, Jul 11 '16
        
    If you want a non-blocking way to execute your function periodically, 
    instead of a blocking infinite loop I'd use a threaded timer. This way 
    your code can keep running and perform other tasks and still have your f
    unction called every n seconds. I use this technique a lot for printing 
    progress info on long, CPU/Disk/Network intensive tasks.

    Here's the code I've posted in a similar question, with start() 
    and stop() control:






@author: nlourie
"""

from threading import Timer
from datetime import datetime
import numpy as np

class RepeatedTimer(object):
    def __init__(self, interval, function, *args, **kwargs):
        self._timer     = None
        self.interval   = interval
        self.function   = function
        self.args       = args
        self.kwargs     = kwargs
        self.is_running = False
        self.start()

    def _run(self):
        self.is_running = False
        self.start()
        self.function(*self.args, **self.kwargs)

    def start(self):
        if not self.is_running:
            self._timer = Timer(self.interval, self._run)
            self._timer.start()
            self.is_running = True

    def stop(self):
        self._timer.cancel()
        self.is_running = False

from time import sleep

def hello(name,start,log):
    print ("Hello %s!" % name)
    dt = datetime.now()-start
    print(dt)
    log.append(dt)
    
print ("starting...")
start = datetime.now()
log = []
rt = RepeatedTimer(1, hello, "World",start,log) # it auto-starts, no need of rt.start()
try:
    sleep(60*5) # your long-running job goes here...
finally:
    rt.stop() # better in a try/finally block to make sure the program ends!
    
    
#%%


dt = []
for i in range(len(log)-1):
    us = np.float((log[i+1]-log[i]).microseconds)*1e-6
    dt.append(us)
    
plt.plot(dt)
np.std(dt)
    
