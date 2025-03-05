#!/usr/bin/env bash
#
# orchestrator.sh
#
# Usage:
#   ./orchestrator.sh <config_name>
#
# Description:
#   1. Takes a config name (e.g., "call-limited", "time-limited").
#   2. Checks if the corresponding YAML file exists in the configurations/ folder.
#   3. Determines the limitation mode from the config.
#   4. Executes the corresponding trigger script.
#   5. After success, runs the log retrieval script.
#   6. Runs the outlier detector, to remove cold starts or anomalies from the statistics
#   7. Finally, runs the statistics script to compute and output results.

set -euo pipefail

# Function to display usage
usage() {
  echo "Usage: $0 <config_name> <input_param1> <input_param2>"
  echo "Example: $0 call-limited 5000000 5500000"
  exit 1
}

# Check if exactly one argument is provided
if [ "$#" -ne 3 ]; then
  usage
fi

CONFIG_NAME="$1"
INPUT_PARAM1="$2"
INPUT_PARAM2="$3"
CONFIG_PATH="configurations/${CONFIG_NAME}.yaml"
ARTILLERY_SCENARIOS=$(yq '.artillery_scenarios' "$CONFIG_PATH")
CLOUD_PROVIDERS=$(echo "$ARTILLERY_SCENARIOS" | yq 'keys | .[]' -)

# Initialize logger
LOG_DIR="logs"
mkdir -p "$LOG_DIR"
ORCHESTRATOR_LOG="${LOG_DIR}/orchestrator.log"

# Redirect all output to the orchestrator log and the console
exec > >(tee -i "$ORCHESTRATOR_LOG") 2>&1

for provider in $CLOUD_PROVIDERS; do
  PROVIDER=$(echo "$provider" | tr -d '"')

  echo "===================================================================="
  echo " Orchestrator: Starting benchmark with configuration '${CONFIG_NAME}' and provider '${PROVIDER}'"
  echo "===================================================================="

  # 1. Check if configuration file exists
  if [ ! -f "$CONFIG_PATH" ]; then
    echo "Error: Configuration '${CONFIG_NAME}' not found in 'configurations/' folder."
    exit 1
  fi

  echo "Configuration file found: $CONFIG_PATH"

  # 2. Extract the limitation mode from the configuration
  MODE=$(yq '.mode' "$CONFIG_PATH" | sed 's/^"//;s/"$//')

  if [ "$MODE" == "null" ] || [ -z "$MODE" ]; then
    echo "Error: 'mode' not specified in the configuration."
    exit 1
  fi

  echo "Limitation mode identified: $MODE"

  # 3. Determine the corresponding trigger script
  TRIGGER_SCRIPT="limitations/${MODE}/trigger_function.sh"

  if [ ! -f "$TRIGGER_SCRIPT" ]; then
    echo "Error: Trigger script for mode '${MODE}' not found at '${TRIGGER_SCRIPT}'."
    exit 1
  fi

  echo "Executing trigger script: $TRIGGER_SCRIPT"

  # 4. Execute the trigger script
  ./"$TRIGGER_SCRIPT" "$CONFIG_PATH" "$PROVIDER" "$INPUT_PARAM1" "$INPUT_PARAM2"

  echo "Trigger script completed successfully."

  # 5. Execute the log retrieval script
  # ./log_retrieval.sh "$CONFIG_NAME"
  sleep 30
  if [[ "$PROVIDER" == "aws" ]]; then
    echo "Executing log_retrieval-aws.py"
    REGION_AWS=$(echo "$ARTILLERY_SCENARIOS" | yq ".\"$PROVIDER\".region" - | tr -d '"')
    LOG_GROUP=$(echo "$ARTILLERY_SCENARIOS" | yq ".\"$PROVIDER\".loggroup" - | tr -d '"')
    ./log_retrieval-aws.py "$CONFIG_NAME" "$LOG_GROUP" "$REGION_AWS"
  elif [[ "$PROVIDER" == "gcp" ]]; then
    echo "Executing log_retrieval-gcp.py"
    PROJECT_ID=$(echo "$ARTILLERY_SCENARIOS" | yq ".\"$PROVIDER\".projectid" - | tr -d '"')
    ./log_retrieval-gcp.py "$CONFIG_NAME" "$PROJECT_ID" "region"
  fi

  echo "Log retrieval completed successfully."

  # 6. Execute the statistics script
  echo "Executing confidence interval analysis..."
  ./bootstrap_percentile_ci.py "$CONFIG_NAME"

  echo "Statistics computation completed successfully."

  echo "===================================================================="
  echo " Orchestrator: Benchmark process for '${CONFIG_NAME}' completed and provider '$PROVIDER'."
  echo "===================================================================="
done

exit 0
