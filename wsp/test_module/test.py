#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
This is a test module to test how to import and create modules and packages

@nlourie

"""

import numpy as np

class dumb:
    def __init__(self,name):
        self.name = name
        
    def printname(self):
        print("my dumb name is: ",np.str(self.name))
        print("the name of the program running is: ",__name__)
	


