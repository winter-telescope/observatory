#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jul  1 12:43:35 2020

@author: nlourie
"""

import sys
from PyQt5 import QtCore, QtGui, QtNetwork, QtWidgets


class Messenger(object):
    def __init__(self):
        super(Messenger, self).__init__()
        self.TCP_HOST = "127.0.0.1"  # QtNetwork.QHostAddress.LocalHost
        self.TCP_SEND_TO_PORT = 7012
        self.pSocket = None
        self.listenServer = None
        self.pSocket = QtNetwork.QTcpSocket()
        self.pSocket.readyRead.connect(self.slotReadData)
        self.pSocket.connected.connect(self.on_connected)
        self.pSocket.error.connect(self.on_error)

    def slotSendMessage(self):
        self.pSocket.connectToHost(self.TCP_HOST, self.TCP_SEND_TO_PORT)

    def on_error(self, error):
        if error == QtNetwork.QAbstractSocket.ConnectionRefusedError:
            print(
                'Unable to send data to port: "{}"'.format(
                    self.TCP_SEND_TO_PORT
                )
            )
            print("trying to reconnect")
            QtCore.QTimer.singleShot(1000, self.slotSendMessage)

    def on_connected(self):
        cmd = "Hi there!"
        print("Command Sent:", cmd)
        ucmd = bytes(cmd, "utf-8")
        self.pSocket.write(ucmd)
        self.pSocket.flush()
        self.pSocket.disconnectFromHost()

    def slotReadData(self):
        print("Reading data:", self.pSocket.readAll())
        # QByteArray data = pSocket->readAll();


class Client(QtCore.QObject):
    def SetSocket(self, socket):
        self.socket = socket
        self.socket.connected.connect(self.on_connected)
        self.socket.disconnected.connect(self.on_connected)
        self.socket.readyRead.connect(self.on_readyRead)
        print(
            "Client Connected from IP %s" % self.socket.peerAddress().toString()
        )

    def on_connected(self):
        print("Client Connected Event")

    def on_disconnected(self):
        print("Client Disconnected")

    def on_readyRead(self):
        msg = self.socket.readAll()
        print(type(msg), msg.count())
        print("Client Message:", msg)


class Server(QtCore.QObject):
    def __init__(self, parent=None):
        QtCore.QObject.__init__(self)
        self.TCP_LISTEN_TO_PORT = 7012
        self.server = QtNetwork.QTcpServer()
        self.server.newConnection.connect(self.on_newConnection)

    def on_newConnection(self):
        while self.server.hasPendingConnections():
            print("Incoming Connection...")
            self.client = Client(self)
            self.client.SetSocket(self.server.nextPendingConnection())

    def StartServer(self):
        if self.server.listen(
            QtNetwork.QHostAddress.Any, self.TCP_LISTEN_TO_PORT
        ):
            print(
                "Server is listening on port: {}".format(
                    self.TCP_LISTEN_TO_PORT
                )
            )
        else:
            print("Server couldn't wake up")


class Example(QtWidgets.QMainWindow):
    def __init__(self):
        super(Example, self).__init__()
        self.setWindowTitle("TCP/Server")
        self.resize(300, 300)

        self.uiConnect = QtWidgets.QPushButton("Connect")

        # layout
        self.layout = QtWidgets.QVBoxLayout()
        self.layout.addWidget(self.uiConnect)
        self.widget = QtWidgets.QWidget()
        self.widget.setLayout(self.layout)
        self.setCentralWidget(self.widget)

        # Connections
        self.uiConnect.clicked.connect(self.setup)

    def setup(self):
        self.server = Server()
        self.server.StartServer()

        self.tcp = Messenger()
        self.tcp.slotSendMessage()
        
def main():

    app = QtWidgets.QApplication(sys.argv)
    ex = Example()
    ex.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()