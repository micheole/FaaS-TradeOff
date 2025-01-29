#!/usr/bin/env bash
#
# money_limited_trigger.sh
#
# Usage:
#   ./money_limited_trigger.sh <path_to_config_yaml>
#
# Description:
#   Runs batches of function invocations and calculates costs for AWS and GCP, stopping when the budget is exceeded.

set -euo pipefail

CONFIG_PATH="$1"

# Pricing details: 128MB of memory
AWS_PRICE_PER_MS=0.0000000021
GCP_PRICE_PER_MS=0.00000000231

# Function to display usage
usage() {
  echo "Usage: $0 <path_to_config_yaml>"
  echo "Example: $0 configurations/money-limited.yaml"
  exit 1
}

# Function to calculate the cost
calculate_cost() {
    local PROVIDER="$1"
    local LOG_FILE="$2"
    local BATCH_COST=0

    while IFS= read -r LINE; do
        if [[ "$PROVIDER" == "aws" ]]; then
            if [[ "$LINE" =~ Billed\ Duration\ for\ Request.*:\ ([0-9]+)\ ms ]]; then
                duration_ms="${BASH_REMATCH[1]}"
                # Send debug info to stderr
                echo "AWS duration: $duration_ms ms" >&2
                # Verify duration_ms is numeric
                if [[ -n "$duration_ms" && "$duration_ms" =~ ^[0-9]+$ ]]; then
                    cost=$(echo "$duration_ms * $AWS_PRICE_PER_MS" | bc -l 2>/dev/null)
                    # If bc fails or cost is empty, skip
                    if [[ $? -ne 0 || -z "$cost" ]]; then
                        echo "Warning: Invalid cost calculation for AWS. Skipping..." >&2
                        continue
                    fi
                    echo "AWS cost for this request: $cost" >&2
                    BATCH_COST=$(echo "$BATCH_COST + $cost" | bc -l 2>/dev/null)
                else
                    echo "Warning: Invalid or empty duration_ms for AWS: '$duration_ms'. Skipping..." >&2
                fi
            fi
        elif [[ "$PROVIDER" == "gcp" ]]; then
            if [[ "$LINE" =~ Execution\ Time\ for\ Trace\ ID.*:\ ([0-9]+)\ ms ]]; then
                duration_ms="${BASH_REMATCH[1]}"
                echo "GCP duration: $duration_ms ms" >&2  # Debug
                # Verify duration_ms is numeric
                if [[ -n "$duration_ms" && "$duration_ms" =~ ^[0-9]+$ ]]; then
                    cost=$(echo "$duration_ms * $GCP_PRICE_PER_MS" | bc -l 2>/dev/null)
                    if [[ $? -ne 0 || -z "$cost" ]]; then
                        echo "Warning: Invalid cost calculation for GCP. Skipping..." >&2
                        continue
                    fi
                    echo "GCP cost for this request: $cost" >&2  # Debug
                    BATCH_COST=$(echo "$BATCH_COST + $cost" | bc -l 2>/dev/null)
                else
                    echo "Warning: Invalid or empty duration_ms for GCP: '$duration_ms'. Skipping..." >&2
                fi
            fi
        fi
    done < "$LOG_FILE"

    # Output only the numeric batch cost to stdout
    printf "%.10f" "$BATCH_COST"
}

# Check if the config file exists
if [ ! -f "$CONFIG_PATH" ]; then
  echo "Error: Configuration file not found at '$CONFIG_PATH'."
  exit 1
fi

# Extract values from YAML using yq
BENCHMARK=$(yq '.benchmark' "$CONFIG_PATH" | sed 's/^"//;s/"$//')
BUDGET=$(yq '.total_budget' "$CONFIG_PATH" | sed 's/^"//;s/"$//')
ARTILLERY_SCENARIOS=$(yq '.artillery_scenarios' "$CONFIG_PATH")
INPUT=1000000
ARRIVALCOUNT=100
MAX_BATCHES=10

# Define the configuration name based on the YAML file name
CONFIG_NAME=$(basename "$CONFIG_PATH" .yaml)

UNIQUE_ID=$(date +'%Y-%m-%d_%H-%M-%S')-$$

