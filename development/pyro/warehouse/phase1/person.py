#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Dec 16 16:48:47 2020

pyro tutorial from here: https://pyro4.readthedocs.io/en/stable/tutorials.html#building-a-warehouse
code here: https://github.com/irmen/Pyro5/tree/master/examples/warehouse

@author: nlourie
"""

class Person(object):
    def __init__(self, name):
        self.name = name

    def visit(self, warehouse):
        print("This is {0}.".format(self.name))
        self.deposit(warehouse)
        self.retrieve(warehouse)
        print("Thank you, come again!")

    def deposit(self, warehouse):
        print("The warehouse contains:", warehouse.list_contents())
        item = input("Type a thing you want to store (or empty): ").strip()
        if item:
            warehouse.store(self.name, item)

    def retrieve(self, warehouse):
        print("The warehouse contains:", warehouse.list_contents())
        item = input("Type something you want to take (or empty): ").strip()
        if item:
            warehouse.take(self.name, item)