#!/usr/bin/env python3

import re
import sys
import os
import numpy as np

def extract_runs(log_file):
    """
    Extracts runs from the log file.
    
    For each matching log entry, returns a tuple:
      (duration, is_cold_start)
    
    A run is considered a cold start if the "Cold Start:" flag is "true".
    """
    runs = []
    with open(log_file, 'r') as file:
        content = file.read()
        pattern = re.findall(
            r'(?:Billed Duration for Request|Execution Time for Unique ID|Execution Time for Trace ID) .*?: (\d+) ms\n.*?Cold Start: (true|false)',
            content,
            re.DOTALL
        )
        for duration, cold_start in pattern:
            runs.append((int(duration), cold_start.lower() == 'true'))
    return runs

def compute_percentage_differences(durations1, durations2):
    """
    Computes percentage differences for matching durations.
    
    For each index i (up to the length of the shorter list), the percentage difference is:
      ((time2 - time1) / time1) * 100.
    """
    differences = []
    min_len = min(len(durations1), len(durations2))
    for i in range(min_len):
        time1 = durations1[i]
        time2 = durations2[i]
        if time1 == 0 and time2 == 0:
            percent_diff = 0  # Avoid division by zero
        elif time1 == 0 or time2 == 0:
            percent_diff = float('inf')  # Undefined percentage change
        else:
            percent_diff = ((time2 - time1) / time1) * 100
        differences.append(percent_diff)
    return differences

def bootstrap_confidence_interval(differences, iterations=10000, lower_percentile=2.5, upper_percentile=97.5):
    """
    Computes the bootstrapped percentile confidence interval for the median of the differences.
    
    Resamples the list with replacement for the given number of iterations. For each
    bootstrap sample, calculates the median and then determines the lower and upper
    percentiles of the distribution.
    
    Returns a tuple: (ci_width, (ci_lower, ci_upper)).
    """
    if not differences:
        return None
    differences = np.array(differences)
    boot_stats = []
    n = len(differences)
    
    for i in range(iterations):
        sample = np.random.choice(differences, size=n, replace=True)
        boot_stats.append(np.median(sample))
    
    boot_stats = sorted(boot_stats)
    lower_idx = int(iterations * lower_percentile / 100)
    upper_idx = int(iterations * upper_percentile / 100)
    
    ci_lower = boot_stats[lower_idx]
    ci_upper = boot_stats[upper_idx]
    ci_width = ci_upper - ci_lower
    
    return ci_width, (ci_lower, ci_upper)

def extract_input_number(filename):
    """
    Extracts the number following 'input' from the filename.
    """
    match = re.search(r"input(\d+)", filename)
    if match:
        return int(match.group(1))
    return 0

def find_log_files(directory):
    """
    Finds and sorts log files in the given directory based on the number after 'input' in their filenames.
    
    Returns the paths for the first two log files found.
    """
    log_files = [f for f in os.listdir(directory) if f.endswith(".log")]
    
    input_logs = sorted(log_files, key=extract_input_number)
    
    if len(input_logs) < 2:
        print("Error: Not enough log files found in the directory.")
        sys.exit(1)
    
    return os.path.join(directory, input_logs[0]), os.path.join(directory, input_logs[1])

def trim_runs_to_equal_size(list1, list2):
    """Trims the larger list so both lists have the same number of elements."""
    min_size = min(len(list1), len(list2))
    return list1[:min_size], list2[:min_size]

def main():
    if len(sys.argv) != 2:
        print("Usage: python3 script.py <configuration_name>")
        sys.exit(1)
    
    config_name = sys.argv[1]
    # Process logs from: logs/tmp/<configuration_name>
    log_directory = os.path.join("logs", "tmp", config_name)
    
    if not os.path.exists(log_directory):
        print(f"Error: Log directory '{log_directory}' does not exist.")
        sys.exit(1)
    
    log1_file, log2_file = find_log_files(log_directory)
    runs1 = extract_runs(log1_file)
    runs2 = extract_runs(log2_file)
    
    # Trim the two lists to the same number of runs.
    runs1, runs2 = trim_runs_to_equal_size(runs1, runs2)
    
    # Filter out pairs where either run was a cold start.
    filtered_pairs = [
        (run1[0], run2[0])
        for run1, run2 in zip(runs1, runs2)
        if not run1[1] and not run2[1]
    ]
    
    if not filtered_pairs:
        print("99% Confidence Interval Width: N/A (no valid runs found)")
        sys.exit(1)
    
    # Unzip filtered pairs into separate lists of durations.
    durations1, durations2 = zip(*filtered_pairs)
    differences = compute_percentage_differences(durations1, durations2)
    bootstrap_result = bootstrap_confidence_interval(differences, iterations=10000, lower_percentile=2.5, upper_percentile=97.5)
    
    if bootstrap_result is not None:
        bootstrap_ci_width, _ = bootstrap_result
        print(f"95% Confidence Interval Width: {bootstrap_ci_width:.2f}")
    else:
        print("95% Confidence Interval Width: N/A")

if __name__ == "__main__":
    main()
