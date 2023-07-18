#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jul 18 13:46:37 2023

@author: winter
"""

import Pyro5.core
import Pyro5.client

ns_host = '192.168.1.10'
ns = Pyro5.core.locate_ns(host = ns_host)
uri = ns.lookup('WINTERimage')
image_daemon = Pyro5.client.Proxy(uri)


images = ['/home/winter/data/images/20230717/WINTERcamera_20230718-110046-624_mef.fits', 
          '/home/winter/data/images/20230717/WINTERcamera_20230718-110126-451_mef.fits', 
          '/home/winter/data/images/20230717/WINTERcamera_20230718-110205-759_mef.fits', 
          '/home/winter/data/images/20230717/WINTERcamera_20230718-110245-518_mef.fits', 
          '/home/winter/data/images/20230717/WINTERcamera_20230718-110325-400_mef.fits', 
          '/home/winter/data/images/20230717/WINTERcamera_20230718-110405-055_mef.fits', 
          '/home/winter/data/images/20230717/WINTERcamera_20230718-110444-586_mef.fits', 
          '/home/winter/data/images/20230717/WINTERcamera_20230718-110524-617_mef.fits', 
          #'/home/winter/data/images/20230717/WINTERcamera_20230718-110604-693_mef.fits', 
          #'/home/winter/data/images/20230717/WINTERcamera_20230718-110643-674_mef.fits', 
          #'/home/winter/data/images/20230717/WINTERcamera_20230718-110723-562_mef.fits', 
          #'/home/winter/data/images/20230717/WINTERcamera_20230718-110802-713_mef.fits',
          ]

focus = image_daemon.get_focus_from_imgpathlist(images)
#focus = image_daemon.get_focus_in_dir('/home/winter/data/images/20230717/')
print(f'Focus Ran! Focus = {focus}')