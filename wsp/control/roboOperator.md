# roboOperator.py

## Purpose
The roboOperator.py module contains the classes that WSP uses to automate and script important robotic sequences. The most important sequences it defines are the observing sequences. This document is a work in progress, but attempts to outline the operation of the primary observing functions in WSP.

# Important Operating Modes/Procedures

## Execute a single observation
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

## Run in automated schedule-driven mode
In automated schedule-driven mode, a "schedule file" database must be loaded into the roboOperator. This schedule file must be a SQLite database with the proper format.

### Generate at schedule file
To generate a schedule file with the optimized targets for the night, run the Daily Winter Schedule script. To do this, go into the main WSP directory and run: `./rerun_daily_scheduler`. This will start up the schedule creator. It may say it's done after a few seconds but it takes ~20 minutes to run and will print out lots of strange things while it's running.

The output of the scheduler is a file in ~/data/schedules with a name like `nightly_20210803.db` where the numbers correspond to the night it's optimizing for.

### Load a schedule file
The schedule file must be in the ~/data/schedules directory. To load it, call the `load_target_schedule <filename>` function from wintercmd. Once the schedule is loaded it will be parsed by roboOperator. If it works, it prints something to the log along the lines of "wrote functions", if it doesn't it will segfault and crash WSP. Sorry... 

Ex: `load_target_schedule nightly_20210803.db`

### Run the schedule file
To run the schedule execute the wintercmd `robo_run` from the command line or GUI. This sends a signal to the roboOperator which turns the flag roboOperator.is_running to True, and runs the method `roboOperator.restart_robo()`. This will run through a short startup and calibration sequence. If things are already set up then this won't do much, but it will still go through it. The startup homes the mount, takes control of the dome, opens it if the weather and sun are okay, and sends the dome to its home position. These sequences will be written to the slack channel as they run.

Once the initial sequences are complete the roboOperator will start stepping through each target in the schedule and observe it. Some notes:
- it doesn't change the filter
- the exposure time is pulled from the schedule file, and if it doesn't match the current exposure time it will change the exposure time of the camera before doing the exposure
- each target is observed by going to it's RA and DEC as specified in the file.

### Run the schedule file in daytime
You can run a schedule file in daytime when all the targets are below the horizon and the dome cannot be opened. In this simulation mode, you must use the simulated dome, and send the mount to the Alt/Az of the targets (as they would be at their requested observation time) rather than their RA/Dec. To do this:
1. run wsp with the domesim option: `./wsp.py -m --smallchiller --domesim`
2. run the schedule execution in altaz mode using `robo_run_test` instead of `robo_run`

## Pointing Model Creation
The pointing model is kept by the Planewave software on Thor, the telescope windows PC. It tells the telescope mount how to convert Alt/Az to RA/DEC at any given time.

### Create a new pointing model 
To create a new pointing model, run the wintercmd: `robo_remakePointingModel`. This will follow this sequence delete the current pointing model on the telescope, then step through a pre-determined set of Alt/Az points (defined in ~/data/25_point_denser_near_zenith_spaced_pointing_model_points.txt) and at each point:
1. do an observation (the same internal method as `robo_observe_altaz`) of the target Alt/Az
2. run a platesolve program to determine the RA/DEC from the stars
3. send a message to the telescope that it is currently pointed at the computed RA/DEC and that it should add this to it's pointing model

NOTE: the exposure time is not set in this method. I had good luck using 10 seconds. We don't need deep images, just deep enough to get a few bright stars but not long enough that we drift from the initial alt/az by much (since we have to track the whole time so the stars aren't streaky.)

### Delete the current pointing model
To delete the current pointing model, we just have to tell the telescope to clear all the currently saved points. To do this just run the wintercmd: `mount_model_clear_points` which will return to the default nominal pointing model.

### Look at the pointing model and evaluate it
The alt/az/ra/dec points are all saved to a tab-separated file in ~/data/current_pointing_model_points.txt which you can open to see how it did. The results also print out to the slack channel along with the nominal RA/DEC so you can see how well the platesolve routine did.

There are also diagnostic tools you can access in the PWI4 Planewave software GUI running on Thor. From the main Mount tab in the box on the left, click Commands > View Pointing Model. This shows a cross-hair with all the current points plotted in yellow. They should nicely sample the full alt/az space. You can also view the error of each point by clicking on the "errors" button under Graph Type. They should all be tightly distributed around the center, if there are any way out in space the model will be BAD. Other nice features within this menu are:
- Error Graph: plots various errors of each data point. You can change the axes to makes plots of, for example, Error in RA vs Azimuth
- Cal Points: shows all the data being used for model generation. You can disable some points if they look bad, or wipe them all out if things are messy (the same thing as `mount_model_clear_points`). Ideally no one point should make a big difference to the model assuming they're all good data.

