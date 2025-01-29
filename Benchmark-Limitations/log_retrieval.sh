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

echo "Wait for 30 seconds to ensure logs are available in the cloud provider's log storage..."
sleep 30

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
API_CALL_LIMIT=60
WINDOW_DURATION=100

# Method that avoids GCP to exceed the rate limit
enforce_rate_limit() {
    CURRENT_TIME=$(date +%s)
    ELAPSED_TIME=$((CURRENT_TIME - LOOP_TIME))

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
    # Extract start-time from the log file name
    FILENAME=$(basename "$TMP_LOG_FILE" .log.tmp)
    TIMESTAMP=$(echo "$FILENAME" | grep -oE '\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}')

    # Convert timestamp to epoch time (compatible with macOS and Linux)
    if [[ -n "$TIMESTAMP" ]]; then
        # Check if OS is macOS or Linux
        if [[ "$OSTYPE" == "darwin"* ]]; then
            START_TIME=$(date -j -f "%Y-%m-%d_%H-%M-%S" "$TIMESTAMP" +"%s" 2>/dev/null)
        else
            START_TIME=$(date -d "$TIMESTAMP" +"%s" 2>/dev/null)
        fi

        if [[ -z "$START_TIME" ]]; then
            echo "Failed to parse timestamp: $TIMESTAMP"
            continue
        fi
    else
        echo "Failed to extract timestamp from filename: $FILENAME"
        continue
    fi

    END_TIME=$(date +%s)

    echo "Processing $TMP_LOG_FILE..."
    > "$LOG_FILE_NAME" # Clear final log file


    while read -r LINE; do
        echo "$LINE" >> "$LOG_FILE_NAME" # Write the current line to the final log

        if [[ "$LINE" == Unique\ ID:* ]]; then
            ID=$(echo "$LINE" | awk -F "Unique ID: " '{print $2}' | tr -d ',')

            # Use filter-log-events to retrieve logs for AWS
            FILTERED_LOGS=$(aws logs filter-log-events \
                --log-group-name "$LOG_GROUP" \
                --filter-pattern "\"REPORT\" \"$ID\"" \
                --start-time $((START_TIME * 1000)) \
                --end-time $((END_TIME * 1000)) \
                --region "$REGION_AWS" \
                --output json)

            # Extract Billed Duration from the logs
            BILLED_DURATION=$(echo "$FILTERED_LOGS" | \
                jq -r '.events[]?.message' | \
                grep "Billed Duration" | awk -F "Billed Duration: " '{print $2}' | awk '{print $1}')
            
            if [ -n "$BILLED_DURATION" ]; then
                echo "Billed Duration for Request $ID: $BILLED_DURATION ms" >> "$LOG_FILE_NAME"
            else
                echo "Billed Duration for Request $ID: Not Found" >> "$LOG_FILE_NAME"
            fi
            
            if [ -z "$FILTERED_LOGS" ]; then
                echo "Execution log for ID $ID not found."
                echo "Execution time for ID $ID: Not Found" >> "$LOG_FILE_NAME"
                continue
            fi
        fi
    done < "$TMP_LOG_FILE"
}

