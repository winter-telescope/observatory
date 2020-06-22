#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jun 16 12:30:12 2020

This is an attempt to recreate Barth's "dirfile_maker_simple.c" code in Python,
downloaded from here: https://sourceforge.net/p/getdata/mailman/message/29184811/
using timing methods from PyQt5

@author: nlourie
"""

import numpy as np
from datetime import datetime
import os
import time
import struct
from PyQt5 import uic, QtCore, QtGui, QtWidgets
import signal
import sys


class DFEntryType(object):
    def __init__(self,fieldname, spf, fp, dtype):
        self.field = fieldname # field name
        self.spf = spf # sample freq
        self.fp = fp # file pointer
        self.type = dtype # data type
        """
        # datatype:
          'f' = FLOAT32
          'd' = FLOAT64
          'u' = UINT16
          for others see getdata documentation
        """
    def write(self,data_point):
        '''
        writes the given data point to the file pointer in binary
        to be used in event loop to add entry to the dirfile
        '''
        # write the data point as a binary entry using struct
        self.fp.write(struct.pack(self.type,data_point))
        
        # clear the write buffer. if you don't do this you can't check the file
        # while its being written (ie with kst) until it's been closed
        self.fp.flush()
       
class DFEntries(object):
    def __init__(self):
        # entries holds a dictionary of entries in the dirfile
        self.entries = dict()
    def add_entry(self,DFEntry):
        
        if 'DFEntryType' in str(type(DFEntry)):
            self.entries.update({DFEntry.field : DFEntry})
        else:
            print(f'Entry of type "{type(DFEntry)}" not a valid DFEntry type')


# time between frames (ms)
dt_frame = 1000.0

# samples per frame of slow loop
slow_spf = 5

# time between executions of the slow loop
dt_slow = dt_frame/slow_spf

# saamples per frame of fast loop
fast_spf = 200

# time between executions of the fast loop
dt_fast = dt_frame/fast_spf

# a list of fields we are going to create
fields = [["fcount",fast_spf,-1,'d'],
          ["scount",slow_spf,-1,'d'],
          ["fcos",fast_spf,-1,'d'],
          ["scos",slow_spf,-1,'d']]
    

# create the entries object
df = DFEntries()

# add all the fields to the entries object
for i in range(len(fields)):
    entry = DFEntryType(fields[i][0],fields[i][1],fields[i][2],fields[i][3])
    df.add_entry(entry)


# create the dirfile directory
now = str(int(datetime.now().timestamp()))
dirname = now + '.dm'
os.mkdir(dirname)

#file = open(filename,"w")

# write the format file, and create/open the raw data files */
format_file = open(dirname + '/format','w')

# entries for the raw fields
for key in df.entries.keys():
    # write the raw entry line to the format file
    format_file.write(f'{df.entries[key].field} RAW {df.entries[key].type} {df.entries[key].spf}\n')
    
    # open and create the file pointer for the faw data files where the data will be written
    df.entries[key].fp = open(dirname + '/' + df.entries[key].field,'wb')
    
# create some derived fields
format_file.write("SCOS LINCOM 1 scos 0.0054931641 -180\n")
format_file.write("SCOS/units STRING ^o\nSCOS/quantity STRING Angle\n")    

format_file.write("FCOS LINCOM 1 fcos 0.0054931641 -180\n")
format_file.write("FCOS/units STRING ^o\nFCOS/quantity STRING Angle\n")    
   
    
format_file.close()

#/* make a link to the current dirfile - kst can read this to make life easy... */
try:
    os.symlink(dirname,'dm.lnk')
except FileExistsError:
    print('deleting existing symbolic link')
    os.remove('dm.lnk')
    os.symlink(dirname,'dm.lnk')


class slow_loop(QtCore.QThread):
    
    def __init__(self,update_time):
        QtCore.QThread.__init__(self)
        #self.n = input("  Enter a number to count up to: ")
        self.index = 0
        self.dt = update_time
    def __del__(self):
        self.wait()
    
    def update(self):
        # Only print the even numbers
        self.index +=1
        
        #print("slowloop: %d" % self.index)
        df.entries['scount'].write(self.index)
        
        scos = 4000*np.cos(2.0*np.pi*self.index/100.0) + 32768 + 1000*np.random.rand()
        df.entries['scos'].write(scos)
        
    def run(self):
        print("slowloop: starting")
        
        self.timer = QtCore.QTimer()
        self.timer.setInterval(self.dt)
        self.timer.timeout.connect(self.update)
        self.timer.start()
        self.exec() # YOU NEED THIS TO START UP THE THREAD!

class fast_loop(QtCore.QThread):
    
    def __init__(self,update_time):
        QtCore.QThread.__init__(self)
        #self.n = input("  Enter a number to count up to: ")
        self.index = 0
        self.dt = update_time
    def __del__(self):
        self.wait()
    
    def update(self):
        # Only print the even numbers
        self.index +=1
        if np.mod(self.index,1000) == 0:   
            print("fastloop: %d" % self.index)
        #print(f"    fastloop: {self.index}")
        df.entries['fcount'].write(self.index)
        
        fcos = 4000*np.cos(2.0*np.pi*self.index/100.0) + 32768 + 1000*np.random.rand()
        df.entries['fcos'].write(fcos)
        
    def run(self):
        print("fastloop: starting")
        
        self.timer = QtCore.QTimer()
        self.timer.setInterval(self.dt)
        self.timer.timeout.connect(self.update)
        self.timer.start()
        self.exec() # YOU NEED THIS TO START UP THE THREAD!

class writeThread(QtCore.QThread):
    
    def __init__(self,update_time):
        self.dt = update_time
    
    


class main(QtCore.QObject):                         # Specify the class your are specializing.
    def __init__(self, parent=None):            # All QObjects receive a parent argument (default to None)
        super(main, self).__init__(parent)   # Call parent initializer.
        
        # define the housekeeping data dictionaries
        # current state values
        self.state = dict()
        self.curframe = dict()
    
        self.fastloop = fast_loop(update_time = dt_fast)
        self.slowloop = slow_loop(update_time = dt_slow)
        
        self.fastloop.start()
        self.slowloop.start()
        
        

def sigint_handler(*args):
    """Handler for the SIGINT signal."""
    sys.stderr.write('\r')
    QtWidgets.QApplication.quit()

if __name__ == "__main__":
    signal.signal(signal.SIGINT, sigint_handler)
    app = QtWidgets.QApplication(sys.argv)

    mainthread = main()

    sys.exit(app.exec_())
