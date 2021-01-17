import Pyro5.core
import Pyro5.server
import random
import time

@Pyro5.server.expose
class Weather(object):
    # ... methods that can be called go here...
    def __init__(self):
        pass

    def checkWeather(self):
        pass

    def weather_safe(self):
        time.sleep(5)
        if random.randint(1,10) > 5:
            return True
        else:
            return False

daemon = Pyro5.server.Daemon()
ns = Pyro5.core.locate_ns()
uri = daemon.register(Weather)
ns.register("weather", uri)
print("weather daemon running")
daemon.requestLoop()
