#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Feb 21 15:00:23 2023

labjackd.py: labjack daemon

This is a standalone daemon which handles all the querying of the labjacks,
and the conversion of raw reads to physical, eg Voltage --> Temperature for
thermistors, and Count --> Flow for the digital flowmeters.

NB:
This was previously done within the mainbody of WSP, the LJ reads were done
within the housekeeping class, and the Voltage --> Temperature was done using a
linterp in the dirfile. This worked fine, but now that we want lots of flow
sensors, and want the ability to pass the actual temperatures around within 
WSP it makes more sense to push this out to a daemon like everything else.

@author: nlourie
"""
import os
import Pyro5.core
import Pyro5.server
#import time
#from PyQt5 import uic, QtGui, QtWidgets
from PyQt5 import QtCore
from datetime import datetime
#from astropy.io import fits
import numpy as np
import sys
import signal
import threading
import logging
import json

# add the wsp directory to the PATH
wsp_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(1, wsp_path)
print(f'wsp_path = {wsp_path}')

try:
    from housekeeping import data_handler
    from housekeeping import labjacks
except:
    import data_handler
    import labjacks
from daemon import daemon_utils
from utils import logging_setup
from utils import utils
from utils import LUT_utils





class LabjackHandler(QtCore.QObject):
    
    
    def __init__(self, base_directory, config, dt = 500, name = 'labjacks', logger = None, verbose = False):
        
        super(LabjackHandler, self).__init__()   
        self.base_directory = base_directory
        self.config = config
        self.logger = logger
        self.verbose = verbose
        self.name = name
        self.dt = dt
        self.state = dict()
        
        # initialize a set of labjacks (automatically sets them all up based on the individual configs)
        self.ljs = labjacks.labjack_set(self.config, self.base_directory)
        
        # set up the labjack interpolation, etc
        self.setupThermLUTs()
        
        if verbose:
            self.daqloop = data_handler.daq_loop(self.pollLabjacks, dt = self.dt, name = self.name, print_thread_name_in_update = True, thread_numbering = 'norm')
        else:
            self.daqloop = data_handler.daq_loop(self.pollLabjacks, dt = self.dt, name = self.name)
    
        
    
    def log(self, msg, level = logging.INFO):
        if self.logger is None:
                print(msg)
        else:
            self.logger.log(level = level, msg = msg)
    
    def pollLabjacks(self):
        self.poll_timestamp = datetime.utcnow().timestamp()
        try:
            self.ljs.read_all_labjacks()
            self.parse_lj_state()
        except Exception as e:
            pass
        for lj in self.ljs.labjacks.keys():
            self.state.update({f'{lj}_is_connected' : self.ljs.labjacks[lj].connected})
        #self.printState()
    
    def setupThermLUTs(self):
        # set up dictionary with all the interpolation parameters for each LUT
        self.LUTs = dict()
        for lj in self.ljs.labjacks.keys():
            for ch in self.ljs.labjacks[lj].config['THERMOMETERS']:
                ftype = self.ljs.labjacks[lj].config['THERMOMETERS'][ch]['ftype']
                if ftype == 'linterp': 
                    LUT_file = self.ljs.labjacks[lj].config['THERMOMETERS'][ch]['LUT_file']
                    if LUT_file not in self.LUTs:
                        # if the LUT_file is not already in the dictionary of LUTs, add it:
                        x_lut, y_lut = np.loadtxt(os.path.join(self.base_directory, LUT_file), unpack = True)
                        LUT_obj = LUT_utils.LUT_Object(x_lut, y_lut)
                        self.LUTs.update({LUT_file : LUT_obj})
            
    def setupFlowmeterArrs(self):
        # set up dictionary with all the flowmeters which will make little
        # circular buffers so that we report back the average flow to smooth
        # out some of the bit noise that comes from the pulse counting
        pass
    
    def parse_lj_state(self):
        # this turns the raw labjack reads into things like temperature and flow
        for lj in self.ljs.labjacks.keys():
            # AINX --> V_LJX_AINX
            
            
            
            # DIOX --> V_LJX_DIOX
            
            # Flowmeters: DIO0_EF_READ_A --> COUNT_LJX_DIOX
            
            for ch in self.ljs.labjacks[lj].config['FLOWMETERS']:
                # try to make the flow by calculating the change in count since last poll
                INPUT = self.ljs.labjacks[lj].config['FLOWMETERS'][ch]['input']
                K_ppl  = self.ljs.labjacks[lj].config['FLOWMETERS'][ch]['K_ppl']
                count = self.ljs.labjacks[lj].state[f'{INPUT}_EF_READ_A']
                
                try:
                    dt_since_last_poll = self.poll_timestamp - self.state['last_poll_timestamp']
                    delta_count_since_last_poll = count - self.state[f'COUNT_{lj}_{INPUT}']
                    flow_lpm = (delta_count_since_last_poll/dt_since_last_poll) * (60.0/K_ppl)
                    self.state.update({f'{lj}_{ch}' : flow_lpm})
                except Exception as e:
                    # this will fail on the first run through the loop before accumulating history
                    # in general just eat this message to avoid lots of messages
                    if self.verbose:
                        self.log(f'could not calculate flow for {ch}: {e}')
                    pass
                # update the raw count for the input channel: eg, COUNT_LJ0_DIO1
                self.state.update({f'COUNT_{lj}_{INPUT}' : count})
            
            # Thermometers: AINX --> TEMP_LJX_AINX
            for ch in self.ljs.labjacks[lj].config['THERMOMETERS']:
                try:
                    INPUT = self.ljs.labjacks[lj].config['THERMOMETERS'][ch]['input']
                    ftype = self.ljs.labjacks[lj].config['THERMOMETERS'][ch]['ftype']
                    voltage = self.ljs.labjacks[lj].state[f'{INPUT}']
                    
                    if ftype == 'linterp':
                        LUT_file = self.ljs.labjacks[lj].config['THERMOMETERS'][ch]['LUT_file']
                        temp = self.LUTs[LUT_file].linterp(voltage)
                        self.state.update({f'TEMP_{lj}_{INPUT}' : temp})
                    
                    if ftype == 'lincom':
                        slope = self.ljs.labjacks[lj].config['THERMOMETERS'][ch]['slope']
                        intercept = self.ljs.labjacks[lj].config['THERMOMETERS'][ch]['intercept']
                        temp = voltage*slope + intercept
                        self.state.update({f'TEMP_{lj}_{INPUT}' : temp})

            
                except Exception as e:
                    # this will fail on the first run through the loop before accumulating history
                    # in general just eat this message to avoid lots of messages
                    if self.verbose:
                        self.log(f'could not calculate temperature for {ch}: {e}')   
                        
            # Update the last poll timestamp
            self.state.update({'last_poll_timestamp' : self.poll_timestamp})
    

    @Pyro5.server.expose
    def getState(self):
        return self.state 

    def printState(self):
        print(json.dumps(self.state, indent = 3))
        
class PyroGUI(QtCore.QObject):   
                  
    def __init__(self, base_directory, config, logger, verbose, parent=None ):            
        super(PyroGUI, self).__init__(parent)   
        print(f'main: running in thread {threading.get_ident()}')
        # how often do you want to poll the labjack (ms)?
        #dt = self.config['daq_dt']['hk']
        dt = 2000
        self.labjackHandler = LabjackHandler(base_directory, config, dt = dt, logger = logger, verbose = False)
        #ns_host = '192.168.1.10'
        #daemon_host = '192.168.1.20'
        ns_host = None
        daemon_host = None
        self.pyro_thread = daemon_utils.PyroDaemon(obj = self.labjackHandler, name = 'labjacks', ns_host = ns_host, daemon_host = daemon_host)
        self.pyro_thread.start()
        
  
        
def sigint_handler( *args):
    """Handler for the SIGINT signal."""
    sys.stderr.write('\r')
    
    main.labjackHandler.daqloop.quit()
    
    QtCore.QCoreApplication.quit()

if __name__ == "__main__":
    app = QtCore.QCoreApplication(sys.argv)
    
    doLogging = False
    
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
    verbose = False
    
    main = PyroGUI(wsp_path, config, verbose = verbose, logger = logger)

    
    signal.signal(signal.SIGINT, sigint_handler)

    # Run the interpreter every so often to catch SIGINT
    timer = QtCore.QTimer()
    timer.start(500) 
    timer.timeout.connect(lambda: None) 

    sys.exit(app.exec_())

