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
import pytz
import logging
import yaml
import socket
import glob
import json
try:
    import pyfits
except:
    from astropy.io import fits as pyfits
import re
import subprocess
import matplotlib.pyplot as plt
from astropy.visualization import astropy_mpl_style
plt.style.use(astropy_mpl_style)

#from astropy.utils.data import get_pkg_data_filename
from astropy.io import fits
import astropy.visualization
import matplotlib.pyplot as plt
import  astropy.time
from mpl_toolkits.axes_grid1 import make_axes_locatable



    
    
def loadconfig(config_file):
    """
    just a wrapper to make the syntax easier to get the config
    """
    config = yaml.load(open(config_file), Loader = yaml.FullLoader)
    return config



def connect_and_query_server(cmd, ipaddr, port,line_ending = '\n', end_char = '', num_chars = 2048, timeout = 0.001, logger = None):
    """
    This is a utility to send a single command to a remote server,
    then wait a response. It tries to return a dictionary from the returned  
    text.
    """
    
    
    # Connect to the server
    sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
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
            msg = f'server query to {ipaddr} Port {port}: {e}'
            if logger is None:
                print(msg)
            else:
                logger.warning(msg)
            
            """
            if len(total_data)>1:
                # check if the end_of_data_was split
                last_pair = total_data[-2]+total_data[-1]
                if end_char in last_pair:
                    total_data[-2] = last_pair[:last_pair.find(end_char)]
                    total_data.pop()
                    break
            """
            # close up shop
            sock.sendall(bytes('BYE\n',"utf-8"))
            sock.close()
            return None
    except Exception as e:
        msg = f'problem with query server, {type(e)}: {e}'
        if logger is None:
                print(msg)
        else:
            logger.warning(msg)
        sock.sendall(bytes('BYE\n',"utf-8"))
        sock.close()
        return None
        
    sock.sendall(bytes('BYE\n',"utf-8"))    
    sock.close()
    reply =  ''.join(total_data)
    try:
        d = json.loads(reply)
    except:
        d = reply
    return d

def query_server(cmd, socket, line_ending = '\n', end_char = '', num_chars = 2048, timeout = 0.001, logger = None, verbose = False):
    """
    This is a utility to send a single command to a remote server,
    then wait a response. It tries to return a dictionary from the returned  
    text.
    """
    
    
   
    
    try:
        # Connect to the server
        sock = socket
        sock.settimeout(timeout)
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
        except Exception as e:
            ipaddr, port = sock.getsockname()
            msg = f'server query to {ipaddr} Port {port}: {e}'
            
            if verbose:
                if logger is None:
                    print(msg)
                else:
                    logger.warning(msg)
                
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
            return None
    except Exception as e:
        msg = f'problem with query server, {type(e)}: {e}'
        if verbose:
            if logger is None:
                    print(msg)
            else:
                logger.warning(msg)

        return None
        
        
    #sock.close()
    reply =  ''.join(total_data)
    try:
        d = json.loads(reply)
    except:
        d = reply
    return d

def create_socket(ipaddr, port, timeout = 0.01, logger = None, verbose = False):
    """
    this takes in a ip address and port, attempts to create a socket connection
    and returns the socket
    """
    
    sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    sock.settimeout(timeout)
    server_address = (ipaddr, port)
    try:
        # attempt to connect to the server
        sock.connect(server_address)
        
        
    except Exception as e:
        if verbose:
            msg = f'problem establishing connection to server, {type(e)}: {e}'
            if logger is None:
                    print(msg)
            else:
                logger.warning(msg)
        sock.close()
        
    return sock


def query_socket(sock, cmd,line_ending = '\n', end_char = '', num_chars = 2048, timeout = 0.001,badchars = None, singlevalue = False):
    """
    This is a utility to send a single command to a remote server,
    then wait a response. It tries to return a dictionary from the returned  
    text.
    """
    
    
    
    
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
        #print(f'server query: {e}')
        pass
        
        """
        if len(total_data)>1:
            # check if the end_of_data_was split
            last_pair = total_data[-2]+total_data[-1]
            if end_char in last_pair:
                total_data[-2] = last_pair[:last_pair.find(end_char)]
                total_data.pop()
                break
        """
    
    reply =  ''.join(total_data)
    
    # splice out any nasty characters from the reply string
    if not badchars is None:
        for char in badchars:
            reply = reply.replace(char,'')
    if singlevalue:
        d = reply
    else:
        try:
            #NPL 3-23-21 switched to yaml which handles bad keys better (ie, keys/values missing quotes)
            #d = json.loads(reply)
            d = yaml.load(reply, Loader = yaml.FullLoader)
        except Exception as e:
            #print(f'could not turn reply into json, {type(e)}: {e}')
            d = reply
    
    #print(f'Reply = {d}')
    return d

