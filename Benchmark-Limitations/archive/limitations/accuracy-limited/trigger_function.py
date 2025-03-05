#!/usr/bin/env python3
"""
Accuracy-Limited Trigger Function using Artillery

This script:
1. Loads an 'accuracy-limited.yaml' config to get threshold, function_url, etc.
2. Iterates over each cloud provider's Artillery scenario.
3. Creates temporary Artillery configurations with the correct target URLs.
4. Runs Artillery for each cloud provider.
5. Checks logs to see if desired accuracy is reached.
6. Stops when threshold is met or a max invocation/cost is reached.
"""

import argparse
import subprocess
import yaml
import logging
import os
import sys
import statistics
import math
import time
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed

from utils.config_loader import load_config
from utils.helper_functions import read_accuracy_from_logs, enforce_rate_limit

def setup_logger():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
    return logging.getLogger("AccuracyLimited")

def replace_placeholders(scenario_content, replacements):
    """
    Replace placeholders in the Artillery scenario content.
    """
    for key, value in replacements.items():
        scenario_content = scenario_content.replace(f"__{key.upper()}__", str(value))
    return scenario_content

def run_artillery(scenario_path, logger):
    """
    Run Artillery with the given scenario path.
    """
    logger.info(f"Running Artillery with scenario: {scenario_path}")
    result = subprocess.run(["artillery", "run", scenario_path], capture_output=True, text=True)
    if result.returncode != 0:
        logger.error(f"Artillery run failed:\n{result.stderr}")
        return False
    logger.info("Artillery run completed successfully.")
    return True

def process_provider(provider_name, scenario_info, config, logger):
    """
    Process a single cloud provider's Artillery scenario.
    """
    path = scenario_info['path']
    target_url = scenario_info['target']

    if not os.path.exists(path):
        logger.error(f"Artillery scenario file not found for {provider_name}: {path}")
        return False

    # Read the base scenario content
    with open(path, 'r') as f:
        scenario_content = f.read()

    # Replace placeholders
    replacements = {
        "DURATION": config.get('batch_duration', 60),
        "ARRIVALCOUNT": config.get('arrival_rate', 120),
    }
    scenario_content = replace_placeholders(scenario_content, replacements)
    scenario_content = scenario_content.replace("{{ target }}", target_url)

    # Create a temporary file for the modified scenario
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=".yaml") as tmp_file:
        tmp_file.write(scenario_content)
        temp_scenario_path = tmp_file.name

    logger.info(f"Temporary Artillery scenario created for {provider_name}: {temp_scenario_path}")

    # Run Artillery
    success = run_artillery(temp_scenario_path, logger)

    # Clean up temporary file
    os.remove(temp_scenario_path)
    logger.info(f"Temporary Artillery scenario deleted: {temp_scenario_path}")

    return success

def main():
    parser = argparse.ArgumentParser(description="Accuracy-Limited Trigger Function")
    parser.add_argument('--config', required=True, help='Path to the YAML config file')
    args = parser.parse_args()

    logger = setup_logger()

    # Load configuration
    config = load_config(args.config)

    benchmark = config.get('benchmark')
    batch_duration = config.get('batch_duration', 60)
    arrival_count = config.get('arrival_count', 120)
    desired_ci_width = config.get('desired_ci_width', 5.0)
    max_batches = config.get('max_batches', 10)
    artillery_scenarios = config.get('artillery_scenarios', {})

    if not benchmark:
        logger.error("Benchmark function not specified in config.")
        sys.exit(1)

    current_ci_width = float('inf')
    batch_count = 0

    with ThreadPoolExecutor(max_workers=len(artillery_scenarios)) as executor:
        while current_ci_width > desired_ci_width and batch_count < max_batches:
            batch_count += 1
            logger.info(f"Starting batch #{batch_count}. Desired CI width: <= {desired_ci_width} ms")

            futures = []
            for provider, scenario_info in artillery_scenarios.items():
                futures.append(executor.submit(process_provider, provider, scenario_info, config, logger))

            # Wait for all providers to finish
            for future in as_completed(futures):
                provider = list(artillery_scenarios.keys())[futures.index(future)]
                success = future.result()
                if not success:
                    logger.error(f"Artillery run failed for {provider}. Stopping benchmark.")
                    sys.exit(1)

            # Allow some time for logs to propagate
            time.sleep(5)

            # Parse logs to get billed durations
            durations = read_accuracy_from_logs()
            if not durations:
                logger.warning("No billed durations found in logs. Possible invocation failure.")
                continue

            # Compute 95% CI width
            current_ci_width = compute_95_ci_width(durations)
            logger.info(f"Batch #{batch_count}: 95% CI width = {current_ci_width:.2f} ms")

            if current_ci_width <= desired_ci_width:
                logger.info(f"Desired CI width of {desired_ci_width} ms achieved. Stopping benchmark.")
                break

    if current_ci_width > desired_ci_width:
        logger.info(f"Reached maximum batches ({max_batches}) without achieving desired CI width.")

    logger.info("Accuracy-limited benchmark completed.")

def compute_95_ci_width(data):
    """
    Compute the width of the 95% confidence interval for the mean of data.
    Formula: CI width = 2 * 1.96 * (stdev / sqrt(n))
    """
    n = len(data)
    if n <= 1:
        return float('inf')  # Undefined CI
    mean_ = statistics.mean(data)
    stdev_ = statistics.stdev(data)
    sem = stdev_ / math.sqrt(n)  # Standard error of the mean
    half_ci = 1.96 * sem
    ci_width = 2 * half_ci
    return ci_width

if __name__ == "__main__":
    main()
