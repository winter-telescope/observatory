# Daemon Architecture

### What are the daemons
Daemons are scripts that run in their own processes, usually in the background. The idea is that long-running processes should happen in their own processes so they don't bog down the main processes in `wsp.py`. Most of the places they will be used are to create an interface from `wsp` to a piece of hardware. This includes: the weather stations at Palomar, the WINTER cameras, the guider cameras, the telescope shutter. The approach replicates how the telescope daemon (which runs on the embedded Windows PC) works. A standalone daemon process runs in the background. This process is multithreaded: it can handle multiple requests, eg to report some housekeeping statuses, while also executing long-runtime tasks (like slewing). 

### General Architecture
Each daemon is a standalone python script, usually called thingd.py (where the d at the end means it's a daemon). Each daemon has a main object class which contains all the necessary attributes for running/communicating with the piece of hardware it is designed to operate. 

Communication between daemons and from `wsp` to each daemon happens using the Pyro5 module. To run properly, the Pyro5 name server must be started first. When each daemon runs, it is registered in the Pyro5 name server by a sensible name (eg, "weather"). 

Each daemon also has a corresponding local class which sits within `wsp.py` and essentially holds local copies of the relevant attributes from the daemon class. The local objects typically have some kind of "update" method which grabs the current state from the remote Pyro5 object. The local object also has methods which attempt to call methods from the remote class to make the hardware do something (eg take an image, open the shutter, etc). The idea is that all the local functions should return essentially immediately and never take appreciable time to execute. 

# Specific Daemons

### Weather Daemon
