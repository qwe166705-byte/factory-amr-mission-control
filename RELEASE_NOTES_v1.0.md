# V1.0 Release Notes

## Factory AMR Mission Control & Recovery System

Release type: **Portfolio Feature Freeze**

### Included

- ROS 2 Jazzy mission orchestration
- Nav2 NavigateToPose Action integration
- AMCL / TF readiness check
- configurable stations
- fake PLC station dispatch
- AUTO ON / OFF
- cyclic route handling
- mission IDs
- mission state machine
- navigation watchdog timeout
- asynchronous goal cancellation
- runtime retry parameters
- retry delay
- recovery manager
- Return Home
- SAFE_IDLE
- FINAL_ERROR
- manual reset
- custom RViz visualization
- MissionMonitor
- robot pose monitoring
- SQLite mission history
- Flask dashboard
- one-click fault injection
- runtime parameter restore

### Feature-Freeze Policy

After V1.0:
- no new major mission-control features are planned for this branch,
- changes should focus on documentation, testing, screenshots and portfolio presentation,
- major robotics learning features should move to a future V1.1 / V2 branch or a separate project.

### Next Technical Learning Track

- C++ ROS 2
- ros2_control
- differential-drive kinematics
- wheel odometry
- IMU
- robot_localization / EKF
- real sensors
- controlled hardware integration
