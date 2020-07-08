#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Jun 26 15:12:45 2020

This is based on the example from Ch18 of "Rapid GUI Programming with Python and Qt"

@author: nlourie
"""

from PyQt5 import uic, QtCore, QtGui, QtWidgets, QtNetwork
import signal
import sys







class command_client(QtCore.QObject):   
    # The main loop
                  
    def __init__(self, parent=None ):            
        super(command_client, self).__init__(parent)   
    
        # create the server socket
        self.socket = QtNetwork.QTcpSocket()
        
        # hold the request in a method. This will be transmitted to the server.
        self.request = None
        
        ### connect signals to slots ###
        
        # send request when we connect to the server
        self.socket.connected.connect(self.sendRequest)
        
        # read the reply from the server when it has been fully received
        self.socket.readyRead.connect(self.serverHasStopped)
        
        # signal that the server has stopped if we get disconnected
        self.socket.disconnected.connect(self.serverHasStopped)
        
        # when error is caught from server announce it
        self.socket.error.connect(self.serverHasError)
        
    def sendRequest(self):
        pass
    
    def readResponse(self):
        pass
    
    def serverHasStopped(self):
        pass
    
    def serverHasError(self):
        pass
    
    def closeEvent(self,event):
        self.socket.close()
        event.accept()
       
def sigint_handler(*args):
    '''Handler for the SIGINT signal'''
    sys.stderr.write('\r')
    
    QtCore.QCoreApplication.quit()
        
if __name__ == "__main__":
    signal.signal(signal.SIGINT, sigint_handler)
    app = QtCore.QCoreApplication(sys.argv)

    client = command_client()
    #mainthread = main()

    # Run the interpreter every so often to catch SIGINT
    timer = QtCore.QTimer()
    timer.start(500) 
    timer.timeout.connect(lambda: None) 

    sys.exit(app.exec_())
