#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Oct 23 15:53:44 2020

@author: winter
"""


import numpy as np
import fcntl
import struct
from serial import Serial, PARITY_EVEN

from umodbus.client.serial import rtu

def get_serial_port():
    """this is an example from umodbus.readthedocs.io/en/latest/client/rtu.html
    Return serial. Serial instance, ready to use for RS485."""
    port = Serial(port = '/dev/ttyUSB0', baudrate = 9600, parity = PARITY_EVEN,
                  stopbits = 1, bytesize = 8, timeout = 1)
    """
    fh = port.fileno()
    
    # A struct with configuration for serial port.
    serial_rs485 = struct.pack('hhhhhhhh', 1,0,0,0,0,0,0,0)
    fcntl.ioctl(fh, 0x542F, serial_rs485)
    """
    return port
    
serial_port = get_serial_port()

# Returns a message or Application Data Unit (ADU) specific for doing
# Modbus RTU.
message = rtu.read_holding_registers(1,16383,1)

# Response depends on Modbus function code.
response = rtu.send_message(message, serial_port)
print(f'response = {response}')
