#!/usr/bin/env python3

import re
import numpy as np
import scipy.stats as stats
import sys
import csv
import os
import shutil

def extract_durations(log_file):
    """Extracts execution times from the log file, ignoring cold starts."""
    durations = []
    with open(log_file, 'r') as file:
        content = file.read()
        
        pattern = re.findall(r'(?:Billed Duration for Request|Execution Time for Trace ID) .*?: (\d+) ms\n.*?Cold Start: (true|false)', content, re.DOTALL)
        
        for duration, cold_start in pattern:
            if cold_start.lower() == 'false':  # Ignore cold starts
                durations.append(int(duration))
    
    return durations

def compute_percentage_differences(durations1, durations2):
    """Computes percentage differences for matching durations."""
    differences = []
    
    min_len = min(len(durations1), len(durations2))
    for i in range(min_len):
        time1 = durations1[i]
        time2 = durations2[i]
        percent_diff = abs(time1 - time2) / max(time1, time2) * 100
        differences.append((time1, time2, percent_diff))
    
    return differences

def compute_ci_width(differences, confidence=0.99):
    """Computes the width of the confidence interval for the differences, ensuring no negative lower bound."""
    if not differences:
        return None
    
    percent_diffs = [diff[2] for diff in differences]
    mean_diff = np.mean(percent_diffs)
    sem = stats.sem(percent_diffs)  # Standard Error of the Mean
    ci_range = stats.t.interval(confidence, len(percent_diffs)-1, loc=mean_diff, scale=sem)
    
    # Ensure the lower bound is non-negative
    ci_lower = max(0, ci_range[0])
    ci_upper = ci_range[1]
    ci_width = ci_upper - ci_lower  # Compute CI width
    
    return ci_width, (ci_lower, ci_upper)

def save_statistics_to_csv(differences, ci_width, ci_range, output_file):
    """Saves the statistical results to a CSV file."""
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["99% Confidence Interval Width", ci_width])
        writer.writerow(["99% Confidence Interval Lower Bound", ci_range[0]])
        writer.writerow(["99% Confidence Interval Upper Bound", ci_range[1]])
        writer.writerow([])
        writer.writerow(["Duration V1 (ms)", "Duration V2 (ms)", "Percentage Difference (%)"])
        writer.writerows(differences)

def find_log_files(directory):
    """Finds the two log files in the given directory based on expected naming patterns."""
    log_files = [f for f in os.listdir(directory) if f.endswith(".log")]
    
    input_logs = sorted(log_files, key=lambda x: int(re.search(r'input(\d+)', x).group(1)))
    
    if len(input_logs) < 2:
        print("Error: Not enough log files found in the directory.")
        sys.exit(1)
    
    return os.path.join(directory, input_logs[0]), os.path.join(directory, input_logs[1])

def move_processed_logs(log1, log2, processed_dir):
    """Moves processed log files to another directory."""
    os.makedirs(processed_dir, exist_ok=True)
    
    shutil.move(log1, os.path.join(processed_dir, os.path.basename(log1)))
    shutil.move(log2, os.path.join(processed_dir, os.path.basename(log2)))
    print(f"Moved processed logs to {processed_dir}")

def main():
    if len(sys.argv) != 2:
        print("Usage: python3 ci_calculator.py <configuration_name>")
        sys.exit(1)
    
    config_name = sys.argv[1]
    log_directory = os.path.join("logs", "tmp", config_name)
    processed_directory = os.path.join("logs", "processed", config_name)
    
    log1_file, log2_file = find_log_files(log_directory)

    # Extract file names without extension
    log1_name = os.path.splitext(os.path.basename(log1_file))[0]
    log2_name = os.path.splitext(os.path.basename(log2_file))[0]
    
    # Create a unique statistics file name
    statistics_filename = f"statistics_{log1_name}_{log2_name}.csv"
    statistics_file = os.path.join("statistics", config_name, statistics_filename)
    
    durations1 = extract_durations(log1_file)
    durations2 = extract_durations(log2_file)
    
    differences = compute_percentage_differences(durations1, durations2)
    result = compute_ci_width(differences)
    
    if result:
        ci_width, ci_range = result
        print(f"99% Confidence Interval Width: {ci_width:.2f}%")
        print(f"99% Confidence Interval: {ci_range}")
        save_statistics_to_csv(differences, ci_width, ci_range, statistics_file)
        print(f"Statistics saved to {statistics_file}")
        
        move_processed_logs(log1_file, log2_file, processed_directory)
    else:
        print("No matching data found for comparison.")

if __name__ == "__main__":
    main()