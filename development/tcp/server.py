#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jan 28 09:02:17 2020

This is a test file for developing the TCP command interface


@author: winter
"""

import socket
"""
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

s.bind((socket.gethostname(),7000))
#s.bind(('odin',7000))
s.listen(5)


while True:
    clientsocket, address = s.accept()
    print(f"Connection from {address} has been established!")
    clientsocket.send(bytes("Welcome to the server!","utf-8")) #this makes the message in bytes
    clientsocket.close()
    
"""    
    
# The main problem with above code is that we have to either:
#    a) use a fixed buffer and make sure it's bigger than the message to the client   
#    b) insert the socket.close() command after the message is sent
# Want a beter way. Let's make a message from the server with a header that
# tells the client how long the message is

msg = "Welcome to the server!"

# want the header to be a FIXED LENGTH string, so that it's always the same size
# no matter what the size of the message is. Let's pick a fixed length that
# accomodates the largest possible message we think we might send

# let's say our longest message is 1 billion characters! that should do it
# 1 billion = 1000000000 which has 10 characters
HEADERSIZE = 10
#print(f'{len(msg):<{HEADERSIZE}}')    # this always prints a number with 10 characters (ie trailing spaces)
# Notes on this string formatting syntax:
    # the < means "left alinged", basically an arrow. Can also use ">" for right, and "^" for center
    # and the : {NUMBER} specifies the length in characters of the string

# This will print: [22        ] ie 22 and then 8 zeros

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
hostname = socket.gethostname()
host = socket.gethostbyname(hostname)
#s.bind((socket.gethostname(),34633))
s.bind((host, 34633))
s.listen(5)

# now make the message always this fixed length
while True:
    clientsocket, address = s.accept()
    print(f"Client from {address} has been established!")
    
    msg = "Welcome to the server!"
    msg = f'{len(msg):<{HEADERSIZE}}' + msg # message is the header with the message size + the message, and the header is alwayst the same length
    
    clientsocket.send(bytes(msg,"utf-8"))


    
    
    
    
    
    
    
    
    
    
    
    
    
    