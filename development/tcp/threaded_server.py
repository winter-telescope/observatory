#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Feb  5 11:31:39 2020

@author: nlourie
"""

import socket 
from threading import Thread 
#from SocketServer import ThreadingMixIn 

def startServer(addr = '', port = 7075):
    # Multithreaded Python server : TCP Server Socket Thread Pool
    class ClientThread(Thread): 
     
        def __init__(self,ip,port): 
            Thread.__init__(self,daemon = True)  #without the daemon thing it keeps going forever even when closed!
            self.ip = ip 
            self.port = port 
            print ("[+] New server socket thread started for " + ip + ":" + str(port) )
    
        def run(self): 
    
            while True : 
                data = conn.recv(2048) 
                print('raw data = ',data)
                print ("Server received data:", data.decode('utf-8'))
                #MESSAGE = input("Multithreaded Python server : Enter Response from Server/Enter exit:")
                #if MESSAGE == 'exit':
                #    break
                if data.decode('utf-8').lower() == 'killserver':
                    print("I'm in the killserver section")
                    tcpServer.close()
                    break
                elif data.decode('utf-8').lower() == 'quit':
                    # the client is closing. just leave this loop
                    break
                else:
                    conn.send(bytes('received: '+data.decode('utf-8'),"utf-8"))  # echo 
    
                
    
    # Multithreaded Python server : TCP Server Socket Program Stub
    #BUFFER_SIZE = 1024  # 20 Usually 1024, but we need quick response 
    
    tcpServer = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
    tcpServer.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) 
    tcpServer.bind((addr, port)) 
    
    threads = [] 
    try: 
        while True: 
            tcpServer.listen(5) 
            print ("Multithreaded Python server : Waiting for connections from TCP clients..." )
            (conn, (ip,port)) = tcpServer.accept() 
            newthread = ClientThread(ip,port) 
            newthread.start() 
            threads.append(newthread) 
    #        if newthread.keepgoing == False:
    #            break
            #print('Threads: ', threads)
    except KeyboardInterrupt:
        tcpServer.close()
    except socket.error as msg:
        print("Socket Closed")
        #tcpServer.close()
        pass
        
    for t in threads: 
        t.join() 
        
if __name__ == '__main__':
    addr = ''
    port = 7075
    
    startServer(addr = addr, port = port)