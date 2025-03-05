import re
import numpy as np
import matplotlib.pyplot as plt
import scipy.stats as stats
import argparse

def extract_durations(log_file):
    """Extracts durations from log file where Cold Start is false."""
    durations = []
    pattern_aws = re.compile(r"Billed Duration for Request .*?: (\d+) ms")
    pattern_gcp = re.compile(r"Execution Time for Trace ID .*?: (\d+) ms")
    
    cold_start_pattern = re.compile(r"Cold Start: (true|false)")
    
    with open(log_file, 'r') as file:
        lines = file.readlines()
    
    current_cold_start = None
    for line in lines:
        match_cold_start = cold_start_pattern.search(line)
        if match_cold_start:
            current_cold_start = match_cold_start.group(1).lower() == 'false'
        
        if current_cold_start:
            match_aws = pattern_aws.search(line)
            match_gcp = pattern_gcp.search(line)
            if match_aws:
                durations.append(int(match_aws.group(1)))
            elif match_gcp:
                durations.append(int(match_gcp.group(1)))
    
    return durations

def compute_ci_width(durations):
    """Computes the 95% confidence interval width for the given durations."""
    if len(durations) < 2:
        return None
    
    mean_duration = np.mean(durations)
    std_err = stats.sem(durations)
    ci_width = 2 * stats.t.ppf(0.975, len(durations)-1) * std_err
    return ci_width

def plot_accuracy(durations):
    """Plots accuracy of CI width convergence."""
    ci_widths = []
    accuracy = []
    target_width = 5  # Target CI width of 5ms
    
    for i in range(2, len(durations) + 1):
        ci_width = compute_ci_width(durations[:i])
        if ci_width is not None:
            ci_widths.append(ci_width)
            accuracy.append(abs(ci_width - target_width))
    
    plt.figure(figsize=(10, 5))
    plt.plot(range(2, len(ci_widths) + 2), accuracy, marker='o', linestyle='-')
    plt.xlabel('Number of Runs')
    plt.ylabel('Accuracy (|CI Width - 5ms|)')
    plt.title('Convergence of CI Width to 5ms')
    plt.grid()
    plt.show()

def main():
    parser = argparse.ArgumentParser(description='Analyze log file for CI width convergence.')
    parser.add_argument('log_file', type=str, help='Path to the log file')
    args = parser.parse_args()
    
    durations = extract_durations(args.log_file)
    if durations:
        plot_accuracy(durations)
    else:
        print("No valid durations found for cold start = false.")

if __name__ == "__main__":
    main()