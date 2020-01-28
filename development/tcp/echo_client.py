#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jan 28 10:18:53 2020

A program to make an echo server/client command interface

@author: winter
"""


import socket

# create a TCP/IP socket
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# connect the socket ot the port where the server is listening
server_address = ('localhost',7575)
print(f'connecting to {server_address[0]} port {server_address[1]}')
sock.connect(server_address)

# now that the connection is established, data can be sent with sendall() and received with recv()

try:
    # send some data
    message = 'This is a message from the client. It should be echoed back!'
    print(f"sending message:'{message}'")
    sock.sendall(bytes(message,"utf-8"))
    
    # Look out for the resonse from the server
    amount_received = 0
    amount_expected = len(message)
    
    while amount_received < amount_expected:
        data = sock.recv(16).decode("utf-8")
        amount_received += len(data)
        print(f"received message back from server: '{data}'")
        
finally:
    print('closing socket')
    sock.close()