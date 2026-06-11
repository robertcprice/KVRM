# KVRM Artifacts Schema

Each benchmark run writes a single run directory with:

- `config.json`: run configuration and thresholds
- `registry.json`: canonical registry payload used for the run
- `metrics.json`: aggregated benchmark metrics
- `per_case_results.jsonl`: one JSON object per evaluated case
- `summary.md`: human-readable summary

## config.json
Must include:
- run_name
- selector_name
- threshold
- timestamp
- notes (optional)

## registry.json
Must include canonical registry content plus computed digest.

## metrics.json
Must include all required metrics from the metrics schema plus counts.

## per_case_results.jsonl
Each row must include:
- case_id
- supported
- ood
- expected_action_id
- selected_action_id
- final_status
- confidence
- abstained
- fallback_used
- valid
- correct
- latency_ms
- validation_reason
- execution_status

## summary.md
Must contain:
- run metadata
- registry metadata
- key metrics table
- counts table
- notes on abstention/fallback behavior
