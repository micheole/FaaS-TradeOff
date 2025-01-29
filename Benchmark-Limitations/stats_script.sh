#!/usr/bin/env bash
#
# stats_script.sh
#
# Usage:
#   ./stats_script.sh <config_name>
#
# Description:
#   1. Reads the retrieved logs to extract necessary metrics.
#   2. Computes statistics like mean duration and 95% confidence interval.
#   3. Saves the computed statistics to a CSV file.

set -euo pipefail

# Function to display usage
usage() {
    echo "Usage: $0 <config_name>"
    echo "Example: $0 call-limited"
    exit 1
}

# Ensure the user provides exactly one argument
if [[ $# -ne 1 ]]; then
    echo "Error: Incorrect number of arguments."
    usage
fi

# Get the configuration name from the first argument
CONFIG_NAME="$1"

# Define directories
LOG_DIR="logs/anomaly_detected/${CONFIG_NAME}"
STATS_DIR="statistics/${CONFIG_NAME}"
# RETRIEVED_LOG_DIR="logs/processed/${CONFIG_NAME}"

echo "===================================================================="
echo " Statistics Script: Computing stats for '${CONFIG_NAME}'"
echo "===================================================================="

for LOG_FILE in "$LOG_DIR"/*.log; do
    if [[ -f "$LOG_FILE" ]]; then
        # Extract the filename without the path
        FILENAME=$(basename "$LOG_FILE")
        STATS_CSV="${STATS_DIR}/${FILENAME}.csv"

        # Initialize the CSV file with headers
        # Updated header as per user request
        echo "Provider,Log_File,Mean_Duration_ms,CI_Lower_ms,CI_Upper_ms,Num_Runs" > "$STATS_CSV"
        
        # Extract the provider from the filename
        # Assuming filename format: trigger_output_<provider>_<rest>.log
        PROVIDER=$(echo "$FILENAME" | awk -F'_' '{print $3}')
        
        # Validate the provider
        if [[ "$PROVIDER" != "aws" && "$PROVIDER" != "gcp" ]]; then
            echo "Warning: Unsupported provider '$PROVIDER' in file '$FILENAME'. Skipping."
            continue
        fi

        echo "Processing file: $FILENAME for provider: $PROVIDER"
        
        # Initialize an array to hold durations
        # durations=()
        durations=($(awk -F',' '$4 == "False" {print $2}' "$LOG_FILE"))
        
        # if [[ "$PROVIDER" == "aws" ]]; then
        #     # Extract Billed Durations for AWS
        #     # Example line: Billed Duration for Request <ID>: 538 ms
        #     durations=($(grep "Billed Duration" "$LOG_FILE" | awk -F": " '{print $2}' | awk '{print $1}'))
        # elif [[ "$PROVIDER" == "gcp" ]]; then
        #     # Extract Execution Times for GCP
        #     # Example line: Execution Time for Trace ID <ID>: 598 ms
        #     durations=($(grep "Execution Time" "$LOG_FILE" | awk -F": " '{print $2}' | awk '{print $1}'))
        # fi

        # Check if durations were extracted
        if [[ ${#durations[@]} -eq 0 ]]; then
            echo "Warning: No durations found in file '$FILENAME'. Skipping."
            continue
        fi

        # Convert durations to a space-separated string for awk
        durations_str=$(printf "%s\n" "${durations[@]}")

        # Compute statistics using awk
        read -r mean ci_lower ci_upper <<< $(echo "$durations_str" | awk '
            BEGIN {
                sum = 0;
                sumsq = 0;
                n = 0;
            }
            {
                sum += $1;
                sumsq += ($1)^2;
                n++;
            }
            END {
                if (n > 1) {
                    mean = sum / n;
                    variance = (sumsq - (sum * sum) / n) / (n - 1);
                    stddev = sqrt(variance);
                    ci95_lower = mean - 1.96 * (stddev / sqrt(n));
                    ci95_upper = mean + 1.96 * (stddev / sqrt(n));
                    printf "%.2f %.2f %.2f", mean, ci95_lower, ci95_upper;
                } else if (n == 1) {
                    # If only one sample, confidence interval is the mean itself
                    printf "%.2f %.2f %.2f", sum, sum, sum;
                } else {
                    printf "NA NA NA";
                }
            }
        ')

        # Calculate the number of runs
        num_runs=${#durations[@]}
        
        # Handle cases where statistics could not be computed
        if [[ "$mean" == "NA" ]]; then
            echo "Warning: Unable to compute statistics for file '$FILENAME'. Skipping."
            continue
        fi
        
        # Append the statistics to the CSV file
        echo "${PROVIDER},${FILENAME},${mean},${ci_lower},${ci_upper},${num_runs}" >> "$STATS_CSV"
        
        echo "Statistics for '$FILENAME' - Mean: ${mean} ms, 95% CI: [${ci_lower}, ${ci_upper}] ms, Num Runs: ${num_runs}"


        # Handle cases where statistics could not be computed
        # if [[ "$mean" == "NA" ]]; then
        #     echo "Warning: Unable to compute statistics for file '$FILENAME'. Skipping."
        #     continue
        # fi
        
        # # Append the statistics to the CSV file
        # echo "${CONFIG_NAME},${PROVIDER},${FILENAME},${mean},${ci_lower},${ci_upper}" >> "$STATS_CSV"
        
        # echo "Statistics for '$FILENAME' - Mean: ${mean} ms, 95% CI: [${ci_lower}, ${ci_upper}] ms"

        # Move the processed log file to the processed_logs directory
        # mv "$LOG_FILE" "$RETRIEVED_LOG_DIR"
    else
        echo "No .log files found in $LOG_DIR."
    fi
done

echo "===================================================================="
echo " Statistics Script: Completed. Statistics saved to '${STATS_CSV}'."
echo "===================================================================="

exit 0