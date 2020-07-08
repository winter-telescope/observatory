#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jul  6 17:58:22 2020

Examples about python decorators from here: https://realpython.com/primer-on-python-decorators/

@author: nlourie
"""

from decorators import do_twice,do_twice_args

@do_twice
def say_whee():
    print('whee!')

@do_twice_args
def printWord(word):
    print(f"I'm printing the word: {word}")
    
print()    
say_whee()


print()
printWord('farts')