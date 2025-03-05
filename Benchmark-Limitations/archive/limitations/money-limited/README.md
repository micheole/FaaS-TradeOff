# Money-Limited Benchmark

This folder contains:
- **trigger_function.py**: A script that runs multiple batches of Artillery tests, checking cost after each batch.
- **money_limited_artillery.yaml**: Default Artillery scenario file for the money-limited test.

## Usage

1. Adjust `money-limited.yaml` in `configurations/`, setting `total_budget`, `batch_duration`, `arrival_rate`.
2. The orchestrator calls `trigger_function.py`, which repeatedly runs `money_limited_artillery.yaml` in small batches, checking cost in between.

## Key Parameters

- **total_budget** (USD)
- **batch_duration** (seconds)
- **arrival_rate** (requests/second)
- **max_batches** to avoid infinite loops

## Example

```bash
python orchestrator.py --config configurations/money-limited.yaml
