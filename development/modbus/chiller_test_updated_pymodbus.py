#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Feb 21 11:57:49 2023

@author: winter
"""


from pymodbus.client.serial import ModbusSerialClient
import numpy as np
from datetime import datetime

config = {'serial_params' :
                  {'port': '/dev/serial/by-id/usb-FTDI_FT232R_USB_UART_AQ00T8I9-if00-port0',
                   'method': 'rtu',
                   'baudrate': 9600, 
                   'timeout': 0.5, 
                   'parity': 'E', 
                   'stopbits': 1, 
                   'bytesize': 8,
                   },
          'registers':
              {'SystemDisplayValueStatus':
                  {'addr': 8992,
                  'scale': 0.1,
                  'mode': 'rw'}
              },
          }
                  
                  

modbus_offset = -1
state = dict()
sock = ModbusSerialClient(
    method      = config['serial_params']['method'],
    port        = config['serial_params']['port'],
    baudrate    = config['serial_params']['baudrate'],
    timeout     = config['serial_params']['timeout'],
    parity      = config['serial_params']['parity'],
    stopbits    = config['serial_params']['stopbits'],
    bytesize    = config['serial_params']['bytesize'])
print('connecting to serial socket...')
sock.connect()

# Now we'll try polling a register:
reg = 'SystemDisplayValueStatus'
# if the connection is live, ask for the dome status
if sock.is_socket_open():
    print('...socket is open!')

else:

    print('...socket is closed :(')

addr = config['registers'][reg]['addr'] + modbus_offset
#%%
reply = sock.read_holding_registers(address = addr, count = 1, slave = 1)

if not reply.isError():
    rawval = reply.registers[0]
    scale = config['registers'][reg]['scale']
    # don't carry arbitrary precision on these numbers. they are only reported to one decimal at most from the chiller
    val = np.round(rawval * scale,1)
    print(f'Reg: {reg}')
    print(f'\t Rawval = {rawval}')
    print(f'\t Val    = {val}')
else:
    print(f'chiller: could not get {reg}: {reply}')
    pass                    
                           