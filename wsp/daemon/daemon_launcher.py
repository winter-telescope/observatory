#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Feb  9 10:58:35 2021

daemon_launcher.py

This is part of WSP

### PURPOSE ###
This is a script to launch the various daemons that WSP requires


@author: winter
"""

import os
import sys
import signal
import ctypes
import subprocess
import platform

# add the wsp directory to the PATH
wsp_path = os.path.dirname(__file__)
sys.path.insert(1, wsp_path)

#if __name__ == '__main__':
    


libc = ctypes.cdll.LoadLibrary("libc.{}".format("so.6" if platform.uname()[0] != "Darwin" else "dylib"))


def set_pdeathsig(sig = signal.SIGKILL):
    def callable():
        return libc.prctl(1, sig)
    return callable

#args = ["python","-m","Pyro5.nsc"]
args = ["pyro5-ns"]

#p = subprocess.Popen(args, preexec_fn = set_pdeathsig(signal.SIGKILL),shell = True)
p = subprocess.Popen(args,shell = True)

while True:
    pass