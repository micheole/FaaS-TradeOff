#!/bin/bash

# Check if the user provided the required arguments
if [ "$#" -lt 1 ]; then
    echo "Usage: $0 <TRIALS>"
    exit 1
fi

TRIALS=$1

sed "s/__TRIALS__/$TRIALS/" ../../../configurations/monte-carlo/aws/temp.yaml > ../../../configurations/monte-carlo/aws/test.yaml

# Define the Artillery test file and log file
LOG_DIR="../../../../data/monte-carlo/aws/logs"
ARTILLERY_TEST_FILE="test.yaml"
LOG_FILE_NAME="$LOG_DIR/aws-log-trials-$TRIALS-$(date +'%Y-%m-%d_%H-%M-%S').log"

echo "Running with TRIALS=$TRIALS"

START_TIME=$(date +%s)
artillery run ../../../configurations/monte-carlo/aws/test.yaml -t "https://mg29etspsa.execute-api.eu-central-1.amazonaws.com/dev/lambda" | grep -E "Unique ID:|Pi:|Trials:" >> "$LOG_FILE_NAME.tmp"

if [ $? -ne 0 ]; then
    echo "Artillery test failed. Check the logs in $LOG_FILE_NAME."
    exit 1
else
    echo "Artillery test completed. Logs saved to $LOG_FILE_NAME."
fi

echo "Waiting 2 minutes for CloudWatch logs to update..."
sleep 120

AWS_REGION="eu-central-1"
LOG_GROUP="/aws/lambda/json_terraform_lambda_monte_carlo_testing" # Replace with your Lambda function log group

> "$LOG_FILE_NAME" # Clear final log file

# Process each Request ID block and add the billed duration
while read -r LINE; do
    echo "$LINE" >> "$LOG_FILE_NAME" # Write the current line (Unique ID block) to the final log

    if [[ "$LINE" == Unique\ ID:* ]]; then
        REQUEST_ID=$(echo "$LINE" | awk -F "Unique ID: " '{print $2}' | tr -d ',')

        # Query CloudWatch logs for the specific Request ID
        QUERY_ID=$(aws logs start-query \
            --log-group-name "$LOG_GROUP" \
            --query-string "fields @message | filter @message like 'REPORT' and @message like '$REQUEST_ID'" \
            --start-time "$START_TIME" \
            --end-time $(date +%s) \
            --region "$AWS_REGION" \
            --output text)
        
        if [ -z "$QUERY_ID" ]; then
            echo "Failed to start CloudWatch query for Request ID: $REQUEST_ID" >> "$LOG_FILE_NAME"
            continue
        fi

        # Fetch query results
        RESULT=$(aws logs get-query-results --query-id "$QUERY_ID" --region "$AWS_REGION")

        # Extract Billed Duration
        BILLED_DURATION=$(echo "$RESULT" | \
            jq -r '.results[] | .[] | select(.field == "@message") | .value' | \
            grep "Billed Duration" | awk -F "Billed Duration: " '{print $2}' | awk '{print $1}')
        
        if [ -n "$BILLED_DURATION" ]; then
            echo "Billed Duration for Request $REQUEST_ID: $BILLED_DURATION ms" >> "$LOG_FILE_NAME"
        else
            echo "Billed Duration for Request $REQUEST_ID: Not Found" >> "$LOG_FILE_NAME"
        fi
    fi
done < "$LOG_FILE_NAME.tmp"

# Remove the temporary file
rm "$LOG_FILE_NAME.tmp"

# Output the final log
echo "Relevant details saved to $LOG_FILE_NAME."
cat "$LOG_FILE_NAME"