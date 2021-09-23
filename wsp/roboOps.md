# WSP Robotic Operations

Notes on how the WSP robotic mode (the `-r` option which can be called when launching WSP) works, and some tips on how to run things and debug the inevitable issues.

## Hows does the robitic mode work?
There are four main pieces of code which define the robotic operations of WSP:
### 1. The "Robotic Operator": [`roboOperator.py'](https://magellomar-gitlab.mit.edu/WINTER/code/-/blob/sunsim/wsp/control/roboOperator.py). 
This script contains a class called `RoboOperator` which defines all (well, there are a few exceptions) of the main methods which define complex observing operations and sequences. Some major examples used nightly:

- `do_observation`: a generic observing method that handles observation of a variety of target types ("targtypes") including alt/az, ra/dec or catalog object. It handles slewing/enabling tracking of the dome, telescope, rotator, triggering the CCD exposure, etc. 
- `do_calibration`: a method which executes the full sequence of calibration operations which ideally is execute at the start and end of the night. It points to 75 deg elevation, and opposite the sun (ie either due east or west depending if it is sunrise or sunset) takes 5 flats using an empirical model to set the exposure time (currently only in r-band), 5 darks, and then 5 biases. 
- `do_currentObs`: this method gets handles executing the observation of the current line in the schedule file. It uses the `do_observation` method. After completing the observation it triggers the following: 
- `log_observation_and_gotoNext`: this adds the finished observation to the ongoing observation log of ALL observations. The log is also a SQLite database at ~/data/WINTER_ObsLog.db. After logging the completed observation, it gets the next one from the schedule file. NOTE: it gets the next one in the database sequentially, NOT the next one by time. So if it's observing an old schedule, or a schedule at the wrong time of night the targets may not be at favorable locations. If there is an error during the observation, or if there is a change in observatory status that makes it not okay to observe, the image may still get saved, but it will *not* get logged before going to the next in the queue.
- `handle_wrap_warning`: if at any time the rotator goes outside of it's allowed range, a PyQt signal will be emitted which triggers this method to be called. It errors out of the current observation (triggering the gotoNext function above) and resets the rotator to its safe posistion (mechanical angle = -25 deg) and stops it from tracking.
- `restart_robo`: this method triggers an event-driven loop of sorts, which checks if its okay to observe (using the `okay_to_observe` method), inititiates a few startup commands, and then begins stepping through the schedule.

There are other complex sequences in the robotic operator which are not used regularly, but still are helpful for debugging, or are critical but used only infrequently, including:
- `remakePointingModel`: a method which starts up a sequence which will observe a number of alt/az targets, platesolve them, and update their (alt/az) --> (ra/dec) mapping to the Planewave PWI4 interface to add to the pointing model.

### 2. The wintercmd interface: [`wintercmd.py`](https://magellomar-gitlab.mit.edu/WINTER/code/-/blob/sunsim/wsp/command/wintercmd.py)

The robotic operator class is instantiated in `systemControl.py`, but lives in its own thread. The roboOperator methods are not called directly elsewhere in the code, but can be executed through the `wintercmd` tcp/ip command server interface using the function calls defined in `wintercmd.py`. Particularly useful robotic operating functions include:
- `robo_observe`: wraps the `roboOperator.do_observation` function. Example calls:
    - `robo_observe altaz 70 270 -f`: do an observation of alt/az = 70/270 and tag as a focus exposure (-f)
    - `robo_observe object "M31"`: do an observation of M31. By default it calls the -t method for "TEST"
    - `robo_observe radec '05:34:30.52', '22:00:59.9' -s`: do an observation of the ra/dec specified in HH:MM:SS DD:MM:SS . The ra can also be specified in decimal hours, and the dec in decimal degrees. The -s option tags the image OBSTYPE as "SCIENCE." 

- `load_target_schedule`: similar to the `load_nightly_schedule` method, but can load any SQLite database that is in the ~/data/schedules directory. 
- `load_nightly_schedule`: loads the nightly schedule file SQLite database which using the pointer symbolic link in ~/data/nightly_schedule.lnk
- `robo_do_calibration`: execute the `do_calibration` method from above.
- `robo_run`: execute the `restart_robo` function from above and begin the observing schedule.
- `robo_run_test`: does the same thing as `robo_run` but instead of observing the ra/dec from the schedule, it observes the alt/az that the target *should* be at as scheduled, based on the MJD of the observation listed in the schedule file.
- `robo_stop`: stops the schedule execution. Basically it just sets a roboOperator.running flag to False. When the roboOperator gets to the `log_observation_and_gotoNext` method, it just doesn't go to the next one, and then just sits there doing nothing unless `robo_run` is executed again.

### 2. The "Robotic Manager": [`roboManager.py`](https://magellomar-gitlab.mit.edu/WINTER/code/-/blob/sunsim/wsp/control/roboManagerd.py)
