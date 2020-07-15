#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Feb 13 11:17:32 2020

@author: nlourie
"""

import socket
import json

# Connect to the server
sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
server_address = ('198.202.125.214',4698)
sock.connect(server_address)

# Send a command
cmd = 'WEATHER_JSON\n'
sock.sendall(bytes(cmd,"utf-8"))
#reply = sock.recv(2048).decode("utf-8")
#print(reply)

end = '}]'

def recv_end(socket, end_char, num = 2048):
    total_data = []
    data = ''
    while True:
        data = socket.recv(2048).decode("utf-8")
        if end_char in data:
            total_data.append(data[:data.find(end_char)] + end_char)
            break
        total_data.append(data)
        """
        if len(total_data)>1:
            # check if the end_of_data_was split
            last_pair = total_data[-2]+total_data[-1]
            if end_char in last_pair:
                total_data[-2] = last_pair[:last_pair.find(end_char)]
                total_data.pop()
                break
        """
    return ''.join(total_data)

reply = recv_end(sock, end_char = '}]', num = 2048)
#print(reply)
# Close the connection
sock.close()


# convert the string to dict using json loads

d = json.loads(reply)
print(json.dumps(d,indent = 4))

d_p200 = d[0]
d_p60 = d[1]
d_p48 = d[2]

# try to grab a single element
print('Grabbing element from dict:')
element = 'P48_Outside_DewPt'
print(f'{element} = {d_p48[element]}')