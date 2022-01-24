#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jan 24 15:23:17 2022

@author: nlourie
"""

import os
import numpy as np
import struct
from datetime import datetime


DTYPE_DICT = dict({'FLOAT64' : 'd',
                   'INT64' : 'q',
                   'UINT16' : 'H'})

NCOL = 1920
NROW = 1080


file = os.path.join(os.getenv("HOME"),'data','streamTest','stream.dat')

frame = np.zeros((NCOL, NROW)).astype(DTYPE_DICT['UINT16'])

#framelen = int(NCOL*NROW*2)
#framebuf = bytearray(framelen)

fp = open(file, mode = 'wb')

#fp.write(struct.pack(DTYPE_DICT['UINT16'], frame))

#fp.write(framebuf)

data = frame.flatten().tobytes()

starttime = datetime.utcnow().timestamp()
fp.write(data)
fp.flush()

endtime = datetime.utcnow().timestamp()


fp.close()


dt_ms = (endtime - starttime)*1.0e3

print(f'Time to Save {NCOL}x{NROW} frame = {dt_ms:.1f} ms')