retrieve_gcp_logs() {
    # Extract start-time from the log file name
    LOOP_TIME=$(date +%s)
    FILENAME=$(basename "$TMP_LOG_FILE" .log.tmp)
    TIMESTAMP=$(echo "$FILENAME" | grep -oE '\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}')

    # Convert timestamp to epoch time (compatible with macOS and Linux)
    if [[ -n "$TIMESTAMP" ]]; then
        # Check if OS is macOS or Linux
        if [[ "$OSTYPE" == "darwin"* ]]; then
            START_TIME=$(date -j -f "%Y-%m-%d_%H-%M-%S" "$TIMESTAMP" +"%Y-%m-%dT%H:%M:%S%z" 2>/dev/null | sed 's/\(.\{22\}\)/\1:/')
        else
            START_TIME=$(date -d "$TIMESTAMP" +"%s" 2>/dev/null)
        fi

        if [[ -z "$START_TIME" ]]; then
            echo "Failed to parse timestamp: $TIMESTAMP"
            continue
        fi
    else
        echo "Failed to extract timestamp from filename: $FILENAME"
        continue
    fi

    END_TIME=$(date +"%Y-%m-%dT%H:%M:%S%z" | sed 's/\(.\{22\}\)/\1:/')

    echo "Processing $TMP_LOG_FILE..."
    > "$LOG_FILE_NAME" # Clear final log file


    while read -r LINE; do
        echo "$LINE" >> "$LOG_FILE_NAME" # Write the current line to the final log

        if [[ "$LINE" == Unique\ ID:* ]]; then
            ID=$(echo "$LINE" | awk -F "Unique ID: " '{print $2}' | tr -d ',')

            ((API_CALL_COUNT++))
            enforce_rate_limit

            # Use gcloud logging read to retrieve logs for GCP
            FILTERED_LOGS=$(gcloud logging read \
                "resource.type=\"cloud_function\" AND trace:\"projects/$PROJECT_ID/traces/$ID\" AND timestamp>=\"$START_TIME\" AND timestamp<=\"$END_TIME\"" \
                --project="$PROJECT_ID" \
                --limit=1 \
                --format=json)

            if [ -z "$FILTERED_LOGS" ]; then
                echo "Execution time for Trace ID $ID: Not Found" >> "$LOG_FILE_NAME"
                continue
            fi

            # Extract execution time
            EXECUTION_TIME=$(echo "$FILTERED_LOGS" | jq -r '.[] | select(.textPayload | contains("Function execution took")) | .textPayload' \
                | awk -F "Function execution took " '{print $2}' | awk -F " ms" '{print $1}')

            if [ -n "$EXECUTION_TIME" ]; then
                echo "Execution Time for Trace ID $ID: $EXECUTION_TIME ms" >> "$LOG_FILE_NAME"
            else
                echo "Execution Time for Trace ID $ID: Not Found" >> "$LOG_FILE_NAME"
            fi
        fi
    done < "$TMP_LOG_FILE"
}

# Function to recheck logs if there are any not found durations (GCP will for sure have many of them - as the Rate Limit always is exceeded - a better way to read logs would remove the necessity of this function)
recheck_logs() {
    LOG_FILE_NAME="$1"

    echo "Rechecking for 'Not Found' Trace IDs in $LOG_FILE_NAME..."

    # Make a temporary file to store updates
    TEMP_FILE=$(mktemp)

    while IFS= read -r LINE; do
        # Check if the line contains "Not Found"
        if [[ "$LINE" == *"Execution Time for Trace ID"*": Not Found" ]]; then
            TRACE_ID=$(echo "$LINE" | awk -F "Trace ID " '{print $2}' | awk -F ": Not Found" '{print $1}')

            enforce_rate_limit

            # Query logs for the execution time using the trace ID
            EXECUTION_LOG=$(gcloud logging read \
                "resource.type=\"cloud_function\" AND trace:\"projects/$PROJECT_ID/traces/$ID\" AND textPayload:\"Function execution took\"" \
                --project="$PROJECT_ID" \
                --limit=1 \
                --format=json)

            if [ -n "$EXECUTION_LOG" ]; then
                # Extract execution time
                EXECUTION_TIME=$(echo "$EXECUTION_LOG" | jq -r '.[] | select(.textPayload | contains("Function execution took")) | .textPayload' \
                    | awk -F "Function execution took " '{print $2}' | awk -F " ms" '{print $1}')

                if [ -n "$EXECUTION_TIME" ]; then
                    echo "Execution Time for Trace ID $ID: $EXECUTION_TIME ms" >> "$TEMP_FILE"
                    echo "Updated Execution Time for Trace ID $ID in $LOG_FILE_NAME"
                else
                    echo "$LINE" >> "$TEMP_FILE"  # Keep the original line if not found
                fi
            else
                echo "$LINE" >> "$TEMP_FILE"  # Keep the original line if no log is found
            fi

            # Increment API call counter
            ((API_CALL_COUNT++))
        else
            # Copy lines that don't require rechecking
            echo "$LINE" >> "$TEMP_FILE"
        fi
    done < "$LOG_FILE_NAME"

    # Replace the original log file with the updated content
    mv "$TEMP_FILE" "$LOG_FILE_NAME"

    echo "Finished rechecking 'Not Found' Trace IDs in $LOG_FILE_NAME."
}

for TMP_LOG_FILE in "$LOG_DIR"/*.tmp; do
    if [[ -f "$TMP_LOG_FILE" ]]; then
        # Check for provider to implement the right log retrieval method
        PROVIDER=$(basename "$TMP_LOG_FILE" | awk -F'_' '{print $3}')

        LOG_FILE_NAME="logs/tmp/${CONFIG_NAME}/$(basename "$TMP_LOG_FILE" .tmp).log"

        if [[ "$PROVIDER" == "aws" ]]; then
            retrieve_aws_logs
        elif [[ "$PROVIDER" == "gcp" ]]; then
            retrieve_gcp_logs
            sleep 100
            recheck_logs "$LOG_FILE_NAME"
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