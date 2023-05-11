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
ns_host = None
#ns_host = '192.168.1.10'
ns = Pyro5.core.locate_ns(host = ns_host)
#uri = ns.lookup('labjacks')
#uri = ns.lookup('hello')
#obj = Pyro5.client.Proxy(uri)

#print(f'Name server registered items: {ns.list()}')

uri = ns.lookup('state')
state = Pyro5.client.Proxy(uri)
curstate = state.GetStatus()
count = curstate['count']
print(f'State Count is {count}')


uri = ns.lookup('labjacks')
lj = Pyro5.client.Proxy(uri)
ljstate = lj.getState()
print(f'LJ State = {ljstate}')


uri = ns.lookup('chiller')
chiller = Pyro5.client.Proxy(uri)
chiller_temp = chiller.GetStatus()['SystemDisplayValueStatus']
print(f'Chiller Temp = {chiller_temp}')