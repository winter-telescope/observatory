#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
All-python implemenation of dirfile setup and writing. This is a python-only
module which replicates some essential pygetdata functions but allows you to
write to dirfiles without having getdata installed.

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
        #print(f'{self.field}')
        self.spf = spf # sample freq
        self.fp = None # file pointer
        #print(f'   dtype = {dtype}, type(dtype) = {type(dtype)}')
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
        self.format_file = open(self.dirpath + '/format','w')
        
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
        
    def add_lincom_entry(self, field, input_field, slope, intercept, units = None, label = None):

        """
        add linear combination entry to the dirfile.
        
        at the moment only allows a linear combination of a single entry, although
        this could be made more general like the dirfile standard which allows up to three entries
        
        the created derived field will have a value determined by:
            value = field*slope + intercept
        
        Arguments:
            - fieldname:    name of the field to add
            - input_field:  name of the field that will be used as the input to the interpolation
            - slope:    the slope of the line
            - intercept: the intercept of the line
            - units:    units label that will be added to the format file/readable with kst
            - label:    axis label that will be added to the format file/readable with kst
        """
        
        
        # write the linterp entry in the dirfile db format file
        num_input_fields = 1
        self.format_file.write(f'{field} LINCOM {num_input_fields} {input_field} {slope} {intercept}')
        
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
            # if val is None, then handle it here:
            if val is None:
                val = -777
            # make sure the val is in the correct format:
            if self.entries[field].dtype == 'FLOAT64':
                val = float(val)
            elif self.entries[field].dtype == 'INT64':
                val = int(val)
            self.entries[field].fp.write(struct.pack(self.entries[field].ctype,val))
        
        # clear the write buffer. if you don't do this you can't check the file
        # while its being written (ie with kst) until it's been closed
        self.entries[field].fp.flush()
        
if __name__ == '__main__':
    
    #############################
    # An example implementation:
    #############################
    
    # create the dirfile directory
    now = str(int(datetime.now().timestamp()))
    dirname = now + '.dm'
    
    basedir = os.path.join(os.getenv("HOME"),'data')
    dirpath = os.path.join(basedir, dirname)
    linkpath = os.path.join(basedir, 'dm.lnk')
    
    #/* make a link to the current dirfile - kst can read this to make life easy... */
    try:
        os.symlink(dirpath,linkpath)
    except FileExistsError:
        print('deleting existing symbolic link')
        os.remove(linkpath)
        os.symlink(dirpath,linkpath)
    
    # create the entries object
    df = Dirfile(dirpath)
    
    spf = 10
    
    df.add_raw_entry(field = 'V0', 
                     spf = spf, 
                     dtype = "float64", 
                     units = 'V', 
                     label = 'Volts')
    
    df.add_raw_entry(field = 'Count',
                     spf = spf,
                     dtype = "int64",
                     units = None,
                     label = None)
    
    #df.add_linterp_entry(field, input_field, LUT_file)
    
    #V0 = list(range(df.entries['V0'].spf))
    #Count = list(range(df.entries['Count'].spf))
    
    V0 = []
    Count = []
    
    i = 0
    
    print('running fake data loop')
    while True:
        try:
            
            
            # update the count
            Count.append(float(i))
            
            # make a cosine curve for V0
            period = 30.0 # units = index units
            V = np.cos((2*np.pi/period)*i/spf) # note the division by spf makes the period come out properly
            V0.append(V)
            
            # if the vector is full, write it out and reset
            if len(V0) == spf:
        
                # write out the data
                df.write_field('V0', V0)
            
                df.write_field('Count', Count)
                
                # reset the vectors
                V0 = []
                Count = []
            else:
                pass
            
            # update the index
            i += 1
            
            
            
            time.sleep(0.1)
            
        except KeyboardInterrupt:
            break
        
    
    
