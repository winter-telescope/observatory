# Notes on schedule execution

### Taking notes on Allan's scheduler code, to get up to speed and document changes
Note that these are notes made by Nate based on Allan's code. Also used Allan's notes here as a reference: [dataLogTest.md](https://magellomar-gitlab.mit.edu/WINTER/code/blob/master/wsp/dataLogTest.md)

## Overview of scheduling architecture (as of 4-23-21)
On startup, `wsp` initializes a `systemControl.control` object. This object initializes all the subsystems. In the `__init__` of the `systemControl.control` object, three important classes are initialized which handle the scheduling: 
1. `self.schedule`, an instance of `schedule.Schedule`, which handles the connection and queries to the schedule file SQLite database
2. `self.writer`, an instance of `ObsWriter.ObsWriter`, which handles the setup and connection to the observation log SQLite database
3. `self.scheduleExec`, an instance of `cmdParser.schedule_executor`, which starts a new thread which has an infinite loop in its `run` method which asks `self.schedule` for the current observation, does the actual execution of the observation, and then commands `self.writer` to log the observation. 

These three objects are only initialized when `wsp` is started in `manual` or `robotic` mode. Once all other systems are initialized, the scheduler is started with `self.scheduleExec.start()`. These objects are defined and explained below:

## Schedule
The schedule object implements `init`, `loadSchedule`, `getCurrentObs`, `gotoNextObs`, and `closeConnection`. These functions handle loading and connecting to the nightly (or otherwise specified) scheule file, and manage all the communications with it. It does *not* know anything about what has or has not been observed. It simply queries the database. The details of these functions are described here.

`__init__`:
In the init method, the schedule class connects to the logger, and sets up several attributes which are used to hold schedule information, including: `self.scheduleFile_directory` which is loaded from `self.config['scheduleFile_directory']`, and `self.scheduleType` which is init'd to `None`. 

`loadSchedule`:


### Changelog:
* **4/26/21: updated logging** Now it handles logging like all the other modules rather than writing to its own `pseudoLog.log` log file. In this case logger is passed in during the class instance definition. If this is cumbersome it could also be changed so that it finds the logger on its own, similar to the daemons.

 

## Schedule Files
The schedule files are written outside of `wsp` by the WINTER scheduler code. 

There are several relevant items which must be included in the config file (`config.yaml`) which are used in the schedule handling:
* `scheduleFile_directory: 'schedule/scheduleFiles'`
* `scheduleFile_nightly_prefix: 'nightly_'`
* `scheduleFile_nightly_link_directory: 'data'`
* `scheduleFile_nightly_link_name: 'nightly_schedule.lnk'`

These must correspond to the naming convention used by the WINTER scheduler. The scheduler code runs daily and saves a new file in /data/schedules/nightly_YYYYMMDD.db, and creates a symbolic link to the most recent daily schedule at /data/nightly_schedule.lnk.
