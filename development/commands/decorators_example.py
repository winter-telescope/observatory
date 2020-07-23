#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jul  6 17:58:22 2020

Examples about python decorators from here: https://realpython.com/primer-on-python-decorators/

@author: nlourie
"""

from decorators import do_twice,do_twice_args, cmd

@do_twice
def say_whee():
    print('whee!')

#@do_twice_args
#@cmd
def printWord(word):
    print(f"I'm printing the word: {word}")
 
#@cmd
def printWords(*kwds,**kwargs):
    print(f"I'm printing the words: {kwds}")
    
#print()    
#say_whee()


print()
printWord('farts')

d = {'prnt' : printWord,
     'prnts' : printWords}

print()
d['prnt']('farts')

print()
d['prnts']('poop','farts','poopfarts')

print()
args = ['string1', 502, 'string 2']
cmd = 'prnts'
d[cmd](*args)

class Shape(object):
    def __init__(self):
        self.nsides = int
        self.color = str
        
class SomeShapes(object):
    def __init__(self):
        pass
        
    class square(Shape):
        def __init__(self):
            self.name = 'square'
            super().__init__()