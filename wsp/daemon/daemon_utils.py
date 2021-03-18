#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Mar  4 14:46:42 2021

daemon_utils.py

This is part of wsp

# Purpose #

This program is a module of common functions used for many of the hardware
daemons. In particular these are common functions which allow daemons to be
easily used within the PyQt framework which allows the daemons to be
multithreaded programs.


@author: nlourie
"""

import os
import Pyro5.core
import Pyro5.server
import time
from PyQt5 import uic, QtCore, QtGui, QtWidgets
import numpy as np
import sys
import signal
import subprocess
import psutil

# add the wsp directory to the PATH
wsp_path = os.path.dirname(os.getcwd())
sys.path.insert(1, wsp_path)



class PyroDaemon(QtCore.QThread):
    """
    This creates a dedicated QThread which operates the Pyro5 requestLoop.
    In a PyQt program this must happen in it's own thread, otherwise it will
    block the main thread. This class instantiates a new thread dedicated
    to handling communications with the daemon. It registers some object (obj)
    with the name server with name (name).
    
    Note that the name server must be running for this to work. If not it will
    crash. We may want to handle this more gracefully somehow if the nameserver
    dies.
    """
    def __init__(self, obj, name):
        QtCore.QThread.__init__(self)
        
        # the object is the remote object which will be registered with the name server
        self.obj = obj
        
        # the name will be used to register it in the name server
        self.name = name
        
    def run(self):
        daemon = Pyro5.server.Daemon()

        ns = Pyro5.core.locate_ns()
        self.uri = daemon.register(self.obj)
        ns.register(self.name, self.uri)
        daemon.requestLoop()



class daemon_list():
    def __init__(self):
        self.daemons = dict()
    
    def add_daemon(self, daemon):
        self.daemons.update({daemon.name : daemon})
        #self.pids.update({daemon.name : daemon.pid})
    
    def launch_all(self):
        for key in self.daemons.keys():
            try:
                self.daemons[key].launch()
                print(f'launching {key} daemon in system PID {self.daemons[key].process.pid}')
            except Exception as e:
                print(f'could not launch {key} daemon due to error: {e}')
                
    def kill_all(self):
        for key in self.daemons.keys():
            try:
                print(f'> killing {key} process...')
                #os.kill(self.pids[key], signal.SIGKILL)
                os.kill(self.daemons[key].process.pid, signal.SIGKILL)
            except Exception as e:
                print(f'could not kill {key} daemon, {e}')
                
class PyDaemon(object):
    """
    this is a general class for creating new instances of daemon python programs
    there will be an instance for each daemon that wsp launches
    
    each daemon has the following attributes:
        name: this is the way that it will be tracked
        pid: process id of the launched program
        filepath: this is the full file path of the program to launch
        args: additional command line arguments that will be used as argv to launch the program
    """
    def __init__(self, name, filepath, args = None, python = True):
        
        self.name = name
        self.filepath = filepath
        self.args = args
        self.pid = None
        self.process = None
        if python == True:
            self._processargs_ = ["python", self.filepath]
        else:
            self._processargs_ = [self.filepath]
        if not args is None:
            for arg in args:
                self._processargs_.append(arg)
    
    def launch(self):
        self.process = subprocess.Popen(self._processargs_, shell = False)
        self.pid = self.process.pid
        
        return self.process
    
    """def add_to_list(self,daemonlist):
        # adds the daemon to the specified list
        daemonlist.add_daemon(self)"""


def cleanup(daemons_to_kill = list(), logger = None):
    py_processes = list()
    
    for p in psutil.process_iter(['pid', 'name','cmdline']):
        #p = psutil.Process(pid)
        try:
            if 'python' in p.name():
                py_processes.append(p)
        except:
            pass
    
    for p in py_processes:
        try:
            if any(daemon_to_kill in p.cmdline()[1] for daemon_to_kill in daemons_to_kill):
                msg = f'killing process with PID {p.pid}'
                if logger is None:
                    print(msg)
                else:
                    logger.info(msg)
                os.kill(p.pid, signal.SIGKILL)
        except:
            pass
