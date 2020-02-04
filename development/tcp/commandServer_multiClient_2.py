#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jan 28 10:18:53 2020

command_server.py

This program is part of wsp

# PURPOSE #
A program to make an echo server/client command interface

@author: winter
"""


import socket
import sys
import threading
from queue import Queue
from psutil import process_iter
from signal import SIGTERM,SIGKILL

# We have to do some threading contrl to get the command server to accept connections from 
# multiple clients
# Did this by following a tutorial from here: https://www.youtube.com/watch?v=Iu8_IpztiOU
    # 



# This is a test function to make sure commands are being parsed 
def printphrase(phrase = 'default phrase'):
    printed_phrase = f"I'm Printing the Phrase: {phrase}"
    print(printed_phrase)
    return printed_phrase

# Socket functions
def socket_create(timeout = 5):
    try:
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        #server_socket.settimeout(timeout)
        return server_socket
    except socket.error as msg:
        print(f"socket creation error: {msg}")
    

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
    receive_commands(server_socket,client_socket)
    client_socket.close()
    return client_socket, client_address

def receive_commands(server_socket, client_socket):         
    try:
        # receive the data in small chunks and retransmit it
        while True:
            cmd = client_socket.recv(1024)
            client_address = client_socket.getsockname()[0]

            print(f'received from client at {client_address}: {cmd.decode("utf-8")}')
            cmd_txt = cmd.decode("utf-8")
            if cmd:
                #reply = f'received command: {cmd}\n'
                #client_socket.send(bytes(reply,"utf-8"))
                if cmd_txt.lower() == 'killserver':
                    client_socket.close()
                    server_socket.close()
                    break
                    #sys.exit()
                else:
                    try:
                        # try to evaluate the command
                        result = eval(cmd_txt)
                        reply = f'command [{cmd_txt}] executed, result = [{result}]'
                        client_socket.send(bytes(reply,"utf-8"))
                    except:
                        reply = f'command [{cmd_txt}] not executed properly: \n enter "quit" to stop client session or "killserver" to stop command server'
                        client_socket.send(bytes(reply,"utf-8"))
            else:
                print(f'no more data from {client_address}')
                break
    

    
    except KeyboardInterrupt:
        # This makes it exit gracefully if you do cntl + c by leaving the loop and proceeding down to close the server socket
        pass
    except:
        print("Error receiving commands")
    
    finally:
        # clean up and close the connection. the try:finally thing makes it close even if there's an error
        print('closing socket.')
        client_socket.close()  
    
    
def start_commandServer(addr = 'localhost', port = 7075):
    server_socket = socket_create()
    socket_bind(server_socket,addr,port)
    #client_socket, client_address = socket_accept(server_socket)
    #client_socket,client_address = server_socket.accept()
    #print(f'connection from IP {client_address[0]} | port  {client_address[1]}')
    
    try:
        
        while True:
            client_socket, client_address = socket_accept(server_socket)
            receive_commands(server_socket,client_socket)
            
            
    except KeyboardInterrupt:
        # This makes it exit gracefully if you do cntl + c by leaving the loop and proceeding down to close the server socket
        pass
    
    # now that you've keyboardinterrupted, close the server socket
    client_socket.close()
    server_socket.close()     




       
            

if __name__ == '__main__':
    addr = ''
    port = 7780
    
    start_commandServer(addr = addr,port = port)
