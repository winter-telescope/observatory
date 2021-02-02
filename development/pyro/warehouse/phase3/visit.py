#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Dec 16 16:48:47 2020
pyro tutorial from here: https://pyro4.readthedocs.io/en/stable/tutorials.html#building-a-warehouse
code here: https://github.com/irmen/Pyro5/tree/master/examples/warehouse

@author: nlourie
"""

# This is the code that visits the warehouse
import sys
#import Pyro5.api as pyro
import Pyro5 as pyro
from warehouse import Warehouse
from person import Person

sys.excepthook = pyro.errors.excepthook

warehouse = pyro.api.Proxy("PYRONAME:example.warehouse")
janet = Person("Janet")
henry = Person("Henry")
janet.visit(warehouse)
henry.visit(warehouse)