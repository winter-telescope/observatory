#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jan 28 10:18:53 2020

A program to make an echo server/client command interface

@author: winter
"""


import socket
import sys

# Create a TCP/IP socket
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# associate the socket with a server address: Bind to an address
server_address = ('localhost', 7575)

print(f'starting up on {server_address[0]} port {server_address[1]}')
sock.bind(server_address)

# listen for incoming connections
sock.listen(5) #not exactly sure what the number means...

while True:
    # wait for a connection
    print('Waiting for a connection')
    client_socket, client_address = sock.accept()
    
    try:
        print(f'connection from {client_address}')
        
        # receive the data in small chunks and retransmit it
        while True:
            data = client_socket.recv(16)
            print(f'received {data.decode("utf-8")}')
            if data:
                print('sending data back to the client')
                client_socket.send(data)
            else:
                print(f'no more data from {client_address}')
                break
    
    finally:
        # clean up and close the connection. the try:finally thing makes it close even if there's an error
        print('closing socket.')
        client_socket.close()
        
    
