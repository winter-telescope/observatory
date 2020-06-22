#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Apr 30 16:05:33 2020

Trying to work with pygetdata


@author: nlourie
"""

import sys
import os
import re
import array
import pygetdata as getdata
import numpy as np
import matplotlib.pyplot as plt
import shutil


# Read in a dirfile
df = getdata.dirfile('dm.lnk')

f0 = 5
n_frames = 10

print('Available Fields:')
for field in df.field_list():
    print(' ',field.decode("utf-8"))

cos = df.getdata("FCOS", getdata.FLOAT, first_frame = f0, num_frames = n_frames)

index = df.getdata("INDEX", getdata.FLOAT, first_frame = f0, num_frames = n_frames)


# Create a dirfile
"""
This if from here: https://github.com/syntheticpp/dirfile/blob/master/bindings/python/test/big_test.py#L140
It's the error checking section from the pygetdata installation
    
# create the dirfile first
data=array.array("B",range(1,81))
os.system("rm -rf dirfile")
os.mkdir("dirfile")
file=open("dirfile/data", 'wb') # NLhad to add the b for bytes otherwise it gets a write error: https://medium.com/@whitelotus/python-error-typeerror-write-argument-must-be-str-not-bytes-730714328ebd
data.tofile(file)
file.close()

ne = 0

fields = ["INDEX", "alias", "bit", "carray", "const", "data", "div", "lincom",
"linterp", "mplex", "mult", "phase", "polynom", "recip", "sbit", "string",
"window"]

nfields = 17
file=open("dirfile/format", 'w')
file.write(
    "/ENDIAN little\n"
    "data RAW INT8 8\n"
    "lincom LINCOM data 1.1 2.2 INDEX 2.2 3.3;4.4 linterp const const\n"
    "/META data mstr STRING \"This is a string constant.\"\n"
    "/META data mconst CONST COMPLEX128 3.3;4.4\n"
    "/META data mlut LINTERP DATA ./lut\n"
    "const CONST FLOAT64 5.5\n"
    "carray CARRAY FLOAT64 1.1 2.2 3.3 4.4 5.5 6.6\n"
    "linterp LINTERP data /look/up/file\n"
    "polynom POLYNOM data 1.1 2.2 2.2 3.3;4.4 const const\n"
    "bit BIT data 3 4\n"
    "sbit SBIT data 5 6\n"
    "mplex MPLEX data sbit 1 10\n"
    "mult MULTIPLY data sbit\n"
    "div DIVIDE mult bit\n"
    "recip RECIP div 6.5;4.3\n"
    "phase PHASE data 11\n"
    "window WINDOW linterp mult LT 4.1\n"
    "/ALIAS alias data\n"
    "string STRING \"Zaphod Beeblebrox\"\n"
    )
file.close()

file=open("dirfile/form2", 'w')
file.write("const2 CONST INT8 -19\n")
file.close()

"""

#%%
"""
# This is some code from Joy pointing out a bug in the code:
# Source: https://sourceforge.net/p/getdata/mailman/message/34463215/

#===================================================================
#! /usr/bin/python

import pygetdata
import os
import shutil
import pylab as pl

# Make new dirfile
dirfile_name = "dirfile_example"
dirfile_path = os.path.join(".", dirfile_name)
if os.path.isdir(dirfile_path):
    shutil.rmtree(dirfile_path)

spf = 1
first_frame = 0
num_frames = 100 # If this is bigger than 10000 Joy says it throws a segfault

d = pygetdata.dirfile(dirfile_path, pygetdata.CREAT | pygetdata.RDWR )#|pygetdata.GZIP_ENCODED)
entry = pygetdata.entry(pygetdata.RAW_ENTRY, 'data', 0, (pygetdata.FLOAT32,spf))
d.add(entry)
data = pl.arange(0.0, num_frames)
d.putdata('data', data , first_frame=first_frame)
d.close()

# Read and print dirfile field
print ('== 1st pass == ')
d = pygetdata.dirfile(dirfile_path)
print ('dirfile nframe', d.nframes)
read_data = d.getdata('data')
print ('data read:')
print( read_data[-10:])
d.close()

# Update the dirfile to write array starting at the end of previous array
first_frame += num_frames
d = pygetdata.dirfile(dirfile_path, pygetdata.CREAT | pygetdata.RDWR )#|pygetdata.GZIP_ENCODED)
d.putdata('data', pl.arange(num_frames, 2*num_frames),
first_frame=first_frame)
d.close()

# Read and plot dirfile
print( '== 2nd pass ==')
d = pygetdata.dirfile(dirfile_path)
print ('dirfile nframe', d.nframes)
read_data = d.getdata('data')
print ('data read:')
print (read_data[-10:])
d.close()

"""

#%%

# First define all the field names of the dirfile

fast_spf = 20
slow_spf = 1

fields = [["fcount",fast_spf,-1,'d'],
          ["scount",slow_spf,-1,'d'],
          ["fcos",fast_spf,-1,'d'],
          ["scos",slow_spf,-1,'d']]

# Create a new database

# Make new dirfile
dirfile_name = "dirfile_example"
dirfile_path = os.path.join(".", dirfile_name)
if os.path.isdir(dirfile_path):
    shutil.rmtree(dirfile_path)

# To make a new dirfile you do this:
    #new_dirfile = getdata.dirfile(dirfile_path, flag1 | flag2 | ...)
    # where the flags are specified here: http://getdata.sourceforge.net/getdata.html
    # under "gd_cbopen()", and the "GD_" is replaced with "getdata." in the calls
#db = getdata.dirfile(dirfile_path, getdata.CREAT | getdata.RDWR | getdata.GZIP_ENCODED)
db = getdata.dirfile(dirfile_path,getdata.CREAT | getdata.RDWR)
'''
for field in fields:
    entry = getdata.entry(getdata.RAW_ENTRY,field,0,(getdata.FLOAT64,20))
    db.add(entry)
            
'''
fieldname = 'data'
units = 'V'
label = 'Voltage'
spf = 20
entry = getdata.entry(getdata.RAW_ENTRY,fieldname,0,(getdata.FLOAT64,spf))
db.add(entry)
db.flush()
#%%
# write the format file, and create/open the raw data files */
format_file = open(dirfile_name + '/format','a')
format_file.write(f"{fieldname}/units STRING {units}\n{fieldname}/quantity STRING {label}\n")   
format_file.close()
#%%
# add data!
i = 0
try:
    while i<100:
        start = spf*i
        end = start+spf
        x = np.arange(start,end)*0.01
        data = np.cos(10*x)
        db.putdata(fieldname,data,first_frame = db.nframes)
        db.flush()
        i+=1
    
except KeyboardInterrupt:
    pass

# Read and print dirfile field
print ('== 1st pass == ')
d = getdata.dirfile(dirfile_path)
print ('dirfile nframe', d.nframes)
read_data = d.getdata('data')
print ('data read:')
print( read_data)
d.close()

