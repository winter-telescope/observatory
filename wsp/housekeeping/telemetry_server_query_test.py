#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Feb 13 11:17:32 2020

@author: nlourie
"""

import socket

# Connect to the server
sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
server_address = ('198.202.125.214',4698)
sock.connect(server_address)

# Send a command
cmd = 'WEATHER_JSON\n'
sock.sendall(bytes(cmd,"utf-8"))
reply = sock.recv(1024).decode("utf-8")

# Close the connection
sock.close()


