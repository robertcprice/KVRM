from __future__ import annotations

from pathlib import Path

from kvrm_bench.replay import load_run


def test_replay_loads_prior_run(tmp_path):
    (tmp_path / 'config.json').write_text('{"run_name":"toy"}')
    (tmp_path / 'registry.json').write_text('{"registry_name":"toy"}')
    (tmp_path / 'metrics.json').write_text('{"total_cases":1}')
    (tmp_path / 'per_case_results.jsonl').write_text('{"case_id":"c1"}\n')
    (tmp_path / 'summary.md').write_text('# Summary\n')
    run = load_run(tmp_path)
    assert run['config']['run_name'] == 'toy'
    assert len(run['cases']) == 1
