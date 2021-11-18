# WINTER Scheduler Documentation
### Danielle Frostig 05/2020 


## Scope 

As part of it’s autonomous observing program, WINTER must generate an observing plan that balances scientific goals of the project while maximizing the scientific quality of the data. The science goals, in order of decreasing priority, are:

1.	Kilonova searches: WINTER will ingest LIGO alerts of neutron star mergers or neutron star black hole mergers. These alerts interrupt all other observations and must be immediately integrated into the nightly schedule. 
2.	Infrared surveys: Surveys of varying cadences and science goals will constitute the majority of observation time.
3.	Guest observations: Up to 25% of observation time is allocated to guest observations, consisting of a variety of observation types, which must be interwoven with the kilonova searches and infrared surveys.

We adapted the Zwicky Transient Facility (ZTF) scheduler for the WINTER project to create a customized WINTER scheduler that builds on the extensive functionality of the ZTF scheduler. Principally, the ZTF scheduler balances many different observing programs with unique cadences while also maximizing data quality by selecting fields through volumetric weighting. In this scheme, the most desirable field probes the greatest volume (Vlim) for any given exposure. The limiting volume for an exposure is related to the distance (dlim) at which a source of absolute magnitude M will be detected. This is constrained by seeing, sky brightness, and instrument noise, which all factor into the limiting magnitude (mlim) for an exposure. Thus, with the distance modulus, dlim=100^0.2(m_lim - M +5) , and Vlim  α dlim^3, each exposure has a volumetric weighting of V=100^0.6(m_lim - 21) (Bellm et al. 2019). 

The ZTF scheduler offers several modes for simulations and on-sky observing. Queue observing ingests a predefined list of fields and steps through each field sequentially, greedy observing continuously selects the best target (based on the volumetric weighting scheme) for a given time--recalculating before each target, and Gurobi observing uses the Gurobi linear optimizer to solve a travelling salesman problem to optimize each night of observing (Bellm et al. 2019). All three modes are used in WINTER’s observing program: queue observing is suited for defined targets of opportunity, such as LIGO alerts, greedy observing works well for reference building surveys which contain too many fields to optimize across, and Gurobi observing is appropriate for balancing science surveys with varying cadences. 
   



## Use 

The WINTER scheduler takes in 4 json (JavaScript Object Notation) configuration files. The top-level reference file (e.g. allsky_config) specifies the name of the run and the default and fallback observing queues. Two more json configuration files specify the observable fields, cadence, filters, and other parameters for default and fallback observing queues (e.g. allsky_reference_building.json and j_band_fallback.json, respectively). Finally, a timing configuration file (e.g. 2021_config.cfg) specifies the start date, duration, and weather conditions (for simulated observing only) for the run. The WINTER scheduler can be run in the top-level folder (with the README file) with run_winter_sim.py as follows:

python run_winter_sim.py './sims/allsky_config.json' './config/2021_reference.cfg'


## Run Nightly

There is a separate folder called daily_winter_scheduler that runs one nightly sim and pulls from the long term database. The nightly schedules are written to `~/data/schedules/nightly_YYYMMDD.db` and pull from the master database at `~/data/WINTER_ObsLog.db`. To run the nightly mode, go to the daily_winter_scheduler file and run:

python run_winter_sim.py './sims/allsky_config.json' './config/tonight.cfg'

## Major changes from the ZTF Scheduler

The WINTER version of the ZTF scheduler implements the following changes to account for WINTER’s differing project requirements. For general bookkeeping, the major changes to the code and the files affected are listed below each category in gray. 

1.	Removes 1 filter per time slot constraint: ZTF’s filter changing mechanism takes 135 seconds, as opposed to WINTER’s ~8 seconds, to exchange passband filters. Therefore, to minimize overhead time and simplify optimizations ZTF is constrained to one filter per time slot (set to 30 minutes). For WINTER’s implementation, we removed this constraint from the optimization and instead introduced the filter exchange time as an overhead time in the travelling salesman problem. This requires reindexing the scheduler such that each observable field in each filter is a unique request and a filter exchange presents extra overhead time between requests. This solution accomplishes WINTER’s science goals more closely by allowing for frequent filter exchanges but can slow down the scheduler optimization by introducing more requests to optimize over.
a.	Remove 1 filter constraint in optimize.py by setting number of filters per block to <=3. 
b.	Reindexed QueueManager.py and small parts of the rest of the scheduler, such as simulate.py
c.	Added filter exchange time to traveling salesman problem in QueueManager.py 

2.	Replaces ZTF fields with smaller WINTER fields: WINTER has a ~1 square degree field of view, as opposed to ZTF’s 47 square degree field of view and can observe to a higher airmass. Combining these two factors, the WINTER simulator must optimize across ~35,000 fields compared to ~600 fields for ZTF (Figure 1). This volume of pointings makes the ZTF program for the Gurobi optimizer prohibitively slow for WINTER reference building surveys and large all-sky surveys. To run reasonable simulations for WINTER, we rewrote how the Gurobi optimizer mode sorts and searches through request databases. By implementing multilevel indexing of databases, rather than searching each line of a database for a request, a simulation that ran in ~24 hours with the original ZTF code instead runs in 13 minutes.    
a.	Created WinterFields.txt
b.	Changed hard coded field limit in Fields.py that constrain the user to 4000 fields. 
c.	Replaced scalar compare line by line searches in optimize.py with multilevel indexing of databases. 

![Size of ZTF fields](/images/ZTF_fields.png "ZTF Fields")

