# Accuracy-Limited Benchmark

This folder contains:
- **trigger_function.py**: Runs Artillery in multiple batches until a 95% confidence interval width on the mean billed duration is below a specified threshold.
- **accuracy_limited_artillery.yaml**: Default Artillery scenario template.

## Usage

1. Define `accuracy-limited.yaml` in `configurations/` with fields like `batch_duration`, `arrival_count`, `desired_ci_width`, and `max_batches`.
2. The orchestrator invokes `trigger_function.py`, which updates and repeatedly runs `accuracy_limited_artillery.yaml`.

## Key Parameters

- **batch_duration**: Each Artillery run length (seconds).
- **arrival_count** or **arrival_rate**.
- **desired_ci_width**: The 95% CI width threshold in milliseconds.
- **max_batches**: Limits how many times we rerun Artillery if the threshold isn't met yet.

## Example

```bash
python orchestrator.py --config configurations/accuracy-limited.yaml
