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
PROVIDER="$2"
INPUT_PARAM1="$3"
INPUT_PARAM2="$4"

# Function to display usage
usage() {
  echo "Usage: $0 <path_to_config_yaml> <provider> <input_param1> <input_param2>"
  echo "Example: $0 configurations/call-limited.yaml aws 1000000 1050000"
  exit 1
}

# Check if the config file exists
if [ ! -f "$CONFIG_PATH" ]; then
  echo "Error: Configuration file not found at '$CONFIG_PATH'."
  exit 1
fi

# Extract values from YAML using yq
BENCHMARK=$(yq '.benchmark' "$CONFIG_PATH" | sed 's/^"//;s/"$//')
ARRIVAL_RATE=$(yq '.arrival_rate' "$CONFIG_PATH" | sed 's/^"//;s/"$//')
DURATION=$(yq '.duration' "$CONFIG_PATH" | sed 's/^"//;s/"$//')
ARTILLERY_SCENARIOS=$(yq '.artillery_scenarios' "$CONFIG_PATH")

# Define the configuration name based on the YAML file name
CONFIG_NAME=$(basename "$CONFIG_PATH" .yaml)

UNIQUE_ID=$(date +'%Y-%m-%d_%H-%M-%S')-$$

echo "===================================================================="
echo " Call-Limited Trigger: Starting benchmark with config '${CONFIG_NAME}' and provider '$PROVIDER'"
echo "===================================================================="

SCENARIO_PATH=$(echo "$ARTILLERY_SCENARIOS" | yq ".\"$PROVIDER\".path" - | tr -d '"')
TARGET_URL=$(echo "$ARTILLERY_SCENARIOS" | yq ".\"$PROVIDER\".target" - | tr -d '"')

# Check if the scenario file exists
if [ ! -f "$SCENARIO_PATH" ]; then
  echo "Error: Artillery scenario file '$SCENARIO_PATH' not found for provider '$PROVIDER'."
  exit 1
fi

COLD_INPUT=1000000
COLD_DURATION=10
COLD_ARRIVAL_RATE=8

WARMING_UP_ARTILLERY_CONFIG="limitations/call-limited/temp_artillery_config_warming_up.yaml"

sed -e "s/__INPUT__/$COLD_INPUT/" \
    -e "s/__DURATION__/$COLD_DURATION/" \
    -e "s/__ARRIVALRATE__/$COLD_ARRIVAL_RATE/" "$SCENARIO_PATH" > "$WARMING_UP_ARTILLERY_CONFIG"

artillery run "$WARMING_UP_ARTILLERY_CONFIG" -t "$TARGET_URL"

rm -f "$WARMING_UP_ARTILLERY_CONFIG"

# Loop through both input parameters and execute Artillery for each
for INPUT_PARAM in "$INPUT_PARAM1" "$INPUT_PARAM2"; do

  # Define the output log file for each input parameter
  TRIGGER_LOG="logs/tmp/${CONFIG_NAME}/trigger_output_${PROVIDER}_${CONFIG_NAME}-input${INPUT_PARAM}-uniqueid-$UNIQUE_ID.tmp"

  # Create a temporary artillery file for each input parameter
  TEMP_ARTILLERY_CONFIG="limitations/call-limited/temp_artillery_config_${CONFIG_NAME}_${PROVIDER}_${INPUT_PARAM}_${UNIQUE_ID}.yaml"

  sed -e "s/__INPUT__/$INPUT_PARAM/" \
      -e "s/__DURATION__/$DURATION/" \
      -e "s/__ARRIVALRATE__/$ARRIVAL_RATE/" $SCENARIO_PATH > $TEMP_ARTILLERY_CONFIG

  echo "Running Artillery for provider: $PROVIDER"
  echo "Artillery Config: $TEMP_ARTILLERY_CONFIG"

  # Execute Artillery and capture specific output lines
  artillery run "$TEMP_ARTILLERY_CONFIG" -t "$TARGET_URL" | grep -E "Unique ID:|Input:|Cold Start:" >> "$TRIGGER_LOG"

  echo "Artillery run for $PROVIDER completed. Output appended to $TRIGGER_LOG"

  # Clean up temporary Artillery config
  rm -f "$TEMP_ARTILLERY_CONFIG"
  echo "Temporary Artillery config '$TEMP_ARTILLERY_CONFIG' deleted."
done

echo "===================================================================="
echo " Call-Limited Trigger: All Artillery runs completed for '${CONFIG_NAME}' and provider '$PROVIDER'."
echo "===================================================================="

exit 0
