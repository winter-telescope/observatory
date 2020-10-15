#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Oct 15 09:33:50 2020


converting MJD to datetime with astropy

@author: nlourie
"""

import astropy.time
from datetime import datetime

t = '59215.0762617701'

t_obj = astropy.time.Time(t,format = 'mjd')

t_datetime_obj = t_obj.datetime

print(f'The MJD is: {t}')
print(f'The Human Readable Time is: {t_datetime_obj.strftime("%Y-%m-%d: %H:%M:%S")}')