echo "===================================================================="
echo " Money-Limited Trigger: Starting benchmark with config '${CONFIG_NAME}'"
echo "===================================================================="

# Iterate over each cloud provider
CLOUD_PROVIDERS=$(echo "$ARTILLERY_SCENARIOS" | yq 'keys | .[]' -)

for provider in $CLOUD_PROVIDERS; do
    PROVIDER=$(echo "$provider" | tr -d '"')
    SCENARIO_PATH=$(echo "$ARTILLERY_SCENARIOS" | yq ".\"$PROVIDER\".path" - | tr -d '"')
    echo "PATH: $SCENARIO_PATH"
    TARGET_URL=$(echo "$ARTILLERY_SCENARIOS" | yq ".\"$PROVIDER\".target" - | tr -d '"')
    echo "Target URL: $TARGET_URL"

    # Check if the scenario file exists
    if [ ! -f "$SCENARIO_PATH" ]; then
        echo "Error: Artillery scenario file '$SCENARIO_PATH' not found for provider '$PROVIDER'."
        exit 1
    fi

    current_batch=0
    total_cost=0

    while [[ "$current_batch" -lt "$MAX_BATCHES" ]]; do
        ((current_batch++))

        # Define the output log file
        TRIGGER_LOG="logs/tmp/${CONFIG_NAME}/trigger_output_${PROVIDER}_${CONFIG_NAME}-batch${current_batch}-uniqueid-$UNIQUE_ID.tmp"

        # Create a temporary artillery file
        TEMP_ARTILLERY_CONFIG="limitations/money-limited/temp_artillery_config_${CONFIG_NAME}_${PROVIDER}_${UNIQUE_ID}.yaml"

        sed -e "s/__INPUT__/$INPUT/" \
            -e "s/__ARRIVALCOUNT__/$ARRIVALCOUNT/" "$SCENARIO_PATH" > "$TEMP_ARTILLERY_CONFIG"
        
        echo "Running Artillery for provider: $PROVIDER"
        echo "Artillery Config: $TEMP_ARTILLERY_CONFIG"
        
        # Execute Artillery and capture specific output lines
        artillery run "$TEMP_ARTILLERY_CONFIG" -t "$TARGET_URL" | grep -E "Unique ID:|Pi:|Trials:" >> "$TRIGGER_LOG"
        
        echo "Artillery run for $PROVIDER completed. Output appended to $TRIGGER_LOG"
        
        # Clean up temporary Artillery config
        rm -f "$TEMP_ARTILLERY_CONFIG"
        echo "Temporary Artillery config '$TEMP_ARTILLERY_CONFIG' deleted."

        # Resolve the absolute path of the current script directory
        SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

        # Compute the absolute path to log_retrieval
        LOG_RETRIEVAL_PATH="$(cd "$SCRIPT_DIR/../../" && pwd)/log_retrieval.sh"

        # Run the log_retrieval script
        "$LOG_RETRIEVAL_PATH" "$CONFIG_NAME"

        LOG_FILE="${TRIGGER_LOG%.tmp}.log"

        echo "Processing log file for cost calculation: $LOG_FILE"
        batch_cost=$(calculate_cost "$PROVIDER" "$LOG_FILE")
        
        # Ensure batch_cost is numeric, otherwise skip
        if [[ "$batch_cost" =~ ^[0-9]+(\.[0-9]+)?$ ]]; then
            # Use awk for floating-point addition
            total_cost=$(awk -v total="$total_cost" -v batch="$batch_cost" 'BEGIN { printf "%.10f", total + batch }')
        else
            echo "Warning: batch_cost is not numeric: '$batch_cost'. Skipping cost addition." >&2
        fi

        echo "Batch $current_batch cost: $batch_cost | Total cost: $total_cost | Budget: $BUDGET"

        # Use awk for floating-point comparison
        if (( $(awk -v total="$total_cost" -v budget="$BUDGET" 'BEGIN { print (total >= budget) }') )); then
            echo "Budget exceeded. Stopping execution."
            break
        fi
    done
done

echo "===================================================================="
echo " Money-Limited Trigger: All Artillery runs completed for '${CONFIG_NAME}'."
echo "===================================================================="