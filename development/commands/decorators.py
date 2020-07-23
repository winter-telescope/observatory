#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jul  6 17:57:51 2020

@author: nlourie
"""

def do_twice(func):
    def wrapper_do_twice():
        func()
        func()
    return wrapper_do_twice

def do_twice_args(func):
    def wrapper_do_twice(*args, **kwargs):
        func(*args, **kwargs)
        func(*args, **kwargs)
    return wrapper_do_twice

def cmd(func):
    def wrapper_cmd(*args, **kwargs):
        func(*args, **kwargs)
    return wrapper_cmd