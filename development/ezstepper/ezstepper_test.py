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
        
    def setupMotor(self,
                   gearRatio = 1,
                   uStepsPerStep = 256,
                   StepSize = 1.8,
                   ):
        '''
        gearRatio=1 # :1
        uStepsPerStep=256
        StepSize=1.8 # deg
        
        uStepsPerTurn=int(gearRatio*uStepsPerStep * (360/StepSize))
        turns=0.5
        uSteps=int(turns*uStepsPerTurn)
        
        rps = 1.1
        V_usps = int(rps * uStepsPerTurn)
        '''
        self.gearRatio = gearRatio
        self.uStepsPerStep = uStepsPerStep
        self.StepSize = StepSize
        self.uStepsPerTurn = int(self.gearRatio*self.uStepsPerStep * (360/self.StepSize))
   
    def ConvertVelocity_RPS_to_USPS(self, Vrps, forceInteger = True):
        V_usps = Vrps * self.uStepsPerTurn
        
        if forceInteger:
            V_usps = int(V_usps)
        
        return V_usps
        
        
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
            #TODO: this may not be the way we want to handle a bad response or one that takes too long
            try:
                reply, status = self.parseReply(reply, verbose = verbose)
            except:
                reply = 'No Response'
                status = 'No Status'
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
    
    ##### COMPLEX MOVE COMMANDS #####
    def move_N_turns(self, N, direction = 'ccw',monitor = True):
        
        # get the direction
        if direction.lower() == 'ccw':
            dir_letter = 'P'
        elif direction.lower() == 'cw':
            dir_letter = 'D'
        else:
            print('improper direction. must be "ccw" or "cw"')
            return
        
        steps2move = int(N*self.uStepsPerTurn)
        print(f'Moving {direction.lower()} {steps2move} steps')
        self.sendAndRead(f'{dir_letter}{steps2move}R')
        time.sleep(0.5)
    
        while True:
            try:
                self.getSwitchStates(verbose = False)
                print(f'Hall1 = {self.state["opto1"]}, Hall2 = {self.state["opto2"]}')
                time.sleep(0.5)
            
            except KeyboardInterrupt:
                self.sendAndRead("T")
                break
            
            except:
                time.sleep(0.5)
                pass
    
    def move_until_switch_state(self, max_move = 10,
                                direction = 'ccw',
                                move_units = 'turns',
                                opto1 = None, 
                                opto2 = None, 
                                switch1 = None, 
                                switch2 = None,
                                verbose = False):
        
        '''
        Move the motor until the specified switch states are TRUE
        The max_move limits the maximum move
        The max move can be specified in move_units of either 'turns', or 'steps'
        If any switch state is None it is ignored.
        '''
        
        # set up the move
        if move_units.lower() == 'turns':
            max_move_steps = max_move*self.uStepsPerTurn
        
        elif move_units.lower() == 'steps':
            max_move_steps = max_move
        
        else:
            print('improper move units. must be "turns" or "steps"')
            return
        # get the direction
        if direction.lower() == 'ccw':
            dir_letter = 'P'
        elif direction.lower() == 'cw':
            dir_letter = 'D'
        else:
            print('improper direction. must be "ccw" or "cw"')
            return
        
        # start the move
        stop_condition = False
        
        steps2move = int(N*self.uStepsPerTurn)
        print(f'Moving {direction.lower()} {steps2move} steps')
        
        self.sendAndRead(f'{dir_letter}{steps2move}R')
        time.sleep(0.5)
        # monitor the move until the switch condition is met
        while True:
            try:
                self.getSwitchStates(verbose = False)
                stop_condition = self.validate_switch_state(opto1 = opto1,
                                           opto2 = opto2,
                                           switch1 = switch1,
                                           switch2 = switch2)
                if verbose:
                    print(f'Hall1 = {self.state["opto1"]}, Hall2 = {self.state["opto2"]}, stop_condition = {stop_condition}')
                
                if stop_condition == True:
                    print('Stop Condition Met!')
                    self.sendAndRead("T")
                    break
                
                time.sleep(0.1)
            
            except KeyboardInterrupt:
                self.sendAndRead("T")
                break
            
            except:
                time.sleep(0.5)
                pass
        
    def validate_switch_state(self,
                              opto1 = None, 
                              opto2 = None, 
                              switch1 = None, 
                              switch2 = None,
                              verbose = False):
        '''
        checks to see if the current switch state matches the specified state
        and returns either True or False
        any switch that is specified as None is ignored
        '''
        checkState = dict()
        checkState_list = []
        
        if not opto1 is None:
            checkState.update({'opto1' : bool(opto1)})
            print('watching opto1')
        if not opto2 is None:
            checkState.update({'opto2' : bool(opto2)})
        
        if not switch2 is None:
            checkState.update({'switch1' : bool(switch1)})
            
        if not switch2 is None:
            checkState.update({'switch2' : bool(switch2)})
    
        # check the state
        for key in checkState.keys():
            if self.state[key] == checkState[key]:
                checkState_list.append(True)
            else:
                checkState_list.append(False)
        
        # if all the list are true then return true, otherwise false
        state_matches = all(checkState_list)
        if len(checkState_list) == 0:
            print('len of states to check is zero')
            state_matches = False
        # note this returns true if the checkState_list is empty
        
        return state_matches
    
    ##### COMMANDS THAT ARE SPECIFIC TO THE SETUP #####
    def goHome(self):
        '''
        # This sends the tray to HOME position.
        
        State as of 3-11-21
        At the moment this is the Left limit switch
        
        The whole track is 1.45 turns end to end
        
        here is the prescription:
            no matter where we are, sending the tray 1.5 turns to the left
            will hit the hard limit.
            
            going through the detent R-> L requires Imax >~ 65%
            
            at the left limit: opto1 = 0, opto2 = 1
            
        '''
        # Set the move current
        move_current = 80
        self.setMoveCurrent(move_current)
        
        # set the hold current
        hold_current = 0
        self.setHoldCurrent(hold_current)
        pass
        
        # set move speed
        move_speed = 0.25 #rps
        self.setSpeed(vel = move_speed, units ='rps')
        
    
        # move until the sensors are at the config for the left limit
        self.move_until_switch_state(1.5, 
                                     direction='cw',
                                     move_units = 'turns',
                                     opto1=0, 
                                     opto2=1, 
                                     verbose=True)

        
    
    ##### SET COMMANDS #####
    def setSpeed(self,vel, units = 'rps'):
        ''' set move speed. specify rps (rotn per sec) or usps (microsteps per sec) '''
        if units.lower() == 'rps':
            speed_usps = self.ConvertVelocity_RPS_to_USPS(vel, forceInteger = True)
        elif units.lower == 'steps':
            speed_usps = vel
        else:
            print('speed units invalid. must be "rps" or "steps"')
        
        print(f'setting move speed to {speed_usps} usps')
        self.sendAndRead(f'V{speed_usps}R')
        time.sleep(0.5)
        
    def setAcceleration(self, acceleration):
        ''' set acceleration. UNITS MUST BE microsec/sec^2 '''
        
        print(f'acceleration set to {acceleration} usteps per sec^2')
        self.sendAndRead(f'L{acceleration}R')
        time.sleep(0.5)
        
    def setMoveCurrent(self,curPct):
        ''' set move current '''
        print("move current limited to " + str(curPct) + "% of max")
        self.sendAndRead(f'm{curPct}R')
        time.sleep(0.5)
        pass
    
    def setHoldCurrent(self,curPct):
        ''' set move current '''
        print("hold current limited to " + str(curPct) + "% of max")
        self.sendAndRead(f'h{curPct}R')
        time.sleep(0.5)
        pass
    
