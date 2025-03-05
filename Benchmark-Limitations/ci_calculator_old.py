#!/usr/bin/env python3
"""
confidence_interval.py

Parses one or more log files, each containing lines like either:
  (AWS-style)
    Unique ID: ...
    Billed Duration for Request X: Y ms
    Cold Start: true/false
  (GCP-style)
    Unique ID: ...
    Execution Time for Trace ID X: Y ms
    Cold Start: true/false

We:
  1) Skip any request that has "Cold Start: true".
  2) Extract the integer duration (in ms) from either "Billed Duration ..." or "Execution Time ...".
  3) Combine durations from all files passed as arguments.
  4) Compute a 2-sided 95% Confidence Interval width across all valid durations.
  5) Print that numeric CI width. If fewer than 2 durations found => print 9999.
"""

import sys
import math

def parse_single_log_file(filepath):
    """
    Parses one log file and returns a list of integer durations
    for all requests that have Cold Start == false.
    We handle either of these lines (as an example):

      Billed Duration for Request 1234: 535 ms
      Execution Time for Trace ID 5678: 580 ms
    """
    durations = []
    
    # Keep track of the 'current' request in a small dictionary,
    # because the logs may have multiple lines for each request.
    current_request = {
        "cold_start": None,
        "duration": None
    }
    
    def flush_request(req, result_list):
        # If the request is valid, append the duration
        if req["cold_start"] is False and req["duration"] is not None:
            result_list.append(req["duration"])
        # Reset for next request
        req["cold_start"] = None
        req["duration"] = None

    with open(filepath, "r") as f:
        for line in f:
            line = line.strip()
            
            # Start of a new request => flush the previous one
            if line.startswith("Unique ID: "):
                flush_request(current_request, durations)

            # Either AWS or GCP pattern
            if "Billed Duration for Request" in line or "Execution Time for Trace ID" in line:
                # Example AWS: Billed Duration for Request X: 535 ms
                # Example GCP: Execution Time for Trace ID X: 580 ms
                parts = line.split(":")
                if len(parts) >= 2:
                    # everything after the first colon is "535 ms" or "580 ms", etc.
                    possible_duration = parts[1].strip()
                    # remove "ms"
                    possible_duration = possible_duration.replace("ms", "").strip()
                    try:
                        current_request["duration"] = int(possible_duration)
                    except ValueError:
                        pass

            elif line.startswith("Cold Start: "):
                # Example line: "Cold Start: true"
                parts = line.split(":")
                if len(parts) == 2:
                    val_str = parts[1].strip().lower()
                    if val_str == "true":
                        current_request["cold_start"] = True
                    elif val_str == "false":
                        current_request["cold_start"] = False

        # End of file => flush any last request
        flush_request(current_request, durations)

    return durations

def main():
    if len(sys.argv) < 2:
        # We expect at least one log file as argument
        print("9999")
        sys.exit(0)

    # Collect all durations from the specified log files
    all_durations = []
    for logfile in sys.argv[1:]:
        try:
            file_durations = parse_single_log_file(logfile)
            all_durations.extend(file_durations)
        except Exception as e:
            # If there's a problem reading/parsing a file, skip it or handle error
            print(f"Error reading file '{logfile}': {e}", file=sys.stderr)

    n = len(all_durations)
    if n < 2:
        # Not enough data to compute a CI
        print("9999")
        return

    # Compute mean
    mean_val = sum(all_durations) / n
    # Compute sample variance
    variance = sum((x - mean_val) ** 2 for x in all_durations) / (n - 1)
    stddev = math.sqrt(variance)

    # 2-sided 95% CI => Full width = 3.92 * (stddev / sqrt(n))
    # (since 1.96 is half-width => 2 * 1.96 = 3.92)
    ci_width = 3.92 * (stddev / math.sqrt(n))

    print(f"{ci_width:.4f}")

if __name__ == "__main__":
    main()
