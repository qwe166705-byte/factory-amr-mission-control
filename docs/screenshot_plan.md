# Screenshot Capture Plan

作品集不需要很多截圖。建議只保留 3–4 張真正有資訊量的。

## 1. Dashboard — Normal Operation

建議檔名：

```text
docs/images/dashboard_normal.png
```

畫面應包含：
- MONITOR = ONLINE
- SYSTEM READY = READY
- AUTO MODE = ON
- MISSION STATE = NAVIGATING
- Mission ID
- Target
- Robot Pose
- Mission History

用途：
> README 首頁主截圖候選。

## 2. RViz — Navigation

建議檔名：

```text
docs/images/rviz_navigation.png
```

應包含：
- Map
- Robot
- LaserScan
- Path
- Station markers
- Station direction arrows

## 3. Recovery / Fault Demo

建議檔名：

```text
docs/images/dashboard_recovery.png
```

最佳時機之一：

```text
MISSION STATE = SAFE_IDLE
DEMO STATUS = READY_FOR_RESET
LAST ERROR = TIMEOUT
```

這張最能區別「一般 Nav2 練習」和你的系統專案。

## 4. Optional — Mission History

建議檔名：

```text
docs/images/mission_history.png
```

顯示：
- Mission ID
- State changes
- Retry / Recovery event
- Reset event

## 截圖原則

- 不要出現公司機密資料
- 不要放內網 IP
- 不要顯示私人帳號 / token
- 不要一次放十幾張
- Dashboard + RViz + Recovery 三張已足夠
