# utils/helper_functions.py

import logging
import math
import statistics

def read_accuracy_from_logs():
    """
    Retrieve a list of accuracy measurements from logs for the last batch.
    Implement this function based on your environment's logging system.
    
    Returns:
    - List of accuracy measurements (float).
    """
    # TODO: Implement log parsing logic.
    # Example:
    # Parse logs to extract 'estimatedPi' and compute accuracy.
    # For Monte-Carlo, accuracy could be |pi_estimate - math.pi|
    
    accuracies = []
    try:
        with open('processed_logs/accuracy_logs.txt', 'r') as f:
            for line in f:
                # Example log line: "Unique ID: 12345, Pi: 3.1415, Trials: 1000, Duration: 120.0 ms"
                if "Pi:" in line:
                    parts = line.strip().split(',')
                    pi_estimate = None
                    for part in parts:
                        if "Pi:" in part:
                            pi_estimate = float(part.split("Pi:")[1].strip())
                    if pi_estimate:
                        accuracy = abs(math.pi - pi_estimate)
                        accuracies.append(accuracy)
        return accuracies
    except Exception as e:
        logging.error(f"Error reading accuracy from logs: {e}")
        return []

def read_current_cost():
    """
    Retrieve the cumulative cost spent so far.
    Implement this function based on your cloud provider's billing APIs or logs.

    Returns:
    - Current cost as a float in USD.
    """
    # TODO: Implement cost retrieval logic.
    # For AWS, use boto3 to access Cost Explorer API.
    # For GCP, use google-cloud-billing library to access billing information.
    
    # Placeholder implementation:
    # Read from a local file 'current_cost.txt' where cost is logged after each batch.
    try:
        with open('processed_logs/current_cost.txt', 'r') as f:
            cost = float(f.read().strip())
            return cost
    except Exception as e:
        logging.error(f"Error reading current cost from logs: {e}")
        return 0.0

def enforce_rate_limit(rate):
    """
    Enforce a rate limit to prevent overwhelming the system.

    Parameters:
    - rate: Number of operations per second.
    """
    import time, threading
    interval = 1.0 / rate
    def rate_limiter():
        while True:
            time.sleep(interval)
    thread = threading.Thread(target=rate_limiter, daemon=True)
    thread.start()

def compute_95_ci_width(data):
    """
    Compute the width of the 95% confidence interval for the mean of data.
    Formula: CI width = 2 * 1.96 * (stdev / sqrt(n))
    
    Parameters:
    - data: List of float values.
    
    Returns:
    - Confidence interval width as a float.
    """
    n = len(data)
    if n <= 1:
        return float('inf')  # Undefined CI
    mean_ = statistics.mean(data)
    stdev_ = statistics.stdev(data)
    sem = stdev_ / math.sqrt(n)  # Standard error of the mean
    half_ci = 1.96 * sem
    ci_width = 2 * half_ci
    return ci_width
