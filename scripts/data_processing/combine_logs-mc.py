import os
import re
import csv
from collections import defaultdict

# Get user input for the folder containing log files and the output file
log_folder = input("Enter the path to the folder containing log files: ").strip()
output_file = input("Enter the name of the output file (e.g., combined_logs.csv): ").strip()

# Regular expression to extract the date and optional descriptor from filenames
date_pattern = re.compile(r"(\d{8})(?:-([a-zA-Z0-9]+))?\.csv")


# Dictionary to hold logs grouped by date and descriptor
logs_grouped = defaultdict(list)

# Iterate over all files in the folder
for filename in os.listdir(log_folder):
    if filename.endswith(".csv"):
        match = date_pattern.match(filename)
        if match:
            date = match.group(1)
            descriptor = match.group(2) if match.group(2) else "general"
            file_path = os.path.join(log_folder, filename)

            # Read the log file and store its content
            with open(file_path, "r") as log_file:
                reader = csv.reader(log_file)
                header = next(reader)  # Skip header
                logs_grouped[(date, descriptor)].append((header, list(reader)))

# Write combined logs to the output file
with open(output_file, "w", newline="") as output:
    writer = csv.writer(output)

    for (date, descriptor), logs in sorted(logs_grouped.items()):
        # Write the date and descriptor as a section header
        output.write(f"{date}, {descriptor}\n")

        for header, rows in logs:
            # Write the header (only once per group of logs)
            writer.writerow(header)
            # Write all rows
            writer.writerows(rows)

        # Add a blank line for separation between sections
        output.write("\n")

print(f"Logs have been combined and written to {output_file}")
