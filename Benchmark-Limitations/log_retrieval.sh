#!/usr/bin/env bash
#
# log_retrieval.sh
#
# Usage:
#   ./log_retrieval.sh <config_name>
#
# Description:
#   1. Based on the configuration name, retrieves logs or metrics from cloud providers or local logs.
#   2. Aggregates the retrieved data into a consolidated log file for statistics computation.

set -euo pipefail

# Function to display usage
usage() {
    echo "Usage: $0 <config>"
    echo "Example: $0 call-limited"
    exit 1
}

# Get the configuration name from the first argument
CONFIG_NAME="$1"

# Check if all required parameters are set
if [[ -z "${CONFIG_NAME}" ]]; then
    echo "Error: Missing required parameter: Configuration."
    usage
fi

LOG_DIR="logs/tmp/${CONFIG_NAME}"

echo "===================================================================="
echo " Log Retrieval: Starting retrieval for '${CONFIG_NAME}'"
echo "===================================================================="

echo "Wait for 10 seconds to ensure logs are available in the cloud provider's log storage..."
sleep 10

# Load the artillery scenarios from the configuration
CONFIG_PATH="configurations/${CONFIG_NAME}.yaml"
ARTILLERY_SCENARIOS=$(yq '.artillery_scenarios' "$CONFIG_PATH")

# Extract cloud providers from the artillery scenarios
CLOUD_PROVIDERS=$(echo "$ARTILLERY_SCENARIOS" | yq 'keys | .[]' -)

# Iterate over each cloud provider to retrieve region and log-group (aws) and project-id (gcp)
for provider in $CLOUD_PROVIDERS; do
    PROVIDER=$(echo "$provider" | tr -d '"')

    if [[ "$PROVIDER" == "aws" ]]; then
        REGION_AWS=$(echo "$ARTILLERY_SCENARIOS" | yq ".\"$PROVIDER\".region" - | tr -d '"')
        LOG_GROUP=$(echo "$ARTILLERY_SCENARIOS" | yq ".\"$PROVIDER\".loggroup" - | tr -d '"')
    elif [[ "$PROVIDER" == "gcp" ]]; then
        REGION_GCP=$(echo "$ARTILLERY_SCENARIOS" | yq ".\"$PROVIDER\".region" - | tr -d '"')
        PROJECT_ID=$(echo "$ARTILLERY_SCENARIOS" | yq ".\"$PROVIDER\".projectid" - | tr -d '"')
    else
        echo "Error: Unsupported provider '$PROVIDER'. Please add retrieval logic for this provider."
        # Exit the script if an unsupported provider is encountered
        exit 1
    fi
done

# Add a counter to avoid the RATE_LIMIT_EXCEEDED for GCP
# Also add a LOOP_TIME of 60 seconds
API_CALL_COUNT=0
API_CALL_LIMIT=50
WINDOW_DURATION=100

# Method that avoids GCP to exceed the rate limit
enforce_rate_limit() {
    CURRENT_TIME=$(date +%s)
    ELAPSED_TIME=$((CURRENT_TIME - LOOP_TIME))

    # echo "API CALL: $API_CALL_COUNT"
    # echo "Time: $ELAPSED_TIME"

    if [ "$API_CALL_COUNT" -ge "$API_CALL_LIMIT" ]; then
        if [ "$ELAPSED_TIME" -lt "$WINDOW_DURATION" ]; then
            SLEEP_DURATION=$((WINDOW_DURATION - ELAPSED_TIME))
            echo "API call limit reached. Waiting for $SLEEP_DURATION seconds to avoid exceeding quota..."
            sleep "$SLEEP_DURATION"

            # Reset the counter and window start time
            API_CALL_COUNT=0
            LOOP_TIME=$(date +%s)
        fi
    fi
}

retrieve_aws_logs() {
    FILENAME=$(basename "$TMP_LOG_FILE" .log.tmp)
    TIMESTAMP=$(echo "$FILENAME" | grep -oE '\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}')
    
    if [[ -n "$TIMESTAMP" ]]; then
        if [[ "$OSTYPE" == "darwin"* ]]; then
            START_TIME=$(date -j -f "%Y-%m-%d_%H-%M-%S" "$TIMESTAMP" +"%s" 2>/dev/null)
        else
            START_TIME=$(date -d "$TIMESTAMP" +"%s" 2>/dev/null)
        fi
    else
        echo "Failed to extract timestamp from filename: $FILENAME"
        return
    fi

    END_TIME=$(date +%s)
    touch "$LOG_FILE_NAME"

    # Extract all Unique IDs and store original log lines
    UNIQUE_IDS=()
    LOG_CONTENTS=()

    while read -r LINE; do
        LOG_CONTENTS+=("$LINE")  # Store original line
        # echo "$LINE" >> "$LOG_FILE_NAME"
        if [[ "$LINE" == Unique\ ID:* ]]; then
            ID=$(echo "$LINE" | awk -F "Unique ID: " '{print $2}' | tr -d ',')
            UNIQUE_IDS+=("$ID")
        fi
    done < "$TMP_LOG_FILE"

    # **Batch Query: Retrieve ALL logs at once**
    FILTERED_LOGS=$(aws logs filter-log-events \
        --log-group-name "$LOG_GROUP" \
        --filter-pattern "\"REPORT\"" \
        --start-time $((START_TIME * 1000)) \
        --end-time $((END_TIME * 1000)) \
        --region "$REGION_AWS" \
        --output json)

    touch "$LOG_FILE_NAME" 

    for LINE in "${LOG_CONTENTS[@]}"; do
        echo "$LINE" >> "$LOG_FILE_NAME"

        if [[ "$LINE" == Unique\ ID:* ]]; then
            ID=$(echo "$LINE" | awk -F "Unique ID: " '{print $2}' | tr -d ',')

            BILLED_DURATION=$(echo "$FILTERED_LOGS" | jq -r --arg id "$ID" '.events[]?.message | select(test($id))' | grep "Billed Duration" | awk -F "Billed Duration: " '{print $2}' | awk '{print $1}')

            if [[ -n "$BILLED_DURATION" ]]; then
                echo "Billed Duration for Request $ID: $BILLED_DURATION ms" >> "$LOG_FILE_NAME"
            else
                echo "Billed Duration for Request $ID: Not Found" >> "$LOG_FILE_NAME"
            fi
        fi
    done
}

