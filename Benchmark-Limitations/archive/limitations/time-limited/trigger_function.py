#!/usr/bin/env python3
"""
Time-Limited Trigger Function

This script:
1. Reads a 'time-limited.yaml' config with fields like:
   - mode: "time-limited"
   - benchmark: "monte-carlo" or "sieve-of-eratosthenes"
   - test_duration: int (in seconds)
   - arrival_rate: float (requests/second)
   - artillery_scenarios: dict containing 'aws' and 'gcp' with 'path' and 'target'
2. Iterates over each cloud provider's Artillery scenario.
3. Creates temporary Artillery configurations with the correct target URLs.
4. Runs Artillery for each cloud provider.
"""

import argparse
import subprocess
import yaml
import logging
import os
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed

def setup_logger():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
    return logging.getLogger("TimeLimited")

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
        "DURATION": config.get('test_duration', 60),
        "ARRIVALRATE": config.get('arrival_rate', 2),
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
    parser = argparse.ArgumentParser(description="Time-Limited Trigger Function")
    parser.add_argument('--config', type=str, required=True, help='Path to the time-limited YAML config file')
    args = parser.parse_args()

    logger = setup_logger()

    # Load config
    config = load_config(args.config)
    benchmark = config.get('benchmark')
    test_duration = config.get('test_duration', 60)
    arrival_rate = config.get('arrival_rate', 5)
    artillery_scenarios = config.get('artillery_scenarios', {})

    if not benchmark:
        logger.error("Benchmark function not specified in config.")
        sys.exit(1)

    with ThreadPoolExecutor(max_workers=len(artillery_scenarios)) as executor:
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

    logger.info("Time-limited benchmark completed successfully.")

def load_config(config_path):
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

if __name__ == "__main__":
    main()
