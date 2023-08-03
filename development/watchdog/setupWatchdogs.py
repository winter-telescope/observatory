#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jul 25 12:07:13 2023

@author: winter
"""

import os
import shutil
import socket
import sys
from pathlib import Path
# add the wsp directory to the PATH
wsp_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'wsp')
service_file_dir = os.path.join(os.path.dirname(wsp_path), 'development', 'watchdog')
enable_on_boot = False
#sys.path.insert(1, wsp_path)
print(f'wsp_path = {wsp_path}')

hostname = socket.gethostname()
print(f'the hostname is {hostname}')

class python_service(object):
    def __init__(self, servicename, condaenvname, daemon_filepath):
        self.servicename = servicename
        self.condaenvname = condaenvname
        self.daemon_filepath = daemon_filepath
    
    def make_launcher_shell_script(self, directory):
        self.shellscript_filepath = os.path.join(directory, self.servicename+'.sh')
        print(f'attempting to make shell script at {self.shellscript_filepath}')
        Path(directory).mkdir(parents=True, exist_ok=True)
        file = open(self.shellscript_filepath, 'w+')
        lines = []
        lines.append('#!/bin/bash')
        #lines.append('source $HOME/anaconda3/etc/profile.d/conda.sh')
        lines.append('source $HOME/anaconda3/etc/profile.d/conda.sh')
        lines.append(f'conda activate {self.condaenvname}')
        lines.append('#-u: unbuffered output')
        lines.append(f'python -u {self.daemon_filepath}')
        for line in lines:
            file.write(line+'\n')
        file.close()
        
        # make the shell script executable
        os.chmod(self.shellscript_filepath, 755)
    
    def make_service_file(self, directory):
        self.service_filepath = os.path.join(directory, self.servicename+'.service')
        print(f'attempting to make service file at {self.service_filepath}')
        Path(directory).mkdir(parents=True, exist_ok=True)
        file = open(self.service_filepath, 'w+')
        lines = []
        lines.append('[Unit]')
        lines.append('Description=watchdog for winter camera daemon')
        #lines.append('After=multi-user.target')
        lines.append('')
        lines.append('[Service]')
        lines.append('Type=simple')
        lines.append('Restart=always')
        lines.append(f'ExecStart={self.shellscript_filepath}')
        lines.append(f'User={os.getlogin()}')
        lines.append('')
        lines.append('[Install]')
        lines.append('WantedBy=multi-user.target')
        for line in lines:
            file.write(line+'\n')
        file.close()
        
    def start_service(self, enable_on_boot = False):
        # copy the service file to /etc/systemd/system
        targetfile = f'{self.servicename}.service'
        targetdir = '/etc/systemd/system'
        targetfilepath = os.path.join(targetdir, targetfile)
        print(f'making new systemctl daemon service file: {targetfile}:')
        print(f'copying {self.service_filepath} --> {targetfilepath}')
        os.system(f'sudo cp {self.service_filepath} {targetfilepath}')
        print()
        
        print('reloading systemctl daemons...')
        os.system("systemctl daemon-reload")
        print()
        print(f'starting {self.servicename} systemctl daemon...')
        os.system(f'systemctl start {self.servicename}')
        if enable_on_boot:
            print()
            print(f'enabling {self.servicename}.service daemon on boot')
            os.system(f'systemctl enable {self.servicename}.service')
        print('...done!')

if hostname == 'freya':
    services = [('winterCamerad', 'wspfocus', '/home/winter/GIT/firmware/software/development/cameraDaemon/winterCamerad.py'),
                ('winterImaged',  'wspfocus', '/home/winter/GIT/observatory/wsp/camera/winter_image_daemon.py')
                ]
    ## copy the daemon service file to /etc/systemd/system/wsp_watchdog.service
    #servicefile = 'freya_wsp_watchdog.service'
    #servicefilepath = os.path.join(service_file_dir, servicefile)
elif hostname == 'odin':
    print(f'we eventually need rules for hostname {hostname}, but they are not yet implemented! exiting...')
    sys.exit()
else:
    print(f'no rules for hostname {hostname}. exiting...')
    sys.exit()

shell_script_directory = os.path.join(os.getenv("HOME"), 'wsp_watchdog', 'shell_scripts')
service_def_directory  = os.path.join(os.getenv("HOME"), 'wsp_watchdog', 'services')

# make the directory if it doesn't already exist
#Path(shell_script_directory).mkdir(parents=True, exist_ok=True)
#Path(shell_script_directory).mkdir(parents=True, exist_ok=True)

for args in services:
    service = python_service(*args)
    
    # make the shell scripts
    service.make_launcher_shell_script(directory = shell_script_directory)
    
    # make the service file
    service.make_service_file(directory = service_def_directory)
    
    # launch the systemctl daemons
    service.start_service(enable_on_boot = True)
# targetfile = 'wsp_watchdog.service'
# targetdir = '/etc/systemd/system'
# targetfilepath = os.path.join(targetdir, targetfile)
# print(f'making new systemctl daemon service file: {targetfile}:')
# print(f'copying {servicefilepath} --> {targetfilepath}')
# os.system(f'cp {servicefilepath} {targetfilepath}')
# print()
# print('reloading systemctl daemons...')
# os.system("systemctl daemon-reload")
# print()
# print('starting wsp_watchdog systemctl daemon...')
# os.system('systemctl start wsp_watchdog.service')
# if enable_on_boot:
#     print()
#     print('enabling wsp_watchdog.service daemon on boot')
#     os.system('systemctl enable wsp_watchdog.service')
# print('...done!')

#%% Set Up Custom Aliases To Start and Stop the watchdog
"""
alias_path = os.path.join(os.getenv("HOME"), '.bash_aliases')
if os.path.exists(alias_path):
    print(f'bash alias file already exists at {alias_path}')
    
else:
    print(f'no existing bash alias file, making one at {alias_path}')

aliascommands = []
aliascommands.append('alias wsp_watchdog_start="sudo systemctl start wsp_watchdog"')
aliascommands.append('alias wsp_watchdog_start="sudo systemctl stop wsp_watchdog"')


for command in aliascommands:
    aliasfile = open(alias_path, 'a+')
    aliases = aliasfile.readlines()
    found = False
    for line in aliases:
        print(line)
        if command in line:
            found = True
    if not found:
        print(f'alias not found: {command}, adding it...')
        aliasfile.write(command+'\n')
    else:
        print(f'alias already in file: {command}')
    aliasfile.close()
    
"""