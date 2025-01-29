#!/usr/bin/env bash
#
# trigger_function.sh
#
# Usage:
#   ./limitations/call-limited/trigger_function.sh <path_to_config_yaml>
#
# Description:
#   1. Parses the YAML configuration to extract necessary parameters.
#   2. For each cloud provider (AWS, GCP), it:
#      a. Generates a temporary Artillery YAML by replacing placeholders.
#      b. Runs Artillery with the generated configuration.
#      c. Greps specific output lines and appends them to a dedicated log file.

set -euo pipefail

CONFIG_PATH="$1"

# Function to display usage
usage() {
  echo "Usage: $0 <path_to_config_yaml>"
  echo "Example: $0 configurations/call-limited.yaml"
  exit 1
}

# Check if the config file exists
if [ ! -f "$CONFIG_PATH" ]; then
  echo "Error: Configuration file not found at '$CONFIG_PATH'."
  exit 1
fi

# Extract values from YAML using yq
BENCHMARK=$(yq '.benchmark' "$CONFIG_PATH" | sed 's/^"//;s/"$//')
TOTAL_CALLS=$(yq '.total_calls' "$CONFIG_PATH" | sed 's/^"//;s/"$//')
DURATION=$(yq '.duration' "$CONFIG_PATH" | sed 's/^"//;s/"$//')
ARTILLERY_SCENARIOS=$(yq '.artillery_scenarios' "$CONFIG_PATH")
INPUT=1000000

# Define the configuration name based on the YAML file name
CONFIG_NAME=$(basename "$CONFIG_PATH" .yaml)

UNIQUE_ID=$(date +'%Y-%m-%d_%H-%M-%S')-$$

echo "===================================================================="
echo " Call-Limited Trigger: Starting benchmark with config '${CONFIG_NAME}'"
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

  # Define the output log file
  TRIGGER_LOG="logs/tmp/${CONFIG_NAME}/trigger_output_${PROVIDER}_${CONFIG_NAME}-uniqueid-$UNIQUE_ID.tmp"

  # Create a temporary artillery file
  TEMP_ARTILLERY_CONFIG="limitations/call-limited/temp_artillery_config_${CONFIG_NAME}_${PROVIDER}_${UNIQUE_ID}.yaml"

  sed -e "s/__INPUT__/$INPUT/" \
    -e "s/__DURATION__/$DURATION/" \
    -e "s/__ARRIVALCOUNT__/$TOTAL_CALLS/" $SCENARIO_PATH > $TEMP_ARTILLERY_CONFIG
  
  echo "Running Artillery for provider: $PROVIDER"
  echo "Artillery Config: $TEMP_ARTILLERY_CONFIG"
  
  # Execute Artillery and capture specific output lines
  artillery run $TEMP_ARTILLERY_CONFIG -t $TARGET_URL | grep -E "Unique ID:|Pi:|Trials:" >> $TRIGGER_LOG
  
  echo "Artillery run for $PROVIDER completed. Output appended to $TRIGGER_LOG"
  
  # Clean up temporary Artillery config
  rm -f "$TEMP_ARTILLERY_CONFIG"
  echo "Temporary Artillery config '$TEMP_ARTILLERY_CONFIG' deleted."
done

echo "===================================================================="
echo " Call-Limited Trigger: All Artillery runs completed for '${CONFIG_NAME}'."
echo "===================================================================="

exit 0
