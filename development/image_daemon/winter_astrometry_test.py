#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed May 28 07:05:52 2025

@author: winter
"""

import os
import Pyro5.api
import json

image_dir = "/data/images/astrometry_test"
data = {"field_1": ["WINTERcamera_20250525-110538-583_mef.fits",
                               "WINTERcamera_20250525-110616-163_mef.fits",
                               "WINTERcamera_20250525-110654-352_mef.fits",
                               "WINTERcamera_20250525-110731-447_mef.fits",
                   ],
                   "field_2": ["WINTERcamera_20250525-115612-586_mef.fits",
                               "WINTERcamera_20250525-115649-052_mef.fits",
                               "WINTERcamera_20250525-115724-569_mef.fits",
                               "WINTERcamera_20250525-115801-540_mef.fits"],
                   }



for field in data:
    image_filenames = data[field]
    

    images = [os.path.join(image_dir, field, filename) for filename in image_filenames]

    #print(images)
    
    # load the image daemon
    
    
    ns = Pyro5.api.locate_ns(host="192.168.1.10")
    
    daemon = Pyro5.api.Proxy(ns.lookup("winter_daemon"))
    
    science_image = images[-1]
    addr = "pb"
    astrom_info = daemon.solve_astrometry(
        addr=addr,
        science_image=science_image,
        background_image_list=images,
        output_dir="/home/winter/data/tmp/",
        pix_coords=(1864, 530),
        timeout=10,
    )
    
    print(
        f"Field {field.split('_')[-1]}: Astrometric solution: {json.dumps(astrom_info, indent = 2)}"
    )