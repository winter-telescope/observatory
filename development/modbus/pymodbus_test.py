#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Oct 23 16:21:03 2020

@author: winter
"""

import sys
import numpy as np
from pymodbus.client.sync import ModbusSerialClient

client = ModbusSerialClient(
    method='rtu',
    port='/dev/ttyUSB0',
    baudrate=9600,
    timeout=1,
    parity='E',
    stopbits=1,
    bytesize=8
)


MODBUS_OFFSET = -1

def read_register(client,regnum,count = 1, unit = 1, modbus_offset = -1):
    
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
    
    else:
        print('Cannot connect to the Modbus Server/Slave')
    
    return reply

if __name__ == '__main__':
    
    args = sys.argv[1:]
    if len(args) > 0:
    
        
        regnum = int(args[0])
        print(f'reading register {regnum}')
        
        if len(args)>1:
            count = int(args[1])
        else:
            count = 1
        reply = read_register(client, regnum, count, modbus_offset = MODBUS_OFFSET)
    
        print(f'reply = {reply}')
    
    else:
        regnum = 16383
        print(f'reading register {regnum}')
    
        reply = read_register(client, regnum)
    
        print(f'reply = {reply}')
        
    
