#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Feb 15 15:18:42 2024

@author: nlourie
"""

import glob

# import pathlib
import json
import logging
import os
import pathlib
import random
import sys
import traceback
from datetime import datetime, timedelta

import jsonschema
import pandas as pd
import pytz
import sqlalchemy as db
import yaml

# add the wsp directory to the PATH
wsp_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "wsp"
)
# switch to this when ported to wsp
# wsp_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

sys.path.insert(1, wsp_path)
print(f"CalTracker: wsp_path = {wsp_path}")

from control import triggerHandler
from utils import utils


class CalTracker(object):
    def __init__(
        self, config, active_cams=["winter"], logger=None, sunsim=False, verbose=False
    ):
        """
        This is an object which will help keep track of whether various
        calibration sequences have been executed, namely darks and biases.

        At some point it may be useful to add a flats track component to this,
        which would require tracking active filters, but for now leaving it out.

        It creates and monitors a json log like this:

            {
                "winter": {
                    "darks" : {
                        "dark_times" : [60, 120]
                        "last_darkseq_timestamp_utc": null,
                        "last_darkseq_time_local": null,
                        }
                    "biases" : {
                        "last_biasseq_timestamp_utc": null,
                        "last_biasseq_time_local": null,
                        }
                    }
            }
        """
        self.config = config
        self.logger = logger
        self.active_cams = active_cams
        self.sunsim = sunsim
        self.verbose = verbose

        self.triggerhandler = triggerHandler.TriggerHandler(
            self.config, sunsim=self.sunsim, verbose=self.verbose, logger=self.logger
        )

        # set up the calibration log dictionary and json file
        # self.cal_log = dict()
        # self.setupCalLog()

        # set up the triggers for when we want cals to be taken
        self.setupTriggers()

        # set up the log file where the cal triggers will be stored
        self.cal_log_dir = os.path.join(
            os.getenv("HOME"), self.config["cal_params"]["cal_log"]["dirname"]
        )
        self.cal_log_filename = (
            self.config["cal_params"]["cal_log"]["filename"]
            + "_"
            + utils.tonight_local()
            + ".json"
        )
        self.cal_log_filepath = os.path.join(self.cal_log_dir, self.cal_log_filename)

        self.cal_log_linkdir = os.path.join(
            os.getenv("HOME"), self.config["cal_params"]["cal_log"]["linkdir"]
        )
        self.cal_log_linkname = self.config["cal_params"]["cal_log"]["linkname"]
        self.cal_log_linkpath = os.path.join(
            self.cal_log_linkdir, self.cal_log_linkname
        )

        self.triggerhandler.setupTrigLog(
            logpath=self.cal_log_filepath, linkpath=self.cal_log_linkpath
        )

    def log(self, msg, level=logging.INFO):
        if self.logger is None:
            print(msg)
        else:
            self.logger.log(level=level, msg=msg)

    # def setupCalLog(self):
    #     """
    #     Try to load in the contents of the cal log file and store it to
    #     self.cal_log. If it does not exist, or is non-compliant, then make a new
    #     one.
    #     """
    #     # file
    #     self.cal_log_dir = os.path.join(os.getenv("HOME"),self.config['cal_params']['cal_log']['dirname'])
    #     self.cal_log_filename = self.config['cal_params']['cal_log']['filename'] + '_' + utils.tonight_local() + '.json'
    #     self.cal_log_filepath = os.path.join(self.cal_log_dir, self.cal_log_filename)

    #     self.cal_log_linkdir = os.path.join(os.getenv("HOME"), self.config['cal_params']['cal_log']['linkdir'])
    #     self.cal_log_linkname = self.config['cal_params']['cal_log']['linkname']
    #     self.cal_log_linkpath = os.path.join(self.cal_log_linkdir, self.cal_log_linkname)

    #     # create the data directory if it doesn't exist already
    #     pathlib.Path(self.cal_log_dir).mkdir(parents = True, exist_ok = True)
    #     self.log(f'ensuring directory exists: {self.cal_log_dir}')

    #     # create the data link directory if it doesn't exist already
    #     pathlib.Path(self.cal_log_linkdir).mkdir(parents = True, exist_ok = True)
    #     self.log(f'ensuring directory exists: {self.cal_log_linkdir}')

    #     # check if the file exists
    #     try:
    #         # assume file exists and try to load cal log from file
    #         self.log(f'loading cal log from file')
    #         self.cal_log = json.load(open(self.cal_log_filepath))

    #     except FileNotFoundError:
    #         # file does not exist: create it
    #         self.log('no cal log found: creating new one')

    #         # create the default cal log: no cmds have been sent
    #         self.resetCalLog()

    #     # check if the json is valid
    #     if self.validateCalLog(self.cal_log):
    #         pass

    #     else:
    #         self.resetCalLog()

    #     # recreate a symlink to tonights trig log file
    #     self.log(f'trying to create link at {self.cal_log_linkpath}')

    #     try:
    #         os.symlink(self.cal_log_filepath, self.cal_log_linkpath)
    #     except FileExistsError:
    #         self.log('deleting existing symbolic link')
    #         os.remove(self.cal_log_linkpath)
    #         os.symlink(self.cal_log_filepath, self.cal_log_linkpath)

    # def validateCalLog(self, cal_log:dict) -> bool:
    #     """

    #     Check whether the cal log dictionary has all the required entries,
    #     and return True or False. This is to avoid issues where a bad cal log,
    #     or one that is old and doesn't have the required entries causes
    #     problems downstream in WSP.

    #     Parameters
    #     ----------
    #     cal_log : dict
    #         cal log dictionary, typically loaded in from a saved json file.

    #     Returns
    #     -------
    #     bool
    #         validity of the cal_log.

    #     """
    #     schemapath = os.path.join(wsp_path, 'cal', 'cal_log_schema.json')
    #     with open(schemapath, "rb") as f:
    #         cal_log_schema = json.load(f)

    #     try:
    #         jsonschema.validate(cal_log, schema=cal_log_schema)
    #         self.log("Successfully validated schema")
    #         return True
    #     except jsonschema.ValidationError as e:
    #         self.log("Error with JSON schema validation, input data not formatted correctly.")
    #         self.log(e)
    #         return False
    #         #raise RequestValidationError(e)

    # def resetCalLog(self, updateFile:bool = True):
    #     """
    #     Builds a new cal log at self.cal_log

    #     Parameters
    #     ----------
    #     updateFile : bool, optional
    #         Flag to specify whether the new self.cal_log dictionary should be
    #         written to the cal log json file. The default is True.

    #     Returns
    #     -------
    #     None.

    #     """
    #     self.log(f'resetting cal log')

    #     # first get the focus reference filters
    #     for cam in self.active_cams:

    #             self.cal_log.update({cam: {
    #                                             'dark' : {
    #                                                 'n_imgs'    : self.config['cal_params'][cam]['dark']['n_imgs'],
    #                                                 'exptimes'  : self.config['cal_params'][cam]['dark']['exptimes'],
    #                                                 'filterID'  : self.config['cal_params'][cam]['dark']['filterID'],
    #                                                 "last_timestamp_utc"    : None,
    #                                                 "last_time_local"       : None,
    #                                                 },
    #                                             'bias' : {
    #                                                 'n_imgs'    : self.config['cal_params'][cam]['dark']['n_imgs'],
    #                                                 'filterID'  : self.config['cal_params'][cam]['dark']['filterID'],
    #                                                 "last_timestamp_utc"    : None,
    #                                                 "last_time_local"       : None,
    #                                                 },

    #                                             }})
    #     if updateFile:
    #         self.updateCalLogFile()

    # def updateCalLogFile(self):

    #     # saves the current value of the log to the log_filepath file
    #     # dump the yaml file

    #     try:
    #         with open(self.cal_log_filepath, 'w+') as file:
    #             json.dump(self.cal_log, file, indent = 2)
    #     except FileNotFoundError:
    #         self.log(f'no existing cal log at {self.cal_log_file}, creating a new one')

    def getScheduledExptimes(self, camname="winter"):
        """
        Run a query on the nightly schedule and all the

        Returns
        -------
        None.

        """
        self.log("querying planned exposure times for all scheduled observations...")
        # get all the files in the ToO High Priority folder
        ToO_schedule_directory = os.path.join(
            os.getenv("HOME"), self.config["scheduleFile_ToO_directory"]
        )
        schedules_to_query = glob.glob(os.path.join(ToO_schedule_directory, "*.db"))

        # also get the nightly schedule

        nightlyschedulefile = os.path.realpath(
            os.path.join(
                os.getenv("HOME"),
                self.config["scheduleFile_nightly_link_directory"],
                self.config["scheduleFile_nightly_link_name"],
            )
        )

        schedules_to_query.append(nightlyschedulefile)

        self.log(f"found these schedules to query: {schedules_to_query}")
        self.log("analyzing schedules...")

        if len(schedules_to_query) > 0:
            # bundle up all the schedule files in a single pandas dataframe
            full_df = pd.DataFrame()
            # add all the ToOs
            for schedulefile in schedules_to_query:
                try:
                    ### try to read in the SQL file
                    engine = db.create_engine("sqlite:///" + schedulefile)
                    conn = engine.connect()
                    df = pd.read_sql("SELECT * FROM summary;", conn)
                    conn.close()

                    df["image_exptime"] = df["visitExpTime"] / df["ditherNumber"]

                    # now add the schedule to the master TOO list
                    full_df = pd.concat([full_df, df])

                except Exception as e:
                    print(f"could not load schedule, {e}")

        unique_exptimes = full_df["image_exptime"].unique()
        print()
        print(f"Unique Exptimes = {unique_exptimes}")
        return unique_exptimes

    def checkLastCalTime(self, camname: str, caltype: str) -> float:
        """


        Parameters
        ----------
        camname : str
            name of camera whose cals you want to query, either 'winter' or 'summer'.
        caltype : str
            type of calibration, eg 'dark', 'bias'.

        Returns
        -------
        float
            UTC timestamp of the last cal sequence for the specified type/camera.

        """

        last_cal_timestamp = self.cal_log[camname][caltype].get(
            "last_timestamp_utc", None
        )
        return last_cal_timestamp

    def updateCalLog(self, camname: str, caltype: str, timestamp="now"):
        """


        Parameters
        ----------
        camname : str
            DESCRIPTION.
        caltype : str
            DESCRIPTION.
        timestamp : int or str, optional
            DESCRIPTION. The default is 'now'.

        Returns
        -------
        None.

        """

        if timestamp == "now":
            timestamp = datetime.now(tz=pytz.UTC).timestamp()

        # try to update the actual time from the timestamp
        try:
            utc = datetime.fromtimestamp(timestamp, tz=pytz.utc)
            local_datetime_str = datetime.strftime(
                utc.astimezone(tz=pytz.timezone(self.config["site"]["timezone"])),
                "%Y-%m-%d %H:%M:%S.%f",
            )
        except Exception as e:
            tb = traceback.format_exc()
            self.log(
                f"could not update the string formatted timestamp, something is bad with timestamp: {e.__class__.__name__}, {e}, traceback = {tb}"
            )
            local_datetime_str = None

        # try to update the cal log with the new timestamp
        try:
            self.cal_log[camname][caltype]["last_timestamp_utc"] = timestamp
            self.cal_log[camname][caltype]["last_time_local"] = local_datetime_str
        except Exception as e:
            tb = traceback.format_exc()
            self.log(
                f"could not update the cal log with the specified information, something is bad: {e.__class__.__name__}, {e}, traceback = {tb}"
            )

    def setupTriggers(self):
        for camname in self.active_cams:
            try:
                self.triggerhandler.setupTrigs(
                    self.config["cal_params"][camname], trigname_prefix=camname
                )
            except Exception as e:
                tb = traceback.format_exc()
                self.log(
                    f"could not set up calibration triggers for {camname} camera: {e.__class__.__name__}, {e}, traceback = {tb}"
                )

    def getCalsToDo(self, sun_alt: float, timestamp: float, sun_rising: bool) -> list:
        """
        Get a list of the current cals which should be executed.

        Parameters
        ----------
        sun_alt : float
            sun altitude in degrees.
        timestsamp : float
            utc timestamp at which to evaluate the triggers.
        sun_rising : bool
            boolean that is True if the sun is rising, and False if it is setting.

        Returns
        -------
        list
            list of cal sequences to do, where each entry is a dictionary with
            key:value pairs corresponding to sequence name : sequence execution
            command.
        """
        # cals_to_do = []
        # for camname in self.active_cams:

        #     if 'triggers' in self.config['cal_params'][camname]:
        #         for trigname in self.config['cal_params'][camname]['triggers']:
        #             try:
        #                 if self.triggerhandler.triggerReady(trigname, sun_alt, timestamp, sun_rising):

        #                     # build the command
        #                     caltype = self.triggerhandler.triggers[trigname].cmd
        #                     if caltype  == 'dark':
        #                         cmd = 'robo_do_darks'
        #                     elif caltype == 'bias':
        #                         cmd = 'robo_do_bias'
        #                     elif caltype == 'flats':
        #                         cmd = 'robo_do_flats'

        #                     cmd = f'{cmd} --{camname}'

        #                     cal_to_do = (trigname, cmd)
        #                     if self.verbose:
        #                         self.log(f'{cal_to_do} added to list of cals to do')
        #                     cals_to_do.append(cal_to_do)

        #             except Exception as e:
        #                 tb = traceback.format_exc()
        #                 self.log(f'could not assess calibration trigger {trigname} for {camname} camera: {e.__class__.__name__}, {e}, traceback = {tb}')
        #     else:
        #         self.log(f'no calibration triggers listed for {camname} camera')

        cals_to_do = self.triggerhandler.getActiveTriggers(
            sun_alt, timestamp, sun_rising
        )

        return cals_to_do

    def logCommand(self, trigname, sun_alt, timestamp):
        """
        log that we've at least attempted to send this command
        """
        self.triggerhandler.logCommand(trigname, sun_alt, timestamp)
        self.log(
            f"logging that we attempted to handle cal trigger {trigname} at sun_alt = {sun_alt}, timestamp = {timestamp}"
        )

    def printCalLog(self):
        """
        Print out the cal log all pretty

        Returns
        -------
        None.

        """
        # print('Cal Log: ', json.dumps(self.cal_log, indent = 2))
        print("Cal Log: ", json.dumps(self.triggerhandler.triglog, indent=2))


