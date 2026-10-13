# V1.0 Acceptance Test

| Test | Expected Result | V1.0 |
|---|---|---|
| Python compile | No syntax errors | PASS |
| Clean colcon build | Package builds successfully | PASS |
| One-command launch | Integrated demo starts | PASS |
| System readiness | `/system_ready` becomes true after TF + Nav2 ready | PASS |
| Custom RViz | `factory_amr.rviz` loads | PASS |
| AUTO ON | AUTO state becomes ON | PASS |
| Auto dispatch | READY + AUTO + IDLE schedules mission | PASS |
| Navigation | Robot reaches configured station | PASS |
| Arrival | Route advances only after arrival | PASS |
| AUTO OFF | Current mission continues; future dispatch stops | PASS |
| Retry | `retry_count` increments only on actual retries | PASS |
| Runtime timeout | `navigation_timeout` is read at runtime | PASS |
| Runtime retry count | `max_retries` is read at failure time | PASS |
| Timeout cancel | Active Nav2 goal is canceled | PASS |
| Recovery | Retry exhaustion enters recovery | PASS |
| Return Home | Recovery attempts Home navigation | PASS |
| SAFE_IDLE | Successful recovery requires manual reset | PASS |
| FINAL_ERROR | Recovery failure is isolated from normal dispatch | PASS |
| Reset | SAFE_IDLE / FINAL_ERROR returns to IDLE when allowed | PASS |
| Demo Fault | Deterministic failure sequence works | PASS |
| Parameter restore | Demo restores original runtime parameters | PASS |
| Demo reset | `READY_FOR_RESET` returns to `IDLE` after reset | PASS |
| MissionMonitor | Consolidated status publisher works | PASS |
| Robot pose | `map -> base_link` pose reaches dashboard | PASS |
| AUTO dashboard state | Actual AUTO state reaches dashboard | PASS |
| Mission history | SQLite history records mission events | PASS |

## Release Decision

All V1.0 release-gate items passed.

**V1.0 Feature Freeze approved.**
