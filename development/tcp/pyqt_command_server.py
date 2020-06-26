#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jun 24 17:34:09 2020

pyqt_command_server.py

This is a test script to make a threaded command server built on PyQt

The idea is that every new connection starts a new thread to listen for input
from the client. Then each new received command triggers a "new_command"
event which signals the command to be exectuted by a threadpool (QRunnable)
worker thread in the main loop.


@author: nlourie
"""

from PyQt5 import uic, QtCore, QtGui, QtWidgets
import socket
import sys
import os
import time
import traceback
import signal
import time

class WorkerSignals(QtCore.QObject):
    '''
    Defines the signals available from a running worker thread.

    In this example we've defined 5 custom signals:
        finished signal, with no data to indicate when the task is complete.
        error signal which receives a tuple of Exception type, Exception value and formatted traceback.
        result signal receiving any object type from the executed function.
    
    Supported signals are:

    finished
        No data
    
    error
        `tuple` (exctype, value, traceback.format_exc() )
    
    result
        `object` data returned from processing, anything

    progress
        `int` indicating % progress 
    '''
    finished = QtCore.pyqtSignal()
    error    = QtCore.pyqtSignal(tuple)
    result   = QtCore.pyqtSignal(object)
    progress = QtCore.pyqtSignal(int)


class Worker(QtCore.QRunnable):
    '''
    Worker thread

    Inherits from QRunnable to handler worker thread setup, signals and wrap-up.

    :param callback: The function callback to run on this worker thread. Supplied args and 
                     kwargs will be passed through to the runner.
    :type callback: function
    :param args: Arguments to pass to the callback function
    :param kwargs: Keywords to pass to the callback function

    '''

    def __init__(self, fn, *args, **kwargs): # Now the init takes any function and its args
        #super(Worker, self).__init__() # <-- this is what the tutorial suggest
        super().__init__() # <-- This seems to work the same. Not sure what the difference is???
        # Store constructor arguments (re-used for processing)
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        
        # This is a new bit: subclass an instance of the WorkerSignals class:
        self.signals = WorkerSignals()
        
        # A new bit since ex7: Add the callback to our kwargs
        self.kwargs['progress_callback'] = self.signals.progress 
        
        

    @QtCore.pyqtSlot()
    def run(self):
        '''
        Initialise the runner function with passed args, kwargs.
        
        Did some new stuff here since ex6.
        Now it returns an exception if the try/except doesn't work
        by emitting the instances of the self.signals QObject
        
        '''

        # Retrieve args/kwargs here; and fire processing using them
        try:
            result = self.fn(
                *self.args, **self.kwargs
            )
        except:
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.signals.error.emit((exctype, value, traceback.format_exc()))
        else:
            self.signals.result.emit(result)  # Return the result of the processing
        finally:
            self.signals.finished.emit()  # Done

class command_client(object):
    
    def __init__(self, socket, addr, port, thread):
        """
        This is a simple class that contains the information about 
        clients that have connected to the command server. Its main purpose
        is to pass client address information between threads
        
        Parameters
        ----------
        socket : socket.socket object
            this is the client socket object
        addr : string
            name of the client ip address, ie '192.168.1.15', or 'localhost', etc..
        port: int
            client connection port number
        thread: 
            the PyQt5.QtCore.QThread instance of the command thread class
            where the server/client communications are ocurring
        name: string
            a name assigned to this object. it is a string of the address 
            and port. if this doesn't work I might need to replace this with
            a random unique identifier. this is used as the key in the client
            list dictionary'
        Returns
        -------
        None.
        
        """
        self.socket = socket
        self.addr = addr 
        self.port = port
        self.name = str(addr) + '_' + str(port)
        self.thread = thread 

class command_thread(QtCore.QThread):
    
    # define some custom signals
    new_client_conn = QtCore.pyqtSignal(object)  
    testSignal = QtCore.pyqtSignal(int)
    
    def __init__(self, server_socket):
        QtCore.QThread.__init__(self)
        
        # start a counter to watch loop execution
        self.index = 0
        
        self.timer = QtCore.QTimer()
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.listen_for_connection)
        self.timer.start()
    
        """
        Command Thread
        
        Inherets from QThread. Each new received connection from a client to the
        server instatiates a new command thread. This thread sits and waits
        patiently for commands to be received. Each received thread triggers a
        new_connection event which passes the command to the main thread.
        
        """
        self.index = 0
        # get the thread ID?
        self.thread = self.currentThread()
        print(f'commandThread: thread ID = {self.thread}')
        
        # subclass the server stuff
        self.server_socket = server_socket
        
        
        # sit and wait for a client connection
        #self.listen_for_connection()
        
    def count(self):
        #print(f'commandThread: index = {self.index}')
        self.index += 1
        print(f'commandThread: emitting test signal {self.index}')
        self.testSignal.emit(self.index)
        
    def listen_for_connection(self):
        
        
        # sit and wait for incoming connection: THIS BLOCKS THE THREAD
        print('commandThread: waiting for new incoming connection...')
        self.index += 1
        print(f'commandThread: emitting test signal {self.index}')
        self.testSignal.emit(self.index)
        # listen for incoming connections
        self.server_socket.listen(5)
        self.client_socket, self.client_addr_port = self.server_socket.accept()
        self.client_addr = self.client_addr_port[0]
        self.client_port = self.client_addr_port[1]
        
        print(f'commandThread: [+] new connection from {self.client_addr} | port {self.client_port}')
        
        # store the client information in a new command client object
        new_client = command_client(self.client_socket, self.client_addr, self.client_port, self.thread)
        print(f'commandThread: signaling new conn from client: {new_client.name}')
        # if we get passed the socket.accept() line, it means we have a new connection!
        self.new_client_conn.emit(new_client)
        
        
    def __del__(self):
        self.wait()
    
    

class main(QtCore.QObject):   

                  
    def __init__(self, parent=None ):            
        super(main, self).__init__(parent)   
        
        # start a counter to watch loop execution
        self.index = 0
        
        self.timer = QtCore.QTimer()
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.count)
        self.timer.start()
        
        
        
        
        # start up the command server
        self.start_command_server('localhost',8454)
        
        # create initial command thread
        print(f'main: initing new command thread')
        self.new_comm_thread = command_thread(server_socket = self.server_socket)
        #self.new_comm_thread = command_thread(server_socket = '')
        # connect the signals
        self.new_comm_thread.new_client_conn.connect(self.new_client_detected)
        self.new_comm_thread.testSignal.connect(self.caught_signal)
        
        
        
        
    def caught_signal(self,number):
        print(f'main: caught signal {number}') 
    
    def start_command_server(self,addr, port):
        """
        creates a TCP/IP socket for the command server, and instantiates
        a command_thread object to wait for connections to the server in a new
        thread
        """
        self.server_addr = addr
        self.server_port = port
        
        print(f'main: creating new socket at {self.server_addr} | port {self.server_port}')
        
        # create the socket
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) 
        
        # bind socket to address
        self.server_socket.bind((self.server_addr, self.server_port))
        
        # create a dictionary of connections
        '''
        this is a nested dictionary. it keeps track of both the client socket
        information (used to gently close the socket) and the thread information
        (used to gently terminate the thread)
        
        each entry is a key:value pair of client information and thread info
        
            'clientIP_clientPORT':
                client: client_object
                thread: command_thread_object
        '''
        self.server_clients = dict()
        
        # create initial command thread to wait for connections
        
        #self.create_command_thread()
        print(f'main: finshed initing server socket')
        
    def create_command_thread(self):
        """
        This function instatiates a new command thread to listen for connections
        to the command server. 
        """
        # create a new command thread
        print(f'main: initing new command thread')
        self.new_comm_thread = command_thread(server_socket = self.server_socket)
        
    def count(self):
        self.index += 1
        print(f'main: index = {self.index}')
     
    def add_client_to_dict(self,command_client):
        """
        Any time a new connection is detected (ie any time the new_client_conn
        signal is caught), add the client to the connection list.
        
        When a connection is detected it adds the thread
        to the list of active clients. This active client list is held in 
        self.server_clients, which holds a key:value pair of
            key =  client.name (ie, 'clientaddr_clientport')
            value = client (the instance of the client object)
        
        this dictionary is useful to check in on what/how many clients are
        connected at any time, and can be used to close connections, 
        stop command threads, etc.
        """
        print(f'main: adding new client [{command_client.name}] to client list')
        
        # add the connection to the list of current clients
        self.server_clients.update({command_client.name : command_client})
        
    def new_client_detected(self,command_client):
        """
        Description:
            this function is a slot which is connected to the command_thread
            "new_client_conn" signal. When this signal is emitted, it signals 
            the detection of a new client. When this happens this function 
            then executes the following:
                1. add the detected client to the client list
                2. instatiate a new command thread to listen for 
                    any new connections

        Parameters
        ----------
        command_client : command client object
            the command client of the most recently detected connection.

        """
        print(f'main: caught new client connected signal from client at {command_client.addr} | port {command_client.port}')
        
        # add the client to the list
        self.add_client_to_dict(command_client)
        
        # start up a new thread to listen for connections
        self.create_command_thread()
        
        
def sigint_handler(*args):
    """Handler for the SIGINT signal."""
    sys.stderr.write('\r')
    
    QtCore.QCoreApplication.quit()

if __name__ == "__main__":
    signal.signal(signal.SIGINT, sigint_handler)
    app = QtCore.QCoreApplication(sys.argv)

    
    mainthread = main()

    # Run the interpreter every so often to catch SIGINT
    timer = QtCore.QTimer()
    timer.start(500) 
    timer.timeout.connect(lambda: None) 

    sys.exit(app.exec_())
