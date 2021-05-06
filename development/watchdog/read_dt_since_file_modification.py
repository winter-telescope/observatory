#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue May  4 09:13:52 2021

@author: nlourie
"""

import os
import time
from datetime import datetime
import numpy as np

filePath = os.getenv("HOME") + '/data/dm.lnk/count'
#filePath = 'test.txt'

# Append-adds at last
file = open(filePath, "a")  # append mode

print('starting write loop')
i = 0
while True:
    try:
        now_timestamp = datetime.now().timestamp()
        file.write(f"{i}\t{now_timestamp}\n")
        file.flush()
        time.sleep(0.5)
        i+=1
    except KeyboardInterrupt:
        print('closing file.')
        file.close()
        break
    
print('done.')



