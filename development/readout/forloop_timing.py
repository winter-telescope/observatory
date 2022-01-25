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




class Counter(object):
    def __init__(self, dt , name = 'counter', verbose = False):
        
        
        self.name = name
        self.dt = dt
        self.count = 0
        self.init_time = datetime.now().timestamp()
        self.loop_starttime = self.init_time
        self.dt_since_start = 0
        
        NROWS = 1920
        NCOLS = 1080
        
        
        
        self.dataPath = os.path.join(os.getenv("HOME"), 'data', 'streamTest')
        
        self.filenum = 0
        self.streamFile = f'stream_{self.filenum}.dat'
        
        self.framelen = int(NCOLS*NROWS*2)
        self.framebuf = bytearray(self.framelen)
        
        frame_float = np.zeros((NROWS, NCOLS))
        self.frame = frame_float.astype(np.uint16)
        self.bindata = self.frame.flatten().tobytes()
        
        
        
        self.setupDataFile()
        self.dt_total = np.array([])
        self.counts = np.array([])
        self.dt_start = np.array([])
        self.dt_loop = np.array([])
    
        self.runUpdateLoop()
    
    def runUpdateLoop(self, nsecs = 5):
        print(f'starting update loop')
        while self.dt_since_start < nsecs:
            self.update()
    
                
        # close the file
        self.fp.close()
        
        self.PrintResults()
        
        
    def setupDataFile(self):
        """
        init a file pointer where we'll save the data
        the mode is 'wb': 'w': write/overwrite the file, 'b': use bytes, eg binary data
        """
        self.iters_since_file_setup = 0
        self.fp = open(os.path.join(self.dataPath, self.streamFile), mode = 'wb')
        
        
    def StartNewFile(self):
        self.fp.close()
        
        self.filenum += 1
        
        self.streamFile = self.streamFile = f'stream_{self.filenum}.dat'
        
        self.setupDataFile()
        
        
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
        if self.iters_since_file_setup> 1000:
            self.StartNewFile()
        
        # save the data here?
        #self.fp.write(self.bindata)
        self.fp.write(self.framebuf)
        
        # don't forget to flush!
        self.fp.flush()
        
        
        
        #update the count and note when the loop is done
        
        self.count += 1
        self.iters_since_file_setup += 1
        
        self.loop_endtime = datetime.now().timestamp()
        dt_loop = (self.loop_endtime - self.loop_starttime)*1.0e3
        self.dt_since_start = self.loop_starttime - self.init_time
        
        # update the log of the data
        self.counts = np.append(self.counts, self.count)
        self.dt_start = np.append(self.dt_start, self.dt_since_last_loop_ms)
        self.dt_loop = np.append(self.dt_loop,dt_loop)
        self.dt_total = np.append(self.dt_total, self.dt_since_start)

        
    def PrintResults(self):
        # print and summarize the results
        
        # turn the data to numpy arrays
        self.counts = self.counts[1:]
        self.dt_start = self.dt_start[1:]
        self.dt_loop = self.dt_loop[1:]
        self.dt_total = self.dt_total[1:]
        
        fig, axes = plt.subplots(2,2, figsize = (10, 10))
        # plot the time between loop executions
        ax = axes[0][0]
        ax.plot(self.dt_total, self.dt_start, 'o')
        median_dt = np.median(self.dt_start)
        std_dt = np.std(self.dt_start)
        max_dt = np.max(self.dt_start)
        min_dt = np.min(self.dt_start)
        
        ax.plot(self.dt_total, median_dt + 0*self.dt_start, 'r--', label = f'Median')
        ax.plot(self.dt_total, median_dt + std_dt + 0*self.dt_start, 'g--', label = f'Median + 1$\sigma$')
        ax.plot(self.dt_total, median_dt - std_dt + 0*self.dt_start, 'g--', label = 'Median - 1$\sigma$')
        ax.set_ylabel('Time Between Loop Executions (ms)')
        ax.set_title(f'Nominal $\Delta$t = {self.dt} ms: Median $\Delta$t: {median_dt:.1f} ms\n$\sigma$ = {std_dt:.1f} ms, max $\Delta$t = {max_dt:.1f} ms, Num Points = {len(self.counts)}')
        ax.set_xlabel('Runtime (s)')

        ax.legend()
        
        # histogram
        axes[1][0].hist(self.dt_start, bins = np.arange(0, 25, 0.5))
        
        axes[1][0].set_yscale('log')
        
        
        # plot the loop execution time
        
        # plot the time between loop executions
        ax = axes[0][1]
        ax.plot(self.dt_total, self.dt_loop, 'o')
        median_dt = np.median(self.dt_loop)
        std_dt = np.std(self.dt_loop)
        max_dt = np.max(self.dt_loop)
        min_dt = np.min(self.dt_loop)
        
        ax.plot(self.dt_total, median_dt + 0*self.dt_loop, 'r--', label = f'Median')
        ax.plot(self.dt_total, median_dt + std_dt + 0*self.dt_loop, 'g--', label = f'Median + 1$\sigma$')
        ax.plot(self.dt_total, median_dt - std_dt + 0*self.dt_loop, 'g--', label = 'Median - 1$\sigma$')
        ax.set_ylabel('Time for Loop to Execute (ms)')
        ax.set_title(f'Nominal $\Delta$t = {self.dt} ms: Median $\Delta$t: {median_dt:.1f} ms\n$\sigma$ = {std_dt:.1f} ms, max $\Delta$t = {max_dt:.1f} ms, Num Points = {len(self.counts)}')
        ax.set_xlabel('Runtime (s)')
        ax.legend()
        
        axes[1][1].hist(self.dt_loop, bins = np.arange(0, 25, 0.5))
        axes[1][1].set_yscale('log')

        
        plt.tight_layout()
        
        
        
 
    
    
if __name__ == "__main__":
    app = QtCore.QCoreApplication(sys.argv)

    
    main = Counter(dt = 0, name = 'counter', verbose = False)

    
    