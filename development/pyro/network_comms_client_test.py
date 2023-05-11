#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Feb 23 15:38:27 2023

@author: winter
"""

import os
os.environ["PYRO_LOGFILE"] = "pyro.log"
os.environ["PRYO_LOGLEVEL"] = "DEBUG"

import Pyro5.client

ns = Pyro5.core.locate_ns(host = '192.168.1.10')
#uri = ns.lookup('labjacks')
#uri = ns.lookup('hello')
#obj = Pyro5.client.Proxy(uri)

#print(f'Name server registered items: {ns.list()}')

uri = ns.lookup('state')
state = Pyro5.client.Proxy(uri)


uri = ns.lookup('labjacks')
lj = Pyro5.client.Proxy(uri)
