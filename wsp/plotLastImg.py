#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jul 20 15:37:23 2021

@author: winter
"""


import getopt
import os
import pathlib
import sys
import time
from datetime import datetime
from pathlib import Path

import astropy.time
import astropy.visualization
import matplotlib.pyplot as plt
import numpy as np
import yaml
from astropy.io import fits
from mpl_toolkits.axes_grid1 import make_axes_locatable

wsp_path = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(1, wsp_path)
print(f"wsp_path = {wsp_path}")

from alerts import alert_handler

auth_config_file = wsp_path + "/credentials/authentication.yaml"
user_config_file = wsp_path + "/credentials/alert_list.yaml"
alert_config_file = wsp_path + "/config/alert_config.yaml"

auth_config = yaml.load(open(auth_config_file), Loader=yaml.FullLoader)
user_config = yaml.load(open(user_config_file), Loader=yaml.FullLoader)
alert_config = yaml.load(open(alert_config_file), Loader=yaml.FullLoader)

alertHandler = alert_handler.AlertHandler(user_config, alert_config, auth_config)


def plotFITS(
    filename,
    printinfo=False,
    xmin=None,
    xmax=None,
    ymin=None,
    ymax=None,
    hist=True,
    min_bin_counts=1,
):
    plt.close("all")

    image_file = filename
    # plt.ion()
    hdu_list = fits.open(image_file, ignore_missing_end=True)
    if printinfo:
        hdu_list.info()

    image_data = hdu_list[0].data

    if xmin is None:
        xmin = 0
    if ymin is None:
        ymin = 0
    if xmax is None:
        xmax = np.shape(data)[0]
    if ymax is None:
        ymax = np.shape(data)[1]

    header = hdu_list[0].header
    image = image_data[xmin:xmax, ymin:ymax]

    filename = header.get("FILENAME", filename.split("/")[-1])
    median_counts = np.median(image)
    stddev = np.std(image)

    if "OBSTYPE" in header.keys():
        """
        if header.get("OBSTYPE", "?") in ["BIAS", "DARK", "FLAT"]:
            hist = True
        """
        # hist = False
        # print(f'hist = {hist}')

    if hist:
        fig, axarr = plt.subplots(
            2, 1, gridspec_kw={"height_ratios": [3, 1]}, figsize=(6, 8)
        )
        ax0 = axarr[0]
    else:
        fig, axarr = plt.subplots(1, 1, figsize=(8, 8))
        ax0 = axarr

    if "AEXPTIME" in header.keys():
        exptime_str = f'{header["AEXPTIME"]:0.1f}'
    elif "EXPTIME" in header.keys():
        exptime_str = f'{header["EXPTIME"]:0.1f}'
    else:
        exptime_str = "?"

    title = f"Last Image Taken: {filename}\nMedian Counts = {median_counts:.0f}, Std Dev = {stddev:.0f}, Exptime = {exptime_str} s"
    title += f'\nFilter: {header.get("FILTERID","?")}, OBSTYPE = {header.get("OBSTYPE", "?").upper()}'
    title += f'\nComment: {header.get("QCOMMENT", "?")}'
    if "UTC" in header:
        tstr = header["UTCISO"]

        image_write_time = datetime.fromisoformat(tstr)
        now = datetime.utcnow()

        # td = tend - tstart
        td = now - image_write_time

        days = td.days
        hours, remainder = divmod(td.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        # If you want to take into account fractions of a second
        seconds += td.microseconds / 1e6

        # print(f'elapsed time = {days} days, {hours} hours, {minutes} minutes, {seconds} seconds')
        msg = f"{hours}:{minutes}:{seconds:0.2f}"
        msg = f"{seconds:0.1f} sec"
        if minutes > 0.0:
            msg = f"{minutes} min " + msg
        if hours > 0.0:
            msg = f"{hours} hours " + msg
        if days > 0.0:
            msg = f"{days} days " + msg
        msg = f"Image taken {msg} ago"
        title = title + f"\n{msg}"
    ax0.set_title(title)  #', stddev = {stddev}')

    # if header.get("OBSTYPE", "?") in ['BIAS', 'DARK']:
    #    hist = True

    # norm = astropy.visualization.simple_norm(image, 'sqrt')

    norm = astropy.visualization.ImageNormalize(
        image,
        interval=astropy.visualization.ZScaleInterval(),
        stretch=astropy.visualization.SqrtStretch(),
    )

    im = ax0.imshow(image, cmap="gray", origin="lower", norm=norm)
    ax0.set_xlabel("X [pixels]")
    ax0.set_ylabel("Y [pixels]")

    # set up the colorbar. this is a pain in this format...
    # source: https://stackoverflow.com/questions/32462881/add-colorbar-to-existing-axis
    divider = make_axes_locatable(ax0)
    cax = divider.append_axes("right", size="5%", pad=0.05)
    fig.colorbar(im, cax=cax, orientation="vertical")

    # PLOT THE HISTOGRAM
    if hist:
        # Plot a histogram, do this iteratively to figure out good limits and binning
        # first flatten the data to 1d
        vec = np.ravel(image)

        # now make an initial histogram. use the full range
        lowerlim0 = 0
        upperlim0 = 2**16
        bins0 = np.linspace(lowerlim0, upperlim0, 1000)
        # n, bins, patches = axarr[1].hist(vec, bins = bins0)

        n0, bins0 = np.histogram(vec, bins=bins0)

        bin_left_edges0 = bins0[0:-1]

        # now remake the histogram to only make bins that have some minimum number of counts

        threshold = min_bin_counts
        full_bins = bin_left_edges0[n0 > threshold]

        lowerlim = np.min(full_bins)
        upperlim = np.max(full_bins)

        # use arange for the bins since we only expect integer counts

        bins = np.arange(lowerlim, upperlim, 1)
        n, bins, patches = axarr[1].hist(vec, bins=bins, color="black")

        axarr[1].set_xlabel("Counts")
        axarr[1].set_ylabel("Nbins")

        axarr[1].set_yscale("log")

    plt.savefig(os.path.join(os.getenv("HOME"), "data", "last_image.jpg"))

    # plt.show()#block = False)
    # plt.pause(0.1)

    return header, image_data


"""
npix_x = 1920
npix_y = 1080
data = np.random.random((npix_x,npix_y))
data = np.transpose(data)
hdu = fits.PrimaryHDU(data = data)
"""

argv = sys.argv[1:]
print(f"argv = {argv}")

# optlist

if ("-h" in argv) or ("-hist" in argv):
    do_hist = True

else:
    do_hist = False

post_to_slack = True

# name = '/home/winter/data/viscam/test_images/20210503_171349_Camera00.fits'
# name = os.path.join(os.getenv("HOME"), 'data','images','20210730','SUMMER_20210730_043149_Camera0.fits')
# %%
# Try multiple possible locations for the last image
last_image_path = None

# Option 1: Try reading the symlink at last_image.fits
try:
    symlink_path = os.path.join(os.path.expanduser("~"), "data", "last_image.fits")
    if os.path.islink(symlink_path):
        # Read where the symlink points
        target = os.readlink(symlink_path)
        # Resolve it to absolute path in case it's relative
        last_image_path = str(Path(target).resolve())
        print(f"Found symlink pointing to: {last_image_path}")
    elif os.path.exists(symlink_path):
        # It's a regular file, not a symlink
        last_image_path = symlink_path
        print(f"Found direct file: {last_image_path}")
except Exception as e:
    print(f"Could not read symlink: {e}")

# Option 2: If symlink didn't work, try the direct path
if last_image_path is None or not os.path.exists(last_image_path):
    fallback_path = os.path.join(os.path.expanduser("~"), "data", "last_image.fits")
    if os.path.exists(fallback_path):
        last_image_path = fallback_path
        print(f"Using fallback path: {last_image_path}")

# Option 3: If still nothing, bail
if last_image_path is None or not os.path.exists(last_image_path):
    print("ERROR: Could not find last image file")
    exit(1)

# Now use last_image_path for plotting
print(f"Using image: {last_image_path}")
# hdu.writeto(name,overwrite = True)

# check if file exists
# check if file exists
imgpath = Path(last_image_path)
timeout = 20
dt = 0.5
t_elapsed = 0
while t_elapsed < timeout:

    file_exists = imgpath.is_file()
    if file_exists:
        break
    else:
        time.sleep(dt)
        t_elapsed += dt
# %%

header, data = plotFITS(
    last_image_path, xmax=2048, ymax=2048, hist=do_hist, min_bin_counts=10
)

# reading some stuff from the header.
## the header is an astropy.io.fits.header.Header object, but it can be queried like a dict
try:
    print(f'FILENAME = {header["FILENAME"]}')
    print(f'RA = {header["RA"]}')
    print(f'DEC  = {header["DEC"]}')
except:
    pass
# %% Post to slack !

if post_to_slack:
    lastimagejpg = os.path.join(os.path.expanduser("~"), "data", "last_image.jpg")
    alertHandler.slack_postImage(lastimagejpg)
