# Mission State Machine

```mermaid
stateDiagram-v2
    [*] --> BOOTING
    BOOTING --> IDLE: initialization complete

    IDLE --> REQUESTED: valid station request
    REQUESTED --> NAVIGATING: Nav2 goal sent

    NAVIGATING --> ARRIVED: navigation success
    ARRIVED --> IDLE: success cleanup

    NAVIGATING --> RETRYING: failure + retry available
    RETRYING --> REQUESTED: retry delay complete

    NAVIGATING --> RECOVERING: retry budget exhausted
    RECOVERING --> RETURNING_HOME: recovery delay complete

    RETURNING_HOME --> SAFE_IDLE: Home reached
    RETURNING_HOME --> FINAL_ERROR: recovery failure

    SAFE_IDLE --> IDLE: manual reset + system ready
    FINAL_ERROR --> IDLE: manual reset + system ready
```

## State Meanings

| State | Meaning |
|---|---|
| `BOOTING` | MissionManager is starting |
| `IDLE` | Ready to accept a new mission |
| `REQUESTED` | Mission accepted and preparing navigation |
| `NAVIGATING` | Nav2 goal is active |
| `ARRIVED` | Target reached successfully |
| `RETRYING` | Normal mission failed but retry budget remains |
| `RECOVERING` | Normal retries are exhausted |
| `RETURNING_HOME` | Recovery navigation is active |
| `SAFE_IDLE` | Recovery succeeded; operator acknowledgement required |
| `FINAL_ERROR` | Recovery failed; manual intervention required |

## Retry Semantics

The initial attempt is not counted as a retry.

```text
ATTEMPT_1 → retry_count = 0
ATTEMPT_2 → retry_count = 1
ATTEMPT_3 → retry_count = 2
```

`retry_count` means the number of retry operations that actually occurred for the current mission, not the configured retry limit.
