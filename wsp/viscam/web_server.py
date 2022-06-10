#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed May 12 11:14:15 2021

@author: frostig
"""

import json
from flask import Flask
from flask import request
from flask.json import jsonify
from datetime import datetime
import FLI as fli
import serial # pip install pyserial
import time
app = Flask(__name__)

# https://stackoverflow.com/questions/19277280/preserving-global-state-in-a-flask-application
#shutter_state = {}
#shutter_state['foo'] = 3
app.logger.info('starrting up the app')
STATE={}
"""
FW = None
SHUTTER_SER = None

# init the shutter
STATE.update({'shutter_open' : -1})             # init to unknown
STATE.update({'shutter_status' : 0})            # init to not connected
STATE.update({'shutter_response_code' : 0})     # init to okay

# init the hardware
try:
    FW = fli.USBFilterWheel.find_devices()[0]
except:
    print('Exception: no filter wheel plugged in on start up')

try:
    SHUTTER_SER = serial.Serial('/dev/serial/by-id/usb-FTDI_MM232R_USB__-__Serial_A146VRZG-if00-port0', baudrate=9600, bytesize=8, parity='N')
except:
    print('could not connect to shutter')
"""
"""
@app.route('/reconnect_fw')
def reconnect_fw():
    try:
        FW = fli.USBFilterWheel.find_devices()[0]
        FW.set_position(-1)
        time.sleep(1)
        pos = FW.get_position()
        fw_status = 1
        fw_response_code = 0
        app.logger.info("successfully connected to filter wheel!")
    except:
        fw_status = 0
        pos = -9
        fw_response_code = -4
        
    STATE.update({'fw_pos' : pos})                   # init to unknown
    STATE.update({'fw_status' : fw_status})                 # init to not conn
    STATE.update({'fw_response_code' : fw_response_code})          # init to okay
    reply_string = json.dumps(STATE)
    return reply_string
    
@app.route('/reconnect_shutter')
def reconnect_shutter():
    try:
        SHUTTER_SER = serial.Serial('/dev/serial/by-id/usb-FTDI_MM232R_USB__-__Serial_A146VRZG-if00-port0', baudrate=9600, bytesize=8, parity='N')
        
        SHUTTER_SER.isOpen() # try to open port
        shutter_open = -1
        shutter_status = 1
        shutter_response_code = 0
        shutter_error = None
    except Exception as e:
        shutter_error = e
        shutter_open = -1
        shutter_status = 0
        shutter_response_code = -4
    STATE.update({'shutter_state' : shutter_open})
    STATE.update({'shutter_status' : shutter_status})
    STATE.update({'shutter_resonse_code' : shutter_response_code})
    STATE.update({'shutter_error ' : shutter_error })
    reply_string = json.dumps(STATE)
    return reply_string
# check raspi/web server responsiveness
@app.route('/check_raspi', endpoint='func1', methods=['GET'])
def check_raspi():
    reply_string = "Raspi is responding"
    return reply_string
