# Demo Fault Flow

## Purpose

The demo function creates a deterministic failure path for a portfolio presentation without permanently changing the normal mission configuration.

## High-Level Demo State

Only four operator-facing states are exposed:

```text
IDLE
ACTIVE
READY_FOR_RESET
ERROR:<reason>
```

## Flow

```mermaid
flowchart TD
    A[Demo Status: IDLE]
    B[Operator presses DEMO FAULT]
    C{SYSTEM_READY and Mission IDLE?}
    D[Demo Status: ACTIVE]
    E[AUTO OFF]
    F[Read current runtime parameters]
    G[Save navigation_timeout and max_retries]
    H[Apply fault parameters]
    I[AUTO ON]
    J[Next mission dispatched]
    K[Navigation timeout]
    L[Cancel NavigateToPose goal]
    M[Retry budget exhausted]
    N[RECOVERING]
    O[RETURNING_HOME]
    P[Restore original runtime parameters]
    Q[Demo Status: READY_FOR_RESET]
    R[Operator presses RESET MISSION]
    S[Mission State: IDLE]
    T[Demo Status: IDLE]
    X[Demo Status: ERROR]

    A --> B
    B --> C
    C -- No --> X
    C -- Yes --> D
    D --> E
    E --> F
    F --> G
    G --> H
    H --> I
    I --> J
    J --> K
    K --> L
    L --> M
    M --> N
    N --> O
    O --> P
    P --> Q
    Q --> R
    R --> S
    S --> T
```

## Meaning of READY_FOR_RESET

`READY_FOR_RESET` means:

> The failure demonstration is complete, recovery has finished, the original runtime parameters have been restored, and the system is waiting for operator acknowledgement.
