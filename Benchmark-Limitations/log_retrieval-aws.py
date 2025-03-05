#!/usr/bin/env python3

import os
import re
import json
import sys
from datetime import datetime, timezone
from collections import defaultdict
import boto3

def extract_timestamp_from_filename(filename):
    """Extracts timestamp from filename and converts it to a Unix timestamp."""
    match = re.search(r"\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}", filename)
    if match:
        timestamp = int(datetime.strptime(match.group(), "%Y-%m-%d_%H-%M-%S").timestamp())
        return timestamp
    print(f"Failed to extract timestamp from filename: {filename}")
    return None

def extract_unique_ids_and_content(log_file):
    """
    Reads a log file and extracts all Unique IDs and log lines.
    Returns a tuple (unique_ids, log_contents).
    """
    unique_ids = set()
    log_contents = []
    
    with open(log_file, "r") as file:
        for line in file:
            stripped = line.strip()
            log_contents.append(stripped)
            if "Unique ID:" in line:
                match = re.search(r"Unique ID:\s*([a-zA-Z0-9-]+)", line)
                if match:
                    unique_ids.add(match.group(1))
    
    return unique_ids, log_contents

def fetch_all_aws_logs(start_time, end_time, log_group, logs_client):
    """
    Fetch all AWS logs (REPORT lines) in multiple paginated requests.
    """

    all_events = []
    next_token = None
    
    while True:
        params = {
            "logGroupName": log_group,
            "filterPattern": "REPORT",
            "startTime": start_time * 1000,
            "endTime": end_time * 1000,
            "limit": 10000,
        }
        if next_token:
            params["nextToken"] = next_token
        
        response = logs_client.filter_log_events(**params)
        events = response.get("events", [])
        
        all_events.extend(events)
        
        next_token = response.get("nextToken")
        if not next_token:
            break
    
    return all_events

def extract_billed_durations(aws_logs, unique_ids):
    """
    Extract billed durations from AWS logs.
    """
    billed_durations = defaultdict(lambda: "Not Found")
    
    for event in aws_logs:
        log_message = event.get("message", "")
        match_id = next((uid for uid in unique_ids if uid in log_message), None)
        match_duration = re.search(r"Billed Duration:\s*(\d+)\s*ms", log_message, re.IGNORECASE)
        
        if match_id and match_duration:
            billed_durations[match_id] = f"{match_duration.group(1)} ms"
    
    return billed_durations

def process_log_file(log_file, log_group, logs_client, output_dir):
    """
    Process a single log file and extract billed durations.
    """
    base_filename = os.path.basename(log_file).replace(".tmp", ".log")
    output_path = os.path.join(output_dir, base_filename)
    
    start_time = extract_timestamp_from_filename(base_filename)
    if not start_time:
        return
    
    end_time = int(datetime.now(timezone.utc).timestamp())
    unique_ids, log_contents = extract_unique_ids_and_content(log_file)
    aws_logs = fetch_all_aws_logs(start_time, end_time, log_group, logs_client)
    billed_durations = extract_billed_durations(aws_logs, unique_ids)
    
    with open(output_path, "a") as output_file:
        for line in log_contents:
            output_file.write(line + "\n")
            if "Unique ID:" in line:
                match = re.search(r"Unique ID:\s*([a-zA-Z0-9-]+)", line)
                if match:
                    uid = match.group(1)
                    output_file.write(f"Billed Duration for Request {uid}: {billed_durations[uid]}\n")
    
    print(f"Processed log saved to {output_path}")
    os.remove(log_file)

def main():
    if len(sys.argv) != 4:
        print("Usage: python3 log_retrieval-aws.py <CONFIG_NAME> <LOG_GROUP> <REGION_AWS>")
        sys.exit(1)
    
    config_name = sys.argv[1]
    log_group = sys.argv[2]
    region = sys.argv[3]
    
    input_dir = os.path.join("logs", "tmp", config_name)
    output_dir = os.path.join("logs", "tmp", config_name)
    os.makedirs(output_dir, exist_ok=True)
    
    if not os.path.exists(input_dir):
        print(f"Error: Log directory '{input_dir}' does not exist.")
        sys.exit(1)
    
    logs_client = boto3.client("logs", region_name=region)
    log_files = [f for f in os.listdir(input_dir) if f.endswith(".tmp")]
    
    if not log_files:
        print(f"No .tmp log files found in {input_dir}.")
        sys.exit(0)
    
    for log_file in log_files:
        log_path = os.path.join(input_dir, log_file)
        print(f"Processing: {log_path}")
        process_log_file(log_path, log_group, logs_client, output_dir)
        print(f"Finished processing {log_path}.")

if __name__ == "__main__":
    main()
