set -euo pipefail

CONFIG_PATH="$1"
PROVIDER="$2"
INPUT_PARAM1="$3"
INPUT_PARAM2="$4"

# Function to display usage
usage() {
  echo "Usage: $0 <path_to_config_yaml> <provider> <input_param1> <input_param2>"
  echo "Example: $0 configurations/accuracy-limited.yaml aws 1000000 1050000"
  exit 1
}

# Extract values from YAML using yq
BENCHMARK=$(yq '.benchmark' "$CONFIG_PATH" | sed 's/^"//;s/"$//')
DURATION=$(yq '.batch_duration' "$CONFIG_PATH" | sed 's/^"//;s/"$//')
ARRIVALCOUNT=$(yq '.arrival_count' "$CONFIG_PATH" | sed 's/^"//;s/"$//')
DESIRED_CI_WIDTH=$(yq '.desired_ci_width' "$CONFIG_PATH" | sed 's/^"//;s/"$//')
MAX_BATCHES=$(yq '.max_batches' "$CONFIG_PATH" | sed 's/^"//;s/"$//')
ARTILLERY_SCENARIOS=$(yq '.artillery_scenarios' "$CONFIG_PATH")

# Define the configuration name based on the YAML file name
CONFIG_NAME=$(basename "$CONFIG_PATH" .yaml)

UNIQUE_ID=$(date +'%Y-%m-%d_%H-%M-%S')-$$

echo "===================================================================="
echo " Accuracy-Limited Trigger: Starting benchmark with config '${CONFIG_NAME}'"
echo "===================================================================="


SCENARIO_PATH=$(echo "$ARTILLERY_SCENARIOS" | yq ".\"$PROVIDER\".path" - | tr -d '"')
TARGET_URL=$(echo "$ARTILLERY_SCENARIOS" | yq ".\"$PROVIDER\".target" - | tr -d '"')

# Check if the scenario file exists
if [ ! -f "$SCENARIO_PATH" ]; then
    echo "Error: Artillery scenario file '$SCENARIO_PATH' not found for provider '$PROVIDER'."
    exit 1
fi

all_batch_logs=()
current_batch=0
current_ci=9999 # start with large CI width
        
while [[ "$current_batch" -lt "$MAX_BATCHES" ]]; do
    ((current_batch++))

    echo "Running Batch number: $current_batch"

    for INPUT_PARAM in "$INPUT_PARAM1" "$INPUT_PARAM2"; do

        # Define the output log file
        TRIGGER_LOG="logs/tmp/${CONFIG_NAME}/trigger_output_${PROVIDER}_${CONFIG_NAME}-input${INPUT_PARAM}-uniqueid-$UNIQUE_ID.tmp"

        # Create a temporary artillery file
        TEMP_ARTILLERY_CONFIG="limitations/accuracy-limited/temp_artillery_config_${CONFIG_NAME}_${PROVIDER}_${INPUT_PARAM}_${UNIQUE_ID}.yaml"

        sed -e "s/__INPUT__/$INPUT_PARAM/" \
            -e "s/__DURATION__/$DURATION/" \
            -e "s/__ARRIVALCOUNT__/$ARRIVALCOUNT/" "$SCENARIO_PATH" > "$TEMP_ARTILLERY_CONFIG"
        
        echo "Running Artillery for provider: $PROVIDER"
        echo "Artillery Config: $TEMP_ARTILLERY_CONFIG"

        # Resolve the absolute path of the current script directory
        SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
        
        # Execute Artillery and capture specific output lines
        if [[ "$PROVIDER" == "aws" ]]; then
            artillery run "$TEMP_ARTILLERY_CONFIG" -t "$TARGET_URL" | grep -E "Unique ID:|Pi:|Input:|Cold Start:" >> "$TRIGGER_LOG"
            rm -f "$TEMP_ARTILLERY_CONFIG"
            # Compute the absolute path to log_retrieval
            LOG_RETRIEVAL_PATH="$(cd "$SCRIPT_DIR/../../" && pwd)/log_retrieval-aws.py"
            REGION=$(echo "$ARTILLERY_SCENARIOS" | yq ".\"$PROVIDER\".region" - | tr -d '"')
            LOG_ID=$(echo "$ARTILLERY_SCENARIOS" | yq ".\"$PROVIDER\".loggroup" - | tr -d '"')
        elif [[ "$PROVIDER" == "gcp" ]]; then 
            artillery run "$TEMP_ARTILLERY_CONFIG" -t "$TARGET_URL" | grep -E "Unique ID:|Input:|Cold Start:" >> "$TRIGGER_LOG"
            rm -f "$TEMP_ARTILLERY_CONFIG"
            # Compute the absolute path to log_retrieval
            LOG_RETRIEVAL_PATH="$(cd "$SCRIPT_DIR/../../" && pwd)/log_retrieval-gcp.py"
            REGION=$(echo "$ARTILLERY_SCENARIOS" | yq ".\"$PROVIDER\".region" - | tr -d '"')
            LOG_ID=$(echo "$ARTILLERY_SCENARIOS" | yq ".\"$PROVIDER\".projectid" - | tr -d '"')
        else
            exit
        fi
        
        echo "Artillery run for $PROVIDER completed. Output appended to $TRIGGER_LOG"
        
        # Clean up temporary Artillery config
        rm -f "$TEMP_ARTILLERY_CONFIG"
        echo "Temporary Artillery config '$TEMP_ARTILLERY_CONFIG' deleted."

        # Run the log_retrieval script
        sleep 15
        "$LOG_RETRIEVAL_PATH" "$CONFIG_NAME" "$LOG_ID" "$REGION"

        LOG_FILE="${TRIGGER_LOG%.tmp}.log"

        if [[ ! -f "$LOG_FILE" ]]; then
            echo "Error: Log file '$LOG_FILE' not found." >&2
            exit 1
        fi
    done

    current_ci=$(python3 bootstrap_percentile_ci-al.py accuracy-limited | awk -F': ' '/95% Confidence Interval Width/ {print $2}' | tr -d ' ')
    echo "Batch $current_batch => Current CI width (overall): $current_ci, desired: $DESIRED_CI_WIDTH"

    # Compare with desired CI
    if (( $(echo "$current_ci <= $DESIRED_CI_WIDTH" | bc -l) )); then
        echo "Achieved desired CI width ($current_ci <= $DESIRED_CI_WIDTH). Achieved after $current_batch batches. Stopping for $PROVIDER."
        break
    fi
done

rm -f "$TRIGGER_LOG"

echo "===================================================================="
echo " Accuracy-Limited Trigger: All Artillery runs completed for '${CONFIG_NAME}'."
echo "===================================================================="