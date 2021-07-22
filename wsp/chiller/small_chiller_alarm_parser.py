#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jul 15 11:08:26 2021

@author: nlourie
"""

import sys
import os
import yaml

# add the wsp directory to the PATH
wsp_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(1, wsp_path)
print(f'StateGetter: wsp_path = {wsp_path}') # make sure this actually prints out the correct path to the main wsp directory
print()
# winter modules
from alerts import alert_handler

class ChillerAlarmParser(object):
    
    def __init__(self, alarm_config, verbose = False):
        self.verbose = verbose
        self.alarm_config = alarm_config
        self.active_alarms = []
        self.active_warnings = []
        self.alarm_msg = ''
        self.rawerrcode = ''
        
    def parse_alarm_code(self, code: str):
        
        self.rawerrcode = code
        
        if self.verbose:
            print(f"Alarm Code = {code}")
    
        
        errstr = code.decode('utf-8')
        
        #print(f"Alarm Code Str = {errstr}")
        
        # parse out the actual code from the keyword
        
        prefix = "#01660rAlrmBit"
        
        prefix_removed = errstr.split(prefix)[1]
        
        # split by space and get the first 8
        error_words = prefix_removed.split(' ')[0:8]
        
        if len(error_words) != 8:
            if self.verbose:
                errormsg = 'Parsed {len(error_words)} error words but expected 8!'
                print(errormsg)
            raise ValueError(errormsg)
            return
        
        if self.verbose:
            print(f'Parsed Error Codes = {error_words}')
        
        self.active_alarms = []
        self.active_warnings = []
        
        for wordnum in range(len(self.alarm_config['alarmFormat'])):
            if self.verbose:
                print()
            keyword = self.alarm_config['alarmFormat'][wordnum]
            
            if self.verbose:
                print(f'checking for active flags in {keyword}')
            
            # process the first 16 bit hex word
            #hex_word = '0400'
            hex_word = error_words[wordnum]
            if self.verbose:
                print(f'word {wordnum} in hex = {hex_word}')
            
            # turn the hex word into a decimal number
            number = int(hex_word, 16)
            
            # turn the decimal number into a binary string with ALL 16 bits
            msbfirst_bitstr = format(number, '016b')
            if self.verbose:
                print(f'bitstring (MSB first) {wordnum} in binary = {msbfirst_bitstr}')
            
            # NOTE THE ALARMS ARE LISTED IN LSB FIRST, SO NEED TO FLIP THE ORDER OF THE BITSTR
            lsbfirst_bitstr = msbfirst_bitstr[::-1]
            if self.verbose:
                print(f'bitstring (LSB first) {wordnum} in binary = {lsbfirst_bitstr}')
            
            
            
            
            # print all active alarms:
            for i in range(len(lsbfirst_bitstr)):
                bit = int(lsbfirst_bitstr[i])
                if bit == 1:
                    
                    msg = self.alarm_config[keyword][i]
                    if 'alarm' in keyword:
                        self.active_alarms.append(msg)
                    elif 'warning' in keyword:
                        self.active_warnings.append(msg)
        
        # make the error message that prints nicely:
        self.createAlarmMessage()
        
        return self.alarm_msg
        
    
    def createAlarmMessage(self, includeraw = False):
        # make a pretty printable string that displays all the alarms
        msglist = []
        msglist.append('')
        if includeraw:
            msglist.append(f'raw error code: {self.rawerrcode}')
        if len(self.active_alarms) >0:
            if len(self.active_alarms) == 1:
                msglist.append(f'{len(self.active_alarms)} ACTIVE ALARM: {self.active_alarms[0]}')
            else:
                msglist.append('{len(self.active_alarms)} ACTIVE ALARMS: ')
                for active_alarm in self.active_alarms:
                    msglist.append('\t{active_alarm')
                
        else:
            msglist.append(f'No active alarms.')
        
        if len(self.active_warnings) >0:
            if len(self.active_warnings) == 1:
                msglist.append(f'{len(self.active_warnings)} ACTIVE WARNING: {self.active_warnings[0]}')
            else:
                msglist.append('{len(self.active_warnings)} ACTIVE WARNINGS: ')
                for active_warning in self.active_warnings:
                    msglist.append('\t{active_warning')
                
        else:
            msglist.append(f'No active warnings.')
        
        self.alarm_msg = '\n'.join(msglist)
    
    def printAlarms(self):
        # print out the warnings and alarms
  
        self.createAlarmMessage()
        print(self.alarm_msg)

if __name__ == '__main__':
    
    def broadcast_alert(alertHandler, name, content):
        # create a notification
        print(f'Broadcasting error: Chiller has encountered {name} : {content}' )
        msg = f':redsiren: *Alert!!*  Chiller has encountered {name} : {content}'       
        group = 'chiller'
        alertHandler.slack_log(msg, group = group)
    
    err_content = b'#01660rAlrmBit0000 0000 0400 0000 0000 0000 0000 0000 41\r'

    #err = b'#01660rAlrmBit0000 0000 0400 1E80 0000 0000 8104 0000 41\r'
    
    alarm_config = yaml.load(open(os.path.join(wsp_path, 'chiller', 'small_chiller_alarm_key.yaml')), yaml.FullLoader)

    # set up alerts locally
    # set up the alert system to post to slack
    auth_config_file  = wsp_path + '/credentials/authentication.yaml'
    user_config_file = wsp_path + '/credentials/alert_list.yaml'
    alert_config_file = wsp_path + '/config/alert_config.yaml'
    
    auth_config  = yaml.load(open(auth_config_file) , Loader = yaml.FullLoader)
    user_config = yaml.load(open(user_config_file), Loader = yaml.FullLoader)
    alert_config = yaml.load(open(alert_config_file), Loader = yaml.FullLoader)
    
    alertHandler = alert_handler.AlertHandler(user_config, alert_config, auth_config)
    
    
    chillerAlarms = ChillerAlarmParser(alarm_config = alarm_config, verbose = False)
    
    parsed_error_msg = chillerAlarms.parse_alarm_code(err_content)
    
    broadcast_alert(alertHandler, 'alarm code', err_content)
    broadcast_alert(alertHandler, '', parsed_error_msg)
    
