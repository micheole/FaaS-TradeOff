#!/usr/bin/env python3
"""
ci_calculator.py

Reads integer durations (one per line) from stdin
and computes a 95% confidence interval width for them.
Outputs the numeric CI width to stdout. If insufficient
durations are provided, outputs a large numeric value
(e.g., 9999).
"""

import sys
import math

def main():
    durations = []
    # Read durations line by line from stdin
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            val = int(line)
            durations.append(val)
        except ValueError:
            # If the line isn't a valid integer, skip
            continue

    n = len(durations)
    if n < 2:
        # Not enough data to compute a CI
        print("9999")
        return

    # Compute mean
    mean_val = sum(durations) / n
    # Compute sample variance
    variance = sum((x - mean_val) ** 2 for x in durations) / (n - 1)
    stddev = math.sqrt(variance)

    # 2-sided 95% CI => Full width = 3.92 * (stddev / sqrt(n)) 
    # (since 1.96 is half-width => 2 * 1.96 = 3.92)
    ci_width = 3.92 * (stddev / math.sqrt(n))

    # Print numeric result only
    print(f"{ci_width:.4f}")

if __name__ == "__main__":
    main()
