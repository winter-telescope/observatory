# Generic WSP Camera API

## Intro
This is a document to specify a generic camera API that WSP will use to communicate with any number of cameras that will get installed on the WINTER observatory. This will be a key need to enable camera switching, and to avoid having to constantly update WSP as cameras are added and we transition from SUMMER to WINTER. 

## History: SUMMER ccd interface:
The SUMMER LLAMAS ccd is run through the ccd_daemon.py and its `CCD` class, and WSP communicates using the ccd.py 'local_ccd' class. 
Methods called by `local_ccd:
- `CCD.GetStatus()`: returns a dictionary with all the housekeeping data


