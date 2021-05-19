#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Feb 13 11:17:32 2020

@author: nlourie
"""

import socket
import json
from datetime import datetime
import time
import yaml

def query_socket(sock, cmd,line_ending = '\n', end_char = '', num_chars = 2048, timeout = 0.001,badchars = None):
    """
    This is a utility to send a single command to a remote server,
    then wait a response. It tries to return a dictionary from the returned  
    text.
    """
    
    
    
    
    cmd = cmd + line_ending
    
    # Send a command
    sock.sendall(bytes(cmd,"utf-8"))

    total_data = []
    data = ''
    try:
        while True:
            data = sock.recv(2048).decode("utf-8")
            if end_char in data:
                total_data.append(data[:data.find(end_char)] + end_char)
                break
            total_data.append(data)
    except socket.timeout as e:
        #print(f'server query: {e}')
        
        """
        if len(total_data)>1:
            # check if the end_of_data_was split
            last_pair = total_data[-2]+total_data[-1]
            if end_char in last_pair:
                total_data[-2] = last_pair[:last_pair.find(end_char)]
                total_data.pop()
                break
        """
    
    reply =  ''.join(total_data)
    
    # splice out any nasty characters from the reply string
    if not badchars is None:
        for char in badchars:
            reply = reply.replace(char,'')
    try:
        #d = json.loads(reply)
        d = yaml.load(reply, Loader = yaml.FullLoader)
    except Exception as e:
        print(f'could not turn reply into json, {type(e)}: {e}')
        d = reply
    return d
    
    
    

#%%
'''
# Connect to the WINTER Command Serverserver
try:
    pcs_sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    pcs_sock.settimeout(0.5)
    server_address = ('198.202.125.142', 62000)
    #server_address = ('localhost', 62000)

    pcs_sock.connect(server_address)
except:
    pass

while True:
    time.sleep(0.5)
    try: 
        d = query_socket(pcs_sock,
                         'status?',
                         end_char = '}',
                         timeout = 2)
                         #badchars = '\\"')

        # convert the string to dict using json loads
        #d = d.replace('\\','')
        #print(d)
        
        print(json.dumps(d,indent = 4))
        
        #time.sleep(0.5)
        # try to grab a single element
        """
        print('Grabbing element from dict:')
        elements = ['Shutter_Status']
        for element in elements:
            
            print(f'{element} = {d[element]}')
        """
    except KeyboardInterrupt:
        break
    
    except Exception as e:
        print(f'could not query command server, error: {e}')
        try:
            pcs_sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
            pcs_sock.settimeout(0.5)
            #server_address = ('198.202.125.142', 62000)
            server_address = ('localhost', 62000)
            pcs_sock.connect(server_address)
        except:
            pass
'''
#%% Connect to the WINTER Command Serverserver

shutter_state_dict = dict({0 : "OPEN",
                           1 : "CLOSED",
                           2 : "OPENING",
                           3 : "CLOSING",
                           4 : "ERROR",
                           5 : "PARTLY_OPEN"})
try:
    pcs_sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    pcs_sock.settimeout(0.5)
    #server_address = ('198.202.125.142', 62000)
    #server_address = ('localhost', 62000)
    server_address = ('192.168.1.12', 9897)
    pcs_sock.connect(server_address)
except:
    pass

while True:
    time.sleep(0.5)
    try: 
        """d = query_socket(pcs_sock,
                         'status?',
                         end_char = '}',
                         timeout = 2)
                         #badchars = '\\"')"""
        d = query_socket(pcs_sock,
                         'shutterstate',
                         end_char = '\n',
                         timeout = 0.25)
                         #badchars = '\\"')
        
        
        
        #print(json.dumps(d,indent = 4))
        
        print(f"Shutter State = {shutter_state_dict[d]}")
        
        #time.sleep(0.5)
        # try to grab a single element
        """
        print('Grabbing element from dict:')
        elements = ['Shutter_Status']
        for element in elements:
            
            print(f'{element} = {d[element]}')
        """
    except KeyboardInterrupt:
        break
    
    except Exception as e:
        print(f'could not query command server, error: {e}')
        try:
            pcs_sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
            pcs_sock.settimeout(0.5)
            #server_address = ('198.202.125.142', 62000)
            server_address = ('localhost', 62000)
            pcs_sock.connect(server_address)
        except:
            pass