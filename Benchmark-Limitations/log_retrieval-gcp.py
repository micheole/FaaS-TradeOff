#!/usr/bin/env python3

import os
import re
import json
import subprocess
import sys
from datetime import datetime, timezone

def extract_timestamp_from_filename(filename):
    """Extracts timestamp from filename and converts it to a Unix timestamp."""
    match = re.search(r"\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}", filename)
    if match:
        return int(datetime.strptime(match.group(), "%Y-%m-%d_%H-%M-%S").timestamp())
    return None

def convert_unix_to_iso8601(unix_time):
    """Converts Unix timestamp to ISO 8601 format with timezone."""
    dt = datetime.utcfromtimestamp(unix_time)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

def fetch_gcp_logs(start_time, end_time, project_id):
    """Fetch logs from GCP using `gcloud logging read`."""
    query = f'resource.type="cloud_function" AND timestamp>="{start_time}" AND timestamp<="{end_time}"'
    cmd = ["gcloud", "logging", "read", query, "--project", project_id, "--format=json"]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return json.loads(result.stdout) if result.stdout.strip() else []
    except subprocess.CalledProcessError as e:
        print(f"Error fetching logs from GCP: {e}")
        return []

def extract_execution_times(gcp_logs, unique_ids):
    """Extract execution times from GCP logs using Unique IDs."""
    execution_times = {}

    for log_entry in gcp_logs:
        log_text = log_entry.get("textPayload", "")
        trace_id = log_entry.get("trace", "").split("/")[-1]
        if trace_id in unique_ids and "Function execution took" in log_text:
            match = re.search(r"Function execution took (\d+) ms", log_text)
            if match:
                execution_times[trace_id] = f"{match.group(1)} ms"
    return execution_times

def process_log_file(log_file, project_id):
    """
    Process a single log file:
      - Extracts a timestamp from its filename.
      - Reads the file to collect Unique IDs.
      - Fetches corresponding GCP logs.
      - Writes a processed output file (in the same folder) with execution times appended.
      - Removes the original .tmp file.
    """
    filename = os.path.basename(log_file).replace(".tmp", ".log")
    output_path = os.path.join(os.path.dirname(log_file), filename)

    start_time_unix = extract_timestamp_from_filename(filename)
    if not start_time_unix:
        print(f"Failed to extract timestamp from {filename}, skipping.")
        return

    end_time_unix = int(datetime.now(timezone.utc).timestamp())
    start_time_iso = convert_unix_to_iso8601(start_time_unix)
    end_time_iso = convert_unix_to_iso8601(end_time_unix)

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

    gcp_logs = fetch_gcp_logs(start_time_iso, end_time_iso, project_id)
    execution_times = extract_execution_times(gcp_logs, unique_ids)

    with open(output_path, "a") as output_file:
        for line in log_contents:
            output_file.write(line + "\n")
            if "Unique ID:" in line:
                match = re.search(r"Unique ID:\s*([a-zA-Z0-9-]+)", line)
                if match:
                    uid = match.group(1)
                    exec_time = execution_times.get(uid, "Not Found")
                    output_file.write(f"Execution Time for Trace ID {uid}: {exec_time}\n")

    print(f"Processed log saved to {output_path}")
    os.remove(log_file)

def main():
    if len(sys.argv) != 4:
        print("Usage: python3 log_retrieval-gcp.py <configuration_name> <project_id> <region>")
        sys.exit(1)

    config_name = sys.argv[1]
    project_id = sys.argv[2]

    log_dir = os.path.join("logs", "tmp", config_name)
    if not os.path.exists(log_dir):
        print(f"Error: Log directory '{log_dir}' does not exist.")
        sys.exit(1)

    log_files = [f for f in os.listdir(log_dir) if f.endswith(".tmp")]
    if not log_files:
        print(f"No .tmp log files found in {log_dir}.")
        sys.exit(0)

    for log_file in log_files:
        log_path = os.path.join(log_dir, log_file)
        print(f"Processing: {log_path}")
        process_log_file(log_path, project_id)
        print(f"Finished processing {log_path}.")

if __name__ == "__main__":
    main()
