#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Aug  3 10:56:14 2021

@author: winter
"""
import json

class Thing():
    def __init__(self):
        self.a = False
        self.state = {}
        
    
    def update_state(self):
        for item in ['a']:
            try:
                self.state.update({item : getattr(self, item)})
            except Exception as e:
                print(f'error: {e}')
        
    def print_state(self):
        print(json.dumps(self.state, indent = 2))
t = Thing()

print(f'initial state')
t.print_state()
print()
t.update_state()
print('final state')
t.print_state()

