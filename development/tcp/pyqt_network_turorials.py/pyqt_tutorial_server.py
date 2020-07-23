#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Jun 26 14:49:46 2020

This is based on the example from Ch18 of "Rapid GUI Programming with Python and Qt"

@author: nlourie
"""

from PyQt5 import uic, QtCore, QtGui, QtWidgets, QtNetwork
import signal
import sys


class Server(QtNetwork.QTcpServer):
    def __init__(self, parent=None):
        super(Server, self).__init__(parent)

        

    def incomingConnection(self, socketDescriptor):
        print('server: incoming connection detected')
        
        reply = 'welcome to the server!'
        
        try:
            # Python v3.
            reply = bytes(reply, encoding='utf-8')
        except:
            # Python v2.
            pass

        thread = Thread(socketDescriptor, reply, self)
        thread.finished.connect(thread.deleteLater)
        thread.start()


class Thread(QtCore.QThread):
    error = QtCore.pyqtSignal(QtNetwork.QTcpSocket.SocketError)

    def __init__(self, socketDescriptor, fortune, parent):
        super(Thread, self).__init__(parent)

        self.socketDescriptor = socketDescriptor
        self.text = fortune

    def run(self):
        tcpSocket = QtNetwork.QTcpSocket()
        tcpSocket.BindFlag(QtNetwork.QAbstractSocket.ReuseAddressHint)
        if not tcpSocket.setSocketDescriptor(self.socketDescriptor):
            self.error.emit(tcpSocket.error())
            return

        block = QtCore.QByteArray()
        outstr = QtCore.QDataStream(block, QtCore.QIODevice.WriteOnly)
        outstr.setVersion(QtCore.QDataStream.Qt_4_0)
        outstr.writeUInt16(0)
        outstr.writeString(self.text)
        outstr.device().seek(0)
        outstr.writeUInt16(block.count() - 2)

        tcpSocket.write(block)
        tcpSocket.disconnectFromHost()
        tcpSocket.waitForDisconnected()
            

class main(QtCore.QObject):   
    # The main loop
                  
    def __init__(self, parent=None ):            
        super(main, self).__init__(parent)   
        self.addr = 'localhost'
        self.port = 9999
        self.server = Server()
        if not self.server.listen(QtNetwork.QHostAddress(self.addr), self.port):
            print(f"Failed to start server: {self.server.errorString()}")
            self.quit()
            return
        
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
