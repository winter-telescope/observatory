import Pyro5.server

@Pyro5.server.expose
class Camera(object):
    # ... methods that can be called go here...
    def __init__(self):
        pass

    def take_image(self):
        pass

daemon = Pyro5.server.Daemon()
uri = daemon.register(Camera)
print(uri)
daemon.requestLoop()
