#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jan 28 10:18:53 2020

command_client.py

This program is part of wsp

# PURPOSE #
A program to make an echo server/client command interface

want to eventually make this so i call it from the command line like:
    wintercom(192.168.1.11,'commandName(opt)')

@author: winter
"""


import socket
import sys

#Testing input options from the commandline

import getopt

def main():
    try:
        opts, args = getopt.getopt(sys.argv[1:], "sh", ["single_cmd","help""])
        print('opts = ',opts)
    except getopt.GetoptError as err:
        # print help information and exit:
        print(err) # will print something like "option -a not recognized"
        #usage()
        sys.exit(2)
    output = None
    verbose = False
    for o, a in opts:
        if o == "-v":
            verbose = True
        elif o in ("-h", "--help"):
            #usage()
            sys.exit()
        elif o in ("-s", "--singleCmd"):
            output = a
        else:
            assert False, "unhandled option"
    # ...

if __name__ == "__main__":
    main()



"""
# create a TCP/IP socket
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# connect the socket ot the port where the server is listening
server_address = ('localhost',7070)
print(f'connecting to {server_address[0]} port {server_address[1]}')
sock.connect(server_address)

# now that the connection is established, data can be sent with sendall() and received with recv()

while True:
    try:
        # send some data
        print("Enter a command:")
        cmd = input()
        
            
    except:
        print('problem with input command')
        print("enter 'quit' to stop client session")
        print("enter 'killserver' to stop command server")

    if cmd.lower() == 'quit':
        sock.close()
        print('stopping the client session')
        sys.exit()
    elif cmd.lower() == 'killserver':
        print('killing the command server')
        sock.sendall(bytes(cmd,"utf-8"))
        print('enter "quit" to end client session')
    else:
        print(f"sending command:'{cmd}'")
        sock.sendall(bytes(cmd,"utf-8"))
        reply = sock.recv(1024).decode("utf-8")
        print(f"received message back from server: '{reply}'")
        
"""