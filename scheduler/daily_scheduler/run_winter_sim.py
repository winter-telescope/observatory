#!/usr/bin/env python

import os.path
import os
import argparse
import astropy.units as u
from winter_sim.simulate import simulate
from astroplan import download_IERS_A
import pathlib
# download_IERS_A()


home = os.path.expanduser("~")
data_dir = home + '/data/'

# create the data directory if it doesn't exist already
pathlib.Path(data_dir).mkdir(parents = True, exist_ok = True)

parser = argparse.ArgumentParser(description="Simulate WINTER observing.")
parser.add_argument('schedule_configuration',
        help="Path to schedule configuration file")
parser.add_argument('simulation_configuration',
        help="Path to simulation configuration file")
parser.add_argument('-o', '--output', default=data_dir,
        help="Directory to write simulation to.")
parser.add_argument('-t', '--time-limit', default=720., type=float,
        help="Number of seconds to allow Gurobi optimizer to run")

args = parser.parse_args()

assert(os.path.isfile(args.schedule_configuration))
schedule_config_path, schedule_config_file = \
        os.path.split(args.schedule_configuration)

assert(os.path.isfile(args.simulation_configuration))
sim_config_path, sim_config_file = \
        os.path.split(args.simulation_configuration)

assert(os.path.isdir(args.output))

simulate(schedule_config_file, sim_config_file,
    scheduler_config_path = schedule_config_path,
    sim_config_path = sim_config_path,
    output_path = args.output,
    time_limit = args.time_limit * u.second)


print(" \n \n \n \nFINISHED RUNNING SCHEDULER")
