# -*- coding: utf-8 -*-
"""
Created on Wed Mar 31 17:33:57 2021

@author: nlourie
"""
import yaml

state_str = '{"telescope" : On, "other_thing" : Off, "fault" : 129}'

state = yaml.load(state_str, yaml.FullLoader)



config_file = 'dome_faults.yaml'

config = yaml.load(open(config_file), Loader = yaml.FullLoader)

for fault_code in config['Dome_Status_Dict']['Faults']:
    if state['fault'] & fault_code:
        
        # print the message (ie log it)
        print(config['Dome_Status_Dict']['Faults'][fault_code]['msg'])
            
        # assign the variable to true
        state.update({config['Dome_Status_Dict']['Faults'][fault_code]['field'] : 1})
    else:
        # assign the variable to false
        state.update({config['Dome_Status_Dict']['Faults'][fault_code]['field'] : 0})