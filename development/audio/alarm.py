#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jul  1 11:03:28 2020

test script to wake up monitor and play audio alert.


@author: nlourie
"""

import sounddevice
import soundfile
import os
import time




time.sleep(70)



# wake up monitor
bashCommand = "caffeinate -t 1"
os.system(bashCommand)

# play the alert sound
alarm_sound_file = 'move_alert.wav'
   
alarm_sound,fs = soundfile.read(alarm_sound_file)

sounddevice.play(alarm_sound, fs)

"""

def set_priority(self,priority):
    if priority.lower() == 'low':
        self.priority = 'low'
        self.alarm_sound = self.alarm_sound_low
    else:
        self.priority = 'high'
        self.alarm_sound = self.alarm_sound_high
        
    self.sound = self.alarm_sound[0]
    self.sound_fs = self.alarm_sound[1]
    self.sound_length = len(self.sound) * (1/self.sound_fs)*1000 # ms

def sound_once(self):
    sounddevice.play(self.sound, self.sound_fs)
"""