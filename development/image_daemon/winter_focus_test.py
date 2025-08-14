#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed May 28 07:35:09 2025

@author: winter
"""
import os
import Pyro5.api
import json
ns = Pyro5.api.locate_ns(host="192.168.1.10")

image_daemon = Pyro5.api.Proxy(ns.lookup("winter_daemon"))

images_dir = "/data/images/focus_test"

image_filenames = ["WINTERcamera_20250528-120732-059_mef.fits",
                   "WINTERcamera_20250528-120812-201_mef.fits",
                   "WINTERcamera_20250528-120851-615_mef.fits",
                   "WINTERcamera_20250528-120931-564_mef.fits",
                   "WINTERcamera_20250528-121010-638_mef.fits",
                   "WINTERcamera_20250528-121050-172_mef.fits",
                   ]

images = [os.path.join(images_dir, filename) for filename in image_filenames]

results = image_daemon.run_focus_loop(image_list = images,
                                   addrs = ["pc"],
                                   output_dir = "/home/winter/data/tmp",
                                   post_results_to_slack=True,
                                   )
print(f"Focus loop results: {json.dumps(results, indent=2)}")
#print(f"Ran the focus script on Freya and got best focus = {x0_fit:.1f}")