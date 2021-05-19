#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Feb  4 18:55:27 2021

@author: winter
"""


import socket
import io
import time
def readline(sock):
    """
    Utility function for reading from a socket until a
    newline character is found
    """
    buf = io.StringIO()
    while True:
        data = sock.recv(1).decode("utf-8")
        buf.write(data)
        if data == '\n':
            return buf.getvalue()
def sendreceive(sock, command):
    """
    Send a command to the server, and read the response.
    The response will be split into an integer error code and an optional error text messsage.
    Returns a tuple (code, error_text)
    """
    sock.send(bytes(command + "\n","utf-8"))
    response = readline(sock)
    # The response should consist of a numeric code, optionally
    # followed by some text if the code is 255 (error). Parse this out.
    fields = response.split(" ")
    response_code = int(fields[0])
    error_text = ""
    if len(fields) > 1:
        error_text = fields[1]
    return (response_code, error_text)
#%%
#### BEGIN SAMPLE SESSION ####
print("Connecting to PWShutter TCP server...")
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.settimeout(0.5)
sock.connect(("192.168.1.12", 9897))
#%
print( "Checking connection...")

(code, text) = sendreceive(sock, "isconnected")
if code == 0:
    print( "PWShutter is connected to the controller")
elif code == 1:
    print("PWShutter is not connected to the controller")
else:
    print("ERROR:", code, text)
print("Trying to connect to controller...")
(code, text) = sendreceive(sock, "connect")
if code == 0:
    print ("Connection established")
else:
    print("ERROR:", code, text)
#%%
print("Trying to begin opening the shutter...")
(code, text) = sendreceive(sock, "beginopen")
if code == 0:
 print("Shutter is starting to open")
else:
    print("ERROR:", code, text)
print("Monitoring shutter status while opening...")
while True:
    (code, text) = sendreceive(sock, "shutterstate")
    if code == 0:
        print("Open")
    elif code == 1:
        print("Closed")
    elif code == 2:
        print("Opening")
    elif code == 3:
        print("Closing")
    elif code == 4:
        print("Error")
    elif code == 5:
        print("Partly open")
    else:
        print("ERROR:", code, text)
     # Exit loop if we are in any state other than Opening
    if code != 2:
        pass#break
    # Wait a bit before checking again
    time.sleep(1)
print("Done")