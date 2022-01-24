#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jan 24 14:12:54 2022

@author: nlourie
"""

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Feb 16 17:42:28 2021

test daemon


@author: nlourie
"""
import os
from PyQt5 import QtCore
import sys
import signal
import numpy as np
import threading
from datetime import datetime
import matplotlib.pyplot as plt
import traceback

# add the wsp directory to the PATH
wsp_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'wsp')
sys.path.insert(1, wsp_path)
print(f'wsp_path = {wsp_path}')



DTYPE_DICT = dict({'FLOAT64' : 'd',
                   'INT64' : 'q',
                   'UINT16' : 'H'})


class daq_loop(QtCore.QThread):
    """
    This version follows the approach here: https://stackoverflow.com/questions/52036021/qtimer-on-a-qthread
    This makes sure that the QTimer belongs to *this* thread, not the thread that instantiated this QThread.
    To do this it forces the update function and Qtimer to be in the namespace of the run function,
    so that the timer is instantiated by the run (eg start) command
    
    This is a generic QThread which will execute the specified function
    at the specified cadence.

    It is meant for polling different sensors or instruments or servers
    each in their own thread so they don't bog each other down.
    """
    def __init__(self, func, dt, name = '', print_thread_name_in_update = False, thread_numbering = 'PyQt', autostart = True, *args, **kwargs):
        QtCore.QThread.__init__(self)

        self.index = 0
        self.name = name
        
        # define the function and options that will be run in this daq loop
        self.func = func
        self.args = args
        self.kwargs = kwargs

        # describe the loop rate
        self.dt = dt
        
        # keep this as an option to debug and print out the thread of each operation
        self._print_thread_name_in_update_ = print_thread_name_in_update
        # how do you want to display the thread? if either specify 'pyqt', or it will assume normal, eg threading.get_ident()
        self._thread_numbering_ = thread_numbering.lower()
        
        # start the thread itself
        if autostart:
            self.start()
    
    
    def run(self):
        def update():
            ### POLL THE DATA ###
            try:
                self.func(*self.args, **self.kwargs)
                
                if self._print_thread_name_in_update_:
                    if self._thread_numbering_ == 'pyqt':
                        print(f'{self.name}: running func: <{self.func.__name__}> in thread {self.currentThread()}')
                    else:
                        print(f'{self.name}: running func: <{self.func.__name__}> in thread {threading.get_ident()}')
            except Exception as e:
                '''
                do nothing, don't want to clog up the program with errors if there's
                a problem. let this get handled elsewhere.
                '''
                print(f'could not execute function <{self.func.__name__}> because of {type(e)}: {e}')
                print(f'FULL TRACEBACK: {traceback.format_exc()}')
                pass
    
            self.index += 1
        
        print(f'{self.name}: starting timed loop')
        self.timer = QtCore.QTimer(timerType = QtCore.Qt.PreciseTimer)
        self.timer.setInterval(self.dt)
        self.timer.timeout.connect(update)
        self.timer.start()
        self.exec()
        
    def __del__(self):
        self.wait()



