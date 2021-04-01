# -*- coding: utf-8 -*-
"""
Created on Wed Mar 31 17:33:57 2021

@author: nlourie
"""
import yaml

state_str = '{"telescope" : On, "other_thing" : Off, "fault" : 0x140}'

state = yaml.load(state_str, yaml.FullLoader)


fault_msg = dict({0x1   : 'Dome Drive Communication Lost',
                  0x2   : 'PLC Communication Lost',
                  0x4   : 'Weather Communication Lost',
                  0x8   : 'Fire Alarm',
                  0x10  : 'Door Open',
                  0x20  : 'ESTOP',
                  0x40  : 'Drive Over Temp',
                  0x80  : 'Drive Internal Voltage',
                  0x100 : 'Drive Over Voltage',
                  0x200 : 'Drive Over Current',
                  0x400 : 'Drive Motor Open Winding',
                  0x800 : 'Drive Bad Encoder'})

config = yaml.load('dome_faults.yaml', yaml.FullLoader)



for fault_code in fault_msg.keys():
    if state['fault'] & fault_code:
        print(fault_msg[fault_code])
