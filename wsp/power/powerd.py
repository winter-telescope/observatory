#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Feb 16 17:42:28 2021

PDU Daemon

@author: nlourie
"""
import os
import Pyro5.core
import Pyro5.server
#import time
#from PyQt5 import uic, QtGui, QtWidgets
from PyQt5 import QtCore
#from astropy.io import fits
#import numpy as np
import sys
import signal
#import queue
import threading
import time
import logging
import getopt
import json
# add the wsp directory to the PATH
wsp_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(1, wsp_path)
print(f'wsp_path = {wsp_path}')


from housekeeping import data_handler
from daemon import daemon_utils
try:
    from power import pdu
except:
    import pdu
from utils import logging_setup
from utils import utils



class PowerManager(QtCore.QObject):
    def __init__(self,  pdu_config, auth_config, dt = 1000, name = 'power', logger = None, verbose = False):
        
        super(PowerManager, self).__init__()   
        
        self.pdu_config = pdu_config
        self.auth_config = auth_config
        self.name = name
        self.dt = dt
        
        self.state = dict()
        self.teststate = dict({'fart' : 'blarg'})
        self.pdu_dict = dict()
        self.setup_pdu_dict()
                
        self.timer = QtCore.QTimer()
        self.timer.setInterval(self.dt)
        self.timer.timeout.connect(self.update)
        self.timer.start()
        """
        if verbose:
            self.daqloop = data_handler.daq_loop(self.update, dt = self.dt, name = self.name, print_thread_name_in_update = True, thread_numbering = 'norm')
        else:
            self.daqloop = data_handler.daq_loop(self.update, dt = self.dt, name = self.name)
        """
    
    def setup_pdu_dict(self):
        
        # make a dictionary of all the pdus
        for pduname in pdu_config['pdus']:
            pduObj = pdu.PDU(pduname, self.pdu_config, self.auth_config, 
                             autostart = False, logger = logger)
            
            self.pdu_dict.update({pduname : pduObj})
            
        
    def update(self):

        for pduname in self.pdu_dict:
            
            # query the pdu status
            pdustate = self.pdu_dict[pduname].getState()
            self.state.update({pduname : pdustate})
            #print(pdustate['status'][7])

        
    @Pyro5.server.expose
    def pdu_off(self, pduname, outlet):
        self.pdu_dict[pduname].off(outlet)
        self.update()
    
    @Pyro5.server.expose
    def pdu_on(self, pduname, outlet):
        self.pdu_dict[pduname].on(outlet)
        self.update()
        
    @Pyro5.server.expose
    def pdu_cycle(self, pduname, outlet):
        self.pdu_dict[pduname].cycle(outlet)
        self.update()
                
    @Pyro5.server.expose
    def getState(self):
        #print(self.state)
        return self.state 
    
    @Pyro5.server.expose
    def test(self):
        print('TEST')
        return 'TEST' 
    
class PyroGUI(QtCore.QObject):   

                  
    def __init__(self, pdu_config, auth_config, ns_host, logger, verbose, parent=None ):            
        super(PyroGUI, self).__init__(parent)   
        print(f'main: running in thread {threading.get_ident()}')
        
        

        self.powerManager = PowerManager(pdu_config, auth_config, dt = 5000, name = 'power', verbose = verbose, logger = logger)
                
        self.pyro_thread = daemon_utils.PyroDaemon(obj = self.powerManager, name = 'power',
                                                   ns_host = ns_host)
        self.pyro_thread.start()
        
        """
        self.timer = QtCore.QTimer()
        self.timer.setInterval(500)
        self.timer.timeout.connect(self.check_pyro_queue)
        self.timer.start()
        """


            
        
def sigint_handler( *args):
    """Handler for the SIGINT signal."""
    sys.stderr.write('\r')
    
    #main.powerManager.daqloop.quit()
    
    QtCore.QCoreApplication.quit()

if __name__ == "__main__":
    
    
    #### GET ANY COMMAND LINE ARGUMENTS #####
    
    args = sys.argv[1:]
    print(f'args = {args}')
    
    # set the defaults
    verbose = False
    doLogging = True
    ns_host = '192.168.1.10'
    
    options = "vpn:s"
    long_options = ["verbose", "print", "ns_host:"]
    arguments, values = getopt.getopt(args, options, long_options)
    # checking each argument
    print()
    print(f'Parsing sys.argv...')
    print(f'arguments = {arguments}')
    print(f'values = {values}')
    for currentArgument, currentValue in arguments:
        if currentArgument in ("-v", "--verbose"):
            verbose = True
            print("Running in VERBOSE mode")
        
        elif currentArgument in ("-p", "--print"):
            doLogging = False
            print("Running in PRINT mode (instead of log mode).")
            
        elif currentArgument in ("-n", "--ns_host"):
            ns_host = currentValue
        
            
    print(f'powerd: launching with ns_host = {ns_host}')
    
    ##### RUN THE APP #####
    app = QtCore.QCoreApplication(sys.argv)

    # set the wsp path as the base directory
    base_directory = wsp_path

    # load the config
    config_file = base_directory + '/config/config.yaml'
    config = utils.loadconfig(config_file)
    
    # set up the logger
    if doLogging:
        logger = logging_setup.setup_logger(base_directory, config)    
    else:
        logger = None
    
    pdu_config = utils.loadconfig(os.path.join(wsp_path, 'config', 'powerconfig.yaml'))
    auth_config = utils.loadconfig(os.path.join(wsp_path, 'credentials', 'authentication.yaml'))
    
    
    main = PyroGUI(pdu_config, auth_config, ns_host, logger, verbose)
    
    signal.signal(signal.SIGINT, sigint_handler)

    # Run the interpreter every so often to catch SIGINT
    timer = QtCore.QTimer()
    timer.start(500) 
    timer.timeout.connect(lambda: None) 

    sys.exit(app.exec_())






    

