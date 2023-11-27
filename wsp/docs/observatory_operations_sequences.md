# Observing Sequence: roboOperator

- [Robotic Observatory Main Loop](#robotic-observatory-main-loop)
  - [check_ok_to_observe(self, logcheck=False)](#check_ok_to_observe)
  - [checkWhatToDo(self)](#checkwhattodo)
- [Observatory Startup/Shutdown Sequences](#observatory-startupshutdown-sequences)
  - [do_startup(self, startup_cameras=False)](#dostartup)
  - [do_camera_startup(self, camname)](#docamerastartup)
  - [do_camera_power_shutdown(self, camname)](#docamerapowershutdown)
  - [do_camera_shutdown(self, camname)](#docamerashutdown)
  - [do_shutdown(self, shutdown_cameras=False)](#doshutdown)
- [Camera Autostart/Autostop Sequences](#camera-autostartautostop-sequences)
  - [autoStartupSequence](#autostartupsequence)
  - [autoShutdownSequence](#autoshutdownsequence)

## `check_ok_to_observe(self, logcheck=False)` <a name="check_ok_to_observe"></a>

The `check_ok_to_observe` method checks whether it's safe to start observatory operations. This includes evaluating various conditions, such as weather and dome status, and determining if the observatory is ready for observations.

### Procedure

1. Check if the emergency stop (`estop_active`) is active. If it is, the observatory can't observe, and the method returns `False`.

2. If the observatory is in `dometest` mode, skip the full check, and the method returns `True`.

3. Verify the status of the sun to ensure it's below a certain altitude.

4. Check the dome status. If the dome shutter is open, it's considered safe to observe.

### Decision Tree

- If the emergency stop is active, return `False`.
- If in `dometest` mode, return `True`.
- If the sun is below a certain altitude, and the dome shutter is open, return `True`. Otherwise, return `False`.

### Logging

- Log an info message when the observatory is safe to observe.

# Robotic Observatory Main Loop

## `checkWhatToDo(self)` <a name="checkwhattodo"></a>

The `checkWhatToDo` method is the core routine for the robotic observatory loop. It decides the next actions based on several conditions and external factors, such as camera status, dome status, and weather conditions.

### Procedure

1. Check if the observatory is running.

2. Determine the status of the cameras and whether they should be on.

3. If the cameras should be on:
   - Check if camera startup has been requested.
   - If requested and not completed, wait.
   - If startup is complete, verify if the camera is ready to observe.
   - If not, start the camera focus sequence if necessary.

4. If the cameras should be off:
   - Check if camera shutdown has been requested.
   - If requested and not completed, wait.
   - If shutdown is complete, ensure the camera is stowed and the observatory is stowed.

5. If the observatory is running and the cameras are ready, proceed to dome, sun, and observatory checks.

6. Check if the dome is open; if not, open it.

7. Verify filter wheel homing.

8. Check camera focus and initiate a focus sequence if necessary.

9. Determine the current observation based on sun altitude, select the best target, and execute the observation.

### Decision Tree

- If the observatory is not running, do nothing.
- If the cameras should be on:
   - If startup is complete and the camera is ready, proceed to dome, sun, and observatory checks.
   - If the startup is not complete, wait.
- If the cameras should be off:
   - If shutdown is complete, stow the observatory and cameras.
   - If shutdown is not complete, wait.
- For the observatory running and cameras ready:
   - Check the dome and sun status.
   - Perform filter wheel homing.
   - Check camera focus and execute focus if necessary.
   - Determine and execute the next observation.

### Logging

- Log relevant information about camera startup, shutdown, dome status, and observatory readiness to `~/data/winter.log` on `odin`. 
- Use `self.announce` to send messages to the `#winter_observatory` slack channel, e.g., opening the dome or focusing the telescope.


# Observatory Startup/Shutdown Sequences <a name="#observatory-startupshutdown-sequences"></a>

## `do_startup(self, startup_cameras=False)` <a name="#dostartup"></a>

### Procedure
1. **Dome Setup**
   - Take control of the dome.
   - Turn off dome tracking.
   - Send the dome through its homing routine.
   - Send the dome to its home/park position.
   - Complete the dome setup.

2. **Mount Setup**
   - Connect the telescope to the mount.
   - Turn off tracking.
   - Load the pointing model explicitly.
   - Turn on the mount motors.
   - Turn on the rotator (if not in simulation mode).
   - Home the rotator (if not in simulation mode).
   - Turn on the focuser (if not in simulation mode).
   - Point the mount to home.
   - Complete the telescope setup.

3. **Mirror Cover Setup**
   - Skip mirror cover setup in simulation mode.
   - Connect to the mirror cover.
   - Open the mirror cover (if not in test mode).
   - Complete the mirror cover setup.

4. If `startup_cameras` is `True`, set up the cameras:
   - Set up chiller, ensuring it's on.
   - Power on the focal planes.
   - Initialize camera power and startup sequence for each camera.

5. If all the setup steps are successful, mark the startup as complete.

### Decision Tree
- If any setup step fails (dome, telescope, mirror cover, cameras), the corresponding `systems_started` element is `False`. The setup continues to the next step even if there is an error.
- If all setup steps succeed, `self.startup_complete` is marked as `True`.

## `do_camera_startup(self, camname)`  <a name="#docamerastartup"></a>

### Procedure
1. Set up the chiller, ensuring it's turned on.
2. Power on the focal planes.
3. Run the auto-start routine for the camera.

### Decision Tree
- If any step fails (chiller setup, focal plane power on, or camera auto-start), the corresponding `systems_started` element is `False.
- If all steps succeed, `self.camera_startup_complete` is marked as `True`.

## `do_camera_power_shutdown(self, camname)`

### Procedure
1. Turn off the LJ (LabJack) for the focal planes.
2. Turn off the PDU (Power Distribution Unit) output channel for FPAs.

### Decision Tree
- If any step fails (LJ turn off or PDU turn off), the corresponding `systems_started` element is `False`.

## `do_camera_shutdown(self, camname)`  <a name="#docamerashutdown"></a>

### Procedure
1. Run the auto-shutdown routine for the camera.

### Decision Tree
- If the auto-shutdown routine fails, the `self.camera_startup_complete` is marked as `False`.

## `do_shutdown(self, shutdown_cameras=False)`

### Procedure
1. **Dome Shutdown**
   - Make sure the dome isn't tracking the telescope.
   - Send the dome to its home/park position.
   - Close the dome.
   - Give control of the dome back.
   - Complete the dome shutdown.

2. **Mount Shutdown**
   - Turn off tracking.
   - Point the mount to home.
   - If not in simulation mode, turn off the focuser and the rotator, and then turn off the motors.
   - Disconnect the telescope.
   - Complete the telescope shutdown.

3. **Mirror Cover Closure**
   - Skip mirror cover closure in simulation mode.
   - Connect to the mirror cover.
   - Close the mirror cover.
   - Complete the mirror cover closure.

4. If `shutdown_cameras` is `True`, shut down the cameras:
   - Shut down each camera.
   - Warm the TECs to 15°C.
   - Complete the camera shutdown.

5. If all the shutdown steps are successful, mark the shutdown as complete.

### Decision Tree
- If any shutdown step fails (dome, telescope, mirror cover, cameras), the corresponding `systems_shutdown` element is `False`. The shutdown continues to the next step even if there is an error.
- If all shutdown steps succeed, `self.shutdown_complete` is marked as `True.



# Camera Autostart/Autostop Sequences <a name="#camera-autostartautostop-sequences"></a>
The camera autostart and autostop sequences are managed within the WINTER camera daemon which runs on the dedicated WINTER camera computer (`freya`). When an auto startup or auto shutdown sequence is initiated by the roboOperator, one of the following sequences is started. The sequences, like the roboOperator observing sequence is a event-driven loop where each trip through the sequence will either take an action and trigger a pause before re-running the sequence, or it will exit the sequence (either because of an error/timeout, or because the sequence has been successfully completed).

This documentation provides a detailed description of the Observatory Control class's `autoStartupSequence` and `autoShutdownSequence` methods for managing an observatory's camera.

## `autoStartupSequence`  <a name="#autostartupsequence"></a>

### Overview

The `autoStartupSequence` method executes an automatic startup sequence for the observatory's camera, ensuring that it is ready for observations. This sequence follows several critical steps:

### Steps

1. **Check Sensor Daemons**
   - Ensure that all sensor daemons are connected.
   - Restart sensor daemons if necessary (up to a maximum retry count).
   - If the retry count is exhausted, an error is logged, and manual intervention is required.
   - Logged Message using `self.announce`: "Restarting sensor daemons at addrs: [List of Addresses]."

2. **Check Sensors**
   - Verify that all sensors are connected and started up.
   - Restart sensors if necessary (up to a maximum retry count).
   - If the retry count is exhausted, an error is logged, and manual intervention is required.
   - Logged Message using `self.announce`: "Running startupCamera on these sensors: [List of Addresses]."

3. **Check for Validated Bias Frames**
   - Ensure that all sensors have a record of a good bias frame.
   - Run a check camera if bias frames are not validated.
   - Shut down sensors that did not start up properly.
   - Logged Message using `self.announce`: "Shutting down these sensors: [List of Addresses]."

4. **Manage TECs**
   - Set TEC setpoints to default values.
   - Start TECs if they are not already running.
   - Check if TECs are ready (steady and at setpoint).
   - Logged Message using `self.announce`: "TEC is taking too long to temperature! After [Max Wait Time] minutes, [Message]."

5. **Completion**
   - If all checks pass, log a success message.
   - Set the 'autoStartComplete' flag.
   - Logged Message using `self.announce`: "Camera Auto Startup Sequence Complete :banana-dance:."

## `autoShutdownSequence` <a name="#autoshutdownsequence"></a>

### Overview

The `autoShutdownSequence` method executes an automatic shutdown sequence for the observatory's camera, ensuring that it is properly shut down. This sequence follows several critical steps:

### Steps

1. **Check Sensors**
   - Poll which sensors are connected and started up.
   - If all sensors are already shutdown, the sequence is marked as complete.
   - Logged Message using `self.announce`: "All sensors are shutdown! AUTO SHUTDOWN COMPLETE :banana-dance:."

2. **Set TEC Setpoints**
   - Set TEC setpoints to a warming value (e.g., 15°C) for sensors that need it.
   - Logged Message using `self.announce`: "Setting TEC setpoint to warming value [TEC Setpoint] C on addrs: [List of Addresses]."

3. **Manage TECs**
   - Identify sensors with running TECs and those with TECs turned off.
   - Shut down sensors whose TECs are off.
   - Logged Message using `self.announce`: "SHUTTING DOWN sensors which are running but whose TECs are off: [List of Addresses]."

4. **Check TECs' Readiness**
   - Check if TECs are steady and at setpoint.
   - Handle alerts if TECs take too long to reach the setpoint.
   - Logged Message using `self.announce`: "Sensor at addr [Address] is taking too long to temperature! After [Max Wait Time] minutes, [Message]."

5. **Completion**
   - If all checks pass, log a success message.
   - Set the 'autoShutdownComplete' flag.

### Logging

- Log relevant information about camera startup, shutdown, dome status, and observatory readiness to `~/data/winterCamera.log` on `freya`. 
- Use `self.announce` to send messages to the `#winter_observatory` slack channel