def connect_to_server(addr,port, timeout = 1.5, logger = None, verbose = False):
    """
    this creates a socket and does so using the nicely formatted dict from
    the config file.
    
    expects values like this:
        ipaddr = 128.91.1.10
        port = 777
        timeout = 1.5
    """    
    
    
    
    
    # Connect to the server
    if verbose:
        msg = f'attempting to create new socket connection to server at {addr} port {port}'
        if logger is None:
            print(msg)
        else:
            logger.info(msg)
    sock = create_socket(ipaddr = addr, port = port, timeout = timeout, logger = logger)

    return sock


'''
# This is an old version that takes in a config. let's make it more generalizable
# and require the address and port and timeout be passed in directly.
def connect_to_server(config,servername,logger = None, verbose = False):
    """
    this creates a socket and does so using the nicely formatted dict from
    the config file.
    
    expects the config to have a line like this in it:
        servername:
            ipaddr = 128.91.1.10
            port = 777
            timeout = 1.5
    """    
    
    
    ipaddr     = config[servername]['addr']
    port       = config[servername]['port']
    timeout    = config[servername]['timeout']
    
    # Connect to the server
    if verbose:
        msg = f'attempting to create new socket connection to server at {ipaddr} port {port}'
        if logger is None:
            print(msg)
        else:
            logger.info(msg)
    sock = create_socket(ipaddr = ipaddr, port = port, timeout = timeout, logger = logger)

    return sock
'''
"""
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
"""

