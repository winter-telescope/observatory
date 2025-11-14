#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed May 12 11:14:15 2021

@author: frostig
"""

import json
import time
from datetime import datetime

import FLI as fli
import serial  # pip install pyserial
from flask import Flask, request
from flask.json import jsonify

app = Flask(__name__)

app.logger.info("starting up the app")

# Initialize STATE with default values
STATE = {
    "fw_pos": -1,
    "fw_status": 0,
    "fw_response_code": 0,
    "shutter_open": -1,
    "shutter_status": 0,
    "shutter_response_code": 0,
}


# send a command to the filter wheel
@app.route("/filter_wheel", endpoint="func2", methods=["GET"])
def get_filter_command():
    """
    # Response code:
        0  : command succeeds
        -1 : command is unknown
        -2 : parameter is bad
        -3 : command cannot be executed at the current time
        -4 : could not communicate with device
    """
    try:
        # get web request
        n = request.args.get("n")
        n = int(n)

        if n == 8:
            # command to get current position - just return cached STATE
            reply_string = json.dumps(STATE)
            return reply_string

        # try to connect to FW for all other commands
        FW = fli.USBFilterWheel.find_devices()[0]

        if (
            n == -1
            or n == 0
            or n == 1
            or n == 2
            or n == 3
            or n == 4
            or n == 5
            or n == 6
        ):
            # command to move filter wheel
            try:
                FW.set_filter_pos(n)
                # if we get here it was successfully completed
                fw_pos = FW.get_filter_pos()

                fw_status = 1
                fw_response_code = 0

            except Exception as e:
                print(f"error setting fw pos: {e}")
                fw_pos = -9
                fw_status = 0
                fw_response_code = -3

            STATE.update({"fw_pos": fw_pos})
            STATE.update({"fw_status": fw_status})
            STATE.update({"fw_response_code": fw_response_code})

            reply_string = json.dumps(STATE)

        else:
            # not a valid command
            fw_response_code = -2
            fw_status = 0
            fw_pos = -9

            STATE.update({"fw_pos": fw_pos})
            STATE.update({"fw_status": fw_status})
            STATE.update({"fw_response_code": fw_response_code})
            reply_string = json.dumps(STATE)

        return reply_string

    except Exception as e:
        print(f"error communicating with filter wheel: {e}")
        fw_response_code = -4
        fw_status = 0
        fw_pos = -9

        # update the state
        STATE.update({"fw_pos": fw_pos})
        STATE.update({"fw_status": fw_status})
        STATE.update({"fw_response_code": fw_response_code})

        reply_string = json.dumps(STATE)
        return reply_string, 403


# send a command to the shutter
@app.route("/shutter", endpoint="func3", methods=["GET"])
def get_shutter_command():
    # open serial port
    # see documentation for baudrate
    # https://www.uniblitz.com/wp-content/uploads/2020/10/VED24-User-Manual-1.41_Rev_B12.pdf
    shutter_cmd_recv_timestamp = datetime.utcnow().timestamp()
    try:
        SHUTTER_SER = serial.Serial(
            "/dev/serial/by-id/usb-FTDI_MM232R_USB__-__Serial_A146VRZG-if00-port0",
            baudrate=9600,
            bytesize=8,
            parity="N",
        )

        n = request.args.get("open")
        n = int(n)

        if n == 0:
            # CLOSE SHUTTER
            # send command
            SHUTTER_SER.write(b"A")
            shutter_open = 0
            shutter_status = 1
            shutter_response_code = 0
            shutter_last_close_timestamp = datetime.utcnow().timestamp()
            shutter_cmd_latency = (
                shutter_last_close_timestamp - shutter_cmd_recv_timestamp
            )

        elif n == 1:
            # OPEN SHUTTER
            # send command
            SHUTTER_SER.write(b"@")
            shutter_open = 1
            shutter_status = 1
            shutter_response_code = 0
            shutter_last_open_timestamp = datetime.utcnow().timestamp()
            shutter_cmd_latency = (
                shutter_last_open_timestamp - shutter_cmd_recv_timestamp
            )

        else:
            # Invalid command
            shutter_open = -1
            shutter_status = 0
            shutter_response_code = -1

        STATE.update({"shutter_open": shutter_open})
        STATE.update({"shutter_status": shutter_status})
        STATE.update({"shutter_response_code": shutter_response_code})
        reply_string = json.dumps(STATE)
        return reply_string

    except Exception as e:
        print(f"error communicating with shutter: {e}")
        # Port could not be opened
        shutter_open = -1
        shutter_status = 0
        shutter_response_code = -4
        STATE.update({"shutter_open": shutter_open})
        STATE.update({"shutter_status": shutter_status})
        STATE.update({"shutter_response_code": shutter_response_code})
        reply_string = json.dumps(STATE)
        return reply_string, 403


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
