#!/usr/bin/env python3
"""
Money-Limited Trigger Function

This script:
1. Reads a 'money-limited.yaml' config with fields:
   - mode: "money-limited"
   - benchmark: "monte-carlo" or "sieve-of-eratosthenes"
   - total_budget: float (USD)
   - batch_duration: int (seconds) for each run
   - arrival_rate: requests/second
   - artillery_scenarios: dict containing 'aws' and 'gcp' with 'path' and 'target'
   - max_batches: int
2. Iterates over each cloud provider's Artillery scenario in batches.
3. Creates temporary Artillery configurations with the correct target URLs.
4. Runs Artillery for each cloud provider.
5. Checks cumulative cost after each batch and stops if budget is exceeded or max_batches reached.
"""

import argparse
import subprocess
import yaml
import logging
import os
import sys
import time
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed

def setup_logger():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
    return logging.getLogger("MoneyLimited")

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

def read_current_cost():
    """
    Implement this function to retrieve current cost spent so far.
    This might involve calling cloud provider APIs or parsing billing logs.
    For demonstration, this function returns a simulated cost.
    Replace this with actual cost retrieval logic.
    """
    # Example stub: replace with real implementation
    # For instance, fetch cost from AWS Cost Explorer or GCP Billing API
    return 0.0  # Placeholder value

def process_provider(provider_name, scenario_info, config, logger):
    """
    Process a single cloud provider's Artillery scenario in a batch.
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
    parser = argparse.ArgumentParser(description="Money-Limited Trigger Function")
    parser.add_argument('--config', type=str, required=True, help='Path to the money-limited YAML config file')
    args = parser.parse_args()

    logger = setup_logger()

    # Load config
    config = load_config(args.config)
    benchmark = config.get('benchmark')
    total_budget = config.get('total_budget', 5.0)
    batch_duration = config.get('batch_duration', 60)
    arrival_rate = config.get('arrival_rate', 5)
    artillery_scenarios = config.get('artillery_scenarios', {})
    max_batches = config.get('max_batches', 10)

    if not benchmark:
        logger.error("Benchmark function not specified in config.")
        sys.exit(1)

    current_cost = read_current_cost()
    batch_count = 0

    with ThreadPoolExecutor(max_workers=len(artillery_scenarios)) as executor:
        while current_cost < total_budget and batch_count < max_batches:
            batch_count += 1
            logger.info(f"Starting batch #{batch_count}. Current cost: ${current_cost:.2f}, Budget: ${total_budget:.2f}")

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

            # Sleep briefly to allow cost to accumulate
            time.sleep(5)

            # Update current_cost
            current_cost = read_current_cost()
            logger.info(f"After batch #{batch_count}, current cost: ${current_cost:.2f}")

            if current_cost >= total_budget:
                logger.info(f"Budget of ${total_budget:.2f} reached. Stopping benchmark.")
                break

    if current_cost < total_budget:
        logger.info(f"Reached maximum batches ({max_batches}) without fully utilizing the budget.")

    logger.info("Money-limited benchmark completed.")

def load_config(config_path):
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

if __name__ == "__main__":
    main()