def plotFITS(filename, printinfo = False, xmin = None, xmax = None, ymin = None, ymax = None, hist = True, min_bin_counts = 1, savefigpath = None):
    plt.close('all')
    
    
    
    
    
    
    image_file = filename
    #plt.ion()
    hdu_list = fits.open(image_file,ignore_missing_end = True)
    if printinfo:
        hdu_list.info()
    
    image_data = hdu_list[0].data
    
    if xmin is None:
        xmin = 0
    if ymin is None:
        ymin = 0
    if xmax is None:
        xmax = np.shape(image_data)[0]
    if ymax is None:
        ymax = np.shape(image_data)[1]
        
    
    header = hdu_list[0].header
    image = image_data[xmin:xmax, ymin:ymax]
    
    filename = header.get("FILENAME", filename.split('/')[-1])
    median_counts = np.median(image)
    stddev = np.std(image)
    
    if "OBSTYPE" in header.keys():
        """
        if header.get("OBSTYPE", "?") in ["BIAS", "DARK", "FLAT"]:
            hist = True
        """
            #hist = False
            #print(f'hist = {hist}')
    
    if hist:
        fig, axarr = plt.subplots(2,1, gridspec_kw = {'height_ratios' : [3,1]}, figsize = (6,8))
        ax0 = axarr[0]
    else:
        fig, axarr = plt.subplots(1,1, figsize = (8,8))
        ax0 = axarr
    
    if "AEXPTIME" in header.keys():
        exptime_str = f'{header["AEXPTIME"]:0.1f}'
    else:
        exptime_str = '?'
    
    
    
    title = f'Last Image Taken: {filename}\nMedian Counts = {median_counts:.0f}, Std Dev = {stddev:.0f}, Exptime = {exptime_str} s'
    title+= f'\nFilter: {header.get("FILTERID","?")}, ObsType = {header.get("OBSTYPE", "?")}'
    title+=f'\nComment: {header.get("QCOMMENT", "?")}'
    if "UTC" in header:
        tstr = header['UTCISO']
        
        
        image_write_time = datetime.fromisoformat(tstr)
        now = datetime.utcnow()
        
        #td = tend - tstart
        td = now-image_write_time
        
        days = td.days
        hours, remainder = divmod(td.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        # If you want to take into account fractions of a second
        seconds += td.microseconds / 1e6
        
        #print(f'elapsed time = {days} days, {hours} hours, {minutes} minutes, {seconds} seconds')
        msg = f'{hours}:{minutes}:{seconds:0.2f}'
        msg =  f'{seconds:0.1f} sec'
        if minutes>0.0:
            msg = f'{minutes} min ' + msg
        if hours>0.0:
            msg = f'{hours} hours ' + msg
        if days>0.0:
            msg = f'{days} days ' + msg
        msg = f'Image taken {msg} ago'
        title = title + f'\n{msg}'
    ax0.set_title(title)#', stddev = {stddev}')
    
    
    #if header.get("OBSTYPE", "?") in ['BIAS', 'DARK']:
    #    hist = True
    
    
    #norm = astropy.visualization.simple_norm(image, 'sqrt')
    
    norm = astropy.visualization.ImageNormalize(image, 
                                             interval = astropy.visualization.ZScaleInterval(),
                                             stretch = astropy.visualization.SqrtStretch())
    
    
    im = ax0.imshow(image, cmap = 'gray', origin = 'lower', norm = norm)
    ax0.set_xlabel('X [pixels]')
    ax0.set_ylabel('Y [pixels]')
    
    # set up the colorbar. this is a pain in this format...
    # source: https://stackoverflow.com/questions/32462881/add-colorbar-to-existing-axis
    divider = make_axes_locatable(ax0)
    cax = divider.append_axes('right', size = '5%', pad = 0.05)
    fig.colorbar(im, cax = cax, orientation = 'vertical')
    
    
    
    # PLOT THE HISTOGRAM
    if hist:
        # Plot a histogram, do this iteratively to figure out good limits and binning
        # first flatten the data to 1d
        vec = np.ravel(image)
        
        # now make an initial histogram. use the full range
        lowerlim0 = 0
        upperlim0 = 2**16
        bins0 = np.linspace(lowerlim0, upperlim0, 1000)
        #n, bins, patches = axarr[1].hist(vec, bins = bins0)
        
        n0, bins0 = np.histogram(vec, bins = bins0)
        
        
        bin_left_edges0 = bins0[0:-1]
        
        # now remake the histogram to only make bins that have some minimum number of counts
        
        threshold = min_bin_counts
        full_bins = bin_left_edges0[n0>threshold]
        
        lowerlim = np.min(full_bins)
        upperlim = np.max(full_bins)
        
        # use arange for the bins since we only expect integer counts
        
        bins = np.arange(lowerlim, upperlim, 1)
        n, bins, patches = axarr[1].hist(vec, bins = bins, color = 'black')
        
        axarr[1].set_xlabel('Counts')
        axarr[1].set_ylabel('Nbins')
    
        axarr[1].set_yscale('log')
    
    if not (savefigpath is None):
        #plt.savefig(os.path.join(os.getenv("HOME"),'data','last_image.jpg'))
        plt.savefig(savefigpath)
    #plt.show()#block = False)
    #plt.pause(0.1)
    
    
    return header, image_data

def getFromFITSHeader(filename, keyword):
    try:
        image_file = filename
        #plt.ion()
        hdu_list = fits.open(image_file,ignore_missing_end = True)
        hdu_list.info()
        
        header = hdu_list[0].header
        value = header[keyword]
    except Exception as e:
        value = None
        print(f'could not get keyword {keyword} from file {filename} due to {type(e)}: {e}')
    return value

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

def MJD_to_Datetime(MJD, timezone = 'America/Los_Angeles'):
    
    t_obj = astropy.time.Time(MJD, format = 'mjd')
    t_datetime_obj = t_obj.datetime
    t_datetime_obj_utc = pytz.utc.localize(t_datetime_obj)
    t_datetime_obj_local = t_datetime_obj_utc.astimezone(pytz.timezone(timezone))    

    return t_datetime_obj_local


    
def getImages(starttime, endtime, camera = 'SUMMER', fullpath = True):
    """
    Returns a list of image filenames that were taken between starttime and endtime
    
    times can be either a datetime object,
    or a string in the following format: YYYYMMDD_HHMMSS,
    or a time in MJD
    """
    timezone = pytz.timezone('America/Los_Angeles')
    if type(starttime) is str:
        datetime_start = datetime.strptime(starttime, '%Y%m%d_%H%M%S')
        datetime_start = timezone.localize(datetime_start)
    elif type(starttime) is datetime:
        datetime_start = starttime
        if datetime_start.tzinfo is None:
            print(f'ASSUMING INPUT DATETIME IS TIMEZONE: {timezone}')
            datetime_start = timezone.localize(datetime_start)
            
    elif type(starttime) is float:
        datetime_start = MJD_to_Datetime(starttime)
    else:
        raise TypeError('starttime must be either a datetime object, string in YYYMMDD_HHMMSS, or MJD')
    
    if type(endtime) is str:
        datetime_end = datetime.strptime(endtime, '%Y%m%d_%H%M%S')
        datetime_end = timezone.localize(datetime_end)
    elif type(endtime) is datetime:
        datetime_end = endtime
        if datetime_end.tzinfo is None:
            print(f'ASSUMING INPUT DATETIME IS TIMEZONE: {timezone}')
            datetime_end = timezone.localize(datetime_end)
    elif type(endtime) is float:
        datetime_end = MJD_to_Datetime(endtime)
    else:
        raise TypeError('endtime must be either a datetime object, string in YYYMMDD_HHMMSS, or MJD')
        
    
    night = tonight_local(datetime_start.timestamp())
    #print(f'night = {night}')
    impath = os.path.join(os.getenv("HOME"),'data','images',night)
    filelist = glob.glob(os.path.join(impath, '*.fits'))
    imglist = []
    for file in filelist:
        if camera.lower() == 'summer':
            timestr = file.split('SUMMER_')[1].split('_Camera0.fits')[0]
            datetime_file = datetime.strptime(timestr, '%Y%m%d_%H%M%S')
            datetime_file = timezone.localize(datetime_file)
            if (datetime_file <= datetime_end) & (datetime_file >= datetime_start):
                if fullpath:
                    imglist.append(file)
                else:
                    imglist.append(os.path.basename(file))
        else:
            raise TypeError('getImages can only search for SUMMER images, other cameras not implemented')
    
    # sort the list (not sure why it doesn't automatically)
    imglist = sorted(imglist)
    return imglist

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


def tonight_local(timestamp = 'now', tz = 'America/Los_Angeles'):
    # a similar version of the minerva function by NPL
    # NPL: 4/27/21 changing the conventions. 
    # Want the night of a given day to be defined from 8a that day, to 7:59 the next day LOCAL TIME so it's easy to keep track of.
    # All the images will be stored with UTC dates, so this is just for labeling logs and telemetry data. THis way it's in a sensible format
    
    tz = pytz.timezone(tz)

    if timestamp == 'now':
        # Get the current LOCAL time in California
        now_cali = datetime.now(tz)
    
    else:
        now_cali = tz.localize(datetime.fromtimestamp(timestamp))
    
    # if the local time is between midnight and 8am (ie, >=0 and <8) then subtract off a day
    if now_cali.hour >= 0 and now_cali.hour < 8:
        now_cali = now_cali - timedelta(days=1)
        
    tonight_string = now_cali.strftime('%Y%m%d') 
    return tonight_string   

def tonight():
    # this uses UT time to match ZTF etc
    utcnow = datetime.utcnow()
    tonight_string = utcnow.strftime('%Y%m%d') 
    return tonight_string   
    
    
"""
def night():
    # DEPRECATED. This if from Minerva
    # was called night in minerva, but tonight is a little more transparent
    today = datetime.utcnow()
    # if the UTC time is between 10a and 4p, ie cali time between 2a and 8a
    if datetime.now().hour >= 10 and datetime.now().hour <= 16:
        today = today + timedelta(days=1)
    return today.strftime('%Y%m%d')    
"""



def getLastModifiedFile(directory, name = '*'):
    """
    
    Gets the last modified file in the directory.
    
    If there are multiple with the same modification date, then get the first from the list
    
    directory is a complete filepath
    
    name: search specifier for file. '*' is anything, but can also do things like "*.txt"
    
    return the filepath of the last modified file

    """
    
    files = np.array(glob.glob(os.path.join(directory, name)))
    
    modtimes = np.array([os.stat(file).st_mtime for file in files])
    
    # get the most recent file(s)
    latest = files[modtimes == np.max(modtimes)]
    
    # return the first element of the latest array
    latest_filepath = latest[0]
    
    return latest_filepath





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



if __name__ == '__main__' :
    """
    plt.figure()
    while True:
        i = 0
        print(f'taking image {i}')
        time.sleep(2)    
        #plt.plot([1,2,3])
        plotFITS('/home/winter/WINTER_GIT/code/wsp/data/' + 'testimage.FITS')
        i += 1
    #plt.show()
    """
    sock = connect_to_server('198.202.125.142', 62000,timeout = 0.1)   

    d = query_server('status?', 
                         socket = sock, 
                         end_char = '}',
                         timeout = 1)
    print(d)

