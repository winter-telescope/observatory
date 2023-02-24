#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Feb 23 15:34:11 2023

@author: winter
"""

import Pyro5.core
import Pyro5.server

class Hello(object):

    def __init__ (self):
        self.word = 'Hello'
    @Pyro5.server.expose
    def hello(self):
        return(self.word)

obj = Hello()
name = 'hello'
heimdall = '192.168.1.10'
ns = Pyro5.core.locate_ns()#host = heimdall)
#%%
freya = '192.168.1.20'
daemon = Pyro5.server.Daemon()#host = heimdall)
uri = daemon.register(obj)
ns.register(name, uri)