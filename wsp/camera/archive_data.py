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
from typing import Optional


# Paths
source_dir = os.path.expanduser("~/data/images")
backup_dir = "/data/images"
log_file = os.path.expanduser("~/data/data_archiver.log")  # Log file path

# Ensure the log directory exists
os.makedirs(os.path.dirname(log_file), exist_ok=True)

# Date format used for folders (YYYYMMDD)
date_format = "%Y%m%d"

# Set up logging
logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


def copy_and_verify(src: str, dst: str) -> bool:
    """
    Copies a directory from src to dst and verifies that all files were copied correctly.

    Args:
        src (str): The source directory path.
        dst (str): The destination directory path.

    Returns:
        bool: True if all files are copied and verified successfully, False otherwise.
    """
    shutil.copytree(src, dst)
    src_files = [os.path.join(root, file) for root, _, files in os.walk(src) for file in files]
    dst_files = [os.path.join(dst, os.path.relpath(file, src)) for file in src_files]

    logging.info(f"Copying {len(src_files)} files from {src} to {dst}.")

    for i, (src_file, dst_file) in enumerate(zip(src_files, dst_files), 1):
        if not os.path.exists(dst_file) or os.path.getsize(src_file) != os.path.getsize(dst_file):
            logging.error(f"Verification failed for {src_file} to {dst_file}.")
            return False
        logging.info(f"Verified {i}/{len(src_files)}: {dst_file}")

    return True


def move_folders_to_backup(days_old: int, dry_run: bool = False) -> None:
    """
    Moves folders from the source directory to the backup directory if they are older than a given number of days.

    Args:
        days_old (int): The number of days old the folders need to be to move them.
        dry_run (bool): If True, only log the actions without executing them.
    """
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
                        logging.info(f"Starting to move folder from {folder_path} to {backup_path}.")
                        if copy_and_verify(folder_path, backup_path):
                            shutil.rmtree(folder_path)
                            logging.info(
                                f"Successfully moved folder from {folder_path} to {backup_path} after verification."
                            )
                        else:
                            shutil.rmtree(backup_path)
                            logging.error(f"Failed to verify folder {folder_path}. Aborting move.")
            except ValueError:
                continue


def delete_old_folders(days_old: int, dry_run: bool = False) -> None:
    """
    Deletes folders from the backup directory if they are older than a given number of days.

    Args:
        days_old (int): The number of days old the folders need to be to delete them.
        dry_run (bool): If True, only log the actions without executing them.
    """
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
                        logging.info(f"Deleting old backup folder {folder_path}.")
                        shutil.rmtree(folder_path)
                        logging.info(f"Deleted old backup folder {folder_path}.")
            except ValueError:
                continue


def main(move_days_old: int, delete_days_old: int, dry_run: bool) -> None:
    """
    Main function to move and delete old image folders based on specified criteria.

    Args:
        move_days_old (int): The number of days old for moving folders to backup.
        delete_days_old (int): The number of days to keep folders before deleting.
        dry_run (bool): If True, only log the actions without executing them.
    """
    logging.info("Script started.")
    move_folders_to_backup(days_old=move_days_old, dry_run=dry_run)
    delete_old_folders(days_old=delete_days_old, dry_run=dry_run)
    logging.info("Script completed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Move and delete old image folders.")
    parser.add_argument(
        "--move_days_old",
        type=int,
        default=1,
        help="Number of days old for moving folders to backup.",
    )
    parser.add_argument(
        "--delete_days_old",
        type=int,
        default=60,
        help="Number of days to keep folders before deleting.",
    )
    parser.add_argument(
        "--dry_run", action="store_true", help="Print actions without executing them."
    )

    args = parser.parse_args()
    main(move_days_old=args.move_days_old, delete_days_old=args.delete_days_old, dry_run=args.dry_run)


