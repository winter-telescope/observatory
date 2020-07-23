#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jul  7 12:45:37 2020

@author: nlourie
"""
import queue
customers = queue.PriorityQueue() #we initialise the PQ class instead of using a function to operate upon a list. 
customers.put((2, "1"))
customers.put((3, "2"))
customers.put((1, "3"))
customers.put((4, "4"))
customers.put((2, "5"))
while not customers.empty():
    priority, item = customers.get() 
    print(item)
#Will print names in the order: Riya, Harry, Charles, Stacy.