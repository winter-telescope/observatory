# Notes on schedule execution

### Taking notes on Allan's scheduler code, to get up to speed and document changes

## Overview of scheduling architecture (as of 4-23-21)
On startup, `wsp` initializes a `systemControl.control` object. This object initializes all the subsystems. In the `__init__` of the `systemControl.control` object, three important classes are initialized which handle the scheduling: (1) `self.schedule`, an instance of `schedule.Schedule`, which handles the connection and queries to the schedule file SQLite database, (2) `self.writer`, an instance of `ObsWriter.ObsWriter`, which handles the setup and connection to the observation log SQLite database, and (3) `self.scheduleExec`, an instance of `cmdParser.schedule_executor`, which starts a new thread which has an infinite loop in its `run` method which asks `self.schedule` for the current observation, does the actual execution of the observation, and then commands `self.writer` to log the observation. These three objects are only initialized when `wsp` is started in `manual` or `robotic` mode. Once all other systems are initialized, the scheduler is started with `self.scheduleExec.start()`. 

## Schedule Executor Class
The `schedule_executor` class inherets from `PyQt5.QtCore.QThread`, and starts a dedicated thread which handles 