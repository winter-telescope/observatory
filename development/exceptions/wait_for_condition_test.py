#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Aug  2 08:46:58 2021

@author: winter
"""


#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Aug  2 04:47:34 2021

@author: winter
"""
import time
from datetime import datetime

class Thing(object):
    def __init__(self):
        self.state = {}
        self.a = 0
        self.state.update({'a' : self.a})
        
    def is_odd(self):
        cond = self.a & 0x1
        self.a += 1
        self.state.update({'a' : self.a})
        return cond
    
    def waitForCondition(self, condition, timeout = 60):
        ## Wait until end condition is satisfied, or timeout ##
        
        # wait for the telescope to stop moving before returning
        # create a buffer list to hold several samples over which the stop condition must be true
        n_buffer_samples = 1
        stop_condition_buffer = [(not condition) for i in range(n_buffer_samples)]

        # get the current timestamp
        start_timestamp = datetime.utcnow().timestamp()
        while True:
            #print('entering loop')
            time.sleep(0.1)
            timestamp = datetime.utcnow().timestamp()
            dt = (timestamp - start_timestamp)
            #print(f'wintercmd: wait time so far = {dt}')
            if dt > timeout:
                raise TimeoutError(f'command timed out after {timeout} seconds before completing')
            
            #stop_condition = condition()
            stop_condition = eval(condition)
            print(f'stop condition = {stop_condition}')
            # do this in 2 steps. first shift the buffer forward (up to the last one. you end up with the last element twice)
            stop_condition_buffer[:-1] = stop_condition_buffer[1:]
            # now replace the last element
            stop_condition_buffer[-1] = stop_condition
            
            if all(entry == True for entry in stop_condition_buffer):
                break 
    
class TargetError(Exception):
    pass

try:
    print(f'trying to do thing')
    raise TargetError(f'invalid target at location')
except Exception as e:
    print(f'while attempting to to thing, caught {e.__class__.__name__}: {e}')
    
thing = Thing()

#thing.waitForCondition(thing.is_odd)
#thing.waitForCondition('thing.state["a"]')