#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Mar 22 13:55:48 2021

chiller.py

This is part of wsp

# Purpose #

This program contains the software interface for the WINTER chiller,
including a class that contains the necessary commands to communicate
with the chiller


@author: nlourie
"""



import os
import numpy as np
import sys
import Pyro5.core
import Pyro5.server
from datetime import datetime
import traceback as tb
from PyQt5 import QtCore
import logging
import time
import json
# add the wsp directory to the PATH
wsp_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(1, wsp_path)
print(f'chiller: wsp_path = {wsp_path}')
from utils import utils




#class local_dome(object):
class local_chiller(QtCore.QObject):    
    '''
    Using a QObject so that it can signals. The problem is that all the Pyro
    calls for a given proxy have to be handled in a single thread. To execute commands
    from outside this thread let's try using the signal/slot approach.
    '''
    newCommand = QtCore.pyqtSignal(object)
    TECshutoffCmd = QtCore.pyqtSignal()
    
    def __init__(self, base_directory, config, ns_host = None, alertHandler=None):
        super(local_chiller, self).__init__()
        
        # Define attributes
        self.base_directory = base_directory
        self.config = config
        self.ns_host = ns_host
        self.state = dict()
        self.remote_state = dict()
        self.connected = False
        self.default = self.config['default_value']
        self.alertHandler = alertHandler
        self.logger = None
        
        # connect the signals and slots
        self.newCommand.connect(self.doCommand)
        
        # make some lists to handle the problems with the chiller
        self.active_alarms = []
        self.active_warnings = []
        self.active_faults = []
        
        # Startup
        # it takes a while to start up, so keep track of when we started
        self.init_timestamp = datetime.utcnow().timestamp()
        self.last_check_timestamp = datetime.utcnow().timestamp()
        self.init_remote_object()
        self.update_state()
        
    def log(self, msg, level = logging.INFO):
        if self.logger is None:
            print(f'localChiller: {msg}')
        else:
            self.logger.log(level, msg)
    def createAlarmMessage(self, includeraw = False):
        # make a pretty printable string that displays all the alarms
        msglist = []
        msglist.append('')
        
        if len(self.active_faults) > 0:
            if len(self.active_faults) == 1:
                msglist.append(f'{len(self.active_faults)} ACTIVE FAULT: {self.active_faults[0]}')
            else:
                msglist.append(f'{len(self.active_faults)} ACTIVE FAULTS: ')
                for active_fault in self.active_faults:
                    msglist.append(f'\t{active_fault}')
        
        if len(self.active_alarms) >0:
            if len(self.active_alarms) == 1:
                msglist.append(f'{len(self.active_alarms)} ACTIVE ALARM: {self.active_alarms[0]}')
            else:
                msglist.append(f'{len(self.active_alarms)} ACTIVE ALARMS: ')
                for active_alarm in self.active_alarms:
                    msglist.append(f'\t{active_alarm}')
                
        else:
            msglist.append(f'No active alarms.')
        
        if len(self.active_warnings) >0:
            if len(self.active_warnings) == 1:
                msglist.append(f'{len(self.active_warnings)} ACTIVE WARNING: {self.active_warnings[0]}')
            else:
                msglist.append(f'{len(self.active_warnings)} ACTIVE WARNINGS: ')
                for active_warning in self.active_warnings:
                    msglist.append(f'\t{active_warning}')
                
        else:
            msglist.append(f'No active warnings.')
        
        alarm_msg = '\n'.join(msglist)
        #print(f'ALARM MESSAGE = {alarm_msg}')
        return alarm_msg
    
    def broadcast_alert(self, content):
        # create a notification
        print(f'Broadcasting error: Chiller has encountered: {content}' )
        msg = f':redsiren: *Alert!!*  Chiller has encountered: {content}'       
        #group = 'chiller'
        group = 'sudo'
        self.alertHandler.slack_log(msg, group = group)
        txtsubject = 'WINTER CHILLER :'
        #txtmsg = f'Chiller has encountered {name} : {content}'
        #self.alertHandler.text_group(group,subject = txtsubject, message = txtmsg)
    
    def doCommand(self, cmd_obj):
        """
        This is connected to the newCommand signal. It parses the command and
        then executes the corresponding command from the list below

        using this as a reference: (source: https://stackoverflow.com/questions/6321940/how-to-launch-getattr-function-in-python-with-additional-parameters)     
        
        """
        cmd = cmd_obj.cmd
        args = cmd_obj.args
        kwargs = cmd_obj.kwargs
        
        #print(f'chiller: caught doCommand signal: {cmd}, args = {args}, kwargs = {kwargs}')

        try:
            getattr(self, cmd)(*args, **kwargs)
        except:
            pass
        
    def init_remote_object(self):
        # init the remote object
        try:
            ns = Pyro5.core.locate_ns(host = self.ns_host)
            uri = ns.lookup('chiller')
            self.remote_object = Pyro5.client.Proxy(uri)
            self.connected = True
        except:
            self.connected = False
            pass
        '''
        except Exception:
            self.logger.error('connection with remote object failed', exc_info = True)
        '''
    def update_state(self):
        # poll the state, if we're not connected try to reconnect
        # this should reconnect down the line if we get disconnected
        if not self.connected:
            self.init_remote_object()
            
        else:
            try:
                self.remote_state = self.remote_object.GetStatus()
                
                
                self.parse_state()
                
                
            except Exception as e:
                #print(f'chiller: could not update remote state: {e}')
                pass
                
        
        # check if the chiller status is okay for operation
        self.check_if_okay()
       
    def check_if_okay(self):
        
        """
        make sure that the chiller is running and that we've heard from it recencly
        """
        
        # init to no issues
        self.active_alarms = []
        self.active_faults = []
        self.active_warnings = []
        
        #self.log(f'in chiller: check_if_okay')
        now_timestamp = datetime.utcnow().timestamp()
        
        #self.log(f'time since last check: {now_timestamp - self.last_check_timestamp:.1f} s')
        
        
        
        if now_timestamp - self.last_check_timestamp > 60.0:
            # only check this every so often so we don't flood the feed
            
            #self.log(f'time since init: {now_timestamp - self.init_timestamp:.1f} s')
            self.last_check_timestamp = now_timestamp

            if now_timestamp - self.init_timestamp > 60.0:
                
                try:
                    # it takes a little while to get going, so start with a grace period
                    #self.log(f'chiller: checking if okay')
                    # assess alerts here
                    # how long has it been since we last got an update from the chiller?
                    # should only be as high as 20 s
                    if self.state['max_dt_since_last_update'] > 45.0 or self.state['max_dt_since_last_update'] < 0.0:
                        
                        # the chiller is OFFLINE
                        self.active_faults.append('CHILLER OFFLINE')
                
                    if self.state['PumpStatusFlag'] == 0:
                        # the chiller is OFF
                        self.active_faults.append('CHILLER OFF')
                    
                    T = self.state['readSupplyT']
                    SP = self.state['readSetT']
                    
                    if abs(T - SP) > 6.0:
                        # the chiller is not keeping up
                        
                        self.active_warnings.append(f'CHILLER NOT AT TEMPERATURE: T = {T:.1f} C, SP = {SP:.1f} C')
                    
                    if T > 25:
                        self.active_faults.append(f'CHILLER ABOVE ROOM TEMP: T = {T:.1f} C')
                    
                
                except Exception as e:
                    #self.broadcast_alert('', msg)
                    print(tb.format_exc())
                    self.active_faults.append(f"CAN'T COMMUNICATE WITH CHILLER")
                
                #print('in chiller check, assigning self.okay')
                if len(self.active_faults) == 0 & len(self.active_alarms) == 0 & len(self.active_warnings) == 0:
                    self.okay = True
                else:
                    self.okay = False
                    parsed_error_msg = self.createAlarmMessage()
                    self.broadcast_alert(parsed_error_msg)
                    print(f'active faults = {self.active_faults}')
                    print(f'active alarms = {self.active_alarms}')
                    print(f'active warnings = {self.active_warnings}')
                
                    # if we get here, need to send an  alert to turn off the TEC
                    self.TECshutoffCmd.emit()
                    
                    
    def parse_state(self):
        '''
        Do any conditioning we need to properly handle and parse the state dictionary
        '''
        """ # things that have to do with querying server
        self.state.update({'last_command_reply'             :   self.remote_state.get('command_reply', self.default)})
        self.state.update({'query_timestamp'                :   self.remote_state.get('timestamp', self.default)})
        self.state.update({'reconnect_remaining_time'       :   self.remote_state.get('reconnect_remaining_time', self.default)})
        self.state.update({'reconnect_timeout'              :   self.remote_state.get('reconnect_timeout', self.default)})
        """
        # update the rest of the stuff
        for key in self.remote_state.keys():
            self.state.update({key : self.remote_state[key]})
        
        self.state.update({'is_connected'                   :   bool(self.remote_state.get('is_connected', self.default))})
        
        self.check_if_okay()
            
    def print_state(self):
        print(f'state = {json.dumps(chiller.state, indent = 2)}')

    def setSetpoint(self, temperature):
        #print(f'chiller: trying to set the set point to {temperature}')
        self.remote_object.setSetpoint(temperature)
    
    def TurnOn(self):
        self.remote_object.TurnOn()
    
    def TurnOff(self):
        self.remote_object.TurnOff()
    
    def WriteRegister(self, register, value):
        self.remote_object.WriteCommand(register, value)
        
        
# Try it out
if __name__ == '__main__':

    config = utils.loadconfig(wsp_path + '/config/config.yaml')
    chiller = local_chiller(wsp_path, config)
    
    '''
    while True:
        try:
            chiller.update_state()
            chiller.print_state()
            time.sleep(0.5)
            
        except KeyboardInterrupt:
            break
    
    '''
    #%%
    chiller.update_state()
    chiller.print_state()
    
    #%%
    #chiller.WriteRegister('UserSetpoint', 18.1)
    #chiller.TurnOn()
    #chiller.setSetpoint(10.9)
    
    #chiller.update_state()
    #chiller.print_state()
