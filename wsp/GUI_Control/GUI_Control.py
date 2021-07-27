# This Python file uses the following encoding: utf-8
import sys
import pandas as pd
try:
    from PyQt5 import uic
    from PyQt5.QtWidgets import QApplication
    from PyQt5.QtCore import QFile
    QT = 'PyQt5'
except:
    from PySide6.QtUiTools import QUiLoader
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import QFile
    from PySide6.QtCore import QIODevice
    QT = 'PySide6'

import time
import socket
import os
import Pyro5.core
import Pyro5.server
import json
from PyQt5 import QtCore
from PyQt5.QtCore import QTimer

wsp_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(1, wsp_path)

"""
This bit handles the update of the dictionary table in a nice HTML
format, and saves the scrollbar position, setting the scrollbar back
where it was after the text updates. There is a slight deviation
downwards from the initial position because of rounding, but this
rounding is necessary to set the positional value, and it's not
very disruptive, so I've deemed it 'good enough'.
"""

def print_html_table_state(state):
    df = pd.DataFrame.from_dict(state, orient='index')
    vsb = window.output_display_2.verticalScrollBar()
    old_pos_ratio = vsb.value() / (vsb.maximum() or 1)
    window.output_display_2.setHtml(df.to_html(header=False))
    vsb.setValue(round(old_pos_ratio * vsb.maximum()))

class StateGetter(QtCore.QObject):

    """
    This is the pyro object that handles polling the published state from the
    Pyro nameserver

    NOTE:
        This inherets from QObject, which allows it to have custom signals
        which can communicate with the communication threads
    """

    def __init__(self, verbose = False):
        super(StateGetter, self).__init__()

        # init the housekeeping state
        self.state = dict()

        # set up the link to the pyro server and make the local object
        self.init_remote_object()



    def init_remote_object(self):
        # init the remote object: set up the link to the housekeeping state on the Pyro5 server
        try:
            self.remote_object = Pyro5.client.Proxy("PYRONAME:state")
            self.connected = True
        except:
            self.connected = False
            pass
        '''
        except Exception:
            self.logger.error('connection with remote object failed', exc_info = True)
        '''
    def update_state(self):
        # poll the state, if we're not connected try to reconnect

        if not self.connected:
            self.init_remote_object()

        else:
            try:
                # get the state from the remote state object and make a local copy
                self.state = self.remote_object.GetStatus()

            except Exception as e:
                print(f'StateGetter: could not update remote state: {e}')
                pass

    def print_state(self):
        #window.output_display_2.setText(json.dumps(self.state, indent = 2))
        print_html_table_state(self.state)


def timer_handlings():
    # get the current housekeeping state
    monitor.update_state()
    state = monitor.state
    monitor.print_state()
    window.ccd_temp_display.display(state['ccd_tec_temp'])
    if state['ccd_tec_status'] == 1:
        change_ccd_indicator_green()
    else:
        change_ccd_indicator_red()
    if state['small_chiller_isRunning'] == 1:
        change_chiller_indicator_green()
    else:
        change_chiller_indicator_red()
    if state['dome_close_status'] == 1:
        change_dome_indicator_red()
    else:
        change_dome_indicator_green()

def send(cmd):
    # now that the connection is established, data can be sent with sendall() and received with recv()
    sock.sendall(bytes(cmd,"utf-8"))
    reply = sock.recv(1024).decode("utf-8")
    window.output_display.appendPlainText(f"received message back from server: '{reply}'\n")
def test():
    print('please')

# In this section, all of the scripts attached to the frontend are defined

def connect_to_server():
    # create a TCP/IP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # connect the socket ot the port where the server is listening
    server_address = ('localhost', 7000)
    sock.connect(server_address)
    window.server_connect_button.setStyleSheet("background-color:green;")
    window.server_connect_button.setText("WINTER Connected")
    timer_handlings()
def chiller_start():
    send('chiller_start')
    window.chiller_button.setStyleSheet("background-color:green;")
    window.chiller_button.setText("Chiller Started")

def run_shutdown_script():
    send('total_shutdown')

