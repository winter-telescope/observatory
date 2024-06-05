#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jun  5 14:18:37 2024

@author: chatGPT
"""
import os
import shutil
from datetime import datetime, timedelta
import argparse
import logging

# Paths
source_dir = os.path.expanduser('~/data/images')
backup_dir = '/data/images'

# Date format used for folders (YYYYMMDD)
date_format = "%Y%m%d"

# Set up logging
log_file = '~/data/data_archiver.log'  # Adjust the path as needed
logging.basicConfig(filename=log_file, level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Function to move folders to backup directory
def move_folders_to_backup(days_old, dry_run=False):
    cutoff_date = datetime.today() - timedelta(days=days_old)
    for folder_name in os.listdir(source_dir):
        folder_path = os.path.join(source_dir, folder_name)
        if os.path.isdir(folder_path):
            try:
                folder_date = datetime.strptime(folder_name, date_format)
                if folder_date < cutoff_date:
                    backup_path = os.path.join(backup_dir, folder_name)
                    if dry_run:
                        logging.info(f"Would move folder from {folder_path} to {backup_path}.")
                    else:
                        shutil.move(folder_path, backup_path)
                        logging.info(f"Moved folder from {folder_path} to {backup_path}.")
            except ValueError:
                # Skip folders that do not follow the date format
                continue

# Function to delete old folders from the backup directory
def delete_old_folders(days_old, dry_run=False):
    cutoff_date = datetime.today() - timedelta(days=days_old)
    for folder_name in os.listdir(backup_dir):
        folder_path = os.path.join(backup_dir, folder_name)
        if os.path.isdir(folder_path):
            try:
                folder_date = datetime.strptime(folder_name, date_format)
                if folder_date < cutoff_date:
                    if dry_run:
                        logging.info(f"Would delete old backup folder {folder_path}.")
                    else:
                        shutil.rmtree(folder_path)
                        logging.info(f"Deleted old backup folder {folder_path}.")
            except ValueError:
                # Skip folders that do not follow the date format
                continue

# Main function
def main(move_days_old, delete_days_old, dry_run):
    logging.info("Script started.")
    move_folders_to_backup(days_old=move_days_old, dry_run=dry_run)
    delete_old_folders(days_old=delete_days_old, dry_run=dry_run)
    logging.info("Script completed.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Move and delete old image folders.')
    parser.add_argument('--move_days_old', type=int, default=1, help='Number of days old for moving folders to backup.')
    parser.add_argument('--delete_days_old', type=int, default=60, help='Number of days to keep folders before deleting.')
    parser.add_argument('--dry_run', action='store_true', help='Print actions without executing them.')
    
    args = parser.parse_args()
    main(move_days_old=args.move_days_old, delete_days_old=args.delete_days_old, dry_run=args.dry_run)
