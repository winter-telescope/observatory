import Pyro5.core
import Pyro5.server
import random
import time
from PyQt5 import uic, QtCore, QtGui, QtWidgets


class palomarWeather:

    def __init__(self):
        self.weatherValue = 0

    def get_weather(self):
        print("getting weather from external source")
        time.sleep(10)
        self.weatherValue += 1
        print("got weather")

class weatherMonitor(QtCore.QThread):
    def __init__(self, weather):
        super().__init__()
        self.running = False
        self.weather = weather

    def stop(self):
        self.running = False

    def run(self):
        self.running = True

        while self.running:
            print("Thread calling get Weather")
            self.weather.get_weather()
            time.sleep(20)


@Pyro5.server.expose
class Weather(object):
    # ... methods that can be called go here...
    def __init__(self):
        self.PalomarWeather = palomarWeather()
        self.weatherThread = weatherMonitor(self.PalomarWeather)

    def startWeather(self):
        # launch a thread which periodically updates the weather
        self.weatherThread.start()

    def shutdownWeather(self):
        #kill the weather thread
        self.weatherThread.stop()


    def getWeather(self):
            pass

    def weather_safe(self):
        #return the most recent value of the weather since it was last updated
        self.weatherValue = self.weather.weatherValue
        return self.weatherValue

if __name__ == '__main__':
    #launch the daemon in a seperate thread. This allows this program to not block when daemon.requestLoop is called
    #We can now do other things in this program I guess

    # Big Question: How do we run a continuous process that the daemon is monitoring.
        #One way I guess could be to have a program that constantly checks weather and writes it down somewhere. The daemon just looks it up then
    daemon = Pyro5.server.Daemon()
    ns = Pyro5.core.locate_ns()
    uri = daemon.register(Weather)
    ns.register("weather", uri)
    print("weather daemon running")
    daemon.requestLoop()

    # weather = Weather()
    # weather.startWeather()
    # counter = 0
    # while counter <= 12:
    #     safe = weather.weather_safe()
    #     print("Weather Safe: " + str(safe))
    #     time.sleep(5)
    #     counter +=1
