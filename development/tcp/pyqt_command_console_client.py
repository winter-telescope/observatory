#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jul  2 10:40:48 2020

pyqt command console client


@author: nlourie
"""

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