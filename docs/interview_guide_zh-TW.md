# Interview Guide — Factory AMR Project

## 30 秒版本

> 我做了一個 ROS 2 Jazzy 的工廠 AMR Mission Control 模擬專案。除了 Nav2 自動導航，我另外做了 Fake PLC 自動派工、System Ready Interlock、Mission State Machine、Timeout、Retry、Goal Cancel、Recovery Return Home、SAFE_IDLE、Manual Reset，以及 Web Dashboard 和 SQLite Mission History。最後還做了一鍵 Fault Injection，可以穩定展示 Timeout 到 Recovery 的完整流程。

## 2 分鐘版本

> 這個專案一開始只是想學 ROS 2 Topic、Service、Action，但後來我把它往工廠系統整合方向做。
>
> Fake PLC 會依 AUTO、System Ready 和 Mission IDLE 三個條件決定能不能派工。MissionManager 接到 Station Request 後，用 Nav2 NavigateToPose Action 做導航，而且不是固定 sleep 等 Nav2，而是檢查 map 到 base_link TF 加上 Action Server 是否 Ready。
>
> 導航過程我做了 Watchdog Timeout，Timeout 時會 Cancel 目前的 Nav2 Goal，再依 Runtime max_retries 決定 Retry。Retry 用完後會進 Recovery，RecoveryManager 會 Return Home。Return Home 成功後不是直接回 IDLE，而是 SAFE_IDLE，要求人工 Reset，避免故障後直接恢復 AUTO。
>
> 系統另外有 MissionMonitor，把 Mission、AUTO、Robot Pose、Error 等狀態整合後送到 Flask Dashboard，也寫入 SQLite History。最後做了一鍵 Demo Fault，可以暫時把 navigation_timeout 調短、max_retries 設為 0，穩定展示 Timeout、Cancel、Recovery、Return Home，再自動恢復原本 Parameter。

## 常見追問

### 為什麼 Navigation 用 Action，不用 Service？

導航是 long-running operation，我需要 feedback、result、cancellation、timeout；這就是 ROS 2 Action 的使用情境。

### 為什麼 AUTO OFF 不直接取消正在跑的 Robot？

AUTO 定義成「是否允許下一筆自動派工」。正在執行的 Mission 是另一個責任。這樣操作模式和任務狀態不會被耦合。

### 為什麼需要 SAFE_IDLE？

Recovery 成功只代表 Robot 已經回到安全位置，不代表故障原因已被確認。因此流程是：

```text
Recovery success
→ SAFE_IDLE
→ Manual Reset
→ IDLE
```

### 為什麼不用 sleep(30) 等 Nav2？

固定時間不能代表系統真的 Ready。我改成檢查：

```text
map -> base_link TF
+
NavigateToPose Action server
```

### 為什麼 Mission State 用 TRANSIENT_LOCAL？

Dashboard / Monitor 可能晚一點啟動。TRANSIENT_LOCAL 可以讓 late subscriber 直接拿到最近一筆 state。

### RecoveryManager 為什麼不是 Node？

Recovery 和 MissionManager 使用同一個 Mission lifecycle、Nav2 client 和 state transitions。我希望拆責任，但不需要增加一個獨立 ROS process。

### Retry Count 為什麼第一次是 0？

`retry_count` 定義是「已經實際 retry 幾次」。

```text
第一次執行 = ATTEMPT_1 / retry_count 0
第一次重試 = ATTEMPT_2 / retry_count 1
```

### Demo Fault 是真的把導航弄壞嗎？

不是破壞 Nav2。DemoController 只是暫時調整 `navigation_timeout` 和 `max_retries`，用可控制方式製造 Timeout 路徑；之後會恢復原始參數。

### 如果真的接 PLC，要怎麼改？

把 PlcSimulator 替換成 protocol adapter，例如 TCP、OPC UA、MQTT 或廠內 API。MissionManager 仍然只需要面對 `station_request` 這個介面。

### 專案目前最大的限制？

目前是 Simulation Portfolio Project，尚未做：
- 真實馬達控制
- ros2_control
- wheel odometry
- IMU fusion
- hardware driver
- Functional Safety
- 真實 AMR deployment
