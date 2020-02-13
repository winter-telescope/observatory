#!/usr/bin/python

import sys
from socket import *
from time import sleep

# Configure server
thisHost = ''
listenPort = 9999
bufsize = 1024
tcpServerSock = socket(AF_INET, SOCK_STREAM)
tcpServerSock.setsockopt(SOL_SOCKET, SO_REUSEADDR,1)
tcpServerSock.bind((thisHost, listenPort))
tcpServerSock.listen(10)

# To echo message back to client
echo = 1

# Server instructions
while True:
    conn, address = tcpServerSock.accept()
    #print("accepted client")
    msg = conn.recv(bufsize).strip()
    if len(msg) == 0 :
        conn.close()
        continue

    print(msg)

    if echo:
        conn.send(msg)
    conn.close()

