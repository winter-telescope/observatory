import Pyro5.core
import Pyro5.server
import random
import time
from PyQt5 import uic, QtCore, QtGui, QtWidgets
from astropy.io import fits
import numpy as np

class demoCamera:

    def __init__(self):
        self.status = {}
        self.status['temperature'] = 0
        self.status['exposing'] = False
        self.status['focus'] = 0
        self.imageCount = 0
        self.lastImage = ''
        self.metadata = {}
        self.exposureTime = 0

    def get_status(self):
        return self.status

    def expose(self):
        print('taking exposure...')
        self.status['exposing'] = True
        time.sleep(self.exposureTime)

    def make_image(self):
        hdu = fits.ImageHDU()
        hdu.data = np.arange(100.0)
        for key in self.metadata:
            hdu.header[key] = self.metadata[key]
        hdu.writeto(f'testImage{self.imageCount}.fits')
        self.lastImage = f'testImage{self.imageCount}.fits'
        self.status['exposing'] = False
        self.imageCount += 1



class cameraThread(QtCore.QThread):
    def __init__(self, camera):
        super().__init__()
        self.running = False
        self.camera = camera

    def stop(self):
        self.running = False

    def run(self):
        self.camera.expose()
        self.camera.make_image()

    def start_image(self, time, metadata):
        self.camera.metadata = metadata
        self.camera.exposureTime = time
        self.start()

@Pyro5.server.expose
class Camera(object):
    # ... methods that can be called go here...
    def __init__(self):
        self.camera = demoCamera()
        self.cameraThread = cameraThread(self.camera)

    def take_image(self, time, metadata):
        # take an exposure for a given number of seconds
        self.cameraThread.start_image( time, metadata)

    def get_last_image(self):
        return self.camera.lastImage

    def get_status(self):
        # return a dictionary with status values of the camera
        return self.camera.get_status()

if __name__ == '__main__':

    daemon = Pyro5.server.Daemon()
    ns = Pyro5.core.locate_ns()
    uri = daemon.register(Camera)
    ns.register("camera", uri)
    print("camera daemon running")
    daemon.requestLoop()
