#!/usr/bin/env python3
"""
Orchestrator Script for FaaS Benchmark Limitations

This script reads a configuration YAML file specifying which
limitation mode to use and its associated parameters, then
executes the corresponding trigger script. No user interaction
is required.

Author: Michele Oliva
Date: 2025-01-15
"""

import os
import sys
import argparse
import subprocess
import logging
from utils.logger import setup_logger
from utils.config_loader import load_config

# If you have a global set of recognized modes
VALID_MODES = {
    "call-limited": "limitations/call-limited/trigger_function.py",
    "time-limited": "limitations/time-limited/trigger_function.py",
    "money-limited": "limitations/money-limited/trigger_function.py",
    "accuracy-limited": "limitations/accuracy-limited/trigger_function.py"
}

def main():
    # Set up argument parsing
    parser = argparse.ArgumentParser(description="FaaS Benchmark Orchestrator")
    parser.add_argument('--config', type=str, required=True,
                        help='Path to the YAML configuration file specifying the limitation mode and parameters.')
    parser.add_argument('--logs_dir', type=str, default='processed_logs',
                        help='Directory to store processed log files.')
    parser.add_argument('--aggregate', action='store_true',
                        help='If set, run the aggregator script after completion.')
    parser.add_argument('--output', type=str, default='aggregated_logs.csv',
                        help='Path for the aggregated CSV output file.')
    args = parser.parse_args()

    logger = setup_logger(name="Orchestrator", log_file="orchestrator.log")
    logger.info("Starting Orchestrator...")

    # 1. Load configuration
    config_path = args.config
    if not os.path.exists(config_path):
        logger.error(f"Configuration file not found: {config_path}")
        sys.exit(1)
    config = load_config(config_path)

    # 2. Identify limitation mode
    mode = config.get("mode")
    if not mode or mode not in VALID_MODES:
        logger.error(f"Invalid or missing mode in config. Supported modes: {list(VALID_MODES.keys())}")
        sys.exit(1)

    logger.info(f"Using limitation mode: {mode}")

    # 3. Run trigger script for the specified mode
    trigger_script = VALID_MODES[mode]
    if not os.path.exists(trigger_script):
        logger.error(f"Trigger script does not exist for mode '{mode}': {trigger_script}")
        sys.exit(1)

    # 4. Subprocess call to the trigger_function.py
    #    We pass the entire config file so the script can interpret relevant parameters.
    try:
        subprocess.run(["python", trigger_script, "--config", config_path], check=True)
        logger.info(f"Benchmark for mode '{mode}' completed successfully.")
    except subprocess.CalledProcessError as e:
        logger.error(f"Benchmark failed with error: {e}")
        sys.exit(1)

    # 5. Optional aggregator step
    if args.aggregate:
        logger.info("Starting aggregator to consolidate log files.")
        aggregator_cmd = ["python", "aggregator.py", "--logs_dir", args.logs_dir, "--output", args.output]
        try:
            subprocess.run(aggregator_cmd, check=True)
            logger.info(f"Aggregation completed. Results saved to {args.output}")
        except subprocess.CalledProcessError as e:
            logger.error(f"Aggregator failed with error: {e}")
            sys.exit(1)

    logger.info("Orchestrator finished successfully.")

if __name__ == "__main__":
    main()