class Counter(QtCore.QObject):
    def __init__(self, dt , name = 'counter', verbose = False):
        
        super(Counter, self).__init__()   
        
        self.name = name
        self.dt = dt
        self.count = 0
        self.loop_starttime = datetime.now().timestamp()
        
        NROWS = 1920
        NCOLS = 1080
        
        
        
        self.dataPath = os.path.join(os.getenv("HOME"), 'data', 'streamTest')
        self.streamFile = 'stream.dat'
        
        #self.framelen = int(NCOLS*NROWS*2)
        #self.framebuf = bytearray(self.framelen)
        
        frame_float = np.zeros((NROWS, NCOLS))
        self.frame = frame_float.astype(np.uint16)
        self.bindata = self.frame.flatten().tobytes()
        
        
        self.setupDataFile()
        
        self.counts = np.array([])
        self.dt_start = np.array([])
        self.dt_loop = np.array([])
        
        if verbose:
            self.daqloop = daq_loop(self.update, dt = self.dt, name = self.name, print_thread_name_in_update = True, thread_numbering = 'norm')
        else:
            self.daqloop = daq_loop(self.update, dt = self.dt, name = self.name)
    
    def setupDataFile(self):
        """
        init a file pointer where we'll save the data
        the mode is 'wb': 'w': write/overwrite the file, 'b': use bytes, eg binary data
        """
        
        self.fp = open(os.path.join(self.dataPath, self.streamFile), mode = 'wb')
        
        
        
        
        
    def update(self):
        now = datetime.now().timestamp()
        self.dt_since_last_loop_ms = (now - self.loop_starttime)*1.0e3
        self.loop_starttime = now
        
        """
        # update the frame?
        # update the fake data here:
        self.frame += self.count
        
        # turn the data to binary
        self.bindata = self.frame.tobytes()
        """
        # save the data here?
        self.fp.write(self.bindata)
        #self.fp.write(self.framebuf)
        
        # don't forget to flush!
        self.fp.flush()
        
        
        
        #update the count and note when the loop is done
        
        self.count += 1
        
        self.loop_endtime = datetime.now().timestamp()
        dt_loop = (self.loop_endtime - self.loop_starttime)*1.0e3
        
        # update the log of the data
        self.counts = np.append(self.counts, self.count)
        self.dt_start = np.append(self.dt_start, self.dt_since_last_loop_ms)
        self.dt_loop = np.append(self.dt_loop,dt_loop)
        
    def PrintResults(self):
        # print and summarize the results
        
        # turn the data to numpy arrays
        self.counts = np.array(self.counts[1:])
        self.dt_start = np.array(self.dt_start[1:])
        self.dt_loop = np.array(self.dt_loop[1:])
        
        fig, axes = plt.subplots(2,2, figsize = (10, 10))
        # plot the time between loop executions
        ax = axes[0][0]
        ax.plot(self.counts, self.dt_start, 'o')
        median_dt = np.median(self.dt_start)
        std_dt = np.std(self.dt_start)
        max_dt = np.max(self.dt_start)
        min_dt = np.min(self.dt_start)
        
        ax.plot(self.counts, median_dt + 0*self.dt_start, 'r--', label = f'Median')
        ax.plot(self.counts, median_dt + std_dt + 0*self.dt_start, 'g--', label = f'Median + 1$\sigma$')
        ax.plot(self.counts, median_dt - std_dt + 0*self.dt_start, 'g--', label = 'Median - 1$\sigma$')
        ax.set_ylabel('Time Between Loop Executions (ms)')
        ax.set_title(f'Nominal $\Delta$t = {self.dt} ms: Median $\Delta$t: {median_dt:.1f} ms\n$\sigma$ = {std_dt:.1f} ms, max $\Delta$t = {max_dt:.1f} ms, Num Points = {len(self.counts)}')
        ax.set_xlabel('Loop Number')

        ax.legend()
        
        # histogram
        axes[1][0].hist(self.dt_start, bins = np.arange(0, 25, 0.5))
        
        
        
        
        # plot the loop execution time
        
        # plot the time between loop executions
        ax = axes[0][1]
        ax.plot(self.counts, self.dt_loop, 'o')
        median_dt = np.median(self.dt_loop)
        std_dt = np.std(self.dt_loop)
        max_dt = np.max(self.dt_loop)
        min_dt = np.min(self.dt_loop)
        
        ax.plot(self.counts, median_dt + 0*self.dt_loop, 'r--', label = f'Median')
        ax.plot(self.counts, median_dt + std_dt + 0*self.dt_loop, 'g--', label = f'Median + 1$\sigma$')
        ax.plot(self.counts, median_dt - std_dt + 0*self.dt_loop, 'g--', label = 'Median - 1$\sigma$')
        ax.set_ylabel('Time for Loop to Execute (ms)')
        ax.set_title(f'Nominal $\Delta$t = {self.dt} ms: Median $\Delta$t: {median_dt:.1f} ms\n$\sigma$ = {std_dt:.1f} ms, max $\Delta$t = {max_dt:.1f} ms, Num Points = {len(self.counts)}')
        ax.set_xlabel('Loop Number')
        ax.legend()
        
        axes[1][1].hist(self.dt_loop, bins = np.arange(0, 25, 0.5))

        
        plt.tight_layout()
        
        
        
        
def sigint_handler( *args):
    """Handler for the SIGINT signal."""
    sys.stderr.write('\r')
    
    main.daqloop.quit()
    
    QtCore.QCoreApplication.quit()
    
    main.PrintResults()
    
    # close the file
    main.fp.close()

if __name__ == "__main__":
    app = QtCore.QCoreApplication(sys.argv)

    
    main = Counter(dt = 5, name = 'counter', verbose = False)

    
    signal.signal(signal.SIGINT, sigint_handler)

    # Run the interpreter every so often to catch SIGINT
    timer = QtCore.QTimer()
    timer.start(500) 
    timer.timeout.connect(lambda: None) 

    sys.exit(app.exec_())

