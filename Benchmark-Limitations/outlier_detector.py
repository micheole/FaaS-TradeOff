#!/usr/bin/env python3
#
# outlier_detector.py
#
# Usage:
#   python3 outlier_detector.py <log_directory>
#
# Description:
#   1. Parses log files from AWS and GCP to extract Unique IDs and Execution Durations.
#   2. Identifies outlier durations indicating potential cold starts using the IQR method.
#   3. Writes the processed data to a new log file with the same name.
#   4. Removes the original log file after processing.

import sys
import os
import re
import pandas as pd
import numpy as np
from datetime import datetime

def parse_log_file(file_path):
    """
    Parses a single log file to extract Unique_ID, Duration_ms, and Provider.
    
    Args:
        file_path (str): Path to the .log file.
    
    Returns:
        pd.DataFrame: DataFrame with columns ['Unique_ID', 'Duration_ms', 'Provider']
    """
    # Regular expressions for AWS and GCP logs
    pattern_unique_id = re.compile(r'Unique ID:\s*([a-f0-9\-]+),')
    pattern_billed_duration = re.compile(r'Billed Duration for Request [a-f0-9\-]+:\s*(\d+)\s*ms')
    pattern_execution_time = re.compile(r'Execution Time for Trace ID [a-f0-9\-]+:\s*(\d+)\s*ms')

    data = []
    unique_id = None
    provider = None

    with open(file_path, 'r') as f:
        for line in f:
            # Extract Unique ID
            if 'Unique ID:' in line:
                match = pattern_unique_id.search(line)
                if match:
                    unique_id = match.group(1)

            # Extract Billed Duration for AWS
            if 'Billed Duration for Request' in line:
                match = pattern_billed_duration.search(line)
                if match and unique_id:
                    duration = int(match.group(1))
                    provider = 'AWS'
                    data.append({'Unique_ID': unique_id, 'Duration_ms': duration, 'Provider': provider, 'Outlier': False})
                    unique_id = None  # Reset for next entry

            # Extract Execution Time for GCP
            if 'Execution Time for Trace ID' in line:
                match = pattern_execution_time.search(line)
                if match and unique_id:
                    duration = int(match.group(1))
                    provider = 'GCP'
                    data.append({'Unique_ID': unique_id, 'Duration_ms': duration, 'Provider': provider, 'Outlier': False})
                    unique_id = None  # Reset for next entry

    df = pd.DataFrame(data)
    return df

def detect_outliers(df, multiplier=1.5):
    """
    Detects outliers in Duration_ms using the IQR method for each provider.
    
    Args:
        df (pd.DataFrame): DataFrame with 'Duration_ms' and 'Provider' columns.
        multiplier (float): Multiplier for IQR to define outliers.
    
    Returns:
        pd.DataFrame: DataFrame with an updated 'Outlier' column.
    """
    for provider in df['Provider'].unique():
        provider_df = df[df['Provider'] == provider]
        Q1 = provider_df['Duration_ms'].quantile(0.25)
        Q3 = provider_df['Duration_ms'].quantile(0.75)
        IQR = Q3 - Q1
        lower_bound = Q1 - multiplier * IQR
        upper_bound = Q3 + multiplier * IQR

        # Identify outliers
        outliers = (df['Provider'] == provider) & ((df['Duration_ms'] < lower_bound) | (df['Duration_ms'] > upper_bound))
        df.loc[outliers, 'Outlier'] = True

    return df

def process_log_file(file_path):
    """
    Processes a single log file: parses, detects outliers, writes processed data, and deletes the original file.
    
    Args:
        file_path (str): Path to the .log file.
    """
    print(f"Processing file: {file_path}")
    
    # Parse the log file
    df = parse_log_file(file_path)
    
    if df.empty:
        print(f"No valid entries found in {file_path}. Skipping.")
        return
    
    # Detect outliers
    df = detect_outliers(df)

    # Extract configuration name from the file path
    config_name = os.path.basename(os.path.dirname(file_path))

    # Define the output file path
    anomaly_dir_base = "logs/anomaly_detected"
    anomaly_dir = os.path.join(anomaly_dir_base, config_name)

    # Ensure the anomaly directory exists
    os.makedirs(anomaly_dir, exist_ok=True)

    # Define the output file path, preserving the original file name
    output_file_name = os.path.basename(file_path)
    output_file_path = os.path.join(anomaly_dir, output_file_name)
    
    # Write the processed data to the same file (overwriting)
    df.to_csv(output_file_path, index=False)
    print(f"Processed data written to: {output_file_path}")

    # Move the original log file to the processed directory
    processed_dir = "logs/processed"
    processed_file_path = os.path.join(processed_dir, os.path.basename(file_path))
    os.rename(file_path, processed_file_path)
    print(f"Original log file moved to: {processed_file_path}")
    
    # Remove the original log file (if different from output, but here it's the same)
    # Since we overwrote, no need to delete. If you have a separate original, implement accordingly.
    # If you prefer to archive originals, uncomment the following lines:
    """
    archive_dir = os.path.join(os.path.dirname(file_path), 'archive')
    os.makedirs(archive_dir, exist_ok=True)
    os.rename(file_path, os.path.join(archive_dir, os.path.basename(file_path)))
    print(f"Original file moved to archive: {archive_dir}")
    """

def main():
    if len(sys.argv) != 2:
        print("Usage: python3 outlier_detector.py <log_directory>")
        print("Example: python3 outlier_detector.py logs/call-limited")
        sys.exit(1)

    log_directory = sys.argv[1]

    if not os.path.isdir(log_directory):
        print(f"Error: The directory '{log_directory}' does not exist.")
        sys.exit(1)

    # Iterate through all .log files in the directory
    for root, dirs, files in os.walk(log_directory):
        for file in files:
            if file.endswith('.log'):
                file_path = os.path.join(root, file)
                process_log_file(file_path)
    
    print("All log files have been processed.")

if __name__ == "__main__":
    main()
