#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jan 28 10:18:53 2020

A program to make an echo server/client command interface

@author: winter
"""


import socket
import sys

def printphrase(phrase = 'default phrase'):
    printed_phrase = f"I'm Printing the Phrase: {phrase}"
    print(printed_phrase)
    return printed_phrase
    

# Create a TCP/IP socket
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# associate the socket with a server address: Bind to an address
server_address = ('localhost', 7070)

print(f'starting up on {server_address[0]} port {server_address[1]}')
sock.bind(server_address)

# listen for incoming connections
sock.listen(5) # the number is the number of bad connections it allows before refusing connection

while True:
    # wait for a connection
    print('Waiting for a connection')
    client_socket, client_address = sock.accept()
    
    try:
        print(f'connection from IP {client_address[0]} | port  {client_address[1]}')
        
        # receive the data in small chunks and retransmit it
        while True:
            cmd = client_socket.recv(1024)
            print(f'received: {cmd.decode("utf-8")}')
            cmd_txt = cmd.decode("utf-8")
            if cmd:
                #reply = f'received command: {cmd}\n'
                #client_socket.send(bytes(reply,"utf-8"))
                if cmd_txt.lower() == 'killserver':
                    client_socket.close()
                    sock.close()
                    sys.exit()
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
    
    finally:
        # clean up and close the connection. the try:finally thing makes it close even if there's an error
        print('closing socket.')
        client_socket.close()
"""        
while True:
    print("enter a command: ")
    cmd = input()
    if cmd.lower() == 'quit':
        break
    try:
        eval(cmd)
    except:
        print("command not recognized")   
"""