#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Feb  5 11:33:46 2020

@author: nlourie
"""

# Python TCP Client B
import socket 

host = 'localhost'#socket.gethostname() 
port = 2033
BUFFER_SIZE = 1024
MESSAGE = input("tcpClientB: Enter message/ Enter exit:") 
 
tcpClientB = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
tcpClientB.connect((host, port))

while MESSAGE != 'exit':
    tcpClientB.send(bytes(MESSAGE,'utf-8'))     
    data = tcpClientB.recv(BUFFER_SIZE)
    print (" Server says it received:", data.decode('utf-8'))
    MESSAGE = input("tcpClientB: Enter message to continue/ Enter exit:")

tcpClientB.close() 