if __name__ == '__main__':
    
    #port = "/dev/tty.SLAB_USBtoUART"
    port_path = "/dev/serial/by-id/"
    port = port_path + "usb-FTDI_FT232R_USB_UART_AG0JG9J3-if00-port0"
    addr = '1'
    
    step = EZstepper(port, addr)
    
    
    
    step.setupSerial()
    
    # Set up motor using default properties
    step.setupMotor()
    
    """
    #step.getFirmwareVersion()
    #step.getStatus()
    step.getSwitchStates(verbose = False)
    time.sleep(0.5)
    
    print(f'switch states = {step.state}')
    
    # Set up motor using default properties
    step.setupMotor()
    
    # Calculate the speed we want to move
    rps = 0.25#1.1
    V_usps = step.ConvertVelocity_RPS_to_USPS(rps, forceInteger = True)
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
    
    # set acceleration
    a = 1000
    a_to_send = int(a)
    step.sendAndRead(f'L{a_to_send}R')
    time.sleep(0.5)
    #
    # set "torque" ie max current percent
    
    Tpct = 80
    step.sendAndRead(f'm{Tpct}R')
    time.sleep(0.5)
    
    
    # set the hold torque
    step.sendAndRead(f'h0R')
    """
    #%%
    # Turn N Turns
    step.setMoveCurrent(80)
    step.setHoldCurrent(0)
    N = 1.5
    
    #LEFT = CW, RIGHT = CCW
    
    
    
    step.move_N_turns(N, direction = 'cw')
    
    #%%
    step.setMoveCurrent(80)
    step.setHoldCurrent(0)
    
    # Move until switch condition is met
    #step.move_until_switch_state(200, opto1 = 0, opto2 = 1, verbose = True)
    step.move_until_switch_state(2.0, opto1 = 0, opto2 = 1,direction = 'cw', verbose = True)
    
    