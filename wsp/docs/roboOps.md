# WSP Robotic Operations

Notes on how the WSP robotic mode (the `-r` option which can be called when launching WSP) works, and some tips on how to run things and debug the inevitable issues.

**Note:** all robotic operations stuff is in the `sunsim` branch of `WSP` and has not yet been merged into `main`.

## Hows does the robitic mode work?
There are four main pieces of code which define the robotic operations of WSP:
### 1. The "Robotic Operator": [`roboOperator.py'](https://magellomar-gitlab.mit.edu/WINTER/code/-/blob/sunsim/wsp/control/roboOperator.py). 
This script contains a class called `RoboOperator` which defines all (well, there are a few exceptions) of the main methods which define complex observing operations and sequences. The observing sequence (eg, the "robot") is defined in roboOperator.py. This file defines a `RoboOperator` class (which is instantiated in its own dedicated thread in `systemControl.py` as `self.roboThread.robo`. All observatory sequences are executed in this thread by this class. That is, while individual subsystems can be commanded directly through the `wintercmd` interface, (eg, sending a `dome_goto <az>` command), but sequenced commands (eg `robo_observe object M31`) are handled by the roboOperator which manages the sequencing and commanding of the various subsystems.

Some major examples used nightly:

- `do_observation`: a generic observing method that handles observation of a variety of target types ("targtypes") including alt/az, ra/dec or catalog object. It handles slewing/enabling tracking of the dome, telescope, rotator, triggering the CCD exposure, etc. 
- `do_calibration`: a method which executes the full sequence of calibration operations which ideally is execute at the start and end of the night. It points to 75 deg elevation, and opposite the sun (ie either due east or west depending if it is sunrise or sunset) takes 5 flats using an empirical model to set the exposure time (currently only in r-band), 5 darks, and then 5 biases. 
- `do_currentObs`: this method gets handles executing the observation of the current line in the schedule file. It uses the `do_observation` method. After completing the observation it triggers the following: 
- `handle_wrap_warning`: if at any time the rotator goes outside of it's allowed range, a PyQt signal will be emitted which triggers this method to be called. It errors out of the current observation (triggering the gotoNext function above) and resets the rotator to its safe posistion (mechanical angle = -25 deg) and stops it from tracking.
- `restart_robo`: this method triggers an event-driven loop of sorts, which checks if its okay to observe (using the `okay_to_observe` method), inititiates a few startup commands, and then begins stepping through the schedule. This observing sequence is described in further detail in the observatory operations sequences file.

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
This describes a trigger with the `trigname` "kill". The goal is that at the end of the night the roboManager will automatically kill WSP, and then the watchdog will restart it. This occurs at 8am because WSP considers a "night" to be between 8am - 7:59 am the next day using Palomar local time (defined in `utils.tonight_local()`. From the above config, there are 2 conditions that must be met: (1) the trigger cannot be sent before the time is 08:01, (2) the Sun must be below 40 degrees. The `repeat_on_restart` key indicates whether or not this command should be sent again if WSP is restarted. By default each command is sent ONLY once per night (based on the triglog file). **NOTE: THIS FUNCTIONALITY DOESN'T WORK, HAS SOME BUGS. DON'T COUNT ON SOMETHING BEING SENT AGAIN ON RESTART AT THE MOMENT**. The `sundir` = 1 means that the command can only be sent when the sun is rising. Note that there is a bit of redundancy in these definitions, hopefully the extra functionality makes it easier to define a set of working conditions.

#### Current robotic operations sequence (clipped from config.yaml):

Roughly speaking, the order of operations is this:
0. start up `WSP` in robotic mode in the morning after 8am Palomar time
1. send some dummy command in the morning to make sure the connection to `WSP` is established
2. turn on the fans in the telescope to equilibrate the temperatures in the afternoon
3. start up all the hardware systems once the Sun gets low on the horizon
4. load up the nightly schedule when the Sun sets (deadline for nightly schedule changes)
5. start up the auto calibration routines (flats/darks/biases) when the Sun is low enough to open the dome
6. focus the telescope
7. run through the nightly schedule 
8. stop the schedule when the sun is close to rising
9. rerun the autocalibration routines when the sky is getting bright
10. shut everything down for the night and turn off the hardware
11. kill WSP so that the next day has a fresh start and a clean set of logfiles

Here is how that is implemented:
``` yaml
########### ROBO MANAGER ###########
# read this as: send the CMD when the current value of sun_alt or time is COND than the specified value.
# eg, if type is sun and cond is >= : then send the cmd when sun_alt >= VAL
robotic_manager_triggers:
    timeformat: '%H:%M:%S.%f'
    triggers:
        daytest:
            conds:
                cond1:
                    type: 'sun'
                    val: 0
                    cond: '>'
            sundir: 0
            repeat_on_restart: True
            cmd: xyzzy
                
        fans_on:
            conds:
                cond1:
                    type: 'time'
                    val: '14:00:0.0'
                    cond: '>'
            sundir: -1
            repeat_on_restart: False
            cmd: 'mount_fans_on'
        startup:
            conds:
                cond1:
                    type: 'sun'
                    val: 5.0
                    cond: '<'
            sundir: 0
            repeat_on_restart: False
            cmd: 'total_startup'
        load_schedule:
            conds:
                cond1:
                    type: 'sun'
                    val: 0.0
                    cond: '<'
            sundir: 0
            repeat_on_restart: True
            cmd: 'load_nightly_schedule'
        evening_flats:
            conds:
                cond1:
                    type: 'sun'
                    val: -5.0
                    cond: '<'
                cond2:
                    type: 'sun'
                    val: -7.0
                    cond: '>'
            repeat_on_restart: True
            sundir: -1
            cmd: 'robo_do_calibration'
        test_image:
            conds:
                cond1:
                    type: 'sun'
                    val: -11.0
                    cond: '<'
            repeat_on_restart: True
            sundir: -1
            cmd: 'robo_observe altaz 75 270'
        focus:
            conds:
                cond1:
                    type: 'sun'
                    val: -12.0
                    cond: '<'
            sundir: 0
            repeat_on_restart: True
            cmd: 'doFocusLoop --roborun'
        #start_obs:
        #    type: 'sun'
        #    val: -14.0
        #    cond: '<'
        #    sundir: 0
        #    cmd: 'robo_run'
        stop_obs:
            conds:
                cond1:
                    type: 'sun'
                    val:  -12.0
                    cond: '>'
                cond2:
                    type: 'time'
                    val: '8:0:0.0'
                    cond: '<'
            sundir: 1
            repeat_on_restart: False
            cmd: 'robo_stop'
        morning_flats:
            conds:
                cond1:
                    type: 'sun'
                    val: -7.0
                    cond: '>'
                cond2:
                    type: 'sun'
                    val: -5.0
                    cond: '<'     
            repeat_on_restart: True           
            sundir: 1
            cmd: 'robo_do_calibration'
        shutdown:
            conds:
                cond1:
                    type: 'sun'
                    val: -4
                    cond: '>'
            repeat_on_restart: False
            sundir: 1
            cmd: 'total_shutdown'
        fans_off:
            conds:
                cond1:
                    type: 'sun'
                    val: 0
                    cond: '>'
            repeat_on_restart: False
            sundir: 1
            cmd: 'mount_fans_off'
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

**NOTE:** I don't promise that trigger conditions in their current form are the most optimal. They may need tweaks so that they don't trigger out of turn, at a weird time of day, or bump into each other so that one is sent before the previous one is finished. This is why there is some padding built in between the Sun altitude between the end of calibration and the start of science observations.


# So you want to run WSP in robotic mode:

## How things should ideally work:
Start up the `WSP Watchdog`: from within WSP_DIRECTORY/wsp execute: `./watchdog_start.py`. This will start up the watchdog process which looks at the housekeeping database (at ~/data/dm.lnk) and restarts `WSP` in robotic mode (`./wsp.py -r --smallchiller`) any time it detects that it has been > 60 s since any housekeeping data was written. The observatory should run though its sequences, then shut itself off in the morning and be ready to go the next day.

*Pro tip:* it is best to start things up before the Sun goes down in Palomar. Things work best when the sequence gets to happen at its specified pace. If you start things in robotic mode during or after the startup and calibration sequences are meant to run, sometimes the commands all pile up and get sent at once, which usually results in a bunch of nonsense getting logged, commands starting but then getting abandoned by `WSP`, some angry seeming timeouts, and inevitably the dome getting sent on a series of wild goose chases. It's not the end of the world but it will require manually sending some of these commands to get the observatory in the proper state. 

## What to do when things don't work as desired:
### Things are kinda working but just bad
Usually this kind of this kind of thing happens during startup if it's going to happen. Often you can get things unstuck by killing WSP (literally just sending `kill` and letting it get rebooted by the watchdog), and resending some specific commands. You can either resend the commands by hand (ie with one of the `wintercmd` clients), or by opening up the current night's triglog file (~/data/triglog_tonight.lnk) and changing some of the trigger `sent` values from `True` to `False`, which will prompt `WSP` to send them again when it is restarted if their send conditions are still satisfied.

Some specific examples:
- The calibration images are nonsense. Flats that are dark, darks that are light, biases that are gradients, etc.
    - Usually this means that the camera is unhappy. Presumably some commands are not being parsed properly and some but not all the commands are making it through to the camera (ie, exposure time is not being set properly but the images are still executing). This can usually be fixed by restarting `WSP` a few times to reset the `huaso_server`. If that doesn't work, kill the watchdog (`./watchdog_stop.py`), make sure `WSP` is really dead (`./wsp_kill.py`). Then start up `WSP` in manual mode. This lets you debug at your own pace, try to send a few camera commands like to change the exposure time (`ccd_set_exposure`), and then try to take some different types of images. You could try to take a bias: `robo_do_exposure -b`, take a flat: `robo_do_exposure -f`, or do a test observation: `robo_observe altaz 75 270 -t`. If things seem happy and working then kill WSP and restart the watchdog. 
- The dome times out a bunch and never seems to know where it's going.
    - This usually is indicative of a homing problem. Follow steps from above to restart in manual mode. If there is a homing problem the following two actions usually fix things: (1) send `dome_stop` command. This will clear/reset the dome's command queue to clear out any commands it's trying to do/is stuck on, (2) send `dome_home` to initiate the dome's homing routine. This takes a few minutes during which the dome will decide (at random) to spin CW or CCW until it crosses it's home sensor, then it will stop and slowly drive to 180 degrees. Now you should be good to try and rerun things.
- The images are streaked.
    - I don't understand why this happens periodically, but sometimes on startup the mount doesn't track properly. It's probably an issue with the sequence of startup commands to enable the mount tracking, but I'm not sure. We'll fix this by following an analogous plan as the dome. Restart in manual mode and then send `mount_stop`. You may also want to reload the pointing model to make sure it's the proper one: `mount_model_load pointing_model_20210810_218pts_180enabled_4p8rms.pxp`(loads files from Thor: ~\Documents\PlaneWave Instruments\PWI4\Mount). Now in manual mode try a few manual pointing commands (`mount_goto altaz 45 145`) and some observations, eg: `robo_observe object M31` (or some other object that is up in the sky).
    - **NOTE:** you can log in to Thor (telescope PC) even if you can't get VNC or TeamViewer working on Odin. Just tunnel to Heimdall: ssh -Y winter@18.25.65.176, then tunnel to Odin: ssh -Y winter@198.202.125.142 -p 51234. Now open a remote desktop connection to Thor by running: `remmina` which will open the remmina RDP client and allow you to open a connection to Thor.
- Nothing works and everything sucks
    - Bummer. Tonight there be gremlins. Just shut everything down (`total_shutdown`), kill the watchdog, and start `WSP` in manual mode so that it will still report if there are any problems like the chiller has an issue or the like. Then I like to do one or more of the following actions: get a beer, watch some stupid TV, go to bed. 


### So WSP died :(
Yeah this happens. Usually the outcome is that the watchdog will restart `WSP`, but the camera will be in a nasty state because it didn't properly shut down the client connection. Sometimes you can jump start the situation by just sending a `kill` command and letting the watchdog reboot (maybe doing this a few times). If you want to have the roboManager send some commands it barfed on, then follow the steps at the top of the section to reset some of the items in the nightly triglog file so the commands will resend on next restart, or delete the triglog file alltogether if you want a clean slate to start from the top. You can also manually set things to where they should be (ie, load the nightly schedule and then send `robo_run`) to start the schedule execution. It should then keep chugging in robotic mode until the morning when it will send the shutdown sequences.

### Some other quirks/issues to debug:
1. Telescope throws an error and crashes WSP when you restart: this is beacuse I added some code to the `__init__` method of WSP_DIRECTORY/telescope/telescope.py which on `WSP` startup safely stows the rotator. The idea is that if `WSP` crashes and restarts, the rotator won't get left in some tracking state to drift off to oblivion. Initially it would send the commands to the rotrator but didn't attempt to reconnect so if it wasn't already connected to the mount then it would crash. I've tried to fix this but haven't tested extensively. To fix, log into Thor and press the connect button on the PWI4 GUI.
2. The morning routines aren't happening. I'm not sure why, but it's been a while since I've gotten them to run. I think it must be some changes I've made, since it worked before I added the ability to make multiple conditions for each trigger. My guess is that there's an issue with the time of day, where it's ignoring triggers from after midnight. It worked before I made these changes, and doesn't work now. Probably something dumb but needs debugging. What is happening these days is that it just keeps observing until the dome closes and then it `roboOperator.ok_to_observe()` returns False and it stops.
3. Handling what roboManager should do if `WSP` is restarted: I started poking at this, hence the `resend_on_restart` keyword. You can see there's some logic that is bad in the RoboManager class which tracks a `self.first_time` flag and is trying to parse it in `self.checkWhatToDo`. It's actually surprisingly complicated to decide what to do if it's been rebooted. THis also is related to how it should handle a situation where say, there is a P200 manual override which clears at 3am. Right now it doesn't do the right thing without manual intervention. Something to think about. Probably the answer is to just get over wanting these cases to be handled super generically and just manually write a sequence.
4. Handling the schedule more sophisticatedly: right now as noted we just go line by line by line. Ideally we'd like a (default) option where it will get the next closest observation by *time*. This might need some cushion built in, as in "just go to the next one as long as it's within 30 minutes of it's scheduled time, otherwise jump to the closest in time". This approach would loosen the requirement that the schedule be a super accurate model of the telescope overheads. If there is a major difference in overheads, just always observing by time will mean that many observations will be skipped. We need to maintain the ability to just go line by line however, because this is how the target observations will be executed. For more info on how the schedule querying works, read [Allan's notes](https://magellomar-gitlab.mit.edu/WINTER/code/blob/master/wsp/dataLogTest.md) and [Nate's notes on Allan's notes](https://magellomar-gitlab.mit.edu/WINTER/code/-/blob/sunsim/wsp/schedule_ops_notes_npl.md).
    Side note: at some point I wrote an option that could be passed to `load_target_schedule` that would let you start observing at a specific line (a `-n` argument), but that seems to be in a branch I've lost track of and it's not currently implemented in the `sunsim` branch.
