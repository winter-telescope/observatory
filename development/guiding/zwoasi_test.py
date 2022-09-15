#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Sep 13 11:03:04 2022

@author: winter
"""
import os
import json
import numpy as np
from datetime import datetime
import matplotlib.pyplot as plt
import zwoasi as asi



sopath = os.path.join(os.getenv("HOME"), 'Documents', 'ASI_linux_mac_SDK_V1.26',
                      'lib','x64','libASICamera2.so')

asi.init(sopath)

num_cameras = asi.get_num_cameras()

print(f'number of detected cameras: {num_cameras}')

if num_cameras == 0:
    raise ValueError('No cameras found')

cameras_found = asi.list_cameras()
print(f'cameras found: {cameras_found}')
print()
print('Info for detected cameras:')
for camera_id in range(num_cameras):
    print(f'CameraID {camera_id}')
    camera = asi.Camera(camera_id)
    camera_info = camera.get_camera_property()
    print(json.dumps(camera_info, indent = 2))
    print()
    
camera_id = 0  # use first camera from list

# Get all of the camera controls
print('')
"""
print('Camera controls:')
controls = camera.get_controls()
for cn in sorted(controls.keys()):
    print('    %s:' % cn)
    for k in sorted(controls[cn].keys()):
        print('        %s: %s' % (k, repr(controls[cn][k])))

"""
# Use minimum USB bandwidth permitted
#camera.set_control_value(asi.ASI_BANDWIDTHOVERLOAD, camera.get_controls()['BandWidth']['MinValue'])

# Set some sensible defaults. They will need adjusting depending upon
# the sensitivity, lens and lighting conditions used.
camera.disable_dark_subtract()
gain_dict = {"High" : 390, "Middle" : 120, "Low" : 0}
bit_dict = {8 : asi.ASI_IMG_RAW8, 16 : asi.ASI_IMG_RAW16}

camera.set_control_value(asi.ASI_GAIN, gain_dict["High"])
exptime = 30
bits = 8
camera.set_control_value(asi.ASI_EXPOSURE, int(exptime*1e6)) # microseconds
#camera.set_control_value(asi.ASI_WB_B, 99)
#camera.set_control_value(asi.ASI_WB_R, 75)
#camera.set_control_value(asi.ASI_GAMMA, 50)
#camera.set_control_value(asi.ASI_BRIGHTNESS, 50)
#camera.set_control_value(asi.ASI_FLIP, 0)

print('Enabling stills mode')
try:
    # Force any single exposure to be halted
    camera.stop_video_capture()
    camera.stop_exposure()
except (KeyboardInterrupt, SystemExit):
    raise


binmode = 2
camera.set_roi(bins = binmode)

print(f'Capturing a single capture mode {bits}-bit mono image')
filename = 'image_mono16.fits'
starttime = datetime.now().timestamp()
camera.set_image_type(bit_dict[bits])
imdata = camera.capture()
endtime = datetime.now().timestamp()
dt = endtime-starttime
print(f'Total Exposure Took {dt:.2f}s')
print(f'Overhead = {dt-exptime:.2f}s')
#%%
print('plotting data')

#%%
fig, axes = plt.subplots(1,2,figsize = (10,5))
fig.suptitle(f'Exposure Mode Image, Bin{binmode} Mode, {bits}-bit Image, Overhead = {dt-exptime:.2f}s')
axes[0].imshow(imdata)
axes[0].set_title(f'Image Size: {np.shape(imdata)[0]} x {np.shape(imdata)[1]}')
axes[1].hist(np.ravel(imdata), log = True, bins = 500)
#print('Saved to %s' % filename)
#%%



try:
    # Force any single exposure to be halted
    camera.stop_exposure()
except (KeyboardInterrupt, SystemExit):
    raise

print('Enabling video mode')
camera.start_video_capture()

# Set the timeout, units are ms
timeout = (camera.get_control_value(asi.ASI_EXPOSURE)[0] / 1000) * 2 + 500
camera.default_timeout = timeout


print(f'Capturing a video mode single {bits}-bit mono image')
camera.set_image_type(bit_dict[bits])
starttime = datetime.now().timestamp()

viddata = camera.capture_video_frame()

endtime = datetime.now().timestamp()
dt = endtime-starttime
print(f'Total Exposure Took {dt:.2f}s')
print(f'Overhead = {dt-exptime:.2f}s')

fig, axes = plt.subplots(1,2,figsize = (10,5))
fig.suptitle(f'Video Mode Image, Bin{binmode} Mode, {bits}-bit Image, Overhead = {dt-exptime:.2f}s')
axes[0].imshow(viddata)
axes[0].set_title(f'Image Size: {np.shape(imdata)[0]} x {np.shape(imdata)[1]}')
axes[1].hist(np.ravel(viddata), log = True, bins = 500)
#print('Saved to %s' % filename)