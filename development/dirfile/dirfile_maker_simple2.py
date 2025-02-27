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


DTYPE_DICT = dict({'FLOAT64' : 'd',
                   'INT64' : 'q'})


class DFEntryType(object):
    def __init__(self,field, spf, dtype, units = None, label = None):
        self.field = field # field name
        self.spf = spf # sample freq
        self.fp = None # file pointer
        self.dtype = dtype.upper() # data type
        self.units = units
        self.label = label
        
        
        
        self.ctype = DTYPE_DICT[self.dtype]


class Dirfile(object):
    def __init__(self, dirpath):
        # entries holds a dictionary of entries in the dirfile
        self.entries = dict()
        self.dirpath = dirpath
        self.makeDirfile()
        self.makeFormatFile()
    
        
    
    def makeDirfile(self):
        os.mkdir(self.dirpath)
        
    def makeFormatFile(self):
        # write the format file, and create/open the raw data files */
        self.format_file = open(dirname + '/format','w')
        
    def add_raw_entry(self,field, spf, dtype = "float64", units = None, label = None):
        """
        add an entry to the dirfile.
        
        Arguments:
            - field:    name of the field to add
            - spf:      samples per frame of the new field
            - dtype:    datatype, specified the numpy way
            - units:    units label that will be added to the format file/readable with kst
            - label:    axis label that will be added to the format file/readable with kst
        """
        # first add the entry
        #entry = gd.entry(gd.RAW_ENTRY,field,0,(GDTYPE_LOOKUP[np.dtype(dtype)],spf))
        #self._df.add(entry)
        
        entry = DFEntryType(field, spf, dtype, units, label)
        self.entries.update({field : entry})
        
        # write the raw entry line to the format file
        self.format_file.write(f'{entry.field} RAW {entry.dtype} {entry.spf}\n')
        
        # open and create the file pointer for the faw data files where the data will be written
        self.entries[field].fp = open(self.dirpath + '/' + field,'wb')
        
        # now add the units and axis label to the format file
        if (not units is None):
            if (units.lower() != 'none'):
                self.format_file.write(f'{entry.field}/units STRING {entry.units}\n')
        if (not label is None):
            if (label.lower() != 'none'):
                self.format_file.write(f'{entry.field}/quantity STRING {entry.label}\n')
        self.format_file.flush()
    
    def add_linterp_entry(self, field, input_field, LUT_file, units = None, label = None):
        """
        add linear interpretation entry to the dirfile.
        
        Arguments:
            - fieldname:    name of the field to add
            - input_field:  name of the field that will be used as the input to the interpolation
            - LUT_file: filepath of the linear intepolation file to use to add 
            - units:    units label that will be added to the format file/readable with kst
            - label:    axis label that will be added to the format file/readable with kst
        """
        
        
        # write the linterp entry in the dirfile db format file
        self.format_file.write(f'{field} LINTERP {input_field} {LUT_file}')
        
        # now add the units and axis label to the format file
        if (not units is None):
            if (units.lower() != 'none'):
                self.format_file.write(f'{field}/units STRING {units}\n')
        if (not label is None):
            if (label.lower() != 'none'):
                self.format_file.write(f'{field}/quantity STRING {label}\n')
        self.format_file.flush()
    
    def write_field(self, field, data, start_frame = 'last'):
        """
        Wrapper for putdata: write the data to the specified field
        
        Argumenmts:
            - field:        the field to write the data to
            - data:         the data to write. takes a numpy array or list.
                            the length can be anything!
            - start_frame:  the frame at which to insert the data.
                            this probably wants to be 'last' or 0 for most 
                            types of data recording
                            can be an integer, or 'last'
                            if it's less than one or 'last' it will use the last frame
        """
        """
        if (str(start_frame).lower() == 'last') or (start_frame < 0):
            start_frame = self._df.nframes
            
        self._df.putdata(field, data, first_frame = start_frame)
        self._df.flush()
        """
        # write the data point as a binary entry using struct
        for val in data:
            self.entries[field].fp.write(struct.pack(self.entries[field].ctype,val))
        
        # clear the write buffer. if you don't do this you can't check the file
        # while its being written (ie with kst) until it's been closed
        self.entries[field].fp.flush()
        

# create the dirfile directory
now = str(int(datetime.now().timestamp()))
dirname = now + '.dm'

#/* make a link to the current dirfile - kst can read this to make life easy... */
try:
    os.symlink(dirname,'dm.lnk')
except FileExistsError:
    print('deleting existing symbolic link')
    os.remove('dm.lnk')
    os.symlink(dirname,'dm.lnk')

# create the entries object
df = Dirfile(dirname)


df.add_raw_entry(field = 'V0', 
                 spf = 10, 
                 dtype = "float64", 
                 units = 'V', 
                 label = 'Volts')

df.add_raw_entry(field = 'Count',
                 spf = 10,
                 dtype = "int64",
                 units = None,
                 label = None)

V0 = list(range(df.entries['V0'].spf))
Count = list(range(df.entries['Count'].spf))

print('running fake data loop')
while True:
    try:
        
        df.write_field('V0', V0)
    
        df.write_field('Count', Count)
    
        
        time.sleep(0.1)
        
    except KeyboardInterrupt:
        break
    
    
    
