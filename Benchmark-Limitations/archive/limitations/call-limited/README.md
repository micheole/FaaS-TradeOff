# Call-Limited Benchmark

This folder contains:
- **trigger_function.py**: Logic to run an Artillery test until a fixed number of calls (invocations) is reached.
- **call_limited_artillery.yaml**: Default Artillery scenario file for call-limited tests.

## Usage

1. Modify `call-limited.yaml` in `configurations/` to set your `total_calls`, `arrival_rate`, and `duration`.
2. The Orchestrator uses this configuration to call `trigger_function.py`, which updates and runs `call_limited_artillery.yaml`.

## Key Parameters

- **total_calls**: The number of total function invocations.
- **arrival_rate**: Requests per second (optional).
- **duration**: Time in seconds (optional).

## Example

```bash
python orchestrator.py --config configurations/call-limited.yaml
