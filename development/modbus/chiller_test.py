#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Oct 23 16:21:03 2020

@author: winter
"""

#import sys
#import numpy as np
from pymodbus.client.sync import ModbusSerialClient
import time
from datetime import datetime
import json

def read_register(client,regnum, unit = 1, modbus_offset = -1, verbose = False):
    count = 1
    regnum = regnum + modbus_offset

    if client.connect():  # Trying for connect to Modbus Server/Slave
        '''Reading from a holding register with the below content.'''
        res = client.read_holding_registers(address=regnum, count=count, unit=unit)
        
        '''Reading from a discrete register with the below content.'''
        # res = client.read_discrete_inputs(address=1, count=1, unit=1)
    
        if not res.isError():
            reply = res.registers
            #print(reply)
        else:
            reply = res
            #print(reply)
        
        if verbose:
            print(f'reg {regnum} = {reply}')
    else:
        if verbose:
            print('Cannot connect to the Modbus Server/Slave')
            reply = None
    return reply




class Chiller(object):
    
    def __init__(self, port, reg_dict, modbus_query_dt = 1.0, modbus_offset = -1, baud = 9600, timeout = 1, parity = 'E', stopbits = 1, bytesize = 8):
        
        # general attributes
        self.modbus_offset = -1
        self.modbus_query_dt = modbus_query_dt
        # Serial connection attributes
        self.ser_method = 'rtu'
        self.ser_port = port
        self.ser_baud = baud
        self.ser_timeout = timeout
        self.ser_parity = parity
        self.ser_stopbits = 1
        self.ser_bytesize = bytesize
        
        # max poll dt: this is the max time between polls. it depends on the length of the reg_dict, and the timeout
        self.max_poll_dt = len(reg_dict) * (self.ser_timeout + self.modbus_query_dt)
        print(f'chiller: will alarm if any poll dt is longer than {self.max_poll_dt} seconds')
        
        # Make a dictionary that holds all the registers
        self.reg_dict = reg_dict
        
        # raw state dictionaryy holds all the states of the registers that we get back from the chiller
        self.rawstate = dict()
        
        # set up the dictionaries
        self.setup_dicts()
        
        # STARTUP
        self.setup_serial()
    def setup_dicts(self):
        
        # state dictionary holds the parsed 
        self.state = dict()
        self.parse_state()
        
        # dictionary that holds the timestamps of the last time each field was successfully polled
        self.last_poll_times = dict()
        self.poll_dt = dict()
        
        init_timestamp = datetime.utcnow().timestamp()
        for key in self.reg_dict.keys():
            self.last_poll_times.update({key : init_timestamp})
            self.poll_dt.update({key : 0.0})
    def setup_serial(self):
        
        self.client = ModbusSerialClient(
            method = self.ser_method,
            port = self.ser_port,
            baudrate = self.ser_baud,
            timeout = self.ser_timeout,
            parity = self.ser_parity,
            stopbits = self.ser_stopbits,
            bytesize = self.ser_bytesize)
        
        print('chiller: connecting serial port')
        self.client.connect()
    
    def parse_state(self):
        '''
        does some work to parse the state (eg convert units, etc) and create some useful flags
        '''
        # these registers are temperature*10. eg the chiller returns 180 ==> 18.0 C
        temps = ['setpoint', 'range', 'fluid_temp']
        
        # update all the individual fields
        for key in self.rawstate.keys():
            #print(f'parsing key {key}')
            if key in temps:
                self.state.update({key : self.rawstate.get(key,-8888)/10.0 })
            
            else:
                self.state.update({key : self.rawstate.get(key, -888)})
                
        
        
    def poll_status(self):
        '''
        send a request to the chiller to get the status back
        '''
        if self.client.is_socket_open():
            # Read the registers one by one
            for key in self.reg_dict.keys():
                regnum = self.reg_dict[key] + self.modbus_offset
                res = self.client.read_holding_registers(address = regnum, count = 1, unit = 1)
                if not res.isError():
                        # get the value from the register list
                        reply = res.registers[0]
                        
                        # update the raw state with the register value
                        self.rawstate.update({key : reply})
                        
                        # calculate the time since the last successfull pol
                        timestamp = datetime.utcnow().timestamp()
                        time_since_last_poll = timestamp - self.last_poll_times.get(key, 0.0 )
                        self.poll_dt.update({key : time_since_last_poll})
                        
                        # log the timestamp of this poll for future calculation of dt
                        self.last_poll_times.update({key : timestamp})
                else:
                    reply = res
                    print(f'chiller: could not get {key}: {reply}')
                    pass
                time.sleep(self.modbus_query_dt)
            self.parse_state()
        else:
            print(f'socket not connected!')
            

if __name__ == '__main__':
        
    regs = dict({'fluid_temp'     : 8992,
                 'setpoint'                 : 16384,
                 'range'                    : 16386,
                 'offset_fluid_temp'        : 16387,
                 'remote_start_stop'        : 16385,
                 'status_dutycycle_status'  : 8971,
                 'alarm_sysfault_status'    : 8967,
                 'warn_general_status'      : 9004})
    
    
    chiller = Chiller('/dev/ttyUSB0', reg_dict = regs, modbus_query_dt = 0.50)
    
    time.sleep(1)
    
    while True:
        try:
            chiller.poll_status()
            print(f'state = {json.dumps(chiller.state, indent = 2)}')
            print(f'poll dt = {json.dumps(chiller.poll_dt, indent = 2)}')
            print()
            time.sleep(5)
        except KeyboardInterrupt:
            break
    
    chiller.client.close()

