#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jan 28 09:02:17 2020

This is a test file for developing the TCP command interface


@author: winter
"""

import socket

s = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
#s.connect((socket.gethostname(),7000))
s.connect(('192.168.1.20', 34633))



"""
# Just send one chunk of data
while True:
    msg = s.recv(8) #this gets the message from the server, this is the bytesize of the data buffer
    print(msg.decode("utf-8")) #the message is sent as bytes, recieved as bytes, and we just have to decode it.
    
"""



"""
# Buffer and then recombine
full_msg = ''
while True:
    msg = s.recv(8) #this gets the message from the server, this is the bytesize of the data buffer
    
    if len(msg)<=0:
        break
    #the message is sent as bytes, recieved as bytes, and we just have to decode it.
    full_msg += msg.decode("utf-8") #keep tagging on the chunks til we get the full message
    
print(full_msg) 
    
"""

# Now read the fixed header length and import the message

HEADERSIZE = 10

while True:
    
    # Buffer and then recombine
    full_msg = ''
    new_msg = True # make a flag for a new incoming message, the first message received is definitely a new message so set to True
    
    while True:
        msg = s.recv(16) # set so it can receive a slightly bigger buffer than the header, but at minimum must be header size
        if new_msg:
            print(f"new message length: {msg[:HEADERSIZE]}") # passes the message up to the first HEADERSIZE characters to the f-string print statement
            msglen = int(msg[:HEADERSIZE]) # remember the msg is coming as bytes so this works
            new_msg = False # no more new message
        
        #the message is sent as bytes, recieved as bytes, and we just have to decode it.
        full_msg += msg.decode("utf-8") #keep tagging on the chunks til we get the full message
        
        if len(full_msg) - HEADERSIZE == msglen:
            #then you've gotten the full message
            print("Full message recvd")
            print(full_msg[HEADERSIZE:]) #print the message and not the header
            new_msg = True #we're done with the old message so now look for a new one
            full_msg = '' #reset the full message to empty so we can fill it next time through the loop
            
        
    print(full_msg) 

