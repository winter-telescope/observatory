# Notes on fresh setup with new Python 3.9 Conda installation
Steps during install

## Setting up conda
Conda version: installed from Anaconda3-2021.11-Linux-x86_64.sh
Python: 3.9.7 (default, Sep 16 2021, 13:09:58)
### Environment
Made new environment by cloning base: wspV0. Working in this envrioment going forward.

To make the new wspV0 env active in a terminal automatically, added this to ~.bashrc under the conda activate stuff (last line `<<< conda initialize`). Note that I think the conda initialize stuff is supposed to do this automatically, but instead it just wipes out the conda path and adds ~/anaconda3/condabin to the path instead of ~/anaconda3/bin which is where all the conda commanmds (eg `activate`) live.

># add anaconda to path (the initialize above isn't doing it...)
>export PATH="/home/winter/anaconda3/bin:$PATH"
>
># set up default conda env
>source activate wspV0

## Setting up python 
### Adding new packages:
- Pyro5: `conda install -c conda-forge pyro5`
- Labjack
	- Instructions here: [labjack.com](https://labjack.com/support/software/examples/ljm/python)
	- Run `python -m pip install labjack-ljm`
- Slack SDK: `python -m pip install slack_sdk`
	- Using version: slack-sdk-3.15.2
- GetData:
	- Download the current installation files
	- Run install:
		- `./configure --with-python-module-dir=/home/winter/anaconda3/envs/wspV0/lib/python3.9/site-packages`
		- `sudo make`
		- `make install`
	- Had some issues in make check (between make and make install), but seems to be working?
- PySerial: 
	- `python -m pip install pyserial`
### Packages needed for huaso communications
- bitstring
	- [bitstring webpage](https://bitstring.readthedocs.io/en/latest/)
	- `python -m pip install bitstring`
- aenum
	- `python -m pip install aenum`
- pyds9
	- `python -m pip install pyds9`
### Packages needed for scheduler
- astroplan
	-  `python -m pip install astroplan`
- sklearn_pandas
	- `python -m pip instsall sklearn_pandas`
- xgboost
	- `python -m pip install xgboost`
- gurobi
	- [Gurobi Installation Instructions](https://www.gurobi.com/documentation/9.5/quickstart_windows/cs_anaconda_and_grb_conda_.html)
	- `conda config --add channels https://conda.anaconda.org/gurobi`
	- `conda install gurobi`
- transitions
	- `python -m pip install transitions`
### Scheduler webpage
- pyweb.io
	-`python -m pip install pywebio`

### Fixing a astropy IERS bug
Note: this is currently under development at astropy and will likely be fixed in future releases.
The issue is that the IERS server (International Earth Rotation and Reference Systems service), a server where astropy gets information about where the earth currently is, can go down. The primary place it tries to get the information is a NASA server, but that has been buggy of late ([astropy issue 13007](https://github.com/astropy/astropy/issues/13007). THe fix is here, to switch to a USNO server: [astropy commit request to switch to IERS USNO server](https://github.com/astropy/astropy/pull/13004/commits/d7c2f6cfb3e48856c81e076bca61638fe7b46250). 

Make this change in `~/anaconda3/envs/wspV0/lib/python3.9/site-packages/astropy/utils/iers/iers.py`:
>#IERS_A_URL = 'ftp://anonymous:mail%40astropy.org@gdc.cddis.eosdis.nasa.gov/pub/products/iers/finals2000A.all'  # noqa: E501
>IERS_A_URL = 'https://maia.usno.navy.mil/ser7/finals2000A.all' # NPL 3-30-22 from here: https://github.com/astropy/astropy/pull/13004/commits/d7c2f6cfb3e48856c81e076bca61638fe7b46250



	- 
