#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Mar 10 15:36:19 2020

This is a pthread test script:
    qt5_pthread_reddit_test.py

@author: nlourie
"""

import urllib.request
import urllib.parse
import json
import time
import numpy as np
from PyQt5.QtCore import QThread, QObject,pyqtSignal
from PyQt5.QtWidgets import QApplication, QWidget

