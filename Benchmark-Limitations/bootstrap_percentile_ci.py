#!/usr/bin/env python3

import re
import sys
import csv
import os
import shutil
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
    Computes percentage differences for matching durations, allowing negative values.
    
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
            percent_diff = ((time2 - time1) / time1) * 100  # Preserve sign
        differences.append(percent_diff)
    return differences

def compute_confidence_interval(differences):
    """
    Computes the 95% confidence interval for the median using the direct percentile method.
    """
    if not differences:
        return None
    
    differences.sort()
    n = len(differences)
    lower_idx = int(n * 0.025)  # 0.5th percentile
    upper_idx = int(n * 0.975)  # 99.5th percentile
    
    ci_lower = differences[lower_idx]
    ci_upper = differences[upper_idx]
    ci_width = ci_upper - ci_lower
    
    return ci_width, (ci_lower, ci_upper)

def bootstrap_confidence_interval(differences, iterations=10000, lower_percentile=2.5, upper_percentile=97.5):
    """
    Computes the bootstrapped percentile confidence interval for the median of the differences.
    
    This function resamples the list of differences with replacement for a given number of iterations.
    For each bootstrap sample, it calculates the median and then determines the lower and upper
    percentiles of the bootstrap distribution.
    
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

def save_statistics_to_csv(differences, direct_ci_width, direct_ci_range, bootstrap_ci_width, bootstrap_ci_range, num_runs, output_file):
    """
    Saves the statistical results to a CSV file, including the number of runs considered.
    """
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["Number of Runs", num_runs])
        writer.writerow([])
        writer.writerow(["Direct 95% Percentile CI Width", direct_ci_width])
        writer.writerow(["Direct 95% Percentile CI Lower Bound", direct_ci_range[0]])
        writer.writerow(["Direct 95% Percentile CI Upper Bound", direct_ci_range[1]])
        writer.writerow([])
        writer.writerow(["Bootstrap 95% Percentile CI Width", bootstrap_ci_width])
        writer.writerow(["Bootstrap 95% Percentile CI Lower Bound", bootstrap_ci_range[0]])
        writer.writerow(["Bootstrap 95% Percentile CI Upper Bound", bootstrap_ci_range[1]])
        writer.writerow([])
        writer.writerow(["Percentage Difference (%)"])
        writer.writerows([[diff] for diff in differences])

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
    Finds and sorts log files based on the number after 'input' in the filename.
    
    Returns the paths for the first two log files found.
    """
    log_files = [f for f in os.listdir(directory) if f.endswith(".log")]
    
    input_logs = sorted(log_files, key=extract_input_number)
    
    if len(input_logs) < 2:
        print("Error: Not enough log files found in the directory.")
        sys.exit(1)
    
    return os.path.join(directory, input_logs[0]), os.path.join(directory, input_logs[1])

def move_tmp_files(config_name):
    """
    Moves all files from logs/tmp/<configuration_name> to logs/processed/<configuration_name>.
    """
    src_dir = os.path.join("logs", "tmp", config_name)
    dst_dir = os.path.join("logs", "processed", config_name)
    
    if not os.path.exists(src_dir):
        print(f"No temporary files found in {src_dir}.")
        return
    
    os.makedirs(dst_dir, exist_ok=True)
    for filename in os.listdir(src_dir):
        src = os.path.join(src_dir, filename)
        dst = os.path.join(dst_dir, filename)
        try:
            shutil.move(src, dst)
            print(f"Moved {src} to {dst}")
        except Exception as e:
            print(f"Error moving {src} to {dst}: {e}")

def main():
    if len(sys.argv) != 2:
        print("Usage: python3 script.py <configuration_name>")
        sys.exit(1)
    
    config_name = sys.argv[1]
    # Process logs from logs/tmp/<configuration_name>
    log_directory = os.path.join("logs", "tmp", config_name)
    # Save output statistics to statistics/<configuration_name>
    output_directory = os.path.join("statistics", config_name)

    if not os.path.exists(log_directory):
        print(f"Error: Log directory '{log_directory}' does not exist.")
        sys.exit(1)
    
    os.makedirs(output_directory, exist_ok=True)

    # Get runs from each log file (each run is a tuple: (duration, is_cold_start))
    log1_file, log2_file = find_log_files(log_directory)
    runs1 = extract_runs(log1_file)
    runs2 = extract_runs(log2_file)
    
    # Trim the two lists to be of equal size (based on their original order)
    min_runs = min(len(runs1), len(runs2))
    runs1 = runs1[:min_runs]
    runs2 = runs2[:min_runs]
    
    # Filter out pairs where either run was a cold start.
    filtered_pairs = [
        (run1[0], run2[0])
        for run1, run2 in zip(runs1, runs2)
        if not run1[1] and not run2[1]
    ]
    
    # Number of runs considered is the number of filtered pairs.
    num_runs = len(filtered_pairs)
    
    if num_runs == 0:
        print("No valid (non-cold start) runs found for comparison.")
        sys.exit(1)
    
    # Unzip filtered pairs into separate lists of durations.
    durations1, durations2 = zip(*filtered_pairs)
    
    # Compute differences and confidence intervals.
    differences = compute_percentage_differences(durations1, durations2)
    direct_result = compute_confidence_interval(differences)
    bootstrap_result = bootstrap_confidence_interval(differences, iterations=10000, lower_percentile=2.5, upper_percentile=97.5)
    
    if direct_result and bootstrap_result:
        direct_ci_width, direct_ci_range = direct_result
        bootstrap_ci_width, bootstrap_ci_range = bootstrap_result
        print(f"Number of Runs: {num_runs}")
        print(f"Direct 95% Percentile CI Width: {direct_ci_width:.2f}%")
        print(f"Direct 95% Percentile CI: {direct_ci_range}")
        print(f"Bootstrap 95% Percentile CI Width: {bootstrap_ci_width:.2f}%")
        print(f"Bootstrap 95% Percentile CI: {bootstrap_ci_range}")
        statistics_filename = f"statistics_{os.path.basename(log1_file)}_{os.path.basename(log2_file)}.csv"
        statistics_file = os.path.join(output_directory, statistics_filename)
        save_statistics_to_csv(differences, direct_ci_width, direct_ci_range, bootstrap_ci_width, bootstrap_ci_range, num_runs, statistics_file)
        print(f"Statistics saved to {statistics_file}")
    else:
        print("No matching data found for comparison.")
    
    # Move processed logs from logs/tmp/<configuration_name> to logs/processed/<configuration_name>
    move_tmp_files(config_name)

if __name__ == "__main__":
    main()
