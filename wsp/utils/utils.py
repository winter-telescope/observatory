#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Feb  7 13:32:13 2020

utils.py

This is part of wsp

# Purpose #
This is a set of general utilities and functions that are useful across the 
wsp modules. Some are original, some are taken from elsewhere, including many
from MINERVA (https://github.com/MinervaCollaboration/minerva-control). Sources
are cited where functions are lifted from elsewhere (or are meant to be!). 

@author: nlourie
"""



import unicodecsv
import numpy as np
from datetime import datetime,timedelta
import time
import os
import sys
import pytz
import logging
import socket
import json
try:
    import pyfits
except:
    from astropy.io import fits as pyfits
import re
import subprocess, psutil, os, signal
import matplotlib.pyplot as plt
from astropy.visualization import astropy_mpl_style
plt.style.use(astropy_mpl_style)

from astropy.utils.data import get_pkg_data_filename
from astropy.io import fits

def query_server(cmd, ipaddr, port,line_ending = '\n', end_char = '', num_chars = 2048, timeout = 0.001):
    """
    This is a utility to send a single command to a remote server,
    then wait a response. It tries to return a dictionary from the returned  
    text.
    """
    
    
    # Connect to the server
    sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    sock.settimeout(timeout)
    server_address = (ipaddr, port)
    sock.connect(server_address)
    
    cmd = cmd + line_ending
    
    # Send a command
    sock.sendall(bytes(cmd,"utf-8"))

    total_data = []
    data = ''
    try:
        while True:
            data = sock.recv(2048).decode("utf-8")
            if end_char in data:
                total_data.append(data[:data.find(end_char)] + end_char)
                break
            total_data.append(data)
    except socket.timeout as e:
        print(e)
        
        """
        if len(total_data)>1:
            # check if the end_of_data_was split
            last_pair = total_data[-2]+total_data[-1]
            if end_char in last_pair:
                total_data[-2] = last_pair[:last_pair.find(end_char)]
                total_data.pop()
                break
        """
    sock.close()
    reply =  ''.join(total_data)
    try:
        d = json.loads(reply)
    except:
        d = reply
    return d
    






def plotFITS(filename):
    plt.close('all')
    image_file = filename
    #plt.ion()
    hdu_list = fits.open(image_file,ignore_missing_end = True)
    hdu_list.info()
    
    image_data = hdu_list[0].data
    plt.title('Last Image Taken:')
    
    imgplot = plt.imshow(image_data,cmap = 'gray')
    plt.show(block = False)
    plt.pause(0.1)
    
if __name__ == '__main__' :
    plt.figure()
    while True:
        i = 0
        print(f'taking image {i}')
        time.sleep(2)    
        #plt.plot([1,2,3])
        plotFITS('/home/winter/WINTER_GIT/code/wsp/data/' + 'testimage.FITS')
        i += 1
    #plt.show()


def getdatestr(date = 'today'):
    try:
        date = str(date)
        if date.lower() in  ['today','tonight']:
            datestr = tonight()
            
        else:
            date_obj = datetime.strptime(date,'%Y%m%d')
            datestr = date_obj.strftime('%Y%m%d')
        return datestr
    
    except:
        print('Date format invalid, should be YYYYMMDD')




## Functions gratefully lifted from MINERVA and converted to python3 ##
def readcsv(filename,skiprows=0):
    # parse the csv file
    with open(filename,'rb') as f:
        reader = unicodecsv.reader(f)
        for i in range(skiprows):
            next(reader)
        headers = next(reader)
        csv = {}
        for h in headers:
            csv[h.split('(')[0].strip()] = []
        for row in reader:
            for h,v in zip(headers,row):
                csv[h.split('(')[0].strip()].append(v)
        for key in csv.keys():
            try:csv[key] = np.asarray(csv[key],dtype = np.float32)
            except: csv[key] = np.asarray(csv[key])
        return csv


def tonight():
    # a similar version of the minerva function by NPL
    today = datetime.utcnow()
    calitz = pytz.timezone('America/Los_Angeles')
    today_cali = datetime.now(calitz)
    
    # if the UTC time is between 10a and 4p, ie cali time between 2a and 8a
    if datetime.now().hour >= 10 and datetime.now().hour <= 16:
        today = today + timedelta(days=1)
    return today.strftime('%Y%m%d')    

    
def night():
    # was called night in minerva, but tonight is a little more transparent
    today = datetime.utcnow()
    # if the UTC time is between 10a and 4p, ie cali time between 2a and 8a
    if datetime.now().hour >= 10 and datetime.now().hour <= 16:
        today = today + timedelta(days=1)
    return today.strftime('%Y%m%d')    

# BELOW FUNCTIONS LOOK HELPFUL BUT HAVE NOT BEEN TESTED FOR COMPATIBILITY
# converts a sexigesimal string to a float
# the string may be delimited by either spaces or colons
def ten(string):
    array = re.split(' |:',string)
    if "-" in array[0]:
        return float(array[0]) - float(array[1])/60.0 - float(array[2])/3600.0
    return float(array[0]) + float(array[1])/60.0 + float(array[2])/3600.0    


# run astrometry.net on imageName, update solution in header
def astrometry(imageName, rakey='RA', deckey='DEC',pixscalekey='PIXSCALE', pixscale=None, nopositionlimit=False, noquadlimit=False):
    hdr = pyfits.getheader(imageName)

    try:
        if pixscale == None:
            pixscale = float(hdr[pixscalekey])
    except:
        return False

    try: ra = float(hdr[rakey])
    except: ra = ten(hdr[rakey])*15.0
    
    try: dec = float(hdr[deckey])
    except: dec = ten(hdr[deckey])
    if dec > 90.0: dec = dec - 360.0
    
    radius = 3.0*pixscale*float(hdr['NAXIS1'])/3600.0
    
    cmd = 'solve-field --scale-units arcsecperpix' + \
        ' --scale-low ' + str(0.99*pixscale) + \
        ' --scale-high ' + str(1.01*pixscale)

    if not nopositionlimit:
        cmd += ' --ra ' + str(ra) + \
            ' --dec ' + str(dec) + \
            ' --radius ' + str(radius)
    if not noquadlimit:
        cmd += ' --quad-size-min 0.4' + \
            ' --quad-size-max 0.6'
    cmd += ' --cpulimit 30' + \
        ' --no-verify' + \
        ' --crpix-center' + \
        ' --no-fits2fits' + \
        ' --no-plots' + \
        ' --overwrite ' + \
        imageName
#        ' --use-sextractor' + \ #need to install sextractor
#        ' --quad-size-min 0.4' + \
#        ' --quad-size-max 0.6' + \

    cmd = r'/usr/local/astrometry/bin/' + cmd + ' >/dev/null 2>&1'
    os.system(cmd)
    
    baseName = os.path.splitext(imageName)[0]
    f = pyfits.open(imageName, mode='update')
    if os.path.exists(baseName + '.new'):
      
        # preserve original solution
        orighdr = pyfits.getheader(imageName)
        f[0].header['WCD1_1'] = float(f[0].header['CD1_1'])
        f[0].header['WCD1_2'] = float(f[0].header['CD1_2'])
        f[0].header['WCD2_1'] = float(f[0].header['CD2_1'])
        f[0].header['WCD2_2'] = float(f[0].header['CD2_2'])
        f[0].header['WCRVAL1'] = float(f[0].header['CRVAL1'])
        f[0].header['WCRVAL2'] = float(f[0].header['CRVAL2'])

        # copy the WCS solution to the file
        newhdr = pyfits.getheader(baseName + '.new')
        f[0].header['WCSSOLVE'] = 'True'
        f[0].header['WCSAXES'] = newhdr['WCSAXES']
        f[0].header['CTYPE1'] = newhdr['CTYPE1']
        f[0].header['CTYPE2'] = newhdr['CTYPE2']
        f[0].header['EQUINOX'] = newhdr['EQUINOX']
        f[0].header['LONPOLE'] = newhdr['LONPOLE']
        f[0].header['LATPOLE'] = newhdr['LATPOLE']
        f[0].header['CRVAL1'] = newhdr['CRVAL1']
        f[0].header['CRVAL2'] = newhdr['CRVAL2']
        f[0].header['CRPIX1'] = newhdr['CRPIX1']
        f[0].header['CRPIX2'] = newhdr['CRPIX2']
        f[0].header['CUNIT1'] = newhdr['CUNIT1']
        f[0].header['CUNIT2'] = newhdr['CUNIT2']
        f[0].header['CD1_1'] = newhdr['CD1_1']
        f[0].header['CD1_2'] = newhdr['CD1_2']
        f[0].header['CD2_1'] = newhdr['CD2_1']
        f[0].header['CD2_2'] = newhdr['CD2_2']
        f[0].header['IMAGEW'] = newhdr['IMAGEW']
        f[0].header['IMAGEH'] = newhdr['IMAGEH']
        f[0].header['A_ORDER'] = newhdr['A_ORDER']
        f[0].header['A_0_2'] = newhdr['A_0_2']
        f[0].header['A_1_1'] = newhdr['A_1_1']
        f[0].header['A_2_0'] = newhdr['A_2_0']
        f[0].header['B_ORDER'] = newhdr['B_ORDER']
        f[0].header['B_0_2'] = newhdr['B_0_2']
        f[0].header['B_1_1'] = newhdr['B_1_1']
        f[0].header['B_2_0'] = newhdr['B_2_0']
        f[0].header['AP_ORDER'] = newhdr['AP_ORDER']
        f[0].header['AP_0_1'] = newhdr['AP_0_1']
        f[0].header['AP_0_2'] = newhdr['AP_0_2']
        f[0].header['AP_1_0'] = newhdr['AP_1_0']
        f[0].header['AP_1_1'] = newhdr['AP_1_1']
        f[0].header['AP_2_0'] = newhdr['AP_2_0']
        f[0].header['BP_ORDER'] = newhdr['BP_ORDER']
        f[0].header['BP_0_1'] = newhdr['BP_0_1']
        f[0].header['BP_0_2'] = newhdr['BP_0_2']
        f[0].header['BP_1_0'] = newhdr['BP_1_0']
        f[0].header['BP_1_1'] = newhdr['BP_1_1']
        f[0].header['BP_2_0'] = newhdr['BP_2_0']
        success = True
    else:
        f[0].header['WCSSOLVE'] = 'False'
        success = False
    f.flush()
    f.close()

    # clean up extra files
    extstodelete = ['-indx.png','-indx.xyls','-ngc.png','-objs.png','.axy',
                    '.corr','.match','.new','.rdls','.solved','.wcs']
    for ext in extstodelete:
        if os.path.exists(baseName + ext):
            os.remove(baseName + ext)
        
    return success
    
# run sextractor on an image
def sextract(datapath,imagefile,sexfile='autofocus.sex',paramfile=None,convfile=None,catfile=None):
    #S Path on MinervaMAIN where all the .sex, .param, etc. files will be
    #S located
    sexpath = '/usr/share/sextractor/'

    #S This is the base command we be calling with sextractor. It has
    #S the default sexfile of autofocus.sex, which will be given some pretty
    #S general values for now.
    # We'll add on other parameters and arguements as they are specified
    sexcommand = 'sex '+datapath+imagefile+' -c ' + sexpath+sexfile
    
    #S If a paramfile was specfied, then we will use that instead of the
    #S default param file in autofocus.sex (which is autofocus.param)
    if paramfile != None:
        sexcommand+= ' -PARAMETERS_NAME ' + sexpath+paramfile

    #S Similar to above, but the convolution filter
    if convfile != None:
        sexcommand+= ' -FILTER_NAME ' + sexpath+convfile

    #S we're going to name the catalog after the image just by removing the
    #S fits and  adding cat. if a cat file is specified we'll use that.
    #S Datapath is the path where the image is (hopefully), but can be anywhere
    #S you want it to go.
    if catfile == None:
        catfile = imagefile.split('.fits')[0] + '.cat'
        sexcommand += ' -CATALOG_NAME ' + datapath+catfile

    #S so we a have sexcommand, which has all of its components split by
    #S spaces ideally, which will allow for just a .split to put in a list
    #S for subprocess.call
    subprocess.call(sexcommand.split())

    #S Just going to return the catalog file name for now, could return fwhm,
    #S whatever later
    return datapath+catfile

# read a generic sextractor catalog file into a dictionary
# the header values (PARAMS) become the dictionary keys
# objects are read into lists under each dictionary key
def readsexcat(catname):

    data = {}
    if not os.path.exists(catname): return data
    with open(catname,'rb') as filep:
        header = []
        for line in filep:
            # header lines begin with # and are the 3rd item in the line
            if line.startswith('#'):
                header.append(line.split()[2])
                for h in header:
                    data[h] = []
            # older sextractor catalogs contain a few nuisance lines; ignore those
            elif not line.startswith('-----') and not line.startswith('Measuring') and \
                    not line.startswith('(M+D)') and not line.startswith('Objects:'):
                # assume all values are floats
                values = [ float(x) for x in line.split() ]
                for h,v in zip(header,values):
                    data[h].append(v)
    for key in data.keys():
        #S try and convert to an np.array, and if not possible jsut pass
        #S the try is in case for some reason a non-numerical entry is 
        #S encountered. may be a l
        try:
            data[key] = np.array(data[key])
        except:
            pass

    return data
    
def dateobs2jd(dateobs):
    t0 = datetime.datetime(2000,1,1)
    t0jd = 2451544.5
    ti = datetime.datetime.strptime(dateobs,"%Y-%m-%dT%H:%M:%S.%f")
    return t0jd + (ti-t0).total_seconds()/86400.0

def findBrightest(imageName):
    catname = sextract('',imageName)
    cat = readsexcat(catname)
    try: brightest = np.argmax(cat['FLUX_ISO'])
    except: return None,None
    
    try:
        x = cat['XWIN_IMAGE'][brightest]
        y = cat['YWIN_IMAGE'][brightest]
        return x,y
    except:
        return None, None



def update_logger_path(logger, newpath):
    fmt = "%(asctime)s.%(msecs).03d [%(filename)s:%(lineno)s - %(funcName)s()] %(levelname)s: %(threadName)s: %(message)s"
    datefmt = "%Y-%m-%dT%H:%M:%S"
    formatter = logging.Formatter(fmt,datefmt=datefmt)
    formatter.converter = time.gmtime

    for fh in logger.handlers: logger.removeHandler(fh)
    fh = logging.FileHandler(newpath, mode='a')
    fh.setFormatter(formatter)
    logger.addHandler(fh)

def setup_logger(base_dir, night, logger_name):

    path = base_dir + '/log/' + night

    if os.path.exists(path) == False:
        # use makedirs instead of mkdir because it makes any needed intermediary directories
        os.makedirs(path)
        
    fmt = "%(asctime)s.%(msecs).03d [%(filename)s:%(lineno)s - %(funcName)s()] %(levelname)s: %(threadName)s: %(message)s"
    datefmt = "%Y-%m-%d  %H:%M:%S"

    logger = logging.getLogger(logger_name)
    formatter = logging.Formatter(fmt,datefmt=datefmt)
    formatter.converter = time.gmtime

    fileHandler = logging.FileHandler(path + '/' + logger_name + '.log', mode='a')
    fileHandler.setFormatter(formatter)

    #console = logging.StreamHandler()
    #console.setFormatter(formatter)
    #console.setLevel(logging.INFO)
    
    # add a separate logger for the terminal (don't display debug-level messages)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(fileHandler)
    #logger.addHandler(console)
    
    return logger






