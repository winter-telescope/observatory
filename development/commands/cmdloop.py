#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jul 31 10:51:13 2023

@author: nlourie
"""

import cmd as pycmd
import sys
import socket

class WinterCmdSocket(object):
    
    def __init__(self, cmd_server_address = 'localhost', cmd_server_port = 7000):
        
        self.addr = cmd_server_address
        self.port = cmd_server_port
        self.connected = False
        
    def send(self, cmd):
        # now that the connection is established, data can be sent with sendall() and received with recv()
        if self.connected:
            try:
                
                self.sock.sendall(bytes(cmd,"utf-8"))
                reply = self.sock.recv(1024).decode("utf-8")
                print(f"received message back from server: '{reply}'\n")
                
            except socket.error:
                try:
                    self.connect_to_server()
                    self.sock.sendall(bytes(cmd,"utf-8"))
                    reply = self.sock.recv(1024).decode("utf-8")
                    print(f"received message back from server: '{reply}'\n")
                    self.connected = True
                except Exception as e:
                    print(f'error after reconnection attempt: {e}')
                    self.sock.close()
                    print(f"WSP has disconnected. Socket is closed until a manual reconnect. Did not send the command {cmd}")
                    self.connected = False
        else:
            try:
                self.connect_to_server()
                self.sock.sendall(bytes(cmd,"utf-8"))
                reply = self.sock.recv(1024).decode("utf-8")
                print(f"received message back from server: '{reply}'\n")
                self.connected = True
            except Exception as e:
                print(f'error after reconnection attempt: {e}')
                self.sock.close()
                print(f"WSP has disconnected. Socket is closed until a manual reconnect. Did not send the command {cmd}")
                self.connected = False

    def connect_to_server(self):
        try:
            # create a TCP/IP socket
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # connect the socket ot the port where the server is listening
            server_address = (self.addr, self.port)
            self.sock.connect(server_address)
            self.connected = True
        except Exception as e:
            print(f"Could not connect to WSP: {e}")
            self.sock.close()
            self.connected = False


class WinterCmdShell(pycmd.Cmd):
    
    
    def __init__(self, completekey='tab', stdin=None, stdout=None, 
                 verbose = False):
        """Instantiate a line-oriented interpreter framework.

        The optional argument 'completekey' is the readline name of a
        completion key; it defaults to the Tab key. If completekey is
        not None and the readline module is available, command completion
        is done automatically. The optional arguments stdin and stdout
        specify alternate input and output file objects; if not specified,
        sys.stdin and sys.stdout are used.

        """
        if stdin is not None:
            self.stdin = stdin
        else:
            self.stdin = sys.stdin
        if stdout is not None:
            self.stdout = stdout
        else:
            self.stdout = sys.stdout
        self.cmdqueue = []
        self.completekey = completekey
        # NPL from here down:
        self.prompt = 'wintercmd: '
        self.intro = 'Welcome to the interactive wintercmd shell!'
        self.verbose = verbose
        self.wintercmd = WinterCmdSocket()
        
    def start(self):
        self.cmdloop()    
    
    def emptyline(self):
        """Called when an empty line is entered in response to the prompt.
        NPL: just want it to print an empty line
        """
        
        return False
    
    def onecmd(self, cmd):
        # this is from the default definition, just changing it here
        
        if not cmd:
            #print(f'if not cmd is true')
            return self.emptyline()
        if cmd is None:
            #print(f'cmd is None')
            return self.default(cmd)
        
        self.lastcmd = cmd
        #print(f'self.lastcmd = {self.lastcmd}')
        
        if cmd == 'EOF' :
            self.lastcmd = ''
        if cmd == '':
            return self.default(cmd)
        elif cmd.lower() == 'quit':
            return self.quitshell()
        else:
            try:
                #func = getattr(self, 'do_' + cmd) # the default thing from cmd.py
                func = self.sendcmd
            except AttributeError:
                return self.default(cmd)
            return func(cmd)
        
    def sendcmd(self, cmd, verbose = False):
        #print(f'received command: <{cmd}>, passing to wintercmd socket...')
        self.wintercmd.send(cmd)
    
    def quitshell(self):
        print('closing wintercmd shell. bye!')
        return True        
    
wintercmd = WinterCmdShell()

wintercmd.start()

