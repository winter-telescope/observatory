#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Feb 13 11:17:32 2020

@author: nlourie
"""

import socket
import json

def query_server(cmd, ipaddr, port,line_ending = '\n', end_char = '', num_chars = 2048, timeout = 0.001,badchars = None):
    """
    This is a utility to send a single command to a remote server,
    then wait a response. It tries to return a dictionary from the returned  
    text.
    """
    
    
    # Connect to the server
    sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    sock.settimeout(timeout)
    server_address = (ipaddr, port)
    sock.connect(server_address)
    
    cmd = cmd + line_ending
    
    # Send a command
    sock.sendall(bytes(cmd,"utf-8"))

    total_data = []
    data = ''
    try:
        while True:
            data = sock.recv(2048).decode("utf-8")
            #print(f'data = {data}')

            if end_char in data:
                total_data.append(data[:data.find(end_char)] + end_char)
                break
            total_data.append(data)
    except socket.timeout as e:
        print(f'server query to {ipaddr} Port {port}: {e}')
        
        """
        if len(total_data)>1:
            # check if the end_of_data_was split
            last_pair = total_data[-2]+total_data[-1]
            if end_char in last_pair:
                total_data[-2] = last_pair[:last_pair.find(end_char)]
                total_data.pop()
                break
        """
    sock.close()
    reply =  ''.join(total_data)
    
    # splice out any nasty characters from the reply string
    if not badchars is None:
        for char in badchars:
            reply = reply.replace(char,'')
    try:
        d = json.loads(reply)
    except Exception as e:
        #print(f'could not turn reply into json, {type(e)}: {e}')
        d = reply
    return d
    
    
    
#%%
try:
    d = query_server('WEATHER_JSON', 
                     '198.202.125.214', 4698, 
                     end_char = '}]',
                     timeout = 1)
    # convert the string to dict using json loads
    
    
    
    d_p200 = d[0]
    d_p60 = d[1]
    d_p48 = d[2]
    
    # try to grab a single element
    print('Grabbing element from dict:')
    elements = ['P48_UTC','P48_Outside_Air_Temp','P48_Wetness','P48_Weather_Status']
    #for element in elements:
    #    print(f'{element} = {d_p48[element]}')
    print()
    print(json.dumps(d_p48,indent = 4))
except:       
        print('could not query telemetry server')

#%%
code = query_server('beginclose','192.168.1.12',9897, end_char = '\n',timeout = 1)

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
    print("ERROR:", code)

#%%

try: 
    d = query_server('status?', 
                     '198.202.125.142', 62000, 
                     end_char = '}',
                     timeout = 1)
                     #badchars = '\\"')
    # convert the string to dict using json loads
    #d = d.replace('\\','')
    print(d)
    #print(json.dumps(d,indent = 4))
    
    
    # try to grab a single element
    print('Grabbing element from dict:')
    elements = ['Shutter_Status']
    for element in elements:
        
        print(f'{element} = {d[element]}')
    
    
except:
    print('could not query command server')

