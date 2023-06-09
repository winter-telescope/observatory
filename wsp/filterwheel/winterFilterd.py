#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Feb 24 15:58:21 2023

@author: winter
"""

import os
import sys
import numpy as np
#from ccdproc_convenience_functions import show_image
from PyQt5 import QtCore
import threading
import Pyro5.core
import Pyro5.server
import logging
from datetime import datetime, timedelta
import pytz
import getopt
from astropy.io import fits
import serial
import signal
import scipy.stats
import time
#from photutils.datasets import make_random_gaussians_table, make_gaussian_sources_image
import yaml


# add the wsp directory to the PATH
wsp_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(1, wsp_path)
print(f'WINTERfilterd: wsp_path = {wsp_path}')


from daemon import daemon_utils
from utils import logging_setup

class EZStepper(QtCore.QObject):
    newReply = QtCore.pyqtSignal(int)
    newStatus = QtCore.pyqtSignal(object)
    newCommand = QtCore.pyqtSignal(str)
    updateStateSignal = QtCore.pyqtSignal(object) # pass it a dict
    resetCommandPassSignal = QtCore.pyqtSignal(int)

    def __init__(self, config, logger = None, verbose = False):
        super(EZStepper, self).__init__()

        self.config = config
        self.verbose = verbose
        self.logger = logger
        self.connected = False
        self.command_pass = 0
        self.timestamp = datetime.utcnow().timestamp()
        self.log('initing EZStepper object')

        # housekeeping attributes
        self.state = dict()

        # connect the update state signal
        self.updateStateSignal.connect(self.updateState)
        self.resetCommandPassSignal.connect(self.resetCommandPass)


        # serial setup settings
        self.port = config['serial']['port']
        self.addr = config['serial']['address']
        self.baud_rate = config['serial']['baud_rate']

        # ezstepper settings
        self.move_max_volt = config['stepper_config']['move_max_volt']
        self.encoder_ratio = config['stepper_config']['encoder_ratio']
        self.speed = config['stepper_config']['speed']
        self.homing_steps = config['stepper_config']['homing_steps']
        self.max_encoder_err = config['stepper_config']['max_encoder_err']
        self.overload_timeout = config['stepper_config']['overload_timeout']
        self.hold_current = config['stepper_config']['hold_current']

        # startup values
        self.filter_pos = -1
        self.filter_goal = -1
        self.pos = -1
        self.pos_goal = -1
        self.is_moving = 0
        self.homed = 0
        self.encoder_pos = -1
        self.is_homing = 0

        # timers
        self.state_update_dt = config['state_update_dt']
        self.reply_timeout = config['reply_timeout']


        ## Startup:
        self.setupSerial()
        
        time.sleep(.5)
        
        self.home(verbose=verbose)  # this will populate the state


    # General Methods
    def log(self, msg, level = logging.INFO):
        msg = f'EZStepper: {msg}'
        if self.logger is None:
                print(msg)
        else:
            self.logger.log(level = level, msg = msg)

    # Filter Methods
    def setupSerial(self, *args, **kwargs):
        # set up the serial port using pyserial "serial" library
        # this can take and pass in any pyserial args

        self.ser = serial.Serial(port=self.port,
                baudrate=self.baud_rate,
                timeout = 1,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                bytesize=serial.EIGHTBITS,
                *args,
                **kwargs
            )


    def updateState(self, dict_to_add):
        for key in dict_to_add:
            self.state.update({key : dict_to_add[key]})


    def resetCommandPass(self, val):
        self.log(f'running resetCommandPass: {val}')
        # reset the command pass value to val (0 or 1), and update state
        self.command_pass = val
        self.state.update({'command_pass' : val})


    def pollStatus(self):
        """
        Get housekeeping status

        """
        self.pos = self.getMicrostepLoc()
        self.encoder_pos = self.getEncoderLoc()
        # now update the state dictionary
        self.update_state()


    def update_state(self):
        self.state.update({ 'timestamp' : datetime.utcnow().timestamp(),
                            'is_moving' : self.is_moving,
                            'position'  : self.pos,
                            'pos_goal'  : self.pos_goal,
                            'encoder_pos' : self.encoder_pos,
                            'encoder_pos_goal' : self.encoder_pos_goal,
                            'filter_pos' : self.getFilterPosition(),
                            'filter_goal' : self.filter_goal,
                            'homed'     : self.homed,
                            'is_homing' : self.is_homing,
                            })


        #emit a signal and pass the new state dict out to the camera from the comm thread
        self.newStatus.emit(self.state)

    def doCommand(self, cmd_obj):
        """
        This is connected to the newCommand signal. It parses the command and
        then executes the corresponding command from the list below

        using this as a reference: (source: https://stackoverflow.com/questions/6321940/how-to-launch-getattr-function-in-python-with-additional-parameters)

        """
        #print(f'dome: caught doCommand signal: {cmd_obj.cmd}')
        cmd = cmd_obj.cmd
        args = cmd_obj.args
        kwargs = cmd_obj.kwargs

        msg = f'(Thread {threading.get_ident()}: caught doCommand signal: {cmd_obj.cmd}, args = {args}, kwargs = {kwargs}'
        if self.verbose:
            self.log(msg)
        try:
            getattr(self, cmd)(*args, **kwargs)
        except:
            pass




    # API methods
    def parse_status(self, status: int):
        error_dict =  {
            0: 'No Error',
            1: 'Init Error',
            2: 'Bad Command (illegal command was sent)',
            3: 'Bad Operand (Out of range operand value)',
            4: 'N/A',
            5: 'Communications Error (Internal communications error)',
            6: 'N/A',
            7: 'Not Initialized (Controller was not initialized before attempting a move)',
            8: 'N/A',
            9: 'Overload Error (Physical system could not keep up with commanded position)',
            10: 'N/A',
            11: 'Move Not Allowed',
            12: 'N/A',
            13: 'N/A',
            14: 'N/A',
            15: 'Command overflow (unit was already executing a command when another command was received)'
        }
        bits = int(format(status, '08b'))
        ready = bits & (2**5) != 0  # Bit5 is the ready bit
        error_code = int(format(bits, '08b')[-4:], 2)
        error_msg = error_dict[error_code]
        if error_code in [1, 2, 3, 5, 7, 9, 11, 15]:
            # problematic codes
            self.log(f'An error was returned from the stepper. '
                     f'Error code: {error_code}. Error: {error_msg}')
        return ready, error_code, error_msg


    def parse_reply(self, reply, verbose=False):
        # FIXME: clean this up. It should respond with the status and the parsed contents
        # e.g., a goto command's reply would be parsed into ()
        # print(f'raw reply = {reply}')

        if len(reply) == 1:
            self.log('Only one thing in reply. Probably want to try this again, in a bit.')
            return None, None
        if verbose: self.log(f'raw reply is {reply}')
        reply_start_sequence = '/0'.encode('utf-8').hex()
        reply_end_sequence = '03'

        try:
            end_list_index = reply.index(reply_end_sequence)
        except ValueError:
            self.log('We are not getting a response we expect from the stepper. '
                     'We can try again, but we should consider power cycling.')
            return None, None
        replystr = ''.join(reply[:end_list_index])
        start_index = replystr.find(reply_start_sequence) + len(reply_start_sequence)

        reply_contents = replystr[start_index:]
        status_code = reply_contents[:2]
        ready, error_code, error_msg = self.parse_status(int(status_code))

        actual_reply = str(reply_contents[2:])

        if verbose: self.log(f'status code = {error_code}')
        if verbose: self.log(f'Ready status = {ready}')
        if verbose: self.log(f'error message = {error_msg}')

        if verbose: self.log(f'actual reply = {actual_reply}')
        contents_hex = [actual_reply[i:i+2] for i in range(0, len(actual_reply), 2)]
        if verbose: self.log(f'hex contents = {contents_hex}')
        contents_parsed = [bytes.fromhex(hx).decode('utf-8') for hx in contents_hex]
        parsed = ''.join(contents_parsed)
        if verbose: self.log(f"parsed contents = {parsed}")

        return error_msg, parsed


    def send(self, serial_command, verbose=False):
        assert self.ser, "No serial setup found"
        self.ser.flushInput()
        self.ser.write(bytes(f"/{self.addr}{serial_command}\r", 'utf-8'))
        reply = []

        time.sleep(self.reply_timeout)

        for i in range(self.ser.in_waiting):
            newbyte = self.ser.read(1).hex()
            reply.append(newbyte)

        return self.parse_reply(reply, verbose=verbose)


    def getEncoderLoc(self, verbose=False) -> int:
        '''Get encoder tick reading.

        Parameters
        ----------
        verbose : bool, optional
            Print additional info, by default False

        Returns
        -------
        int
            Encoder position
        '''
        status, enc_loc = self.send('?8', verbose=verbose)
        self.encoder_pos = int(enc_loc)
        self.update_state()
        return self.encoder_pos


    def getMicrostepLoc(self, verbose=False) -> int:
        '''Get microstep location reading.

        Parameters
        ----------
        verbose : bool, optional
            Print additional info, by default False

        Returns
        -------
        int
            Microstep position
        '''
        status, ustep_loc = self.send('?0', verbose=verbose)
        self.ustep_loc = int(ustep_loc)
        self.update_state()
        return self.ustep_loc


    def getInputStatus(self, verbose=False) -> int:
        '''Get opto/switch status.

        Parameters
        ----------
        verbose : bool, optional
            Print additional info, by default False

        Returns
        -------
        dict (dict of str: int):
            dict for switch1, switch2, opto1, opto2
        '''
        status, input_bitnum = self.send('?4', verbose=verbose)
        bitword = format(int(input_bitnum), '04b')  # 4 bits, one for each input
        input_status = {
            'switch1': int(bitword[-1]),
            'switch2': int(bitword[-2]),
            'opto1': int(bitword[-3]),
            'opto2': int(bitword[-4]),
        }
        return input_status
    
    
    def getFilterPosition(self, verbose=False) -> int:
        '''Get filter position based on encoder position and known filter
        encoder locations.

        Parameters
        ----------
        verbose : bool, optional
            Verbosity. The default is False.

        Returns
        -------
        int
            Filter position. Int in [1, 2, 3, 4] if encoder position is 
            within the allowed tolerance of a known filter position.
            Returns -1 if not.
        '''
        enc_loc = self.encoder_pos
        arrived = {filter: abs(enc_loc - goal) < self.max_encoder_err
                  for filter, goal in self.config['filters']['encoder_positions'].items()}
        assert sum(arrived.values()) <= 1, "We think we are at more than one filter position, something has gone very wrong"
        filter_pos = sum([k*v for k, v in arrived.items()])
        if filter_pos < 1:
            return -1
        else:
            return filter_pos


    def home(self, verbose=False):
        # perform homing
        self.pos = -1.0
        self.pos_goal = 0
        self.encoder_pos_goal = 0
        self.filter_goal = 0
        self.homed = 0
        self.is_homing = 1
        self.is_moving = 1
        self.update_state()

        self.log('Beginning homing sequence')
        # send homing command
        cmd = 'n0R'  # reset n mode to the default zero before homing command
        status, response = self.send(cmd, verbose=verbose)
        # applying settings and moving homing_steps until we hit the opto
        cmd = (
            f'm{self.move_max_volt}N1aE{self.encoder_ratio}'
            f'V{self.speed}f1Z{self.homing_steps}aC{self.max_encoder_err}'
            f'au{self.overload_timeout}h{self.hold_current}z0R'
            )
        status, response = self.send(cmd, verbose=verbose)

        arrived = False
        timed_out = False
        start_time = time.time()
        try:
            while not (arrived or timed_out):
                time.sleep(self.state_update_dt)
                self.encoder_pos = self.getEncoderLoc()
                if verbose: self.log(f'while homing: encoder pos is {self.encoder_pos}')
                time.sleep(self.state_update_dt)
                self.pos = self.getMicrostepLoc()
                if verbose: self.log(f'while homing: microstep pos is {self.pos}')
                arrived = abs(self.encoder_pos) < self.max_encoder_err
                timed_out = ((time.time() - start_time) >
                             self.config['stepper_config']['timeout_secs'])
        except Exception as e:
            self.log(f'We ran into an error: {e}')

        if timed_out:
            self.log('Homing the filter timed out. Might want to power cycle.')
            return -1

        # opto check
        input_status = self.getInputStatus()
        actually_homed = input_status['opto1'] == 0

        if actually_homed:
            self.homed = 1
            self.is_homing = 0
            self.is_moving = 0
            self.homed = 1
            self.filter_pos = 1
            self.update_state()
            # we have homed successfully, go back to the mode we like
            cmd = 'n72R'
            status, response = self.send(cmd, verbose=verbose)
            self.log('Homing complete')
            return self.encoder_pos
        else:
            self.log("The stepper thinks we homed, but we actually didn't. "
                     "Might want to power cycle, otherwise filter positions "
                     "will likely be incorrect.")
            return -1


    def goToLocation(self, microstep_loc: int, verbose=False) -> int:
        '''Tell motor to go to the specific microstep location.

        Parameters
        ----------
        microstep_loc : int
            Microstep location.

        Returns
        -------
        int
            Final encoder position, or -1 if error.
        '''
        self.pos_goal = microstep_loc
        self.encoder_pos_goal = microstep_loc
        status, response = self.send(f'A{microstep_loc}n72R', verbose=verbose)
        self.is_moving = 1
        self.update_state()

        arrived = False
        timed_out = False
        start_time = time.time()
        while not (arrived or timed_out):
            time.sleep(self.state_update_dt)
            self.encoder_pos = self.getEncoderLoc()
            self.pos = self.getMicrostepLoc()
            arrived = abs(microstep_loc - self.encoder_pos) < self.max_encoder_err
            timed_out = ((time.time() - start_time) >
                         self.config['stepper_config']['timeout_secs'])

        if timed_out:
            self.log(f'Moving the filter to position {microstep_loc} timed out. '
                     'Might want to power cycle.')
            return -1

        self.is_moving = 0
        self.update_state()
        return self.encoder_pos


    def goToFilter(self, filter_num: str, force=False, verbose=False) -> int:
        '''Move filter tray to the requested filter.

        Parameters
        ----------
        filter_num : int
            Number of requested filter. Should be one of 1, 2, 3, 4.
        force : bool, default
            Force filter to move even if it isn't homed.
        Returns
        -------
        int
            Final encoder position.
        '''
        assert filter_num in [1, 2, 3, 4], f"Filter {filter_num} not in [1, 2, 3, 4]"
        if not force: 
            assert self.homed == 1, 'Filter is not homed, we are not doing this!'
        else:
            self.log('Filter is not homed but we are forcing it to move anyway. '
                     'Behaviour will likely be weird.')
        self.filter_goal = filter_num
        position = self.config['filters']['encoder_positions'][filter_num]
        self.log(f'Moving to filter number {filter_num}, at position {position}.')
        final_enc =  self.goToLocation(position, verbose=verbose)
        self.log(f'Moved to filter number {filter_num}, at position {final_enc}.')
        self.filter_pos = filter_num
        return final_enc


    def goto(self, pos):
        try:
            self.pos_goal = pos
            self.encoder_pos_goal = self.config['filters']['encoder_positions'].get(pos, -1.0)
            self.log(f'moving position: {self.pos} --> {self.pos_goal}')
            self.is_moving = 1
            self.update_state()

            # do the simulated move
            dt_total_move = 30.0 # how long will the move take?
            dt_update = 1.0
            n_steps = int(dt_total_move/dt_update)
            encoder_positions = np.linspace(self.encoder_pos, self.encoder_pos_goal, n_steps)
            for i in range(n_steps):
                self.encoder_pos = encoder_positions[i]
                if self.verbose:
                    self.log(f'step {i}/{n_steps+1}: encoder pos = {self.encoder_pos}')
                time.sleep(dt_update)
                self.pos = -1
                self.is_moving = 1
                self.update_state()

            self.pos = pos
            self.is_moving = 0
            self.update_state()
            self.log('move complete!')
        except Exception as e:
            self.log('could not move ')




class signalCmd(object):
    '''
    this is an object which can pass commands and args via a signal/slot to
    other threads, ideally for daemons
    '''
    def __init__(self, cmd, *args, **kwargs):
        self.cmd = cmd
        self.argdict = dict()
        self.args = args
        self.kwargs = kwargs



class CommThread(QtCore.QThread):
    """
    CommThread: Communication Thread for Talking to the Sensor

    All communications with the sensor happen through this thread.
    """

    newReply = QtCore.pyqtSignal(int)
    #newCommand = QtCore.pyqtSignal(str)
    newCmdRequest = QtCore.pyqtSignal(object)
    #doReconnect = QtCore.pyqtSignal()
    newStatus = QtCore.pyqtSignal(object)
    stopPollTimer = QtCore.pyqtSignal()

    def __init__(self, config, logger = None, verbose = False):
        super(QtCore.QThread, self).__init__()
        self.config = config
        self.logger = logger
        self.verbose = verbose
        print('initing comm thread')

    def HandleCommandRequest(self, cmdRequest):
        self.newCmdRequest.emit(cmdRequest)

    def DoReconnect(self):
        #print(f'(Thread {threading.get_ident()}) Main: caught reconnect signal')
        self.doReconnect.emit()

    def run(self):
        print('in the run method for the comm thread')
        def SignalNewReply(reply):
            self.newReply.emit(reply)
        def SignalNewStatus(newStatus):
            self.newStatus.emit(newStatus)

        def StopPollTimer():
            print('trying to stop poll timer?')
            self.pollTimer.stop()

        self.ezstep = EZStepper(config = self.config, logger = self.logger, verbose = self.verbose)

        # if the newReply signal is caught, execute the sendCommand function
        #self.newCommand.connect(self.sensor.doCommand)
        self.newCmdRequest.connect(self.ezstep.doCommand)
        self.ezstep.newReply.connect(SignalNewReply)

        # if we recieve a doReconnect signal, trigger a reconnection
        self.ezstep.newStatus.connect(SignalNewStatus)
        self.stopPollTimer.connect(StopPollTimer)

        self.pollTimer = QtCore.QTimer()
        self.pollTimer.setSingleShot(False)
        self.pollTimer.timeout.connect(self.ezstep.pollStatus)

        # How often can you realistically poll the stepper bus?
        stepper_time_between_polls_ms = 1000
        self.pollTimer.start(stepper_time_between_polls_ms)


        self.exec_()


class WINTERfw(QtCore.QObject):

    # Define any pyqt signals here
    #commandRequest = QtCore.pyqtSignal(str)
    newCmdRequest = QtCore.pyqtSignal(object)

    def __init__(self, config, logger = None, verbose = False ):
        super(WINTERfw, self).__init__()

        ## init things here
        self.config = config
        self.logger = logger
        self.verbose = verbose
        self.state = dict()

        ## some things to keep track of what is going on
        # doing an exposure?
        # set up the other threads
        self.commthread = CommThread(self.config, logger = self.logger, verbose = self.verbose)

        # start up the other threads
        self.commthread.start()

        # set up the signal/slot connections for the other threads
        self.commthread.newStatus.connect(self.updateStatus)
        self.newCmdRequest.connect(self.commthread.HandleCommandRequest)

    def log(self, msg, level = logging.INFO):

        msg = f'WINTERfw: {msg}'

        if self.logger is None:
            print(msg)
        else:
            self.logger.log(level = level, msg = msg)


    def updateStatus(self, newStatus):
        '''
        Takes in a new status dictionary (eg, from the status thread),
        and updates the local copy of status

        we don't want to overwrite the whole dictionary!

        So do this element by element using update
        '''
        if type(newStatus) is dict:
            # make sure we don't get some garbage, and only attempt if this is actually a dictionary
            for key in newStatus.keys():
                try:
                    self.state.update({key : newStatus[key]})

                except:
                    pass



    ###### PUBLIC FUNCTIONS THAT CAN BE CALLED USING PYRO SERVER #####

    # Return the Current Status (the status is updated on its own)
    @Pyro5.server.expose
    def getStatus(self):
        if self.verbose:
            self.log('got command to return state dict')

        try:
            self.timestamp = datetime.utcnow().timestamp()


            self.state.update({ 'timestamp' : self.timestamp,

                            })
        except Exception as e:
            if self.verbose:
                self.log(f'Could not run getStatus: {e}')
            pass
        #print(self.state)
        return self.state
        #print(f'I dunno I tried I guess?')

    @Pyro5.server.expose
    def goto(self, pos):
        sigcmd = signalCmd('goto', pos)
        self.newCmdRequest.emit(sigcmd)


    @Pyro5.server.expose
    def home(self):
        sigcmd = signalCmd('home')
        self.newCmdRequest.emit(sigcmd)
        
    @Pyro5.server.expose    
    def send(self, serial_command, verbose=False):
        sigcmd = signalCmd('send', serial_command, verbose=verbose)
        self.newCmdRequest.emit(sigcmd)


    @Pyro5.server.expose
    def getEncoderLoc(self, verbose=False):
        sigcmd = signalCmd('getEncoderLoc', verbose=verbose)
        self.newCmdRequest.emit(sigcmd)


    @Pyro5.server.expose
    def getMicrostepLoc(self, verbose=False):
        sigcmd = signalCmd('getMicrostepLoc', verbose=verbose)
        self.newCmdRequest.emit(sigcmd)


    @Pyro5.server.expose
    def getInputStatus(self, verbose=False):
        sigcmd = signalCmd('getInputStatus', verbose=verbose)
        self.newCmdRequest.emit(sigcmd)

    @Pyro5.server.expose
    def goToLocation(self, microstep_loc):
        sigcmd = signalCmd('goToLocation', microstep_loc, verbose=verbose)
        self.newCmdRequest.emit(sigcmd)

    @Pyro5.server.expose
    def goToFilter(self, filter_num):
        sigcmd = signalCmd('goToFilter', filter_num, verbose=verbose)
        self.newCmdRequest.emit(sigcmd)


class PyroGUI(QtCore.QObject):
    """
    This is the main class for the daemon. It is a QObject, which means that
    it can be initialized with it's own event loop. This runs the whole daemon,
    and has a dedicated QThread which handles all the Pyro stuff (the PyroDaemon object)
    """

    def __init__(self, config, ns_host = None, logger = None, verbose = False, parent=None):
        super(PyroGUI, self).__init__(parent)

        self.config = config
        self.ns_host = ns_host
        self.logger = logger
        self.verbose = verbose

        msg = f'(Thread {threading.get_ident()}: Starting up Filter Daemon '
        if logger is None:
            print(msg)
        else:
            logger.info(msg)


        self.alertHandler = None


        self.fw = WINTERfw(
                                config = self.config,
                                logger = self.logger,
                                verbose = self.verbose,
                                )

        self.pyro_thread = daemon_utils.PyroDaemon(obj = self.fw,
                                                   name = 'WINTERfw',
                                                   ns_host = self.ns_host,
                                                   )
        self.pyro_thread.start()





def sigint_handler( *args):
    """Handler for the SIGINT signal."""
    sys.stderr.write('\r')

    print('CAUGHT SIGINT, KILLING PROGRAM')

    # explicitly kill each thread, otherwise sometimes they live on
    main.fw.commthread.stopPollTimer.emit()
    time.sleep(0.5)

    main.fw.commthread.quit() #terminate is also a more rough option?

    print('KILLING APPLICATION')
    QtCore.QCoreApplication.quit()


if __name__ == '__main__':

    argumentList = sys.argv[1:]

    verbose = False
    doLogging = False
    ns_host = '192.168.1.20'
    # Options
    options = "vpn:a:"

    # Long options
    long_options = ["verbose", "print", "ns_host ="]



    try:
        # Parsing argument
        print(f'winterfw: argumentList = {argumentList}')
        arguments, values = getopt.getopt(argumentList, options, long_options)
        print(f'winterfw: arguments: {arguments}')
        print(f'winterfw: values: {values}')
        # checking each argument
        for currentArgument, currentValue in arguments:

            if currentArgument in ("-v", "--verbose"):
                verbose = True

            elif currentArgument in ("-n", "--ns_host"):
                ns_host = currentValue

            elif currentArgument in ("-p", "--print"):
                doLogging = False



    except getopt.error as err:
        # output error, and return with an error code
        print(str(err))

    print(f'winterfw: verbose = {verbose}')
    print(f'winterfw: logging mode = {doLogging}')

    # load the config
    fwconfig = os.path.join(wsp_path, 'filterwheel', 'winterfw_config.yaml')
    config = yaml.load(open(fwconfig), Loader = yaml.FullLoader)

    app = QtCore.QCoreApplication(sys.argv)

    if doLogging:
        logger = logging_setup.setup_logger(os.getenv("HOME"), config)
    else:
        logger = None


    main = PyroGUI(config = config, ns_host = ns_host, logger = logger, verbose = verbose)

    signal.signal(signal.SIGINT, sigint_handler)

    # Run the interpreter every so often to catch SIGINT
    timer = QtCore.QTimer()
    timer.start(500)
    timer.timeout.connect(lambda: None)

    sys.exit(app.exec_())
