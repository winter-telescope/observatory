#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Dec 16 16:27:04 2020

@author: nlourie
"""


#from Pyro5.api import expose, behavior, serve
import Pyro5.api as pyro


@pyro.expose
@pyro.behavior(instance_mode = "single")
class Warehouse(object):
    def __init__(self):
        self.contents = ["chair", "bike", "flashlight", "laptop", "couch"]

    def list_contents(self):
        return self.contents

    def take(self, name, item):
        self.contents.remove(item)
        print("{0} took the {1}.".format(name, item))

    def store(self, name, item):
        self.contents.append(item)
        print("{0} stored the {1}.".format(name, item))
        
def main():
    pyro.Daemon.serveSimple(
        {
            Warehouse: "example.warehouse"
        },
        ns = True)
    
if __name__ == '__main__':
    main()