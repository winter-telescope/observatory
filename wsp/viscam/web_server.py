#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed May 12 11:14:15 2021

@author: frostig
"""


from flask import Flask
from flask import request
from flask.json import jsonify
import serial # pip install pyserial
import time
app = Flask(__name__)

# https://stackoverflow.com/questions/19277280/preserving-global-state-in-a-flask-application
shutter_state = {}
shutter_state['foo'] = 3

class FilterWheel():
    # initialize
    def __init__(self):
        self.ser = serial.Serial('/dev/serial/by-id/usb-Silicon_Labs_CP2102_USB_to_UART_Bridge_Controller_0001-if00-port0', baudrate=9600)
        #self.ser = serial.Serial('/dev/tty.usbserial-0001', baudrate=9600)
        time.sleep(25)
    
    def filterwheel_command(self, command):
        self.ser.write(command)
        time.sleep(1)
        reply = self.ser.read(self.ser.inWaiting())
        return reply 

try:
    FW = FilterWheel()
except:
    print('Exception: no filter wheel plugged in on start up')


# check raspi/web server responsiveness
@app.route('/check_raspi', endpoint='func1', methods=['GET'])
def check_raspi():
    reply_string = "Raspi is responding"
    return reply_string

# send a command to the filter wheel
@app.route('/filter_wheel', endpoint='func2', methods=['GET'])
def get_filter_command():
    # open serial port
    try:
        #ser = serial.Serial('/dev/serial/by-id/usb-Silicon_Labs_CP2102_USB_to_UART_Bridge_Controller_0001-if00-port0')
        #time.sleep(25)
        # get web request
        n = request.args.get("n")
        n = int(n)
        
        if (n == 1 or n == 2 or n == 3 or n == 4 or n == 5 or n == 6 or n == 7):
            # command
            command = str(n-1) # make string
            command = command.encode() # make bytes
            ret = FW.filterwheel_command(command)
            reply_string = "Set filter wheel position to " + str(n)
        elif (n == 8):
            # command 
            command = b'NOW'
            ret = FW.filterwheel_command(command)
            reply_string = "Current position is " + str(ret)
        elif (n == 9):
            # command 
            command = b'MXP'
            ret = FW.filterwheel_command(command)
            reply_string = "Number of available positions:  " + str(ret)
        elif (n == 10):
            # command 
            command = b'MXP'
            ret = FW.filterwheel_command(command)
            reply_string = "Filter wheel firmware version:  " +  str(ret.decode('ascii')) + "\n Firmware should be version 2. If not, see https://www.qhyccd.com/index.php?m=content&c=index&a=show&catid=68&id=181"
        else:
            reply_string = "Not a valid command"
        
        return reply_string
    except:
        reply_string = "Port could not be opened, try restarting the pi"
        return reply_string, 403


# send a command to the shutter
@app.route('/shutter', endpoint='func3', methods=['GET'])
def get_shutter_command():
    # open serial port
    # see documentation for baudrate
    # https://www.uniblitz.com/wp-content/uploads/2020/10/VED24-User-Manual-1.41_Rev_B12.pdf
    
    try:
        ser = serial.Serial('/dev/serial/by-id/usb-FTDI_MM232R_USB__-__Serial_A146VRZG-if00-port0', baudrate=9600, bytesize=8, parity='N')
    
        n = request.args.get("open")
        n = int(n)
        reply_string = ""
        if (n == 0):
            # command
            ser.write(b'A')
            shutter_state['foo'] = 0
            reply_string = "Close shutter" 
        elif n == 1:
            # command 
            command = str(n) # make string
            command = command.encode() # make bytes
            shutter_state['foo'] = 1
            ser.write(b'@')
            reply_string = "Open shutter"
        else:
            reply_string = "Not a valid command"
        
        return reply_string
    except:
        reply_string = "Port could not be opened"
        return reply_string, 403
    
# send a command to the shutter
@app.route('/shutter_state', endpoint='func4', methods=['GET'])
def get_shutter_state():
    # check shutter state
    #reply_string = str(shutter_state)
    return jsonify(shutter_state['foo'])

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
