#!/bin/bash
source $HOME/anaconda3/etc/profile.d/conda.sh
conda activate wspfocus
#-u: unbuffered output
#python -u $HOME/GIT/observatory/development/daemon/servicepython.py
python -u $HOME/GIT/firmware/software/development/cameraDaemon/winterCamerad.py