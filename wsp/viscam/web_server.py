#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed May 12 11:14:15 2021

@author: frostig
"""


from flask import Flask
from flask import request
from flask.json import jsonify
import FLI as fli
import serial # pip install pyserial
import time
app = Flask(__name__)

# https://stackoverflow.com/questions/19277280/preserving-global-state-in-a-flask-application
shutter_state = {}
shutter_state['foo'] = 3



try:
    FW = fli.USBFilterWheel.find_devices()[0]
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
        
        if (n == -1 or n == 0 or n == 1 or n == 2 or n == 3 or n == 4 or n == 5 or n == 6):
            # command
            try:
                FW.set_filter_pos(n)
                # if we get here it was successfully completed
                pos = FW.get_filter_pos()
                ret = pos
            except Exception as e:
                print(f'error setting fw pos: {e}')
                pos = -9
            #reply_string = "Set filter wheel position to " + str(n)
            reply_string = str(pos)
        elif (n == 8):
            # command 
            try:
                # if we get here it was successfully completed
                pos = FW.get_filter_pos()
                #reply_string = "Current position is " + str(pos)
                reply_string = str(pos)
            except:
                pos = -9
                #reply_string = "Could not  " + str(ret)
                reply_string = str(pos)
        else:
            #reply_string = "Not a valid command"
            reply_string = str(-10)
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
