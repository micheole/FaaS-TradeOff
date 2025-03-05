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
PROVIDER="$2"
INPUT_PARAM1="$3"
INPUT_PARAM2="$4"

# Pricing details: 512MB of memory
AWS_PRICE_PER_MS=0.0000000083
GCP_PRICE_PER_MS=0.00000000925

# Function to display usage
usage() {
  echo "Usage: $0 <path_to_config_yaml> <provider> <input_param1> <input_param2>"
  echo "Example: $0 configurations/money-limited.yaml aws 1000000 1050000"
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
                
                # Verify duration_ms is numeric
                if [[ -n "$duration_ms" && "$duration_ms" =~ ^[0-9]+$ ]]; then
                    cost=$(echo "$duration_ms * $AWS_PRICE_PER_MS" | bc -l 2>/dev/null)
                    # If bc fails or cost is empty, skip
                    if [[ $? -ne 0 || -z "$cost" ]]; then
                        echo "Warning: Invalid cost calculation for AWS. Skipping..." >&2
                        continue
                    fi
                    BATCH_COST=$(echo "$BATCH_COST + $cost" | bc -l 2>/dev/null)
                else
                    echo "Warning: Invalid or empty duration_ms for AWS: '$duration_ms'. Skipping..." >&2
                fi
            fi
        elif [[ "$PROVIDER" == "gcp" ]]; then
            if [[ "$LINE" =~ Execution\ Time\ for\ Trace\ ID.*:\ ([0-9]+)\ ms ]]; then
                duration_ms="${BASH_REMATCH[1]}"
                # Verify duration_ms is numeric
                if [[ -n "$duration_ms" && "$duration_ms" =~ ^[0-9]+$ ]]; then
                    cost=$(echo "$duration_ms * $GCP_PRICE_PER_MS" | bc -l 2>/dev/null)
                    if [[ $? -ne 0 || -z "$cost" ]]; then
                        echo "Warning: Invalid cost calculation for GCP. Skipping..." >&2
                        continue
                    fi
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
MAX_BATCHES=$(yq '.max_batches' "$CONFIG_PATH" | sed 's/^"//;s/"$//')

# Define the configuration name based on the YAML file name
CONFIG_NAME=$(basename "$CONFIG_PATH" .yaml)

UNIQUE_ID=$(date +'%Y-%m-%d_%H-%M-%S')-$$

echo "===================================================================="
echo " Money-Limited Trigger: Starting benchmark with config '${CONFIG_NAME}' and provider '${PROVIDER}'"
echo "===================================================================="

SCENARIO_PATH=$(echo "$ARTILLERY_SCENARIOS" | yq ".\"$PROVIDER\".path" - | tr -d '"')
TARGET_URL=$(echo "$ARTILLERY_SCENARIOS" | yq ".\"$PROVIDER\".target" - | tr -d '"')

# Check if the scenario file exists
if [ ! -f "$SCENARIO_PATH" ]; then
    echo "Error: Artillery scenario file '$SCENARIO_PATH' not found for provider '$PROVIDER'."
    exit 1
fi

# Resolve the absolute path of the current script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Compute the absolute path to the log retrieval script
if [[ "$PROVIDER" == "aws" ]]; then
    LOG_RETRIEVAL_PATH="$(cd "$SCRIPT_DIR/../../" && pwd)/log_retrieval-aws.py"
    REGION=$(echo "$ARTILLERY_SCENARIOS" | yq ".\"$PROVIDER\".region" - | tr -d '"')
    LOG_ID=$(echo "$ARTILLERY_SCENARIOS" | yq ".\"$PROVIDER\".loggroup" - | tr -d '"')
elif [[ "$PROVIDER" == "gcp" ]]; then 
    LOG_RETRIEVAL_PATH="$(cd "$SCRIPT_DIR/../../" && pwd)/log_retrieval-gcp.py"
    REGION=$(echo "$ARTILLERY_SCENARIOS" | yq ".\"$PROVIDER\".region" - | tr -d '"')
    LOG_ID=$(echo "$ARTILLERY_SCENARIOS" | yq ".\"$PROVIDER\".projectid" - | tr -d '"')
fi

total_cost=0

for INPUT_PARAM in "$INPUT_PARAM1" "$INPUT_PARAM2"; do
    partial_cost=0
    current_batch=0
    while [[ "$current_batch" -lt $((MAX_BATCHES / 2)) ]]; do

        ((current_batch++))

        # Define the output log file
        TRIGGER_LOG="logs/tmp/${CONFIG_NAME}/trigger_output_${PROVIDER}_${CONFIG_NAME}-input${INPUT_PARAM}-uniqueid-$UNIQUE_ID.tmp"

        # Create a temporary artillery file
        TEMP_ARTILLERY_CONFIG="limitations/money-limited/temp_artillery_config_${CONFIG_NAME}_${PROVIDER}_${UNIQUE_ID}.yaml"

        sed -e "s/__INPUT__/$INPUT_PARAM/" "$SCENARIO_PATH" > "$TEMP_ARTILLERY_CONFIG"
        
        echo "Running Artillery for provider: $PROVIDER"
        echo "Artillery Config: $TEMP_ARTILLERY_CONFIG"
        
        # Execute Artillery and capture specific output lines
        artillery run "$TEMP_ARTILLERY_CONFIG" -t "$TARGET_URL" | grep -E "Unique ID:|Input:|Cold Start:" >> "$TRIGGER_LOG"
        
        echo "Artillery run for $PROVIDER completed. Output appended to $TRIGGER_LOG"
        
        # Clean up temporary Artillery config
        rm -f "$TEMP_ARTILLERY_CONFIG"
        echo "Temporary Artillery config '$TEMP_ARTILLERY_CONFIG' deleted."

        # Run the log_retrieval script
        sleep 15
        "$LOG_RETRIEVAL_PATH" "$CONFIG_NAME" "$LOG_ID" "$REGION"

        LOG_FILE="${TRIGGER_LOG%.tmp}.log"

        echo "Processing log file for cost calculation: $LOG_FILE"
        batch_cost=$(calculate_cost "$PROVIDER" "$LOG_FILE")
        
        # Ensure batch_cost is numeric, otherwise skip
        if [[ "$batch_cost" =~ ^[0-9]+(\.[0-9]+)?$ ]]; then
            # Use awk for floating-point addition
            partial_cost=$(awk -v total="$partial_cost" -v batch="$batch_cost" 'BEGIN { printf "%.10f", total + batch }')
        else
            echo "Warning: batch_cost is not numeric: '$batch_cost'. Skipping cost addition." >&2
        fi

        echo "Batch $current_batch cost: $batch_cost | Total cost: $partial_cost | Budget: $BUDGET"

        # Use awk for floating-point comparison
        if (( $(awk -v total="$partial_cost" -v budget="$BUDGET" 'BEGIN { print (total >= (budget / 2)) }') )); then
            echo "Budget exceeded. Stopping execution."
            break
        fi
    done
    total_cost=$(echo "$total_cost + $partial_cost" | bc)
done

echo "Total cost of execution: $total_cost"

echo "===================================================================="
echo " Money-Limited Trigger: All Artillery runs completed for '${CONFIG_NAME}'."
echo "===================================================================="