# Time-Limited Benchmark

This folder contains:
- **trigger_function.py**: Logic to run an Artillery test for a certain duration (e.g., 120 seconds).
- **time_limited_artillery.yaml**: Artillery scenario template.

## Usage

1. Edit `time-limited.yaml` in `configurations/` to set `test_duration` and optionally `arrival_rate`.
2. The orchestrator calls `trigger_function.py`, which updates and runs `time_limited_artillery.yaml`.

## Key Parameters

- **test_duration**: Total benchmark time in seconds.
- **arrival_rate**: Requests per second.

## Example

```bash
python orchestrator.py --config configurations/time-limited.yaml
