#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jan 28 10:18:53 2020

command_server.py

This program is part of wsp

# PURPOSE #
A program to make an echo server/client command interface

@author: winter
"""


#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Feb  5 11:31:39 2020

@author: nlourie
"""

import socket 
from threading import Thread 
#from SocketServer import ThreadingMixIn 


# This is a test function to make sure commands are being parsed 
def printphrase(phrase = 'default phrase'):
    printed_phrase = f"I'm Printing the Phrase: {phrase}"
    print(printed_phrase)
    return printed_phrase

def start_commandServer(addr = '', port = 7075):
    # Multithreaded Python server : TCP Server Socket Thread Pool
    class ClientThread(Thread): 
     
        def __init__(self,ip,port): 
            Thread.__init__(self,daemon = True)  #without the daemon thing it keeps going forever even when closed!
            self.ip = ip 
            self.port = port 
            print ("[+] New server socket thread started for " + ip + ":" + str(port) )
    
        def run(self): 
            try:
                while True : 
                    cmd = conn.recv(2048) 
                    cmd_txt = cmd.decode('utf-8')
                    print(f'received from client at {self.ip}: {cmd.decode("utf-8")}')
                    #MESSAGE = input("Multithreaded Python server : Enter Response from Server/Enter exit:")
                    #if MESSAGE == 'exit':
                    #    break
                    if cmd_txt == 'killserver':
                        print("I'm in the killserver section")
                        tcpServer.close()
                        break
                    elif cmd_txt == 'quit':
                        # the client is closing. just leave this loop
                        break
                    else:
                        #conn.send(bytes('received: '+cmd_txt,"utf-8"))  # echo 
                        try:
                            # try to evaluate the command
                            result = eval(cmd_txt)
                            print(result)
                            reply = f'\n\tcommand [{cmd_txt}] executed\n\tresult = [{result}]'
                            conn.send(bytes(reply,"utf-8"))
                        except:
                            reply = f'\n\tcommand [{cmd_txt}] not executed properly: \n\tenter "quit" to stop client session or "killserver" to stop command server'
                            conn.send(bytes(reply,"utf-8"))

            except:
                pass
    
    # Multithreaded Python server : TCP Server Socket Program Stub
    #BUFFER_SIZE = 1024  # 20 Usually 1024, but we need quick response 
    
    tcpServer = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
    tcpServer.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) 
    tcpServer.bind((addr, port)) 
    
    threads = [] 
    conns = []
    try: 
        while True: 
            tcpServer.listen(5) 
            print ("Multithreaded Python server : Waiting for connections from TCP clients..." )
            (conn, (ip,port)) = tcpServer.accept() 
            conns.append(conn)
            newthread = ClientThread(ip,port) 
            newthread.start() 
            threads.append(newthread) 
    #        if newthread.keepgoing == False:
    #            break
            #print('Threads: ', threads)
    except KeyboardInterrupt:
        for conn_instance in conns:
            conn_instance.close()
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
    
    start_commandServer(addr = addr, port = port)