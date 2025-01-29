#!/usr/bin/env python3
"""
process_logs_sieve.py

This script parses log files to extract durations from multiple patterns, calculates the mean duration
and 95% confidence intervals for the Sieve of Eratosthenes logs, and saves the results to a CSV file.

Usage:
    python process_logs_sieve.py --input_dir path/to/logs --output_file results.csv

Dependencies:
    - pandas
    - numpy
    - scipy
"""

import os
import re
import argparse
import pandas as pd
import numpy as np
from scipy import stats


def extract_durations(log_file_path):
    """
    Extracts durations from a single log file.

    Args:
        log_file_path (str): Path to the log file.

    Returns:
        list: A list of durations in milliseconds.
    """
    durations = []
    # Regular expression to match both patterns
    patterns = [
        r'Billed Duration for Request [\w-]+: (\d+) ms',
        r'Execution Time for Trace ID [\w-]+: (\d+) ms'
    ]

    try:
        with open(log_file_path, 'r') as file:
            for line in file:
                for pattern in patterns:
                    match = re.search(pattern, line)
                    if match:
                        duration = int(match.group(1))
                        durations.append(duration)
                        break  # Stop checking other patterns for the same line
    except Exception as e:
        print(f"Error reading {log_file_path}: {e}")

    return durations


def filter_durations(durations, threshold_factor=0.1):
    """
    Filters out anomalous durations that are too low compared to the mean.

    Args:
        durations (list): List of durations.
        threshold_factor (float): Fraction of the mean duration to use as the lower threshold.

    Returns:
        list: Filtered durations.
    """
    mean_duration = np.mean(durations)
    threshold = mean_duration * threshold_factor
    filtered_durations = [d for d in durations if d >= threshold]

    if len(filtered_durations) < len(durations):
        print(f"Filtered {len(durations) - len(filtered_durations)} low durations (threshold: {threshold:.2f} ms)")

    return filtered_durations


def calculate_statistics(durations, confidence=0.95):
    """
    Calculates mean and confidence interval for a list of durations.

    Args:
        durations (list): List of durations in milliseconds.
        confidence (float): Confidence level for the interval.

    Returns:
        tuple: (mean, ci_lower, ci_upper)
    """
    n = len(durations)
    if n == 0:
        return (None, None, None)

    mean = np.mean(durations)
    sem = stats.sem(durations)  # Standard error of the mean
    if sem == 0:
        # If SEM is zero, CI cannot be calculated
        return (mean, mean, mean)

    h = sem * stats.t.ppf((1 + confidence) / 2., n - 1)
    ci_lower = mean - h
    ci_upper = mean + h
    return (mean, ci_lower, ci_upper)


def parse_arguments():
    """
    Parses command-line arguments.

    Returns:
        argparse.Namespace: Parsed arguments.
    """
    parser = argparse.ArgumentParser(description="Process log files to calculate mean durations and confidence intervals.")
    parser.add_argument('--input_dir', type=str, required=True, help='Path to the directory containing log files.')
    parser.add_argument('--output_file', type=str, default='results.csv', help='Path to the output CSV file.')
    return parser.parse_args()


def main():
    args = parse_arguments()
    input_dir = args.input_dir
    output_file = args.output_file

    # Initialize a list to store results
    results = []

    # Walk through the input directory to find all .log files
    for root, dirs, files in os.walk(input_dir):
        for file in files:
            if file.endswith('.log'):
                log_file_path = os.path.join(root, file)

                # Extract Provider and Num from the directory structure
                # Assuming the structure: .../sieve-of-eratosthenes/gcp/raw/20241231/log1000000.log
                path_parts = root.split(os.sep)
                try:
                    provider = path_parts[-4]  # e.g., gcp
                    # Extract "Num" from the log file name, e.g., log1000000.log
                    num_match = re.search(r'log-num-(\d+)', file, re.IGNORECASE)
                    if num_match:
                        num = int(num_match.group(1))
                    else:
                        num = None
                except IndexError:
                    provider = 'Unknown'
                    num = None

                # Extract durations from the log file
                durations = extract_durations(log_file_path)

                # Filter out durations that are way too low
                filtered_durations = filter_durations(durations)

                # Calculate statistics
                mean, ci_lower, ci_upper = calculate_statistics(filtered_durations)

                # Append the results
                results.append({
                    'Provider': provider.upper(),
                    'Num': num,
                    'Log_File': file,
                    'Mean_Duration_ms': mean,
                    'CI_Lower_ms': ci_lower,
                    'CI_Upper_ms': ci_upper,
                    'Num_Runs': len(filtered_durations)
                })

                print(f"Processed {file}: Mean={mean} ms, CI=({ci_lower}, {ci_upper})")

    # Create a DataFrame from the results
    results_df = pd.DataFrame(results)

    # Sort the DataFrame for better readability
    results_df = results_df.sort_values(by=['Provider', 'Num'])

    # Save the results to a CSV file
    results_df.to_csv(output_file, index=False)
    print(f"\nAll results have been saved to {output_file}")


if __name__ == "__main__":
    main()
