#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jul 17 11:12:45 2023

@author: nlourie
"""

#import subprocess
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
import yaml

from winter_utils import focusloop_winter as foc
from winter_utils.paths import astrom_sex, astrom_param, astrom_filter, astrom_nnw, MASK_DIR, MASTERDARK_DIR, MASTERFLAT_DIR, DEFAULT_OUTPUT_DIR
#from winter_utils.io import get_focus_images_in_directory
#from winter_utils import quick_combine_images


# add the wsp directory to the PATH
wsp_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(1, wsp_path)
print(f'wsp_path = {wsp_path}')


#from housekeeping import data_handler
from daemon import daemon_utils
from alerts import alert_handler


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
        
    def post_results_to_slack(self, results_plot_filepath = None):
        try:        
            #focus_plot = '/home/winter/data/plots_focuser/latest_focusloop.jpg'
            if results_plot_filepath is None:
                #results_plot_filepath = '/home/winter/winterutils_output/focusloop_all_detectors.png'
                results_plot_filepath = '/home/winter/winterutils_output/focusloop.png'

            
            auth_config_file  = wsp_path + '/credentials/authentication.yaml'
            user_config_file = wsp_path + '/credentials/alert_list.yaml'
            alert_config_file = wsp_path + '/config/alert_config.yaml'

            auth_config  = yaml.load(open(auth_config_file) , Loader = yaml.FullLoader)
            user_config = yaml.load(open(user_config_file), Loader = yaml.FullLoader)
            alert_config = yaml.load(open(alert_config_file), Loader = yaml.FullLoader)

            alertHandler = alert_handler.AlertHandler(user_config, alert_config, auth_config)
        
            alertHandler.slack_postImage(results_plot_filepath)
            
            
            
        
        except Exception as e:
            msg = f'image_daemon: Unable to post focus graph to slack due to {e.__class__.__name__}, {e}'
            self.log(msg)
            
    @Pyro5.server.expose
    def get_focus_in_dir(self, directory: str,
                         board_ids_to_use = None,
                         plot_all = False) -> float:
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
        if board_ids_to_use is not None:
            board_ids_to_use = board_ids_to_use
        else:
            board_ids_to_use = [1, 2, 3, 4]
        
        best_focus = foc.calculate_best_focus_from_images(directory,
                                                      #masterdarks_dir=MASTERDARK_DIR,
                                                      #masterflats_dir=MASTERFLAT_DIR,
                                                      #maskdir=MASK_DIR,
                                                      board_ids_to_use=board_ids_to_use,
                                                      statsfile=os.path.join(DEFAULT_OUTPUT_DIR,
                                                                             'focusloop_stats.txt')
                                                      )

        if plot_all:
            for board_id in range(6):
                _ = foc.calculate_best_focus_from_images(directory,
                                                     #masterdarks_dir=MASTERDARK_DIR,
                                                     #masterflats_dir=MASTERFLAT_DIR,
                                                     #maskdir=MASK_DIR,
                                                     board_ids_to_use=[board_id],
                                                     statsfile=
                                                     os.path.join(DEFAULT_OUTPUT_DIR,
                                                                  f'focusloop_stats_{board_id}'
                                                                  f'.txt')
                                                     )
            try:
                foc.plot_all_detectors_focus(DEFAULT_OUTPUT_DIR)
            except Exception as e:
                print(f'could not plot all detectors: {e}')
                
        self.post_results_to_slack()
        return best_focus
    
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









