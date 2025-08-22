# Plan/Notes for Rework of roboOperator.py

## RoboOperator Methods Req'd by State Machine

- `get_camera_should_be_running_status`

    This method drives whether the SM should go from `CHECKING_CAMERAS` --> `STARTING_CAMERAS`
- 


## Walking through the SM:
- Starts in OFF
- OFF:
    - When `robo.running == True`, the SM transitions to IDLE.
    - This assessment will get triggered every time the SM is commanded to SM.checkWhatToDo() by the QTimer in roboOperator
- IDLE:
    - If `robo.running` is True, then goes to CHECKING_CAMERAS, otherwise it just returns to OFF
- CHECKING_CAMERAS:
    - Maybe the most complex state?
    - Needs to determine if cameras should be running: 
        - `robo.get_camera_should_be_running_status()`
            - assess a sun-altitude based trigger. If it's nighttime, start 'em up.
    - Has logic for assessing camera readiness, which relies on the camera state machine, and the parsing of which cameras are in CameraState.READY.
        - This means that we have to standardize the readiness assessment! We will need to implement a readiness check. 
        - For WINTER, let's NOT touch the camera daemon code, but rather move this state assessment into the local_camera layer.
        - For all new cameras, let's move the state assessment and management into the interface daemon layer. 

## Organization Rework:

camera/
├── __init__.py
├── state.py          # Shared state definitions (CameraState enum)
├── config.py         # Configuration management (CameraInfo, CameraConfigManager)
├── base.py           # BaseCamera and interface definitions
├── status.py         # Runtime status tracking (CameraStatus)
└── implementations/  # Camera-specific implementations
    ├── __init__.py
    ├── winter.py
    └── summer.py
