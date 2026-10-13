# Factory AMR Mission Control & Recovery System

> ROS 2 Jazzy · Nav2 · AMCL · Gazebo · 任務狀態機 · 自動派工 · Recovery · Monitoring · Web Dashboard

[English README](README.md)

## 專案定位

這是一個以「工廠 AMR 系統整合」為核心的 ROS 2 模擬專案。

目標不只是讓機器人在 Gazebo 裡從 A 點移動到 B 點，而是模擬工廠 AMR 實際會碰到的系統問題：

- PLC / 上位系統如何派工
- Localization / Nav2 尚未 Ready 時如何禁止派工
- Nav2 任務如何做 Timeout
- 任務失敗後如何 Retry
- Retry 用完後如何 Recovery
- Return Home 後為什麼不能直接恢復 AUTO
- Operator 如何 Reset
- 如何把 ROS 狀態整合到 Web Dashboard
- 如何留下 Mission History
- 如何用一鍵 Fault Injection 證明 Recovery 流程真的有效

因此本專案重點是 **Robotics System Integration / Mission Control / Fault Recovery**。

## V1.0 狀態

**Feature Freeze 已完成。**

已實際驗收：

- 一鍵啟動
- AMCL / TF / Nav2 readiness
- AUTO ON / OFF
- 自動循環派工
- Station 到站流程
- Navigation timeout
- Retry count
- Nav2 Goal Cancel
- Recovery
- Return Home
- SAFE_IDLE
- FINAL_ERROR
- Manual Reset
- Demo Fault Injection
- Runtime Parameter Restore
- Mission Monitor
- SQLite Mission History
- Web Dashboard
- Custom RViz

## 系統核心流程

```text
Fake PLC
   ↓
Mission Manager
   ↓
Nav2
   ↓
AMR

失敗：
NAVIGATING
   ↓
RETRYING
   ↓
RECOVERING
   ↓
RETURNING_HOME
   ↓
SAFE_IDLE / FINAL_ERROR
   ↓
Manual Reset
```

## 派工 Interlock

Fake PLC 只有在：

```text
AUTO = ON
SYSTEM_READY = TRUE
MISSION_STATE = IDLE
```

三個條件都成立時才允許派工。

AUTO OFF 不會取消正在執行的導航，只會阻止下一筆自動派工。

## System Ready

MissionManager 不使用固定 `sleep()` 猜系統是否完成啟動。

它實際檢查：

```text
map -> base_link TF
+
NavigateToPose Action Server
```

兩者 Ready 才發布：

```text
/system_ready = true
```

## Timeout / Retry / Recovery

Runtime Parameter：

```text
navigation_timeout
max_retries
retry_delay
```

第一次 Navigation 不算 Retry：

```text
ATTEMPT_1 → retry_count = 0
```

失敗並真正重新執行後才會：

```text
retry_count = 1
```

Retry 用完：

```text
RECOVERING
↓
RETURNING_HOME
```

Return Home 成功：

```text
SAFE_IDLE
```

Return Home 失敗：

```text
FINAL_ERROR
```

兩者都需要人工 Reset 才能回 `IDLE`。

## Demo Fault Injection

Dashboard 的 `DEMO FAULT` 用來做可重現作品展示：

```text
IDLE
↓
DEMO FAULT
↓
ACTIVE
↓
保存原始 Runtime Parameters
↓
AUTO OFF
↓
套用 Fault Parameters
↓
AUTO ON
↓
Navigation Timeout
↓
Cancel Nav2 Goal
↓
Recovery
↓
Return Home
↓
恢復原始 Parameters
↓
READY_FOR_RESET
↓
RESET MISSION
↓
IDLE
```

Dashboard 對外只顯示：

```text
IDLE
ACTIVE
READY_FOR_RESET
ERROR:<reason>
```

內部細節只留在 ROS Log。

## ROS 2 Components

| Component | 功能 |
|---|---|
| `mission_manager` | 任務狀態機、Nav2 Action、Timeout、Retry、Reset、System Ready |
| `recovery_manager.py` | MissionManager 內部 Recovery helper，不是獨立 Node |
| `plc_simulator` | Fake PLC、AUTO mode、派工 Interlock、Route sequencing |
| `factory_visualizer` | RViz Station、Heading、Mission visualization |
| `mission_monitor` | 系統狀態整合、Robot Pose、SQLite History |
| `demo_controller` | Fault Injection 與 Runtime Parameter Restore |
| `dashboard_bridge` | ROS / Flask Web Bridge |

## Dashboard

Dashboard 顯示：

```text
MONITOR
SYSTEM READY
AUTO MODE
MISSION STATE
MISSION ID
TARGET
RETRY
LAST ERROR
ROBOT POSE
DEMO STATUS
MISSION HISTORY
```

操作：

```text
AUTO ON
AUTO OFF
RESET MISSION
DEMO FAULT
```

網址：

```text
http://127.0.0.1:8088
```

## Build / Run

```bash
cd ~/factory_amr_ws

colcon build   --packages-select factory_amr   --symlink-install

source install/setup.bash

ros2 launch   factory_amr   factory_amr_demo.launch.py
```

## 這個專案能證明什麼

這個作品不是單純證明「我會跑 Nav2」。

它更能證明：

- ROS 2 Topic / Service / Action 設計
- Mission State Machine
- Async callback
- Nav2 Goal Cancel
- Timeout / Retry / Recovery
- Operator Interlock
- TF / Localization readiness
- Runtime Parameter
- ROS 狀態整合 Web UI
- Observability / Mission History
- Failure Mode 的系統化處理

## 專案界線

這是模擬與作品集專案。

目前沒有宣稱：

- 已部署到真實 AMR
- 已接真實工廠 PLC
- 已完成 Functional Safety
- 已完成量產環境驗證

## 後續學習

```text
C++ ROS2
↓
ros2_control
↓
Diff Drive / Kinematics
↓
Wheel Odometry
↓
IMU
↓
robot_localization / EKF
↓
Real Sensors
↓
Hardware Abstraction
```
