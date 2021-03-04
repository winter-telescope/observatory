#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Feb 22 13:28:21 2021

EZ Stepper Test Script

@author: nlourie
"""

import serial
import time
from datetime import datetime
import numpy as np
import codecs

class EZstepper(object):
    def __init__(self,port, addr):
        
        # serial port, eg: '/dev/ttyUSB0'
        self.port = port
        
        # ez stepper device addresss, eg: 1
        self.addr = addr
        
        # set up the state dictionary
        self.state = dict()
        
        ### define some characteristics ###
        # the start sequence on a reply is "/0". define the sequence as a list of hex bytes
        self.reply_start_sequence_str = ['/','0']
        self.reply_start_sequence = [codecs.encode(bytes(bytestr,"utf-8"),"hex").decode("utf-8") for bytestr in self.reply_start_sequence_str]
        self.reply_end_sequence_str = ['\x03'] # ASCII ETX (end of text) Character
        self.reply_end_sequence = [codecs.encode(bytes(bytestr,"utf-8"),"hex").decode("utf-8") for bytestr in self.reply_end_sequence_str]

        
        # status bytes: 
    def setupSerial(self, *args, **kwargs):
        # set up the serial port using pyserial "serial" library
        # this can take and pass in any pyserial args
        
        self.ser = serial.Serial(port=self.port,
                baudrate=9600,
                timeout = 1,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                bytesize=serial.EIGHTBITS,
                *args,
                **kwargs
            )
    
    def send(self, cmd, parsed = True, verbose = False):
        self.ser.flushInput()
        self.ser.write(bytes(f"/{self.addr}{cmd}\r", 'utf-8'))
        
        
        
    def sendAndRead(self, cmd, parsed = True, verbose = False):
        self.ser.flushInput()
        cmd_text = f"/{self.addr}{cmd}\r"
        if verbose:
            print(f'Sending Command: {cmd_text}')
        self.ser.write(bytes(cmd_text, 'utf-8'))
        #reply = self.ser.readline().hex()
        reply = []
        n_bytes_to_read = 0
        timeout = 1.0
        start_timestamp = datetime.utcnow().timestamp()
        iter_timestamp = np.copy(start_timestamp)
        while (n_bytes_to_read == 0) & (iter_timestamp - start_timestamp < timeout):
            n_bytes_to_read = self.ser.inWaiting()
            iter_timestamp = datetime.utcnow().timestamp()
            
        #print(f'there are {n_bytes_to_read} bytes to read')
        for i in range(self.ser.inWaiting()):
            newbyte = self.ser.read(1).hex()
            #print(newbyte)
            reply.append(newbyte)
      
        if parsed:
            reply, status = self.parseReply(reply, verbose = verbose)
        
        else:
            status = None
            
        
    
        return reply, status
        
    
        
    def parseReply(self, reply, verbose = False):
        """
        reply is a list of hex bytes from the ez stepper
        based on the documentation from the EZHR17EN command set
        the reply is structured as follows:
            'ff' : RS485 line turn around character. transmitted at start of message
            '2f' : '/', the first byte of the '/0' start string
            '30' : '0', the second byte of the '/0' start string
            '60' : the status character. this is always 8 bits
                 After /0, next comes the “Status Character” which consists of 8 bits:
                    Bit7 Reserved
                    Bit6 Always set
                    Bit5 Ready bit. Set when the EZStepper® or EZServo® is ready to accept a command.
                    Bit4 Reserved
                    Bits 3 thru 0. These form an error code N from 0-15: N Function
                        0 No Error
                        1 Init Error
                        2 Bad Command (illegal command was sent)
                        3 Bad Operand (Out of range operand value)
                        4 N/A
                        5 Communications Error (Internal communications error)
                        6 N/A
                        7 Not Initialized (Controller was not initialized before attempting a move)
                        8 N/A
                        9 Overload Error (Physical system could not keep up with commanded position)
                        10 N/A
                        11 Move Not Allowed
                        12 N/A
                        13 N/A
                        14 N/A
                        15 Command overflow (unit was already executing a command when another command was received)
            Now comes the actual reply. this can be one or more bytes:
                eg, for the "/1?4" switch querey you might get back ['31', '31']
            '03' : ETX, or end of text character (ascii '\x03') located at the end of the answer string
            '0d' : carriage return, ascii '\r'
            '0A' : line feed, ascii '\n'
            
        """
        if verbose:
            print(f'raw reply = {reply}')
        
        # find the reply start index
        start_index = [(i + len(step.reply_start_sequence) + 1) for i in range(len(reply)) if reply[i:i+len(step.reply_start_sequence)] == step.reply_start_sequence][0]
        if verbose:
            print(f'start_index = {start_index}')
        
        end_index = [(i) for i in range(len(reply)) if reply[i:i+len(step.reply_end_sequence)] == step.reply_end_sequence][0]
        if verbose:
            print(f'end index = {end_index}')
    
        parsed_reply = reply[start_index : end_index]
        if verbose:
            print(f'parsed reply = {parsed_reply}')
        
        status = None
        return parsed_reply, status
        
    ##### GET COMMANDS ######
    
    def getFirmwareVersion(self):
        cmd = f'&'
        
        reply = self.sendAndRead(cmd)
        print(f"firmware version: {reply}")
        
    def getStatus(self):
        '''
        0 = No Error
        1 = Initialization error
        2 = Bad Command
        3 = Operand out of range

        '''
        cmd = f'{self.addr}Q'
        reply = self.sendAndRead(cmd)
        print(f'Status: {reply}')
    
    
    
    def getSwitchStates(self, verbose = False):
        cmd = f'?4'
        
        reply, status = self.sendAndRead(cmd, verbose = verbose)
        
        '''
        Now parse the switch states:
            Step 0: reply = ['31', '34']
            Step 1: number = 14
            Step 2: binstr = '1110'
            Step 3: state = [1, 1, 1, 0]
                        Returns the status of all four inputs, 0-15 representing a 4- bit binary pattern:
                            Bit 0 = Switch1 
                            Bit 1 = Switch2 
                            Bit 2 = Opto 1 
                            Bit 3 = Opto 2
            Step 4: state_dict = {'switch1': 1, 'switch2': 1, 'opto1': 1, 'opto2': 0}
        
        '''
        if verbose:
            print(f'reply = {reply}')
        # Step 1: this has to be a loop because the reply is sometimes 1 and sometimes 2 bytes
        numstr = ''
        for i in range(len(reply)):
            numstr += bytes.fromhex(reply[i]).decode('utf-8')
        
        number = int(numstr)
        if verbose:
            print(f'parsed switch state number = {number}')
        
        # Step 2: convert to binary using format
        binstr = format(number, '04b') #04 means 4 numbers ALWAYS to represent the 4 bits, and b means binary
        if verbose:
            print(f'parsed switch state binary state = {binstr}')
        # Step 3:
        state_list = [int(char) for char in binstr]
        if verbose:
            print(f'parsed switch state list = {state_list}')
        # Step 4:
        self.state.update({'opto1' : state_list[1]})
        self.state.update({'opto2' : state_list[0]})
        self.state.update({'switch1'   : state_list[3]})
        self.state.update({'switch2'   : state_list[2]})
    
    ##### SET COMMANDS #####
    def setSpeed(self,vel):
        '''self.write("/8v"+str(vel)+"R\r")
        print("new speed is :" + str(vel))'''
        pass
    
    def setTorque(self,curPct):
        '''self.write("/8m"+str(curPct)+"R\r")
        print("current limited to " + str(curPct) + "%")'''
        pass
    
if __name__ == '__main__':
    
    port = "/dev/tty.SLAB_USBtoUART"
    addr = '1'
    
    step = EZstepper(port, addr)
    
    step.setupSerial()
    
    #step.getFirmwareVersion()
    #step.getStatus()
    step.getSwitchStates(verbose = False)
    
    
    print(f'switch states = {step.state}')
    
    
    gearRatio=1 # :1
    uStepsPerStep=256
    StepSize=1.8 # deg
    
    uStepsPerTurn=int(gearRatio*uStepsPerStep * (360/StepSize))
    turns=0.5
    uSteps=int(turns*uStepsPerTurn)
    
    rps = 1.1
    V_usps = int(rps * uStepsPerTurn)
    print(f'{rps} rps = {V_usps} uSteps-per-sec')
    
    Imax = 2.0
    Tmax = 113.0 # in-oz
    T_desired = 69.0
    Tpct_desired = (T_desired/Tmax)*100
    Tpct = int(Tpct_desired)
    T = Tpct*Tmax
    #Ipct = 25
    I = (Tpct/100.0)*Imax
    T = (Tpct/100.0)*Tmax
    
    print(f'To get a Torque of {T:0.1f}, use a max current pct of {Tpct}% (gives {T:.1f} in-oz')
    
    # set speed
    step.sendAndRead(f'V{V_usps}R')
    time.sleep(0.5)
    # set "torque" ie max current percent
    step.sendAndRead(f'm{Tpct}R')
    time.sleep(0.5)
    # Turn N Turns
    N = 500
    step.sendAndRead(f'P{N*uStepsPerTurn}R')
    
    while True:
        try:
            step.getSwitchStates(verbose = False)
            print(f'Hall1 = {step.state["opto1"]}, Hall2 = {step.state["opto2"]}')
            time.sleep(0.5)
            
        except KeyboardInterrupt:
            break
        
        
    