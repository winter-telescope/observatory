# First test of DB Integration

### Documenting progress/thoughts while integrating WSP control code with SQlite dbs for observation scheduling and logging

## Pre-integration code overview

`wsp.py` is the top level program tasked with facilitating the operation of WINTER. It uses an infinite loop to stay running indefinitely. After selecting a mode, it initialize a `systemControl.control` object which handles the actual work of controlling the telescope.

Within `systemControl.py`, when in robotic mode, the initialization function starts another infinite loop, inside of which lies the code operating the telescope. One of its first lines creates a Schedule object, storing it in `self.schedule`. The infinite loop then repeatedly tries to make an observation according to the `self.schedule.currentObs` attribute. It then uses the schedule object's `logCurrentObs()` method to log the observation that was just taken. Finally, it calls `gotoNextObs` to move to the next observation in the schedule.

In the new version, there is a separate ObsWriter class which handles the logging of observations, leaving the schedule object to handle only the actual schedule.

We need to replace the functionality of the Schedule Class, so we will first examine what it does.

### Schedule Class

Describing the functionality of the `schedule.py` file as it stands before the changes.

`__init__`:

In the init method, the schedule class connects to the database and loads the schedule from a file. It then loads the log and finds the current observation by referencing the log.

`loadSchedule`:

This method supports the init method, reading and storing a csv style schedule into `self.schedule`.

`loadObslog`:

This method supports init, and tries to load the observation log, also a csv in this implementation. It then finds out what the id of the last logged observation was and compares it to the current Observation somehow. We are planning to change this functionality so I am not covering it in detail. If no obsLog is found a new one is made.

`makeObslog`:

This method supports `loadObslog`, and creates a new csv log for the observations to be stored in.

`logCurrentObs`:

This method is supposed to log the current observation by appending to the csv file.

`getCurrentObs`:

This method stores the information required for the current observation that the telescope is supposed to be making into instance variables. It does not return anything. The instance variable can be found at `self.currentObs`

`gotoNextObs`:

This method moves to the next line, stopping at the end of the schedule, and then calls `self.getCurrentObs` to store its value.

#### We replace this implementation with the following two classes

### Schedule

This class implements `init`, `loadSchedule`, `getCurrentObs`, and `gotoNextObs`, though admittedly with different specifications(i.e. getCurrentObs now returns the observation, rather than storing the info in an instance variable)

It does not implement the other 3 functions, since they are handled by a different class.

The differences in the new implementation are summarized here.

`__init__`:

In this implementation, we only connect to the database in the init method, and do not call loadSchedule. This was done to allow for additional input into the process of loading the Schedule after initialization of the schedule and the separate Observation logger. Also, this implementation reads a sqlite db instead of a csv file.

`loadSchedule`:

This method executes a query on the database according to preferences set in the method parameters. It can get all rows after and including an arbitrary row, currently ordered by the obsHistID field in the schedule. It then uses the sqlalchemy `fetchone` method to store the first row in the `self.currentObs` variable. We take advantage of sqlalchemy's generator-like behavior and allow it to handle the storage of the schedule while we simply ask it for the next line whenever we feel the need.

`getCurrentObs`:

This method now simply returns `self.currentObs`, which is a sqlalchemy RowProxy object which acts largely like a python dictionary, and can easily be converted into one.

`gotoNextObs`:

This method uses fetchone to move to the next line in the query result from `loadSchedule`, storing it in `self.currentObs`. It also watches for when fetchone returns `None`, which indicates that we've reached the end of the schedule and that we should close the connections to the database.

### ObsWriter

This class implements `init`, `create_obs_log`, and `log_observation`, to replace the remaining functionality of the old schedule class.

We no longer use the log to decide where to start in the schedule, since the schedule is based on time of night, not on the last observation.

`init`:

The init method sets up a db connection under a name provided(maybe will change this to a hardcoded name if we don't intend to change the name of the database very often), and then calls create_obs_log to create the tables.

`create_obs_log`:

This method uses the connection created in init to access the database and create the necessary tables to setup the database. If we don't need a new database, then perhaps we don't need to call this function, or we can implement it in such a way that it detects whether its functionality is necessary.

`log_observation`:

takes in row data in the form of a dictionary type object and a filepath to the fits image. Uses pandas DataFrame generated from that dictionary and a to_sql function in pandas to insert the row into the database.

#### To implement as of July 6:

Change the database structure to be cumulative across multiple days, and to utilize the relational structure of SQL.

Should change the way that `self.currentObs` is stored, so that it is a dictionary. Also change the log function to require a dictionary, rather than rowProxy input. 
