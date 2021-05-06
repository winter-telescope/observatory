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


filePath = 'test.txt'



print('starting write loop')
i = 0
while True:
    try:
        file = open(filePath, "a")  # append mode
        now_timestamp = datetime.now().timestamp()
        file.write(f"{i}\t{now_timestamp}\n")
        file.flush()
        file.close()
        time.sleep(0.5)
        i+=1
    except KeyboardInterrupt:
        print('closing file.')
        file.close()
        break
    
print('done.')