if __name__ == "__main__":

    config = yaml.load(open(wsp_path + "/config/config.yaml"), Loader=yaml.FullLoader)

    sunsim = True

    cal = CalTracker(config, active_cams=["winter"], verbose=True, sunsim=sunsim)
    # cal.resetCalLog()
    # cal.printCalLog()

    # print()
    # print(f'doing a pretend dark sequence now...')
    # print()
    # cal.updateCalLog('winter', 'dark')
    # cal.printCalLog()
    print("------------------------------------------------------------------")

    # cal.resetCalLog()
    cal.printCalLog()

    calname = "midnight_darks"
    sun_alt = -30
    print("------------------------------------------------------------------")

    print("try at 10:30 pm:")
    timestr = "22:30:0.0"
    datestr = utils.tonight_local()

    timefmt = "%Y%m%d %H:%M:%S.%f"
    datetime_obj = datetime.strptime(f"{datestr} {timestr}", timefmt)

    timestamp = datetime_obj.timestamp()
    sun_rising = False
    # print(f'now checking if we can do this cal: {calname}')
    # cal.triggerhandler.triggerReady(calname, sun_alt, timestamp, sun_rising)

    print()
    cals_to_do = cal.getCalsToDo(sun_alt, timestamp, sun_rising)
    print(f"#############################")
    print(f"Cals to Do: {cals_to_do}")
    print(f"#############################")

    print("------------------------------------------------------------------")
    print("try at 12:05 am the next morning")
    timestr = "00:05:0.0"
    datestr = utils.tonight_local()
    timefmt = "%Y%m%d %H:%M:%S.%f"
    datetime_obj = datetime.strptime(f"{datestr} {timestr}", timefmt)
    datetime_obj = datetime_obj + timedelta(days=1)
    timestamp = datetime_obj.timestamp()
    sun_rising = False
    # print(f'now checking if we can do this cal: {calname}')
    # cal.triggerhandler.triggerReady(calname, sun_alt, timestamp, sun_rising)

    print()
    cals_to_do = cal.getCalsToDo(sun_alt, timestamp, sun_rising)
    print(f"#############################")
    print(f"Cals to Do: {cals_to_do}")
    print(f"#############################")

    print()
    cal_desc = cals_to_do[0][0]
    cal_cmd = cals_to_do[0][1]
    print(f"doing the first cal sequence in the queue: {cal_desc}")
    print(f"sending command: {cal_cmd}")

    cal.logCommand(trigname=cal_desc, sun_alt=sun_alt, timestamp=timestamp)

    print("------------------------------------------------------------------")
    print("try again at 12:05 am the next morning")
    timestr = "00:05:0.0"
    datestr = utils.tonight_local()
    timefmt = "%Y%m%d %H:%M:%S.%f"
    datetime_obj = datetime.strptime(f"{datestr} {timestr}", timefmt)
    datetime_obj = datetime_obj + timedelta(days=1)
    timestamp = datetime_obj.timestamp()
    sun_rising = False
    # print(f'now checking if we can do this cal: {calname}')
    # cal.triggerhandler.triggerReady(calname, sun_alt, timestamp, sun_rising)

    print()
    cals_to_do = cal.getCalsToDo(sun_alt, timestamp, sun_rising)
    print(f"#############################")
    print(f"Cals to Do: {cals_to_do}")
    print(f"#############################")
