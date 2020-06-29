
# Building a Sky Model with PWI4

## A textual interpretation of the pwi4_build_model.py file

### Main Method

The main method is the function in a python module which is called when the module is invoked at the command line.

First, the method creates an instance of the PWI4 class defined in the pwi4_client module. It is a client to the PWI4 telescope control application. The default constructor creates it with the localhost at port 8220.

Next the method checks the status of the client object it just created. It saves the result to a status variable which contains a status object with many fields describing the telescope.

If it isn't connected to the mount, it attempts to connect.

It then checks status again, and enables axis 0 and axis 1.

Next it creates a list of points in the sky to look at with Alt-Az points.

Finally, it loops through these points and calls map point with the telescope client object and each point.

### map_point method

```python
"""
  Slew to the target Alt-Az, take an image,
  PlateSolve it, and (if successful) add to the model
"""
```

As the method spec says, it seems first to try to move to the altitude and azimuth coordinates provided. It then uses an infinite loop and the `time.sleep` to wait until the telescope has reached the correct point in the sky.

Once it has reached the target, it attempts to check if we have actually reached the correct point in the sky, raising an exception if it hasn't made it.

There is a comment, but no code accompanying, which calls for us to turn on sidereal tracking at this point, since the mount will stop moving after slewing.

Next the routine takes an image, using the `take_image` method.

After this step, it calls the `platesolve` method from another module. This result is then fed to `mount_model_add_point` presumably to add to the sky model.

### take_image and take_image_virtualcam methods

Uses the virtual camera in the PWI4 client module to get a simulated starfield. In the method comments it makes a note that the star catalog needs to be installed in the correct place to be used.

## platesolve method/module

runs an executable function outside of the python programs defined in this module, along with a few other arguments, then parses and returns the output. I don't know much about this code as it stands, so it may be a source of issues.

## mount_model_add_point method

This method makes another web request to the HTTP communicator, supposedly to add this point gained by running platesolve on the image taken by the build model module. 
