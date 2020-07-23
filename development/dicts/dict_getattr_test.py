#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jul 15 19:18:11 2020

@author: nlourie
"""
class Obj(object):
    def __init__(self, config, telescope):
        self.config = config
        self.telescope = telescope
        self.status = dict()
        self.update_status()
    def update_status(self, default_value = -999):
        for field in self.config:
            try:
                key = field
                value = getattr(getattr(self,self.config[field]['sys']),field)
                self.status.update({key : value})
                print(f'> updated key = {key} with value = {value}')
            except Exception as e:
                self.status.update({key : default_value})
                print(f'> Could not update value for key = {key}, used default value {default_value} instead.')

    
    
class Telescope(object):
    def __init__(self):
        self.a = 1
        self.c = 2
    
    def update_a(self,num):
        self.a = num
    def update_c(self, num):
        self.c = num
        
telescope = Telescope()
thing = 'fart'

config = dict({'a' : dict({'sys' : 'telescope'}),
               'b' : dict({'sys' : 'telescope'}),
               'c' : dict({'sys' : 'telescope'})})

print('initializing object:')
obj = Obj(config = config, telescope = telescope)
print('status: ', obj.status)
print()

print('now updating telescope params:')
telescope.update_a(40)
telescope.update_c(50)

obj.update_status()
print('status: ', obj.status)

#%%
def get(name_of_thing, default_val = -999):
    try:
        return eval( name_of_thing)
    except Exception as e:
        print('could not get thing: ',e)
        return default_val

class Obj(object):
    def __init__(self, config, telescope):
        self.config = config
        self.telescope = telescope
        self.status = dict()
        self.update_status()
    def get(self, varname, default_val = -999):
        try:
            return eval( 'self.' + varname)
        except Exception as e:
            #print('could not get thing: ',e)
            return default_val
    
    def update_status(self, default_value = -999):
        for field in self.config:
            try:
                self.status.update({field : self.get(self.config[field]['var'])})
            except Exception as e:
                """
                we end up here if there's a problem either getting the field,
                or with the config for that field. either way log it and 
                just keep moving
                """
                #print(f'could not update field [{field}] due to {e.__class__}: {e}')
                pass
telescope = Telescope()

config = dict({'a' : dict({'var' : 'telescope.a'}),
               'b' : dict({'var' : 'telescope.b'}),
               'c' : dict({'varg' : 'telescope.c'})})

obj = Obj(config = config, telescope = telescope)
print(f'using get method, status = {obj.status}')
print()
newval = 30
print(f'updating telescope a value to {newval}')
obj.telescope.update_a(newval)
obj.update_status()
print(f'using get method, status = {obj.status}')



#%%%
default_value = -999
status = dict()
key = 'key1'
try:
    value = obj.telescope.az
except:
    value = default_value
status.update({key : value})
print(f'status = {status}')

#%%