# Generic WSP Camera API

## Intro
This is a document to specify a generic camera API that WSP will use to communicate with any number of cameras that will get installed on the WINTER observatory. This will be a key need to enable camera switching, and to avoid having to constantly update WSP as cameras are added and we transition from SUMMER to WINTER. This is based on the SUMMER daemon structure developed for running the LLAMAS CCD, this is described in SUMMER_Camera_Interface.md.

## Methods
At the moment, most of these functions don't return. Maybe we want to have them return a boolean, or some kind of status code instead?

### Deamon Handling
- `reconnectCameraDaemon(daemon_name)` -> None
- `killCameraDaemon()` -> None
- `restartCameraDaemon()` -> None

### TEC Handling
Note these methods are set up to handle multiple TEC addresses, so that it's straghtforward to send commands to individual sensors. You don't need to pass a list of addresses, but you can. This way on the daemon side you can decide what to do with it.

- `tecSetSetpoint(temperature, addr: list = [])` -> None
- `tecStart(addr: list = [])` -> None
- `tecStop(addr: list = [])` -> None

### Taking Images

-`setExposure(exptime_s: float, addr: list = [])` -> None
-`doExposure(addr: list = [])` -> None

### Getting housekeeping data
Returns a dictionary of various housekeeping keywords. These will be different for each camera daemon.
- `getStatus()` -> dict





