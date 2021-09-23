# WSP Robotic Operations

Notes on how the WSP robotic mode (the `-r` option which can be called when launching WSP) works, and some tips on how to run things and debug the inevitable issues.

## Hows does the robitic mode work?
There are three main pieces of code which define the robotic operations of WSP:
1. The "robotic operator": [`roboOperator.py'](https://magellomar-gitlab.mit.edu/WINTER/code/-/blob/sunsim/wsp/control/roboOperator.py). This script contains a class called `RoboOperator` which defines all (well, there are a few exceptions) of the main methods which define complex observing operations and sequences. Some major examples used nightly:

- `do_observation`: a generic observing method that handles observation of a variety of target types ("targtypes") including alt/az, ra/dec or catalog object. It handles slewing/enabling tracking of the dome, telescope, rotator, triggering the CCD exposure, etc. 
- `do_calibration`: a method which executes the full sequence of calibration operations which ideally is execute at the start and end of the night. It points to 75 deg elevation, and opposite the sun (ie either due east or west depending if it is sunrise or sunset) takes 5 flats using an empirical model to set the exposure time (currently only in r-band), 5 darks, and then 5 biases. 

There are other complex sequences in the robotic operator which are not used regularly, but still are helpful for debugging, or are critical but used only infrequently, including:
- `remakePointingModel`: a method which starts up a sequence which will observe a number of alt/az targets, platesolve them, and update their (alt/az) --> (ra/dec) mapping to the Planewave PWI4 interface to add to the pointing model.
