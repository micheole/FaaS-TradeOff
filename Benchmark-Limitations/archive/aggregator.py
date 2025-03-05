# aggregator.py

#!/usr/bin/env python3
"""
Aggregator Script

This script consolidates individual log files into a single CSV file
for easier analysis and reporting.

Usage:
    python aggregator.py --logs_dir processed_logs --output aggregated_logs.csv
"""

import os
import sys
import argparse
import logging
import csv

from utils.logger import setup_logger

def setup_aggregator_logger():
    logger = setup_logger(name="Aggregator", log_file="aggregator.log")
    return logger

def aggregate_logs(logs_dir, output_file, logger):
    """
    Aggregate log files from the specified directory into a single CSV file.
    
    Parameters:
    - logs_dir: Directory containing individual log files.
    - output_file: Path to the output CSV file.
    """
    if not os.path.exists(logs_dir):
        logger.error(f"Logs directory does not exist: {logs_dir}")
        sys.exit(1)
    
    aggregated_data = []
    headers = set()
    
    # Iterate over all log files in the logs_dir
    for filename in os.listdir(logs_dir):
        if filename.endswith('.txt'):
            filepath = os.path.join(logs_dir, filename)
            with open(filepath, 'r') as f:
                for line in f:
                    # Assuming log lines are in "key: value" format, separated by commas
                    entry = {}
                    parts = line.strip().split(',')
                    for part in parts:
                        if ':' in part:
                            key, value = part.split(':', 1)
                            entry[key.strip()] = value.strip()
                    if entry:
                        aggregated_data.append(entry)
                        headers.update(entry.keys())
    
    if not aggregated_data:
        logger.warning(f"No data found in logs directory: {logs_dir}")
        return
    
    headers = sorted(headers)
    
    # Write aggregated data to CSV
    with open(output_file, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=headers)
        writer.writeheader()
        for data in aggregated_data:
            writer.writerow(data)
    
    logger.info(f"Aggregated logs written to {output_file}")

def main():
    parser = argparse.ArgumentParser(description="Aggregate log files into a CSV.")
    parser.add_argument('--logs_dir', type=str, required=True, help='Directory containing log files to aggregate.')
    parser.add_argument('--output', type=str, required=True, help='Output CSV file path.')
    args = parser.parse_args()
    
    logger = setup_aggregator_logger()
    logger.info(f"Starting aggregation of logs from {args.logs_dir} into {args.output}")
    
    aggregate_logs(args.logs_dir, args.output, logger)
    
    logger.info("Aggregation completed successfully.")

if __name__ == "__main__":
    main()
