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

The robotic operator class is instantiated in `systemControl.py`, but lives in its own thread. The roboOperator methods are not called directly elsewhere in the code, but can be executed through the `wintercmd` tcp/ip command server interface using the function calls defined in `wintercmd.py`. These commands can be executed by typing into the WSP terminal, using the GUI that Josh wrote, launching the [`commandClient.py`](https://magellomar-gitlab.mit.edu/WINTER/code/-/blob/master/wsp/command/commandClient.py) program, or using any other process connected to localhost:7000 to pass text command strings. Particularly useful robotic operating functions include:

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

### 3. The "Robotic Manager": [`roboManagerd.py`](https://magellomar-gitlab.mit.edu/WINTER/code/-/blob/sunsim/wsp/control/roboManagerd.py)
The actual triggering of any of the above routines in robotic mode is handled by the Robotic Manager Daemon, a standalone process which is launched by WSP in `-r` mode. It executes a set routine of commands each with its own set of trigger criteria. The commands are dispatch the same way they would be if you were to execute them by hand: using the `wintercmd` TCP/IP interface. The daemon can *also be launched on its own in standalone mode* if WSP is already running in manual (`-m`) mode. This is useful if WSP is already running, and you decide you'd like to startup robotic operations. In this case you would execute the program direction by navigating to the WSP_DIRECTORY/control and running `./roboManagerd.py`. 

The daemon has three main classes which follow the general approach of all the other WSP [daemons](https://magellomar-gitlab.mit.edu/WINTER/code/-/blob/master/wsp/daemon/readme.md) (okay I know that documentation is pretty sad but getting there slowly ;) ):
- `RoboManager`: this is the main class. It regularly (at the moment every 5 s, set by a QTimer) checks what it should be doing (`roboManager.checkWhatToDo`). When it detects that the trigger criteria for any of it's predifined trigger events have been met, it sends a signal to WSP to execute the command. The trigger checking and handling happens in the main thread. There are two additional threads (QThreads), a `StatusThread` where the `StatusMonitor` object lives, and a `CommandThread` where the `CommandHandler` object lives (see below). This keeps the communications with WSP and the Pyro server, etc out of the mian thread.
- `StatusMonitor`: this class handles the roboManager's connection to the WSP housekeeping and passes current housekeeping data to the `roboManager.state` dictionary. It's primary method is `pollStatus`. The roboManager really only cares about three status fields: the sun's altitude (stored in `roboManager.state['sun_alt']`), the timestamp associated with the sun (stored in `roboManager.state['timestamp']`), and a flag to indicate whether the sun is rising or not (`roboManager.state['sun_rising']`). By default these values are grabbed from the Pyro5 server, by making a proxy of the housekeeping state object which is published to the Pyro5 server by a dedicated QThread in [`systemControl.py`](https://magellomar-gitlab.mit.edu/WINTER/code/-/blob/master/wsp/control/systemControl.py). It is also possible to run the roboManager in a sun-simulation mode by passing the `--sunsim` option to WSP (or to the daemon directly if it is executed as a standlone). When this option is passed, the daemon will launch a PyQt5 GUI which allows the user to control the position of the sun. The position is driven by the local observatory time at Palomar, which can be reset, changed, started, sped up/slowed down, and paused. In sun-simulation mode this simulated sun position/time is passed to the roboManager and used for evaluating the trigger criteria. WSP does *not* use the sun simulator, so WSP will report the **actual** time, not the simulation time, so there will be some disagreement between what WSP/KST says the sun is doing and what the roboManager thinks the sun is doing. In both normal and sunsim modes, the StatusMonitor gets the Sun information using the Pyro5 server.
- `CommandHandler`: this class handles the roboManager's communiations with the WSP `wintercmd` command server. It opens up a TCP/IP socket connection to the command server at `localhost:7000`. It's primary method is `sendCommand`. ~WARNING~ this is still a little buggy in terms of establishing the connection and handling disconnections. The main thing that is a non-ideal is that WSP launches all the subsystem daemons first, right at the top of the `systemControl.py` init. It takes some time before the `wintercmd` server is set up and ready for connection. At the moment I've added a simple 30 s sleep to the roboManagerd mainbody before the main application is instantiated. Ideally this means that the command server is ready for connection by the time the roboManager stats up. The CommandHandler object has a ReconnectHandler object which prevents infinite loops of reconnection attempts so all the bones of the necessary stuff is there but sometimes the startup is a bit buggy. Importantly, the CommandHandler emits a PyQtSignal `self.updateTrigLog` whenever a command is **successfully** sent to WSP. This signal is connected to the `roboManager.HandleUpdateTrigLog` method which stores the information about when (it time and sun position) the triggered command was sent, and saves the information to the nightly `triglog` which is located at ~/data/triglogs/triglog_YYYYMMDD.json and linked at ~/data/triglog_tonight.lnk. 
### 4. Robotic Trigger Config (part of [`config.yaml`](https://magellomar-gitlab.mit.edu/WINTER/code/-/blob/sunsim/wsp/config/config.yaml)):
All of the robotic operations are defined in the `config.yaml` main WSP config file, under the section heading  `robotic_manager_triggers`. Under the `triggers` subheading each entry is read into the roboManager to define a `roboManagerd.RoboTrigger` object, which has a command (`cmd`) which must be a text command from `wintercmd`, a name (`trigname`) which is used to keep track of the trigger within roboManager, and a series of conditions which must be met saved as a list (`triglist`). These conditions are defined in the config file under the `conds` keyword for each trigger entry. Each trigger can have an arbitrary number of conditions. These conditions are read in by roboManager and each one is used to define a `roboManagerd.RoboTriggerCond` object. All of this information is then used to create a dictionary member of the `RoboManager` class (`self.triggers`) which has key:value pairs of trigname:RoboTrigger objects. Each condition must be either a sun-type or time-type trigger, meaning the condition to be met is on the Sun's altitude, or the time of day. Each trigger also has a `sundir` keyword which describes when the command can be sent: 

| sundir | meaning |
| ------ | ------ |
| -1 | Sun must be setting |
| 0 | Doesn't matter if setting or rising |
| -1 | Sun must be rising |

An example trigger definition:

``` yaml
triggers:
    kill:
        conds:
            cond1:
                type: 'time'
                val: '8:01:0.0'
                cond: '>'
            cond2:
                type: 'sun'
                val: 40
                cond: '<'
        repeat_on_restart: False
        sundir: 1
        cmd: 'kill'
```
This describes a trigger with the `trigname` "kill". The goal is that at the end of the night the roboManager will automatically kill WSP, and then the watchdog will restart it. This occurs at 8am because WSP considers a "night" to be between 8am - 7:59 am the next day using Palomar local time (defined in `utils.tonight_local()`. From the above config, there are 2 conditions that must be met: (1) the trigger cannot be sent before the time is 08:01, (2) the Sun must be below 40 degrees. The `repeat_on_restart` key indicates whether or not this command should be sent again if WSP is restarted. By default each command is sent ONLY once per night (based on the triglog file). *NOTE: THIS FUNCTIONALITY DOESN'T WORK, HAS SOME BUGS*. The `sundir` = 1 means that the command can only be sent when the sun is rising. Note that there is a bit of redundancy in these definitions, hopefully the extra functionality makes it easier to define a set of working conditions.




