#!/bin/bash

# Check if the user provided the required arguments
if [ "$#" -lt 1 ]; then
    echo "Usage: $0 <TRIALS>"
    exit 1
fi

# Get the URL and number of trials from the command-line arguments
# URL=$1
TRIALS=$1

sed "s/__TRIALS__/$TRIALS/" temp.yaml > test.yaml

# Define the Artillery test file and log file
LOG_DIR="./logs"
ARTILLERY_TEST_FILE="test.yaml"
LOG_FILE_NAME="$LOG_DIR/gcp-log-trials-$TRIALS-$(date +'%Y-%m-%d_%H-%M-%S').log"

echo "Running with TRIALS=$TRIALS"

artillery run test.yaml -t "https://europe-west3-monte-carlo-estimation-testing.cloudfunctions.net/json_terraform_gcp_function_monte_carlo" | grep -E "Trace ID:|Unique ID:|Pi:|Trials:" >> "$LOG_FILE_NAME.tmp"

if [ $? -ne 0 ]; then
    echo "Artillery test failed. Check the logs in $LOG_FILE_NAME."
    exit 1
else
    echo "Artillery test completed. Logs saved to $LOG_FILE_NAME.tmp."
fi

# Extract all unique IDs and trace IDs from the Artillery output
TRACE_IDS=$(grep "Trace ID:" "$LOG_FILE_NAME.tmp" | awk -F "Trace ID: " '{print $2}' | tr -d ',')

PROJECT_ID="monte-carlo-estimation-testing"  # Replace with your GCP Project ID

echo "Waiting for 2 minutes for logs to update..."
sleep 120

> "$LOG_FILE_NAME" # Clear final log file

# Process each Trace ID block and append the execution time
while read -r LINE; do
    echo "$LINE" >> "$LOG_FILE_NAME" # Write the current line (Trace ID block) to the final log

    if [[ "$LINE" == Trace\ ID:* ]]; then
        TRACE_ID=$(echo "$LINE" | awk -F "Trace ID: " '{print $2}' | tr -d ',')

        # Query logs for the execution time using the trace ID
        EXECUTION_LOG=$(gcloud logging read \
            "resource.type=\"cloud_function\" AND trace:\"projects/$PROJECT_ID/traces/$TRACE_ID\" AND textPayload:\"Function execution took\"" \
            --project="$PROJECT_ID" \
            --limit=1 \
            --format=json)

        if [ -z "$EXECUTION_LOG" ]; then
            echo "Execution log for Trace ID $TRACE_ID not found."
            echo "Execution time for Trace ID $TRACE_ID: Not Found" >> "$LOG_FILE_NAME"
            continue
        fi

        # Extract execution time
        EXECUTION_TIME=$(echo "$EXECUTION_LOG" | jq -r '.[] | select(.textPayload | contains("Function execution took")) | .textPayload' \
            | awk -F "Function execution took " '{print $2}' | awk -F " ms" '{print $1}')

        if [ -n "$EXECUTION_TIME" ]; then
            echo "Execution Time for Trace ID $TRACE_ID: $EXECUTION_TIME ms" >> "$LOG_FILE_NAME"
        else
            echo "Execution Time for Trace ID $TRACE_ID: Not Found" >> "$LOG_FILE_NAME"
        fi
    fi
done < "$LOG_FILE_NAME.tmp"

# Remove the temporary file
rm "$LOG_FILE_NAME.tmp"

# Output the final log
echo "Relevant details saved to $LOG_FILE_NAME."
cat "$LOG_FILE_NAME"

# for TRACE_ID in $TRACE_IDS; do
#     echo "Processing Trace ID: $TRACE_ID"

#     # Query logs for the execution time using the trace ID
#     EXECUTION_LOG=$(gcloud logging read \
#         "resource.type=\"cloud_function\" AND trace:\"projects/$PROJECT_ID/traces/$TRACE_ID\" AND textPayload:\"Function execution took\"" \
#         --project="$PROJECT_ID" \
#         --limit=1 \
#         --format=json)

#     if [ -z "$EXECUTION_LOG" ]; then
#         echo "Execution log for Trace ID $TRACE_ID not found."
#         continue
#     fi

#     # Extract execution time
#     EXECUTION_TIME=$(echo "$EXECUTION_LOG" | jq -r '.[] | select(.textPayload | contains("Function execution took")) | .textPayload' \
#         | awk -F "Function execution took " '{print $2}' | awk -F " ms" '{print $1}')

#     if [ -n "$EXECUTION_TIME" ]; then
#         echo "Execution Time for Trace ID $TRACE_ID: $EXECUTION_TIME ms" >> "$LOG_FILE_NAME"
#     else
#         echo "Execution time for Trace ID $TRACE_ID not found." >> "$LOG_FILE_NAME"
#     fi
# done
