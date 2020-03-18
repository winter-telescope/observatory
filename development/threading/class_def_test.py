#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Mar 17 13:02:43 2020

Just testing out this alternate method of defining classes
I've found in internet tutorials


@author: nlourie
"""


# These are equivalent ways to define class attributes
class thing():
    
    a = 5
    b = 7
    


class thingy():
    def __init__(self):
        self.a = 5
        self.b = 7

thing1 = thing()
thing2 = thingy()      

print('Make a Thing:')
print(f'   thing.a = {thing1.a}')
print(f'   thing.b = {thing1.b}')
print()
print('Make a Thingy:')
print(f'   thingy.a = {thing2.a}')
print(f'   thingy.b = {thing2.b}')
print()