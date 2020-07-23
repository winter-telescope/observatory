#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jul 22 11:26:32 2020

@author: nlourie
"""
import functools
import time

class wrapper(object):
    def __init__(self, func, *args, **kwargs):
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.do_func()
    
    def do_func(self):
        self.func(*self.args, **self.kwargs)
        

class dec_wrapper(object):
    def __init__(self, func):
        functools.update_wrapper(self,func)
        self.func = func
        
    def __call__(self, *args, **kwargs):
        while True:
            self.func(*args, **kwargs)
            time.sleep(1)
def cmd(func):
    def wrapper_cmd(*args, **kwargs):
        func(*args, **kwargs)
    return wrapper_cmd


def printWord(word):
    print(f"I'm printing the word: {word}")
    
instance = wrapper(printWord, 'zorp')


@dec_wrapper
def printWord2(word):
    print(f"I'm printing the word: {word}") 
    
printWord2('zzzzzzp')