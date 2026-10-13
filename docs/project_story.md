# Project Story

## Problem

A basic navigation demo answers:

> Can the robot reach a pose?

A factory system must answer more questions:

- Who is allowed to dispatch?
- What happens if localization is not ready?
- What happens if Nav2 does not finish?
- Can the active goal be canceled safely?
- How many retries are allowed?
- What happens after retries fail?
- How does the robot recover?
- When may AUTO resume?
- How does an operator know the actual state?
- How are failures recorded?

This project was built to explore those system-level questions.

## Development Progression

### Phase 1 — ROS 2 Fundamentals
Topic, Service, Action, Parameter, Launch, TF, URDF, RViz, Gazebo, Nav2, AMCL.

### Phase 2 — Factory Mission Layer
Station configuration, mission IDs, fake PLC dispatch, cyclic route control and mission state machine.

### Phase 3 — Fault Handling
Navigation timeout, goal cancellation, retry count, retry delay, RecoveryManager, Return Home, SAFE_IDLE, FINAL_ERROR and manual reset.

### Phase 4 — System Readiness
Replaced blind startup waiting with:

```text
TF ready + Nav2 Action server ready
```

### Phase 5 — Observability
MissionMonitor, consolidated JSON system status, TF robot pose, SQLite mission events and Web Dashboard.

### Phase 6 — Portfolio Demo Hardening
Deterministic fault injection, runtime parameter preservation / restore and operator reset workflow.

## Key Engineering Lesson

The most important part of the project was not making navigation work.

It was learning to separate:

```text
command
state
mode
fault
recovery
observation
```

into explicit responsibilities instead of hiding everything inside one node or one boolean flag.
