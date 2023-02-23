# Generic WSP Camera API

## Intro
This is a document to specify a generic camera API that WSP will use to communicate with any number of cameras that will get installed on the WINTER observatory. This will be a key need to enable camera switching, and to avoid having to constantly update WSP as cameras are added and we transition from SUMMER to WINTER. 

## History: SUMMER ccd interface:
The SUMMER LLAMAS ccd is run through the ccd_daemon.py and its `CCD` class, and WSP communicates using the ccd.py 'local_ccd' class. 
Methods called by `local_ccd:
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
- `CCD.shutdownCameraClient()`:
  - Called by: `local_ccd.shutdownCameraClient()`
- `CCD.reconnectServer()`:
  - Called by: `local_ccd.reconnectServer()`
- `CCD.killServer()`:
  - Called by: `local_ccd.killServer()`
- Note: there some other methods, which poll individual status fields like exposure time, various temperatures, etc, but these are basically defunct: they work but they're not used within WSP so could be safely excised.
  


