#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Sep  7 16:40:52 2023

@author: nlourie
"""

from flask import Flask, render_template, Response
import json
import time

app = Flask(__name__)

# Sample JSON data
data = {
    "column1": {
        "box1": {
            "header": "Chiller",
            "key1": "Value1",
            "key2": "Value2"
        },
        "box2": {
            "header": "Subsystem 1",
            "key1": "Value1",
            "key2": "Value2"
        }
    },
    "column2": {
        "box1": {
            "header": "Dome",
            "key1": "Value1",
            "key2": "Value2"
        },
        "box2": {
            "header": "Camera",
            "key1": "Value1",
            "key2": "Value2"
        }
    }
}

# Function to generate and update JSON data (for demonstration)
def generate_data():
    # while True:
    #     # Simulate data updates
    #     data["column1"]["box1"]["key1"] = str(time.time())
    #     data["column2"]["box2"]["key2"] = str(time.time())
    #     yield f"data: {json.dumps(data)}\n\n"
    #     time.sleep(1)  # Update every second
    # Simulate data updates
    data["column1"]["box1"]["key1"] = str(time.time())
    data["column2"]["box2"]["key2"] = str(time.time())
    yield f"data: {json.dumps(data)}\n\n"

# Configure a static route for the 'static' directory
app.static_folder = 'static'
app.static_url_path = '/static'

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_data')
def get_data():
    return Response(generate_data(), content_type='text/event-stream')

if __name__ == '__main__':
    app.run(debug=True)
