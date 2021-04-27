# Notes on schedule execution

### Taking notes on Allan's scheduler code, to get up to speed and document changes
Note that these are notes made by Nate based on Allan's code. Also used Allan's notes here as a reference: [dataLogTest.md](https://magellomar-gitlab.mit.edu/WINTER/code/blob/master/wsp/dataLogTest.md) My goal with this document is to go through all of Allan's code carefully to understand all of its parts, figure out what's happening where, and see what needs updating. In general the database code has been demonstrated and works great. The main improvements that need to be made are in the observing sequence, adding more fields to be logged, and making the process of getting the current observation a bit more sophisticated.

## Overview of scheduling architecture (April 2021)
On startup, `wsp` initializes a `systemControl.control` object. This object initializes all the subsystems. In the `__init__` of the `systemControl.control` object, three important classes are initialized which handle the scheduling: 
1. `self.schedule`, an instance of `schedule.Schedule`, which handles the connection and queries to the schedule file SQLite database
2. `self.writer`, an instance of `ObsWriter.ObsWriter`, which handles the setup and connection to the observation log SQLite database
3. `self.scheduleExec`, an instance of `cmdParser.schedule_executor`, which starts a new thread which has an infinite loop in its `run` method which asks `self.schedule` for the current observation, does the actual execution of the observation, and then commands `self.writer` to log the observation. 

These three objects are only initialized when `wsp` is started in `manual` or `robotic` mode. Once all other systems are initialized, the scheduler is started with `self.scheduleExec.start()`. These objects are defined and explained below:

## Schedule
The schedule object implements `init`, `loadSchedule`, `getCurrentObs`, `gotoNextObs`, and `closeConnection`. These functions handle loading and connecting to the nightly (or otherwise specified) scheule file, and manage all the communications with it. It does *not* know anything about what has or has not been observed. It simply queries the database. The details of these functions are described here.

### init:
In the init method, the schedule class connects to the logger, and sets up several attributes which are used to hold schedule information, including: `self.scheduleFile_directory` which is loaded from `self.config['scheduleFile_directory']`, and `self.scheduleType` which is init'd to `None`. 

### loadSchedule:
This method handles the connection to the database. It takes in a `schedulefile_name` argument which is used to load the schedule file itself. This schedule file name can take either a filename (of a file which must be in the `self.scheduleFile_directory`) or the keyword `nightly` which signals the function to load the nightly schedule (see Schedule section below). It also takes a `currentTime` argument which defaults to zero. At present, this "time" is a misnomer, and actually is handled as the obsHistID number. 

After determiniming the database file to load and storing it to the `self.schedulefile` attribute, it uses the `sqlalchemy` `create_engine` function to create a database engine which is then used to connect to the database. The database connection object is initialized using the engine's `connect` method and the `sqlalchemy.Connection` object is stored as `self.conn`. After creating the database connection, `loadSchedule` creates a `sqlalchemy.Table` object from the 'Summary' field in the schedule file. It then grabs the elements of this table (ie all of the observations from the file) which have an `obsHistID` >= `currentTime`. This table is stored in `self.result`. Once this list of observations to do is loaded, the first row of the table is grabbed (as a sqlalchmey RowProxy object) using `sqlalchemy.Table.fetchone()`, converted to a Python dictionary, and stored in `self.currentObs`.

### getCurrentObs
This method simply returns `self.currentObs` which is a Python dictionary of the current line from the schedulefile Summary table.

### gotoNextObs
This method moves to the next observation (ie next line in the Summary table in the schedule file) using the sqlalchemy `fetchone` method. When there are no more lines in the database (ie no more observations to complete), `fetchone` returns None and we know it's finished. This method does not return anything.

### closeConnection:
This method closes the table (`self.result.close()`) and the connection to the database (`self.conn.close`). This is called at the end of the schedule executor's `run` method after the observing loop, and is called only when the observing loop is broken out of, eg when the schedule is complete (and thus `self.schedule.currentObs == None`) or the schedule execution is stopped (which sets `schedule_executor.running` to False).

### Changelog:
* **4/26/21: updated logging** Now it handles logging like all the other modules rather than writing to its own `pseudoLog.log` log file. In this case logger is passed in during the class instance definition. If this is cumbersome it could also be changed so that it finds the logger on its own, similar to the daemons.

### To Do:
- [ ] Replace `currentTime` with `startingTime` and make it actually refer to a time, and add a `startingRow` argument which replaces the previous functionality. That is, when loading the Summary table, load all rows where `expMJD` is >= `startingTime` (if specified) and where obsHistID is >= `startingRow` (if specified).
- [ ] Add some more sophisticated logic to `gotoNextObs`. Ideally we want to step through observations line by line, but this should check to make sure that the timing hasn't gotten way out of whack. The way to do this is probably to make sure that expMJD from the current observation is within some time window (eg 30 minutes) of its scheduled time. If the observation is *not* within this grace period, it should re-run `loadSchedule` passing it the current time and the last observation ID. That will make sure it gets resynced so things get observed near their optimal time, and ensures that nothing gets re-observed during these resyncronizations. 
- [ ] Add some sort of observation evaluator which makes sure the observation is acceptable. This should calculate the current Az/Alt of the target based on the field RA/DEC using astropy. If the expected RA/DEC is outside of allowed limits, it should throw an error and skip the observation. Could add other conditions to check too.

## ObsWriter
This class handles the connection to the observation log which contains the record of all observations.
### init
This method sets up a database connection to the observation log database, with the name `log_name` by using sqlalchemy's `create_engine` function to create an engine for the file at 'sqlite:///' + f'/home/winter/data/{self.log_name}.db'. After creating the database engine, it initializes the database structure based on the config file in config/dataconfig.json. This dataconfig is read in using `json.load` and stored in the instance attribute `self.dbStructure`.

### generateDBCommands
This function supports `create_tables` by creating a dictionary of commands saved as `self.sqlCommands`. In this dictionary, each key is the name of one of the tables in the dataconfig.json file (eg 'Observation', 'Field', 'Night'). The value for each key in `self.sqlCommands` is a string which can be handled by `execute` method of the `sqlalchemy.Connection` object `self.conn` and creates the corresponding table in the SQLite database.

### setUpDatabase
This is called by `schedule_executor` at the beginning of the observing loop. It creates a sqlalchemy Connection object which is stored in `self.conn`, the same approach used when loading the schedule database. After init'ing the connection, it calls `self.create_tables()`.

### create_tables
This method supports `setUpDatabase`. This method uses the connection created in init to access the database and create the necessary tables to setup the database. This function calls `self.generateDBCommands`. Then for each table (ie each key in `self.sqlCommands`) it looks to see if the table **already** exists in the database (by checking if `self.engine.dialect.has_table(self.engine, table)`). If the table does not exist, then the corresponding command from `self.sqlCommands` is executed to set up that table in the observation log database. The end result of running this method is that the observation log database has all the necessary tables to be able to properly log an observation. This design allows the database structure to be changed without having to create a new database file. 

If the `clobber` option is set to True when `self.create_tables` is called, it will delete (`DROP` in SQL language) the Observation, Field, and Night tables before recreating them. This can be useful for clearing out an old file if desired.

### log_observation
This writes a new entry into the observation log database. It is called from within the `run` method of `schedule_executor` after each observation. It takes in two arguments
* *data*: a dictionary or SQLite rowProxy object containing the data which will be written to the database. This data can contain extra entries. `log_observation` will go through the data and grab all key:value pairs with keys that correspond to keys in `self.dbStructure` (ie those from dataconfig.json). Any missing keys in `self.dbStructure` will have their values set to None. 
* *image*: this is the filepath to the saved image, which is added as an entry with the key 'pathToFits' to the data dictionary.

This function uses `self.separate_data_dict(data)` to convert the data dictionary to the format it needs to write it out to the database. After getting the separated data dictionary (`separatedData`), the method iterates through each table in `separatedData` (eg Observation, Field, Night) and queries the database to see if an entry with the primary key for each table matches an entry in the database. Any duplicates are not re-written.

For example, the primary key of Observation is obsHistID, which should be a unique identifier of every observation. If there is already an entry in the Observation table in the database that has the same obsHistID as the observation to log, this entry is not re-written. 

In practice, Observation entries should not be attempted to be re-written unless there is an error with the schedule setup. However, each field will be observed multiple times, so this means only unobserved fields are added to the database. It also means that a new Night entry is only created once per night.

### separate_data_dict
This method supports log_observation. It takes in the big data dictionary (`dataDict`) of status fields received by log_observation (eg, the state dictionary from `wsp`, the image filename, etc) and converts it into a new dictionary `separatedData` that matches the format of the `self.dbStructure` dictionary. It loops through all the entries in dataDict and matches them against the entries in `self.dbStructure`. If an entry in dbStructure is not found in dataDict, the value for the entry will be set to the default value specified in `self.dbStructure` (ie and dataconfig.json) or just to None if no default is specified.


### To Do:
- [ ] Get rid of hard-coded paths, and add the paths to the config. This includes the database structure configuration (in <wsp_path>/config/dataconfig.json), and maybe the 1_night_test.db reference in `populateFieldsTable`?
- [ ] Add more relevant entries to dataconfig.json that have all the things we want to record in the FITS header.


### Change log
* **4/26/21 added config and logger as arguments** when instantiating an `ObsWriter` object, so now it uses the same log file as the rest of the code (instead of pseudoLog.log), and has access to the config if we want.

## Schedule Files
The schedule files are written outside of `wsp` by the WINTER scheduler code. 

There are several relevant items which must be included in the config file (`config.yaml`) which are used in the schedule handling:
* `scheduleFile_directory: 'schedule/scheduleFiles'`
* `scheduleFile_nightly_prefix: 'nightly_'`
* `scheduleFile_nightly_link_directory: 'data'`
* `scheduleFile_nightly_link_name: 'nightly_schedule.lnk'`

These must correspond to the naming convention used by the WINTER scheduler. The scheduler code runs daily and saves a new file in /data/schedules/nightly_YYYYMMDD.db, and creates a symbolic link to the most recent daily schedule at /data/nightly_schedule.lnk.

### Changelog:
* **4/26/21: updated schedule paths in the config file** to match documentation above


## Schedule Executor
The schedule executor, the `self.scheduleExec` attribute of the `systemControl.control` object inherits from QThread, and runs a dedicated thread which handles loading the schedule, making observations, and logging them. 

There are two `pyqtSignals` assiciated with the schedule executor:
* **changeSchedule: ** This signal is connected to `self.setup_new_schedule` in the init method. It is emitted any time `wsp` gets a command to change to a new schedule. This can happen when the wintercmds `load_target_schedule` or `load_nightly_schedule` commands are requested.

### init
The init method 

### To Do:
- [ ] Pass all the relevant information needed for logging each observation to the ObsWriter. The main thing that needs to happen is that all the fields from the schedule file need to get ported to scheduled entries in the data dictionary passed to `log_observation`. For example, the `azimuth` field from the current observation should get turned into something like `azimuth_scheduled` and added to the data dictionary. This could be done by looping through all the entries in `schedule.currentObs` and making a new `scheduled` dictionary that appends `_scheduled` to each key.






