# roboOperator.py

## Purpose
The roboOperator.py module contains the classes that WSP uses to automate and script important robotic sequences. The most important sequences it defines are the observing sequences. This document is a work in progress, but attempts to outline the operation of the primary observing functions in WSP.

## Important Operating Modes/Procedures

### Execute a single observation
The roboOperator class has a general observing method which can be called to execute an observation of a specified target. The observation procedure for all targets is:
1. slew the dome to the target azimuth
2. slew the telescope mount to the target
3. turn on mount tracking to follow the target
4. send the rotator to it's field angle which corresponds to being aligned with the equatorial plane (according to Viraj it is `rotator_field_angle` = 155 deg )
5. initiate an exposure
6. run the plotting script which posts the image to the slack (note at the moment I think the image doesn't generate if nobody is logged in... a strange wrinkle...)

There are several commands accessible to the telescope operator defined in `wintercmd` which run these observations:
- `robo_observe_altaz <target_alt_degs> <target_az_degs>`
- `robo_observe_radec <target_ra_hours> <target_dec_degs>
- `robo_observe_object <object_name_string>`

### Run in automated schedule-driven mode
In automated schedule-driven mode, a "schedule file" database must be loaded into the roboOperator. This schedule file must be a SQLite database with the proper format.

#### Generate at schedule file
To generate a schedule file with the optimized targets for the night, run the Daily Winter Schedule script. To do this, go into the main WSP directory and run: `./rerun_daily_scheduler`. This will start up the schedule creator. It may say it's done after a few seconds but it takes ~20 minutes to run and will print out lots of strange things while it's running.

The output of the scheduler is a file in ~/data/schedules with a name like `nightly_20210803.db` where the numbers correspond to the night it's optimizing for.

### Load a schedule file


