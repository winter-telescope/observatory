#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Jun 13 01:42:46 2021

@author: frostig
"""




import socket
import io
from datetime import datetime

class MirrorCovers:

    # initialize
    def __init__(self, addr, port, config, logger):
        self.state = dict()
        self.addr = addr
        self.port = port
        self.config = config
        self.logger = logger
        
    def open_mirror_cover_socket(self, addr, port):
        self.log.info(f'Connecting to PWShutter TCP server at address {addr} and port {port}')
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(0.5)
        self.sock.connect((addr, port))
            
    def update_state(self):
        
        (code, text) = self.sendreceive("isconnected")
        if (code == 0 or code == 1):  
            self.state.update({'mirror_cover_connected' : int(not(code))})
            self.state.update({'mirror_cover_connected_last_timestamp'  : datetime.utcnow().timestamp()})
        elif code == 255:
            self.state.update({'mirror_cover_connected' : code})
            self.log.info(f'Error while connecting to mirror cover, code {code} ')
            self.state.update({'mirror_cover_connected_last_timestamp'  : datetime.utcnow().timestamp()})    
        
        (code, text) = self.sendreceive( "shutterstate")
        if (code == 0 or code == 1 or code == 2 or code == 3 or code == 4 or code == 5 or code == 255):  
            self.state.update({'mirror_cover_state' : code})
            self.state.update({'mirror_cover_state_last_timestamp'  : datetime.utcnow().timestamp()})
        

    def readline(self):
        """
        Utility function for reading from a socket until a
        newline character is found
        """
        buf = io.StringIO()
        while True:
            data = self.sock.recv(1).decode("utf-8")
            buf.write(data)
            if data == '\n':
                return buf.getvalue()
            
    
    def sendreceive(self, command):
        """
        Send a command to the server, and read the response.
        The response will be split into an integer error code and an optional error text messsage.
        Returns a tuple (code, error_text)
        """
        self.sock.send(bytes(command + "\n","utf-8"))
        response = self.readline(self.sock)
        # The response should consist of a numeric code, optionally
        # followed by some text if the code is 255 (error). Parse this out.
        fields = response.split(" ")
        response_code = int(fields[0])
        error_text = ""
        if len(fields) > 1:
            error_text = fields[1]
        return (response_code, error_text)
