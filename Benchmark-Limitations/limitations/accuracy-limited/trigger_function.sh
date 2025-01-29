

set -euo pipefail

CONFIG_PATH="$1"

# Function to display usage
usage() {
  echo "Usage: $0 <path_to_config_yaml>"
  echo "Example: $0 configurations/accuracy-limited.yaml"
  exit 1
}

# Extract values from YAML using yq
BENCHMARK=$(yq '.benchmark' "$CONFIG_PATH" | sed 's/^"//;s/"$//')
DURATION=$(yq '.batch_duration' "$CONFIG_PATH" | sed 's/^"//;s/"$//')
ARRIVALCOUNT=$(yq '.arrival_count' "$CONFIG_PATH" | sed 's/^"//;s/"$//')
DESIRED_CI_WIDTH=$(yq '.desired_ci_width' "$CONFIG_PATH" | sed 's/^"//;s/"$//')
# MAX_BATCHES=$(yq '.max_batches' "$CONFIG_PATH" | sed 's/^"//;s/"$//')
ARTILLERY_SCENARIOS=$(yq '.artillery_scenarios' "$CONFIG_PATH")
MAX_BATCHES=6
INPUT=1000000

# Define the configuration name based on the YAML file name
CONFIG_NAME=$(basename "$CONFIG_PATH" .yaml)

UNIQUE_ID=$(date +'%Y-%m-%d_%H-%M-%S')-$$

echo "===================================================================="
echo " Accuracy-Limited Trigger: Starting benchmark with config '${CONFIG_NAME}'"
echo "===================================================================="

echo "Desired CI width: $DESIRED_CI_WIDTH"

# Iterate over each cloud provider
CLOUD_PROVIDERS=$(echo "$ARTILLERY_SCENARIOS" | yq 'keys | .[]' -)

for provider in $CLOUD_PROVIDERS; do
    PROVIDER=$(echo "$provider" | tr -d '"')
    SCENARIO_PATH=$(echo "$ARTILLERY_SCENARIOS" | yq ".\"$PROVIDER\".path" - | tr -d '"')
    # echo "PATH: $SCENARIO_PATH"
    TARGET_URL=$(echo "$ARTILLERY_SCENARIOS" | yq ".\"$PROVIDER\".target" - | tr -d '"')
    # echo "Target URL: $TARGET_URL"

    # Check if the scenario file exists
    if [ ! -f "$SCENARIO_PATH" ]; then
        echo "Error: Artillery scenario file '$SCENARIO_PATH' not found for provider '$PROVIDER'."
        exit 1
    fi

    current_batch=0
    current_ci=9999 # start with large CI width

    while [[ "$current_batch" -lt "$MAX_BATCHES" ]] && \
        [[ "$(echo "$current_ci > $DESIRED_CI_WIDTH" | bc -l)" == "1" ]]; do
        ((current_batch++))

        # Define the output log file
        TRIGGER_LOG="logs/tmp/${CONFIG_NAME}/trigger_output_${PROVIDER}_${CONFIG_NAME}-batch${current_batch}-uniqueid-$UNIQUE_ID.tmp"

        # Create a temporary artillery file
        TEMP_ARTILLERY_CONFIG="limitations/accuracy-limited/temp_artillery_config_${CONFIG_NAME}_${PROVIDER}_${UNIQUE_ID}.yaml"

        sed -e "s/__INPUT__/$INPUT/" \
            -e "s/__DURATION__/$DURATION/" \
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

        # Run the outlier detector for removing anomalies from analysis
        python3 outlier_detector.py logs/tmp/${CONFIG_NAME}

        # Final log
        TRIGGER_LOG_FILENAME=$(basename "$TRIGGER_LOG")
        NEW_DIR="logs/anomaly_detected/${CONFIG_NAME}"
        LOG_FILE="${NEW_DIR}/${TRIGGER_LOG_FILENAME%.tmp}.log"

        if [[ ! -f "$LOG_FILE" ]]; then
            echo "Error: Log file '$LOG_FILE' not found." >&2
            exit 1
        fi

        # Extract *valid* (non-outlier) durations => accumulate
        #   Format: Unique_ID,Duration_ms,Provider,Outlier
        #   We'll get durations from column 2 if Outlier == "False"
        # new_durations=$(grep -E "([0-9]+) ms" "$LOG_FILE" | sed -E 's/.*: ([0-9]+) ms/\1/')
        new_durations=$(awk -F, '$4=="False" {print $2}' "$LOG_FILE" 2>/dev/null)

        # Accumulate in ALL_DURATIONS
        if [[ -n "$new_durations" ]]; then
            ALL_DURATIONS+=$'\n'"$new_durations"
        else
            echo "Warning: No durations found for batch $current_batch." >&2
        fi

        # Now call the Python script to compute the CI width from ALL_DURATIONS
        current_ci=$(echo "$ALL_DURATIONS" | python3 ci_calculator.py)
        echo "Batch $current_batch => Current CI width (overall): $current_ci, desired: $DESIRED_CI_WIDTH"

        # Compare with desired CI
        if (( $(echo "$current_ci <= $DESIRED_CI_WIDTH" | bc -l) )); then
            echo "Achieved desired CI width ($current_ci <= $DESIRED_CI_WIDTH). Stopping for $PROVIDER."
            break
        fi
    done
done

echo "===================================================================="
echo " Accuracy-Limited Trigger: All Artillery runs completed for '${CONFIG_NAME}'."
echo "===================================================================="