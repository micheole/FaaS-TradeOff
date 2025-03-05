#!/usr/bin/env python3
"""
Call-Limited Trigger Function

This script:
1. Reads a 'call-limited.yaml' config with fields:
   - mode: "call-limited"
   - benchmark: "monte-carlo" or "sieve-of-eratosthenes"
   - total_calls: int
   - duration: (optional) time in seconds for the Artillery scenario
   - artillery_scenarios: dict containing 'aws' and 'gcp' with 'path' and 'target'
2. Iterates over each cloud provider's Artillery scenario.
3. Creates temporary Artillery configurations with the correct target URLs.
4. Runs Artillery for each cloud provider.
5. Captures specific output lines and appends them to a dedicated log file.
"""

import argparse
import subprocess
import yaml
import logging
import os
import sys
import tempfile
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from utils.config_loader import load_config
from utils.logger import setup_logger

def replace_placeholders(scenario_content, replacements):
    """
    Replace placeholders in the Artillery scenario content.
    """
    for key, value in replacements.items():
        scenario_content = scenario_content.replace(f"__{key.upper()}__", str(value))
    return scenario_content

def run_artillery(scenario_path, logger, output_log_path):
    """
    Run Artillery with the given scenario path.
    Capture specific output lines and append them to the output log file.
    
    Parameters:
    - scenario_path: Path to the Artillery YAML configuration.
    - logger: Logger instance for logging.
    - output_log_path: Path to the output log file where specific lines will be appended.
    
    Returns:
    - Boolean indicating success or failure.
    """
    logger.info(f"Running Artillery with scenario: {scenario_path}")
    
    try:
        # Execute Artillery and capture stdout and stderr
        result = subprocess.run(
            ["artillery", "run", scenario_path],
            capture_output=True,
            text=True,
            check=True  # This will raise CalledProcessError for non-zero exit codes
        )
        
        logger.info("Artillery run completed successfully.")
        
        # Define the regex pattern to match desired lines
        pattern = re.compile(r"(Unique ID:.*|Pi:.*|Trials:.*)")
        
        # Find all matching lines in stdout
        matching_lines = pattern.findall(result.stdout)
        
        if matching_lines:
            # Ensure the directory for output_log_path exists
            os.makedirs(os.path.dirname(output_log_path), exist_ok=True)
            
            # Append matching lines to the output log file
            with open(output_log_path, 'a') as log_file:
                for line in matching_lines:
                    log_file.write(line + '\n')
            
            logger.info(f"Appended {len(matching_lines)} lines to {output_log_path}")
        else:
            logger.warning("No matching lines found in Artillery output.")
        
        return True
    
    except subprocess.CalledProcessError as e:
        logger.error(f"Artillery run failed with exit code {e.returncode}")
        logger.error(f"Error output:\n{e.stderr}")
        return False

def process_provider(provider_name, scenario_info, config, logger, output_log_path):
    """
    Process a single cloud provider's Artillery scenario.
    
    Parameters:
    - provider_name: Name of the cloud provider (e.g., 'aws', 'gcp').
    - scenario_info: Dictionary containing 'path' and 'target' for the scenario.
    - config: Parsed YAML configuration.
    - logger: Logger instance for logging.
    - output_log_path: Path to the output log file for capturing specific lines.
    
    Returns:
    - Boolean indicating success or failure.
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
        "DURATION": config.get('duration', 60),
        "ARRIVALCOUNT": config.get('total_calls', 100),
        "TRIALS": config.get('trials', 1000),  # Adjust based on your scenario
    }
    scenario_content = replace_placeholders(scenario_content, replacements)
    scenario_content = scenario_content.replace("{{ target }}", target_url)

    # Create a temporary file for the modified scenario
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=".yaml") as tmp_file:
        tmp_file.write(scenario_content)
        temp_scenario_path = tmp_file.name

    logger.info(f"Temporary Artillery scenario created for {provider_name}: {temp_scenario_path}")

    # Run Artillery and capture specific output
    success = run_artillery(temp_scenario_path, logger, output_log_path)

    # Clean up temporary file
    os.remove(temp_scenario_path)
    logger.info(f"Temporary Artillery scenario deleted: {temp_scenario_path}")

    return success

def main():
    parser = argparse.ArgumentParser(description="Call-Limited Trigger Function")
    parser.add_argument('--config', type=str, required=True, help='Path to the call-limited YAML config file')
    args = parser.parse_args()

    logger = setup_logger(name="CallLimited", log_file="processed_logs/call_limited.log")

    # Load config
    config = load_config(args.config)
    benchmark = config.get('benchmark')
    total_calls = config.get('total_calls', 100)
    duration = config.get('duration', 60)
    artillery_scenarios = config.get('artillery_scenarios', {})

    if not benchmark:
        logger.error("Benchmark function not specified in config.")
        sys.exit(1)

    # Define the output log file path
    output_log_path = os.path.join("processed_logs", "call_limited_output.log")

    with ThreadPoolExecutor(max_workers=len(artillery_scenarios)) as executor:
        futures = []
        for provider, scenario_info in artillery_scenarios.items():
            futures.append(executor.submit(
                process_provider,
                provider,
                scenario_info,
                config,
                logger,
                output_log_path
            ))

        # Wait for all providers to finish
        for future in as_completed(futures):
            provider = list(artillery_scenarios.keys())[futures.index(future)]
            success = future.result()
            if not success:
                logger.error(f"Artillery run failed for {provider}. Stopping benchmark.")
                sys.exit(1)

    logger.info("Call-limited benchmark completed successfully.")

def load_config(config_path):
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

if __name__ == "__main__":
    main()
