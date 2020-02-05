#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Feb  5 11:33:35 2020

@author: nlourie
"""

# Python TCP Client A
import socket 

host = 'localhost'#socket.gethostname() 
port = 2035
BUFFER_SIZE = 1024
MESSAGE = input("tcpClientA: Enter message to continue/ Enter quit to close client/or killserver:")
 
tcpClientA = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
tcpClientA.connect((host, port))
tcpClientA.settimeout(3)
while True:
    tcpClientA.send(bytes(MESSAGE,'utf-8'))     

    if MESSAGE == 'quit':
        print(" Shutting Down Client...")
        break
    if MESSAGE == 'killserver':
        print(" Sent killserver command to server.")
        MESSAGE = input("tcpClientA: Enter message to continue/ Enter quit to close client/or killserver:")
    else:
        data = tcpClientA.recv(BUFFER_SIZE)
        print (" Server says it received:", data.decode('utf-8'))
        MESSAGE = input("tcpClientA: Enter message to continue/ Enter quit to close client/or killserver:")
        
tcpClientA.close() 