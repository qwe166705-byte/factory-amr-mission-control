# Resume Bullets

## 中文履歷 — 精簡版

**Factory AMR Mission Control & Recovery System｜ROS 2 Jazzy**

- 使用 ROS 2 Jazzy、Nav2、AMCL、Gazebo 建立工廠 AMR 任務控制模擬系統，整合 Topic / Service / Action、TF 與自動導航流程。
- 設計 Mission State Machine 與 Fake PLC Auto Dispatch，加入 System Ready Interlock，避免 Localization / Nav2 尚未就緒時派工。
- 實作 Navigation Timeout、Goal Cancel、Runtime Retry、Recovery Return Home、SAFE_IDLE / FINAL_ERROR 與 Manual Reset。
- 建立 Mission Monitor、SQLite Mission History 與 Web Dashboard，整合 AUTO、Mission、Robot Pose、Error 與 Demo Fault 狀態。
- 製作一鍵 Fault Injection Demo，可暫時修改 ROS Runtime Parameters、觸發 Timeout / Recovery 並自動恢復正常參數。

## 中文履歷 — 一行版

> ROS 2 Jazzy / Nav2 工廠 AMR Mission Control 模擬專案，實作 Auto Dispatch、TF/Localization Ready Interlock、Timeout/Retry/Recovery Return Home、Web Dashboard 與 SQLite Mission History。

## English Resume Version

**Factory AMR Mission Control & Recovery System — ROS 2 Jazzy**

- Built a factory-oriented AMR mission-control simulation using ROS 2 Jazzy, Nav2, AMCL and Gazebo, integrating Topics, Services, Actions and TF.
- Designed a mission state machine and simulated PLC auto-dispatch workflow with localization/Nav2 readiness interlocks.
- Implemented navigation watchdogs, goal cancellation, runtime retry policies, Return Home recovery, SAFE_IDLE / FINAL_ERROR states and operator reset.
- Developed a mission-monitoring layer with TF-based robot pose, SQLite event history and a Flask web dashboard.
- Added deterministic one-click fault injection that temporarily changes ROS runtime parameters, demonstrates timeout/recovery behavior and restores the original configuration.

## LinkedIn / Project Card

> Factory-oriented ROS 2 AMR system project focused on mission orchestration and fault recovery rather than basic point-to-point navigation. Includes simulated PLC auto dispatch, Nav2 Action control, TF/AMCL readiness, timeout/retry/cancel, Return Home recovery, operator reset, monitoring, SQLite history and a web dashboard.
