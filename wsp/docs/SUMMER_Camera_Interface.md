# SUMMER Camera Interface Description

The SUMMER LLAMAS ccd is run through the ccd_daemon.py and its `CCD` class, and WSP communicates using the ccd.py 'local_ccd' class. 
## Overview of methods used in WSP for SUMMER:
The general functions needed are:
- Get the housekeeping status of the camera
- Take an exposure and pass on naming and housekeeping info for the FITS file
- Start/Stop the TEC
- Change the TEC setpoint
- Shutdown/Restart the camera daemon
- Shutdown the camera client connection to the camera daemon
## Specific methods called by `local_ccd:
- `CCD.GetStatus()`: returns a dictionary with all the housekeeping data
  - Called by: `local_ccd.update_hk_state()`
- `CCD.setexposure(exptime)`: sets the camera exposure time to the specified `exptime`
  - Called by: `local_ccd.setexposure(exptime)`
- `CCD.doExposure(state_dict = {}, image_suffix = None, dark = False)`: takes an exposure and passes the `state_dict` housekeeping dictionary to the camera daemon to build the FITS header. The `dark` boolean flag is used to decide whether the shutter should be fired. The `image_suffix` is included in the `CCD` method, but is not used by the `local_ccd`; it just allows you to tack a suffix onto the end of the filename.
  - Called by: `local_ccd.doExposure(state = self.hk_state, dark = dark)`
- `CCD.tecStart()`: starts up the TEC on the camera
  - Called by: `local_ccd.tecStart()`
- `CCD.tecStop()`: stopst up the TEC on the camera
  - Called by: `local_ccd.tecStop()`
- `CCD.setSetpoint(temperature)`: set the TEC setpoint to the given temperature
  - `Called by: `local_ccd.setSetpoint(temp)`
- `CCD.shutdownCameraClient()`: this kills the client connection to the huaso server daemon. Basically it shuts down the connection to the server nicely so that it doesn't leave any open sockets or anything like that. This is called when shutting down.
  - Called by: `local_ccd.shutdownCameraClient()`
- `CCD.triggerReconnect()`: this emits a PyQt signal in the camera daemon, which is connected to the `CCD.reconnect` slot method. This reconnect method attempts to kill any running processes which have instances of the huaso server daemon running. It then launches the hauso server using the `daemon_utils.PyDaemon` methods based on the python subprocess modules. After successfully launching the hauso server, it (re)initializes an instance of the huaso camera client object to handle communications with the camera daemon. If it doesn't successfully find a running instance of huaso server daemon, it waits a bit and then tries again.
  - Called by: `local_ccd.reconnectServer()`
- `CCD.killServer()`: this is a pretty brute force method which just searches for linux process IDs that are associated with any running instances of a huaso server daemon, and tries to kill them.
  - Called by: `local_ccd.killServer()`
- Note: there some other methods, which poll individual status fields like exposure time, various temperatures, etc, but these are basically defunct: they work but they're not used within WSP so could be safely excised.

## Thread structure of the camera daemon 
The CCD daemon is essentially set up like all the other WSP daemons. The main class is a QObject defined locally as PyroGUI, and it initializes a `CCD` class as `self.ccd` within it's init definition. The PyroGUI init defines a number of QTimers which will be used to trigger the shutter to go, and sequence saving sequences that must happen throughout an exposure capture and save. This is all necessary because the huaso server daemon just spits back the raw data stream and then the huaso client object which is a member of `CCD` handles all the formatting and saving. The init of the PyroGUI also connects all these signals to slots in the `CCD` object. As one example, after triggering an exposure, the `PyroGUI.expTimer` single shot QTimer counts down the exposure, and then its completion is connected to the local slot method `PyroGUI.expTimerComplete()` which emits the `PyroGUI.Tell_CCD_To_Read_Image.emit()` signal. This `PyroGUI.Tell_CCD_To_Read_Image` signal is connected to a slot method of the `CCD`: `CCD.readImg` which within the `CCD` object triggers some action. This structure is necessary to properly handle the threading communications with the Pyro communications. I don't remember all the issues exactly but if I tried to handle this sequencing within the `CCD` class it ran into all sorts of issues where Pyro was trying to talk to the wrong thread and it wouldn't work. For other sensors requireing this kind of sequencing I think this needs to be replicated, but for sensors twhich handle this all internally and block the trhead while waiting for them to finish, this is probably fine to ignore.

