#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Oct 23 07:26:18 2024

@author: winter
"""

import pandas as pd

# Function to load the text file using pandas
def load_field_txt(file_path):
    # Assign column names manually if they are missing or incorrect
    column_names = ['ID', 'RA', 'Dec', 'EBV', 'Gal Long', 'Gal Lat', 'Ecl Long', 'Ecl Lat', 'Entry']
    
    # Load text file as CSV with specified column names if necessary
    df = pd.read_csv(file_path, delim_whitespace=True, comment='#', names=column_names)
    return df

# Function to load the CSV files, append new IDs and Entries, and track the new field numbers for each file
def load_and_append_csv_files(df, csv_files, start_id, start_entry):
    new_field_numbers = {}  # Dictionary to store new field numbers for each CSV file
    
    for file in csv_files:
        # Load the CSV file
        df_csv = pd.read_csv(file)
        # Select the required columns
        df_csv = df_csv[['ID', 'RA', 'Dec', 'EBV', 'Gal Long', 'Gal Lat', 'Ecl Long', 'Ecl Lat', 'Entry']]
        
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
txt_file_path = '/home/winter/WINTER_GIT/observatory/scheduler/daily_scheduler/data/WINTER_fields.txt'  # Replace with actual path
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