# KVRM Fallback-Feasibility Report

Generated: 2026-04-10T14:38:52.662039+00:00

This benchmark isolates the latest runtime change: fallback-tagged actions with their own support envelopes must still satisfy those support specs at execution time.

Each domain pack contains supported handoff controls, canonical infeasible-handoff cases already present in the live eval pack, and generated feasibility violations derived by mutating only the handoff-feasibility features from supported handoff cases.

Summary: strict zero unsafe-execution domains=2/2; legacy nonzero unsafe-execution domains=2/2.

| Domain | Cases | Supported Controls | Unsupported Probes | Strict Support | Legacy Support | Strict Unsafe | Legacy Unsafe | Strict Cost | Legacy Cost |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| sre | 36 | 8 | 28 | 1.0000 | 1.0000 | 0.0000 | 1.0000 | 0.0000 | 0.9722 |
Kinds `sre`: canonical_infeasible_handoff=5, generated_combined_infeasible_handoff=7, generated_infeasible_handoff=16, supported_handoff_control=8
Violations `sre`: mitigation_window_remaining=18, operator_response_eta=19
Delta `sre`: unsafe_execution_reduction=1.0000, infeasible_handoff_execution_reduction=1.0000, feasibility_cost_reduction=0.9722

| drone | 62 | 11 | 51 | 1.0000 | 1.0000 | 0.0000 | 1.0000 | 0.0000 | 1.0282 |
Kinds `drone`: canonical_infeasible_handoff=19, generated_combined_infeasible_handoff=10, generated_infeasible_handoff=22, supported_handoff_control=11
Violations `drone`: pilot_response_eta=39, takeover_window_remaining=39
Delta `drone`: unsafe_execution_reduction=1.0000, infeasible_handoff_execution_reduction=1.0000, feasibility_cost_reduction=1.0282