retrieve_gcp_logs() {
    FILENAME=$(basename "$TMP_LOG_FILE" .log.tmp)
    TIMESTAMP=$(echo "$FILENAME" | grep -oE '\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}')

    if [[ -n "$TIMESTAMP" ]]; then
        if [[ "$OSTYPE" == "darwin"* ]]; then
            START_TIME=$(date -j -f "%Y-%m-%d_%H-%M-%S" "$TIMESTAMP" +"%Y-%m-%dT%H:%M:%S%z" 2>/dev/null | sed 's/\(.\{22\}\)/\1:/')
        else
            START_TIME=$(date -d "$TIMESTAMP" +"%s" 2>/dev/null)
        fi
    else
        echo "Failed to extract timestamp from filename: $FILENAME"
        return
    fi

    END_TIME=$(date +"%Y-%m-%dT%H:%M:%S%z" | sed 's/\(.\{22\}\)/\1:/')
    
    # Ensure the final log file exists (do not truncate yet)
    touch "$LOG_FILE_NAME"

    # 1) Read all GCP logs in one go.
    FILTERED_LOGS=$(gcloud logging read \
        "resource.type=\"cloud_function\" AND timestamp>=\"$START_TIME\" AND timestamp<=\"$END_TIME\"" \
        --project="$PROJECT_ID" \
        --format=json)

    # 2) Truncate/clear the final log file, so we can rewrite lines in correct order
    touch "$LOG_FILE_NAME"

    # 3) Process each line from the .tmp file in a single pass
    while read -r LINE; do
        # Write the line (Pi, Cold Start, or anything else) to the final log
        echo "$LINE" >> "$LOG_FILE_NAME"

        # If it's a Unique ID line, retrieve & print the associated execution time right after it
        if [[ "$LINE" == Unique\ ID:* ]]; then
            ID=$(echo "$LINE" | awk -F "Unique ID: " '{print $2}' | tr -d ',')

            # Use endswith($id) to match if .trace ends with the same string
            EXECUTION_TIME=$(echo "$FILTERED_LOGS" | jq -r --arg id "$ID" '
                .[]
                | select(.trace? | endswith($id))        # .trace ends with the unique ID
                | select((.textPayload? // "")          # textPayload not null
                  | test("Function execution took"))     # must contain the phrase
                | .textPayload
            ' | sed -nE 's/.*Function execution took ([0-9]+) ms.*/\1/p')

            if [[ -n "$EXECUTION_TIME" ]]; then
                echo "Execution Time for Trace ID $ID: $EXECUTION_TIME ms" >> "$LOG_FILE_NAME"
            else
                echo "Execution Time for Trace ID $ID: Not Found" >> "$LOG_FILE_NAME"
            fi
        fi
    done < "$TMP_LOG_FILE"
}

for TMP_LOG_FILE in "$LOG_DIR"/*.tmp; do
    if [[ -f "$TMP_LOG_FILE" ]]; then
        # Check for provider to implement the right log retrieval method
        PROVIDER=$(basename "$TMP_LOG_FILE" | awk -F'_' '{print $3}')

        LOG_FILE_NAME="logs/tmp/${CONFIG_NAME}/$(basename "$TMP_LOG_FILE" .tmp).log"

        echo "Checking: $LOG_FILE_NAME"

        if [[ "$PROVIDER" == "aws" ]]; then
            retrieve_aws_logs
        elif [[ "$PROVIDER" == "gcp" ]]; then
            retrieve_gcp_logs
        else
            echo "Error: Unsupported provider '$PROVIDER'. Please add retrieval logic for this provider."
            # Exit the script if an unsupported provider is encountered
            exit 1
        fi

        echo "Finished processing $TMP_LOG_FILE."

        # Delete the .tmp file after processing
        rm -f "$TMP_LOG_FILE"
    else
        echo "No .tmp files found in $LOG_DIR."
    fi
done

echo "===================================================================="
echo " Log Retrieval: Data extraction complete."
echo "===================================================================="

exit 0