def run_startup_script():


    # get the current housekeeping state
    monitor.update_state()
    monitor.print_state()
    state = monitor.state
    if monitor.state['ccd_tec_temp'] < 25:
        send('total_startup')

def run_restart_script():
    restart_type = window.restart_selection.currentText()
    if restart_type == 'Total Restart':
        window.output_display.appendPlainText("Total Restart")
    if restart_type == 'Mount Restart':
        window.output_display.appendPlainText("Mount Restart")
    if restart_type == 'Dome Restart':
        window.output_display.appendPlainText("Dome Restart")
def do_exposure_script():
    filter_selection = window.filter_selection.currentText()
    if filter_selection == 'U Band Filter':
        wheel = 1
    if filter_selection == 'R Band Filter':
        wheel = 3
    ra = window.RA_input.text()
    dec = window.DEC_input.text()
    exp = window.exposure_input.text()
    send('command_filter_wheel ' + str(wheel))
    window.output_display.appendPlainText("Taking a " + exp + " second exposure with " + filter_selection + " at coordinates " + ra + " , " + dec)
    send('ccd_set_exposure '+ exp)
    send('ccd_do_exposure')
def goto_coordinate_script():
    ra = window.RA_input.text()
    dec = window.DEC_input.text()
    window.output_display.appendPlainText("Moved to " + ra + " , " + dec)
    send('mount_goto_ra_dec_j2000 ' + ra + " " + dec)
    
def change_chiller_indicator_red():
    window.chiller_status_light.setStyleSheet("background-color:red;")

def change_chiller_indicator_green():
    window.chiller_status_light.setStyleSheet("background-color:green;")

def change_dome_indicator_red():
    window.dome_status_light.setStyleSheet("background-color:red;")

def change_dome_indicator_green():
    window.dome_status_light.setStyleSheet("background-color:green;")
    
def change_ccd_indicator_red():
    window.ccd_status_light.setStyleSheet("background-color:red;")

def change_ccd_indicator_green():
    window.ccd_status_light.setStyleSheet("background-color:green;")
    
def toggle_dome_tracking():
    if window.dome_tracking_toggle.isChecked()==True:
        window.output_display.appendPlainText("Dome Tracking On")
        send('dome_tracking_on')
    else:
        window.output_display.appendPlainText("Dome Tracking Off")
        send('dome_tracking_off')
def toggle_mount_tracking():
    if window.mount_tracking_toggle.isChecked()==True:
        window.output_display.appendPlainText("Mount Tracking On")
        send('mount_tracking_on')
    else:
        window.output_display.appendPlainText("Mount Tracking Off")
        send('mount_tracking_off')

def command_entry():
    send(window.command_entry.text())
# In this section, the application is started, and the methods of the different widgets are linked to functions.

if __name__ == "__main__":
    # create a TCP/IP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # connect the socket ot the port where the server is listening
    server_address = ('localhost', 7000)
    sock.connect(server_address)
    app = QApplication(sys.argv)
    ui_file_name = "form.ui"
    if QT == 'PySide6':
        ui_file = QFile(ui_file_name)
        loader = QUiLoader()
        window = loader.load(ui_file)
        ui_file.close()
    elif QT == 'PyQt5':
        window = uic.loadUi(ui_file_name)
    window.show()
    update_timer = QTimer()
    update_timer.timeout.connect(timer_handlings)
    update_timer.start(5000)
    # init the state getter
    monitor = StateGetter()
    window.startup_button.pressed.connect(run_startup_script)
    window.shutdown_button.pressed.connect(run_shutdown_script)
    window.restart_button.pressed.connect(run_restart_script)
    window.exposure_button.pressed.connect(do_exposure_script)
    window.server_connect_button.pressed.connect(connect_to_server)
    window.chiller_button.pressed.connect(chiller_start)
    window.goto_button.pressed.connect(goto_coordinate_script)
    window.dome_tracking_toggle.stateChanged.connect(toggle_dome_tracking)
    window.mount_tracking_toggle.stateChanged.connect(toggle_mount_tracking)
    window.command_execute.pressed.connect(command_entry)
    window.update_button.pressed.connect(timer_handlings)
    sys.exit(app.exec())
