# 90 秒作品集 Demo 影片腳本

目標：讓面試官在 60–90 秒內看到「正常派工 + 故障 Recovery」，不要把影片拍成 ROS 教學。

## 建議畫面

如果螢幕夠大：

```text
左側：RViz / Gazebo
右側：Web Dashboard
```

Terminal 只在必要時短暫切入，不要當主畫面。

## 0–8 秒：專案定位

畫面：
- Dashboard
- RViz Robot
- Station markers

旁白：
> Factory AMR Mission Control & Recovery System，使用 ROS 2 Jazzy、Nav2、AMCL 與 Gazebo，模擬工廠 AMR 的自動派工、任務監控與故障復歸流程。

## 8–25 秒：正常 AUTO 派工

操作：
1. 確認 SYSTEM READY
2. 按 `AUTO ON`
3. 顯示 AUTO MODE = ON
4. Mission State 進入 NAVIGATING
5. Robot 往 Station 移動

旁白：
> 系統只有在 Localization、Nav2、AUTO 與 Mission IDLE 條件成立時才允許自動派工。

## 25–38 秒：到站與下一站

畫面：
- Robot 到 Station
- Mission State ARRIVED → IDLE
- Mission History 更新
- 等待下一筆派工

旁白：
> Route 只有在實際 ARRIVED 後才切換下一站，避免派工狀態與實際到站不同步。

## 38–48 秒：Fault Demo

操作：
1. 等待 IDLE
2. 按 `DEMO FAULT`
3. Demo Status = ACTIVE

旁白：
> 一鍵 Fault Demo 會暫時修改 Runtime Parameter，建立可重現的 Navigation Timeout。

## 48–68 秒：Timeout / Recovery

畫面重點：

```text
NAVIGATING
↓
TIMEOUT
↓
RECOVERING
↓
RETURNING_HOME
```

旁白：
> Timeout 發生後系統會取消 Nav2 Goal；Retry 用完後進入 Recovery，並自動 Return Home。

## 68–78 秒：安全狀態

畫面：

```text
MISSION STATE = SAFE_IDLE
DEMO STATUS = READY_FOR_RESET
```

旁白：
> Recovery 完成後不會直接恢復自動派工，而是停在 SAFE_IDLE 等待 Operator 確認。

## 78–88 秒：Reset

按：

```text
RESET MISSION
```

畫面：

```text
MISSION STATE = IDLE
DEMO STATUS = IDLE
```

旁白：
> Reset 後才重新回到可派工狀態，同時 Fault Demo 的 Runtime Parameters 已恢復。

## 88–90 秒：結尾

最後一張：

```text
ROS 2 Jazzy
Nav2 / AMCL / TF
Mission State Machine
Timeout / Retry / Recovery
Web Dashboard
SQLite History
```
