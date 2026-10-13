# Portfolio Finalization Checklist

## Code
- [x] V1.0 feature freeze
- [x] clean build
- [x] full acceptance test
- [x] local Git repository
- [x] V1.0 commit
- [ ] V1.0 Git tag
- [ ] optional second static code review
- [ ] final `git status` clean

## Repository
- [x] English README
- [x] Chinese README
- [x] architecture documentation
- [x] mission state-machine documentation
- [x] fault-demo flow documentation
- [x] acceptance test document
- [x] resume bullets
- [x] interview guide
- [x] project story
- [ ] add real screenshots
- [ ] add demo video link
- [ ] push to GitHub

## Screenshots
- [ ] Dashboard normal operation
- [ ] RViz navigation
- [ ] SAFE_IDLE / READY_FOR_RESET
- [ ] optional Mission History close-up

## Demo Video
- [ ] 60–90 seconds
- [ ] normal AUTO mission
- [ ] fault injection
- [ ] recovery Return Home
- [ ] SAFE_IDLE
- [ ] reset to IDLE
- [ ] no confidential factory information

## GitHub

Recommended repository name:

```text
factory-amr-mission-control
```

Recommended description:

```text
ROS 2 Jazzy factory AMR mission-control simulation with Nav2, auto dispatch, timeout/retry/recovery, monitoring and web dashboard.
```

Suggested topics:

```text
ros2
robotics
nav2
amr
autonomous-mobile-robot
gazebo
amcl
python
robotics-software
```

## Interview Readiness

Be able to explain without looking at code:

- Topic vs Service vs Action
- Nav2 Action lifecycle
- `map / odom / base_link`
- System Ready design
- AUTO vs Mission State
- timeout and cancellation
- retry semantics
- recovery state machine
- SAFE_IDLE
- QoS TRANSIENT_LOCAL
- why RecoveryManager is not another ROS node
- project limitations and next learning steps
