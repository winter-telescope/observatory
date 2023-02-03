#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Feb  3 14:39:38 2023

@author: winter
"""

import Pyro5.core

ns = Pyro5.core.locate_ns()

# unregister all the entries
entrylist = list(ns.list().keys())[1:]
print(f'all entries: {entrylist}')
for name in entrylist:
    print(f'removing {name}...')
    ns.remove(name)
    
entrylist = list(ns.list().keys())[1:]
print(f'all entries: {entrylist}')