import re
import sys
import numpy as np

def extract_durations(log_file):
    """Extracts execution times from the log file, ignoring cold starts when applicable."""
    durations = []
    
    with open(log_file, 'r') as file:
        content = file.read()
        
        pattern = re.findall(
            r'(?:Billed Duration for Request|Execution Time for Trace ID) .*?: (\d+) ms(?:\n.*?Cold Start: (true|false))?',
            content,
            re.DOTALL
        )
        
        for duration, cold_start in pattern:
            if cold_start is None or cold_start.lower() == 'false':
                durations.append(int(duration))
    
    return durations

def calculate_median(durations):
    """Calculates and returns the median of a list of durations."""
    if not durations:
        return None
    return np.median(durations)

def main():
    if len(sys.argv) != 2:
        print("Usage: python3 script.py <log_file>")
        sys.exit(1)
    
    log_file = sys.argv[1]
    durations = extract_durations(log_file)
    
    if not durations:
        print("No valid durations found in the log file.")
        sys.exit(1)
    
    median_duration = calculate_median(durations)
    print(f"Median Duration: {median_duration:.2f} ms")

if __name__ == "__main__":
    main()
