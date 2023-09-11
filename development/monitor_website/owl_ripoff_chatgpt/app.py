#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Sep  7 14:49:45 2023

@author: nlourie
"""

from flask import Flask, render_template
import json

app = Flask(__name__)

# Load data from the JSON file
with open("data.json", "r") as json_file:
    data = json.load(json_file)

# Load the config file
with open("config.json", "r") as config_file:
    config = json.load(config_file)

# Define a route to render the HTML page
@app.route("/")
def index():
    # Create a dictionary to hold the data for each box
    box_data = {}

    # Iterate through the boxes defined in the config file
    for box in config.get("boxes", []):
        source_key = box.get("_source")
        if source_key:
            # Get the corresponding data from the JSON file
            box_data[box["_id"]] = data.get(source_key)

    return render_template("index.html", boxes=config.get("boxes", []), box_data=box_data)

if __name__ == "__main__":
    app.run(debug=True)
