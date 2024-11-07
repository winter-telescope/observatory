#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Oct 23 07:26:18 2024

@author: winter
"""

import pandas as pd
from astropy.coordinates import SkyCoord
import astropy.units as u

# Special M31 coordinates
M31_coords = [
    (11.3751416, 41.9797358),
    (10.6189082, 41.3531119),
    (10.2313704, 40.598088)
]

# Function to load the text file using pandas
def load_field_txt(file_path):
    # Assign column names manually if they are missing or incorrect
    column_names = ['ID', 'RA', 'Dec', 'EBV', 'Gal Long', 'Gal Lat', 'Ecl Long', 'Ecl Lat', 'Entry']
    
    # Load text file as CSV with specified column names if necessary
    df = pd.read_csv(file_path, delim_whitespace=True, comment='#', names=column_names)
    return df

# Function to compute Galactic and Ecliptic coordinates using astropy
def compute_coordinates(ra, dec):
    # Create SkyCoord object from RA/Dec
    sky_coord = SkyCoord(ra=ra * u.deg, dec=dec * u.deg, frame='icrs')
    
    # Convert to Galactic coordinates
    gal_coord = sky_coord.galactic
    gal_long = gal_coord.l.deg
    gal_lat = gal_coord.b.deg
    
    # Convert to Ecliptic coordinates
    ecl_coord = sky_coord.barycentricmeanecliptic
    ecl_long = ecl_coord.lon.deg
    ecl_lat = ecl_coord.lat.deg
    
    return gal_long, gal_lat, ecl_long, ecl_lat

# Function to add special M31 fields to the DataFrame
def add_m31_fields(df_csv, start_id, start_entry):
    # Loop through the M31 coordinates and append them to the DataFrame
    for ra, dec in M31_coords:
        gal_long, gal_lat, ecl_long, ecl_lat = compute_coordinates(ra, dec)
        
        new_row = {
            'ID': start_id,
            'RA': ra,
            'Dec': dec,
            'EBV': 1.0,  # Use a default value or adjust as needed
            'Gal Long': gal_long,
            'Gal Lat': gal_lat,
            'Ecl Long': ecl_long,
            'Ecl Lat': ecl_lat,
            'Entry': start_entry
        }
        df_csv = df_csv.append(new_row, ignore_index=True)
        start_id += 1
        start_entry += 1
    return df_csv, start_id, start_entry

# Function to load the CSV files, append new IDs and Entries, and track the new field numbers for each file
def load_and_append_csv_files(df, csv_files, start_id, start_entry):
    new_field_numbers = {}  # Dictionary to store new field numbers for each CSV file
    
    for file in csv_files:
        # Load the CSV file
        df_csv = pd.read_csv(file)
        # Select the required columns
        df_csv = df_csv[['ID', 'RA', 'Dec', 'EBV', 'Gal Long', 'Gal Lat', 'Ecl Long', 'Ecl Lat', 'Entry']]
        
        # If it's the very_nearby_galaxies_winter_fields.csv file, add the M31 fields
        if 'very_nearby_galaxies_winter_fields.csv' in file:
            df_csv, start_id, start_entry = add_m31_fields(df_csv, start_id + 1, start_entry + 1)
        
        # Generate new unique IDs starting from the current max ID
        new_ids = list(range(start_id + 1, start_id + 1 + len(df_csv)))
        df_csv['ID'] = new_ids
        
        # Generate new Entry numbers starting from the current max Entry
        new_entries = list(range(start_entry + 1, start_entry + 1 + len(df_csv)))
        df_csv['Entry'] = new_entries
        
        # Append the new CSV data to the original dataframe
        df = pd.concat([df, df_csv], ignore_index=True)
        
        # Store the new field numbers for this file
        new_field_numbers[file] = new_ids
        
        # Update start_id and start_entry for the next file
        start_id = new_ids[-1]
        start_entry = new_entries[-1]
    
    return df, new_field_numbers

# Define paths
txt_file_path = '/home/winter/WINTER_GIT/observatory/scheduler/daily_scheduler/data/WINTER_fields_orig.txt'  # Replace with actual path
csv_file_paths = ['/home/winter/WINTER_GIT/observatory/scheduler/daily_scheduler/data/very_nearby_galaxies_winter_fields.csv',
                  '/home/winter/WINTER_GIT/observatory/scheduler/daily_scheduler/data/winter_fields_nearby.csv',
                  '/home/winter/WINTER_GIT/observatory/scheduler/daily_scheduler/data/winter_fields_ulirgs.csv']  # Replace with actual CSV paths
output_txt_file = '/home/winter/WINTER_GIT/observatory/scheduler/daily_scheduler/data/WINTER_fields_mod.txt'  # Replace with desired output file path

# Load the original fields from the text file using pandas
df_fields = load_field_txt(txt_file_path)

# Get the max ID and Entry from the original dataframe
max_id = df_fields['ID'].max()
max_entry = df_fields['Entry'].max()

# Load the CSV files, append new IDs and Entries, and track new field numbers
df_fields, new_field_numbers = load_and_append_csv_files(df_fields, csv_file_paths, max_id, max_entry)

# Save the final dataframe back to a text file
df_fields.to_csv(output_txt_file, sep=' ', index=False, float_format='%.5f')

# Print new field numbers for each CSV file
for file, ids in new_field_numbers.items():
    print(f"New fields from {file}: {ids}")

print("Field appending complete.")
