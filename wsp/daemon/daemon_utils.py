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
#import time
#from PyQt5 import uic, QtGui, QtWidgets
from PyQt5 import QtCore
#import numpy as np
import sys
import signal
import subprocess
import psutil
import threading
import time

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
    def __init__(self, obj, name, verbose = False):
        QtCore.QThread.__init__(self)
        
        # the object is the remote object which will be registered with the name server
        self.obj = obj
        
        # the name will be used to register it in the name server
        self.name = name
        
    def run(self):
        try:
            host = None
            ns = Pyro5.core.locate_ns()
        except Exception as e:
            host = Pyro5.socketutil.get_ip_address('localhost', workaround127 = True)
            ns = Pyro5.core.locate_ns(host = host)
        
        daemon = Pyro5.server.Daemon()
        self.uri = daemon.register(self.obj)
        ns.register(self.name, self.uri)
        daemon.requestLoop()
        
class PyroGUI(QtCore.QObject):   

                  
    def __init__(self, Object, name, parent=None ):            
        super(PyroGUI, self).__init__(parent)   
        print(f'PyroGUI {name}: main thread = {threading.get_ident()}')
        
        self.Object = Object
                
        self.pyro_thread = PyroDaemon(obj = self.Object, name = name)
        self.pyro_thread.start()


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
            pid = self.daemons[key].process.pid
            try:
                print(f'> killing {key} process with PID {pid}...')
                #os.kill(self.pids[key], signal.SIGKILL)
                os.kill(pid, signal.SIGKILL)
                time.sleep(0.5)
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

def getPIDS(progname):
    """
    get any pids of programs that are running with the specified program name
    """
    pidlist = list()
    for p in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if progname in p.name():
                pidlist.append(p.pid)
        except:
            pass
    return pidlist


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
                msg = f'killing {p.cmdline()[1]} process with PID {p.pid}'
                if logger is None:
                    print(msg)
                else:
                    logger.info(msg)
                os.kill(p.pid, signal.SIGKILL)
        except:
            pass

def killPIDS(pidlist, logger = None):
    
    if type(pidlist) is int:
        pidlist = [pidlist]
    
    
    for pid in pidlist:
        try:
            msg = f'>> killing process with PID {pid}'
            os.kill(pid, signal.SIGTERM)
        except:
            msg = f'could not kill process with PID {pid}'
        
        if logger is None:
            print(msg)
        else:
            logger.info(msg)

#%%

def checkParent(main_program_name, printall = False, verbose = False):
    main_pid = None
    child_pids = []
    
    py_processes = []
    main_process = None
    child_processes = []
    for p in psutil.process_iter(['pid', 'name','cmdline']):
        #p = psutil.Process(pid)
        try:
            if 'python' in p.name():
                py_processes.append(p)
        except:
            pass
    
    
    #main_program_name = 'wsp.py'
    for p in py_processes:
        #print(p.cmdline())
        try:
            if main_program_name in p.cmdline()[1]:
                main_process = p
                main_pid = p.pid
        except:
            pass
        
    if main_process is None:
        if verbose:
            print(f'No {main_program_name} process running.')
    
    else:
        for p in py_processes:
            if p.parent().pid == main_process.pid:
                child_processes.append(p)
        if verbose:
            print()
            print(f'Main Process:')      
            for p in [main_process]:
                print(f'\t pid     = \t {p.pid}')
                print(f'\t name    = \t {p.name()}')
                print(f'\t program = \t {p.cmdline()[1].split("/")[-1]}')
                print()
            print(f'Child Processes:')
            for p in child_processes:
                try:
                    print(f'\t pid     = \t {p.pid}')
                    child_pids.append(p.pid)
                    print(f'\t name    = \t {p.name()}')
                    print(f'\t program = \t {p.cmdline()[1].split("/")[-1]}')
                    print(f'\t parent  = \t {p.parent().cmdline()[1].split("/")[-1]}')
                    print()
                except Exception as e:
                    print(f'Could not parse process with PID = {p.pid}, {e}')
                
    # print all the process info
    #printall = False
    if verbose:
        print()
    if printall:
        print("All info for currently running Python Processes")    
        for p in py_processes:
            try:
                print(f'PID {p.pid}: \t{p.cmdline()}')
                print(f'\t\t\tParent Process = {p.parent().cmdline()[1].split("/")[-1]}')
                print()
            except:
                pass
    return main_pid, child_pids