"""
# send a command to the filter wheel
@app.route('/filter_wheel', endpoint='func2', methods=['GET'])
def get_filter_command():
    '''
    # Response code:
        0  : command succeeds
        -1 : command is unknown
        -2 : parameter is bad
        -3 : command cannot be executed at the current time
        -4 : could not communicate with device
    '''      
    try:
        # try to connect to FW
        FW = fli.USBFilterWheel.find_devices()[0]
        #time.sleep(25)
        # get web request
        n = request.args.get("n")
        n = int(n)
        
        if (n == -1 or n == 0 or n == 1 or n == 2 or n == 3 or n == 4 or n == 5 or n == 6):
            # command
            try:
                FW.set_filter_pos(n)
                # if we get here it was successfully completed
                fw_pos = FW.get_filter_pos()
                
                fw_status = 1
                fw_response_code = 0
                
            except Exception as e:
                print(f'error setting fw pos: {e}')
                fw_pos = -9
                fw_status = 0
                fw_response_code = -3
                
            STATE.update({'fw_pos' : fw_pos})
            STATE.update({'fw_status' : fw_status})
            STATE.update({'fw_response_code' : fw_response_code})
                
            #reply_string = "Set filter wheel position to " + str(n)
            #reply_string = str(pos)
            reply_string = json.dumps(STATE)
            
        elif (n == 8):
            # command 
            try:
                # if we get here it was successfully completed
                fw_pos = FW.get_filter_pos()
                #reply_string = "Current position is " + str(pos)
                #reply_string = str(pos)
                fw_response_code = 0
            except:
                pos = -9
                fw_response_code = -3
                #reply_string = "Could not  " + str(ret)
                #reply_string = str(pos)
            STATE.update({'fw_pos' : fw_pos})
            STATE.update({'fw_status' : fw_status})
            STATE.update({'fw_response_code' : fw_response_code})
            
        else:
            # not a valid command
            fw_response_code = -2
            #reply_string = "Not a valid command"
            reply_string = str(-10)
            STATE.update({'fw_pos' : pos})
            STATE.update({'fw_status' : fw_status})
            STATE.update({'fw_response_code' : fw_response_code})
            reply_string = json.dumps(STATE)    
        return reply_string
    except:
        fw_response_code = -4
        fw_status = 0
        fw_pos = -9
        
        # update the state        
        STATE.update({'fw_pos' : fw_pos})
        STATE.update({'fw_status' : fw_status})
        STATE.update({'fw_response_code' : fw_response_code})
        
        #reply_string = "Port could not be opened, try restarting the pi"
        reply_string = json.dumps(STATE)
        return reply_string, 403


# send a command to the shutter
@app.route('/shutter', endpoint='func3', methods=['GET'])
def get_shutter_command():
    # open serial port
    # see documentation for baudrate
    # https://www.uniblitz.com/wp-content/uploads/2020/10/VED24-User-Manual-1.41_Rev_B12.pdf
    shutter_cmd_recv_timestamp = datetime.utcnow().timestamp()
    try:
        SHUTTER_SER = serial.Serial('/dev/serial/by-id/usb-FTDI_MM232R_USB__-__Serial_A146VRZG-if00-port0', baudrate=9600, bytesize=8, parity='N')
    
        n = request.args.get("open")
        n = int(n)
        reply_string = ""
        if (n == 0):
            # CLOSE SHUTTER
            # send command
            SHUTTER_SER.write(b'A')
            #shutter_state['foo'] = 0
            shutter_open = 0
            shutter_status = 1
            shutter_response_code = 0
            shutter_last_close_timestamp = datetime.utcnow().timestamp()
            shutter_cmd_latency = shutter_last_close_timestamp - shutter_cmd_recv_timestamp
            #reply_string = "Close shutter" 
        elif n == 1:
            # OPEN SHUTTER
            # send command 
            command = str(n) # make string
            command = command.encode() # make bytes
            #shutter_state['foo'] = 1
            #shutter_state = 1
            
            SHUTTER_SER.write(b'@')
            shutter_open = 1
            shutter_status = 1
            shutter_response_code = 0
            shutter_last_open_timestamp = datetime.utcnow().timestamp()
            shutter_cmd_latency = shutter_last_open_timestamp - shutter_cmd_recv_timestamp
            
            #reply_string = "Open shutter"
        else:
            #reply_string = "Not a valid command"
            shutter_response_code = -1
        
        shutter_status = 1
        STATE.update({'shutter_state' : shutter_open})
        STATE.update({'shutter_status' : shutter_status})
        STATE.update({'shutter_response_code' : shutter_response_code})
        reply_string = json.dumps(STATE)
        return reply_string
        
    except:
        # Port could not be opened
        #reply_string = "Port could not be opened"
        shutter_open = -1
        shutter_status = 0
        shutter_response_code = -4
        STATE.update({'shutter_state' : shutter_open})
        STATE.update({'shutter_status' : shutter_status})
        STATE.update({'shutter_response_code' : shutter_response_code})
        reply_string = json.dumps(STATE)
        return reply_string, 403



"""    
# send a command to the shutter
@app.route('/shutter_state', endpoint='func4', methods=['GET'])
def get_shutter_state():
    # check shutter state
    #reply_string = str(shutter_state)
    return jsonify(shutter_state['foo'])
"""
if __name__ == '__main__':
    #reconnect_fw()
    #time.sleep(5)
    #reconnect_shutter()
    app.run(host='0.0.0.0', port=5001, debug=True)
