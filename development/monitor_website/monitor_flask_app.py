#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Sep  7 13:41:25 2023

@author: nlourie
"""

from flask import Flask, render_template, jsonify
import json
import threading
import time

app = Flask(__name__)

# Define the allowed temperature range
min_temp = 18
max_temp = 28

# Initialize equipment data for different systems
systems_data = {
    "Chiller": {
        "chiller1": {"temperature": 25},
        "chiller2": {"temperature": 30},
        "chiller3": {"temperature": 22},
        "chiller4": {"temperature": 29},
        # Add more chiller equipment and initial temperatures as needed
    },
    "Dome": {
        "dome_sensor1": {"temperature": 22.5},
        "dome_sensor2": {"temperature": 29.2},
        "dome_sensor3": {"temperature": 23.8},
        "dome_sensor4": {"temperature": 27.3},
        # Add more dome sensors and initial values as needed
    },
    # Add more systems and equipment data as needed
}

# Function to continuously monitor and update equipment temperatures
def update_temperatures():
    while True:
        for system, equipment_data in systems_data.items():
            for equipment, data in equipment_data.items():
                # Simulate temperature changes (you can replace this with actual data retrieval)
                data["temperature"] += 0.1
                
                # Check if temperatures are within the allowed range
                temperature = data["temperature"]
                if min_temp <= temperature <= max_temp:
                    data["status"] = "green"
                else:
                    data["status"] = "red"

        # Sleep for a while before checking again (adjust the interval as needed)
        time.sleep(5)

# Start the temperature monitoring thread
temperature_thread = threading.Thread(target=update_temperatures)
temperature_thread.daemon = True
temperature_thread.start()

@app.route('/')
def index():
    return render_template('index.html', systems_data=systems_data)

if __name__ == '__main__':
    app.run(debug=True)
