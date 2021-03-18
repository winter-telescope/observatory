#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Mar 18 12:24:22 2021

@author: nlourie
"""

class signalCmd(object):
    '''
    this is an object which can pass commands and args via a signal/slot to
    other threads, ideally for daemons
    '''
    def __init__(self, cmd, *args, **kwargs):
        self.cmd = cmd
        self.argdict = dict()
        self.args = args
        self.kwargs = kwargs

"""
# function to call
        def wibble(a, b, foo='foo'):
            print(a, b, foo)
        
        
        # have to be in the same scope as wibble
        def call_function_by_name(function_name, args=[], kwargs={}):
            getattr(sys.modules[__name__], function_name)(*args, **kwargs)
        
            
        call_function_by_name('wibble', args=['arg1', 'arg2'], kwargs={'foo': 'bar'})
        
"""

class Main(object):
    
    def __init__(self):
        pass
    
    def print_word(self, word, secondWord = None, *args, **kwargs):
        
        if secondWord is None:
            print(f"I'm printing the word: {word}")
        
        else:
            print(f"I'm printing the word: {word} and also the word: {secondWord}")
    
    
    
    def doCommand(self, cmd_obj):
        """
        This is connected to the newCommand signal. It parses the command and
        then executes the corresponding command from the list below
       
        
        """
        cmd = cmd_obj.cmd
        args = cmd_obj.args
        kwargs = cmd_obj.kwargs
        
        try:
            getattr(self, cmd)(*args, **kwargs)
        except:
            pass

main = Main()

cmds = list()

cmds.append(signalCmd('print_word', word = 'dumb'))

cmds.append(signalCmd('print_word', 'thingy'))

cmds.append(signalCmd('print_word', 'apple', secondWord = 'banana'))

for cmd in cmds:
    main.doCommand(cmd)