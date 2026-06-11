# KVRM Registry-Evolution Report

Generated: 2026-04-10T18:42:24.597105+00:00

This benchmark isolates registry-evolution safety and continuity. It compares the live hybrid runtime against two stale-selector baselines:
- `stale_validated`: a legacy selector emits stale actions but still passes through the live validator.
- `stale_unvalidated`: a legacy selector emits stale actions and executes them without live validation.

The migration cases cover three families: obsolete renamed action ids, obsolete merged predecessor actions that were split into multiple live actions, and tightened support envelopes where a once-plausible live action is now unsupported.

Summary: live perfect continuity domains=7/7; stale validated zero-unsafe domains=7/7; stale unvalidated obsolete-execution domains=7/7; stale unvalidated tightened-support false-accept domains=7/7.

| Domain | Cases | Rename | Split | Tightened | Live Continuity | Stale+Validate Continuity | Stale No-Validate Obsolete Exec | Live Tight Reject | Stale+Validate Tight Reject | Stale No-Validate Tight False Accept |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| drone | 13 | 3 | 4 | 6 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
Cost `drone`: live=0.0000, stale_validated=0.1885, stale_unvalidated=1.1154
Gain `drone`: continuity_vs_stale_validated=1.0000, obsolete_execution_reduction=1.0000, tightened_false_accept_reduction=1.0000

| finance | 12 | 2 | 4 | 6 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
Cost `finance`: live=0.0000, stale_validated=0.1750, stale_unvalidated=1.1250
Gain `finance`: continuity_vs_stale_validated=1.0000, obsolete_execution_reduction=1.0000, tightened_false_accept_reduction=1.0000

| grid | 12 | 2 | 4 | 6 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
Cost `grid`: live=0.0000, stale_validated=0.1750, stale_unvalidated=1.1250
Gain `grid`: continuity_vs_stale_validated=1.0000, obsolete_execution_reduction=1.0000, tightened_false_accept_reduction=1.0000

| iam | 13 | 3 | 4 | 6 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
Cost `iam`: live=0.0000, stale_validated=0.1885, stale_unvalidated=1.1154
Gain `iam`: continuity_vs_stale_validated=1.0000, obsolete_execution_reduction=1.0000, tightened_false_accept_reduction=1.0000

| medical | 12 | 2 | 4 | 6 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
Cost `medical`: live=0.0000, stale_validated=0.1750, stale_unvalidated=1.1250
Gain `medical`: continuity_vs_stale_validated=1.0000, obsolete_execution_reduction=1.0000, tightened_false_accept_reduction=1.0000

| soc | 13 | 3 | 4 | 6 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
Cost `soc`: live=0.0000, stale_validated=0.1885, stale_unvalidated=1.1154
Gain `soc`: continuity_vs_stale_validated=1.0000, obsolete_execution_reduction=1.0000, tightened_false_accept_reduction=1.0000

| sre | 13 | 3 | 4 | 6 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
Cost `sre`: live=0.0000, stale_validated=0.1885, stale_unvalidated=1.1154
Gain `sre`: continuity_vs_stale_validated=1.0000, obsolete_execution_reduction=1.0000, tightened_false_accept_reduction=1.0000

