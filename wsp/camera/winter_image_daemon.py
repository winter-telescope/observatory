#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jul 17 11:12:45 2023

@author: nlourie
"""

import subprocess
import Pyro5.core
import Pyro5.server
import pathlib
import os
from PyQt5 import QtCore
#from astropy.io import fits
import sys
import signal
import getopt
import threading
from datetime import datetime

# add the wsp directory to the PATH
wsp_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(1, wsp_path)
print(f'wsp_path = {wsp_path}')


from housekeeping import data_handler
from daemon import daemon_utils


class ImageHandler(QtCore.QObject):

    def __init__ (self):
        super(ImageHandler, self).__init__()
        # Path to the winterutils conda environment
        self.python_path = "/home/winter/anaconda3/envs/winterutils/bin/python"
        # Path to the focusloop_winter.py script
        self.code_path = "/home/winter/GIT/winter_utils/winter_utils/focusloop_winter.py"
        
        # init the state dictionary
        self.state = dict()
        
        # init the connection to the nameserver
        
        # Qtimer to handle making sure it's connected to the nameserver
        self.pollTimer = QtCore.QTimer()
        self.pollTimer.setSingleShot(False)
        self.pollTimer.timeout.connect(self.update_state)
        self.pollTimer.start(1000)
    
    def update_state(self):
        # update some useful entries in the state dictionary and make sure
        # that this is connected to the nameserver
        self.state.update({'timestamp' : datetime.utcnow().timestamp()})
        
        
    
    def get_focus_in_dir(self, directory: str) -> float:
        """
        This script is an example wrapper function for using winter_utils to
        get the focus. It only takes a directory as an argument, and returns the focus

        Parameters
        ----------
        directory: directory containing the focus images.
        Can be a directory with all raw images,
        because winter_utils will choose the correct focus images.

        Returns
        -------
        focus: float
        """
        # IF YOU DON'T RUN IT IN SILENT MODE IT CAN'T PICK OUT THE FOCUS FROM THE REST OF THE OUTPUT
        cmd = f"{self.python_path} {self.code_path} {directory} "#--silent"

        res = subprocess.run(
            [cmd], capture_output=True, shell=True,
            executable="/bin/bash",
        )
        focus = res.stdout.decode().strip()
        print(focus)
        #focus = float(focus.split('Best focus:')[1])
        #focus = float(res.stdout.decode().strip())
        return focus#float(res.stdout.decode().strip())
    
    def make_dir_with_symlinks_from_imgpathlist(self, dirpath, imgpathlist):
        """
        make a directory with specified dirpath name which is just full of
        symbolic links to other images. This can then be analyzed with the
        focusloop_winter.py script
        """
        # first make the directory
        # create the data link directory if it doesn't exist already
        pathlib.Path(dirpath).mkdir(parents = True, exist_ok = True)
        print(f'focuserd: making directory: {dirpath}')
        
        # now make the symbolic links
        for imgpath in imgpathlist:
            
            imgname = os.path.basename(imgpath)
            
            linkpath = os.path.join(dirpath, imgname)
            
            try:
                os.symlink(imgpath, linkpath)
            except FileExistsError:
                print('imagedaemon: deleting existing symbolic link')
                os.remove(linkpath)
                os.symlink(imgpath, linkpath)
        
        return
    
    @Pyro5.server.expose
    def get_focus_from_imgpathlist(self, imgpathlist, dirpath = None):
        print(f'running focus analysis of these images: {imgpathlist}')

        if dirpath is None:
            # if not specified, the directory will be a new one timestamped in
            # the same directory as the first item from the imagpathlist
            #timestr = datetime.now().strftime('%Y%m%d_%H%M%S')
            timestr = os.path.basename(imgpathlist[0]).split('WINTERcamera_')[1].strip('_mef.fits')
            dirname = f'focusLoop_{timestr}'
            dirpath = os.path.join(os.path.dirname(imgpathlist[0]), dirname)
        
        # first make the directory of symlinks
        self.make_dir_with_symlinks_from_imgpathlist(dirpath, imgpathlist)
        
        print(f'analyzing focus images in this directory of symbolic links: {dirpath}')

        # now run the focus script on the directory
        best_focus = self.get_focus_in_dir(dirpath)
        
        print(f'found best focus to be: {best_focus} um')
        return best_focus




        
        
        




        
class PyroGUI(QtCore.QObject):   

                  
    def __init__(self, ns_host, parent=None ):            
        super(PyroGUI, self).__init__(parent)   
        print(f'main: running in thread {threading.get_ident()}')
        
        self.imageHandler = ImageHandler()
                
        self.pyro_thread = daemon_utils.PyroDaemon(obj = self.imageHandler, name = 'WINTERimage', ns_host = ns_host)
        self.pyro_thread.start()
        
        


            
        
def sigint_handler( *args):
    """Handler for the SIGINT signal."""
    sys.stderr.write('\r')
    
    
    QtCore.QCoreApplication.quit()

if __name__ == "__main__":
    
    ##### GET ANY COMMAND LINE ARGUMENTS #####
    
    args = sys.argv[1:]
    print(f'args = {args}')
    
    # set the defaults
    verbose = False
    doLogging = True
    ns_host = '192.168.1.10'
    
    options = "vpn:"
    long_options = ["verbose", "print", "ns_host:"]
    arguments, values = getopt.getopt(args, options, long_options)
    # checking each argument
    print()
    print(f'Parsing sys.argv...')
    print(f'arguments = {arguments}')
    print(f'values = {values}')
    for currentArgument, currentValue in arguments:
        if currentArgument in ("-v", "--verbose"):
            verbose = True
            print("Running in VERBOSE mode")
        
        elif currentArgument in ("-p", "--print"):
            doLogging = False
            print("Running in PRINT mode (instead of log mode).")
        elif currentArgument in ("-n", "--ns_host"):
            ns_host = currentValue
    
    ##### RUN THE APP #####
    app = QtCore.QCoreApplication(sys.argv)
    
    
    main = PyroGUI(ns_host = ns_host)

    
    signal.signal(signal.SIGINT, sigint_handler)

    # Run the interpreter every so often to catch SIGINT
    timer = QtCore.QTimer()
    timer.start(500) 
    timer.timeout.connect(lambda: None) 

    sys.exit(app.exec_())









