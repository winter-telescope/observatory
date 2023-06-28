# Using Pyro5 with Multiple PCs
This is built in, but kind of tricky to understand from the documentation. In testing, this approach worked:

## Name Server
By default the name server runs on localhost. Running the name server on localhost prevents external machines from accessing it. To allow multiple machines you have to explicitly give it a host IP address. Pryo's documentation says to avoid having multiple computers running name servers. I think it's not a big deal though, since if you are setting up your name server to be accessible from other PCs you will need to be more explicit about WHICH name server you register daemons on.

Launch the name server on the machine you want, and explicitly pass it the IP address to run on. In this example, I want to run the nameserver on Heimdall: 192.168.1.10. From a terminal window, enter this:
```console
winter@heimdall:~$ pyro5-ns -n 192.168.1.10
```

## Pyro Daemon Server Side
The pyro daemon is what "hosts" the object that you want to be able to talk to and call functions on from various places. Again, we have to now be explicit about WHERE the object is hosted. We ALSO have to be explicit about which (eg where) the name server is that we want to register the object.

A simple object to test this out is defined here:
```python
import Pyro5.core
import Pyro5.server

class ObjectToHost(object):

    def __init__ (self):
        self.word = 'Hello'
    @Pyro5.server.expose
    def hello(self):
        return(self.word)
```



In python script, first create the daemon which will host the object:

```python
# instantiate the object to host
obj = ObjectToHost()

# create a pyro daemon to host the object
# BE EXPLICIT ABOUT WHERE TO HOST THE OBJECT. Here I'm using freya: 192.168.1.20
daemon_host = '192.168.1.20'
daemon = Pyro5.server.Daemon(host = self.daemon_host)

# find the name server. remember we launched it on 192.168.1.10
ns_host = '192.168.1.10'
ns = Pyro5.core.locate_ns(host = ns_host)

# get the uri (address) of the daemon so we can register it on the name server
uri = daemon.register(obj)

# now register the daemon on the name server, and call it "test_object" on the name server
label_on_nameserver = 'test_object'
ns.register(label_on_nameserver, uri)

# launch the daemon request loop to handle communications
daemon.requestLoop()
```

## Pyro Client Side
Now we want to access the object that is being hosted in the Pyro daemon. We can do this from any machine that can talk to these machines. We will first look up the address (uri in Pyro speak) of the pyro daemon on the name server, and then we will create a proxy object for it. 

```python
import Pyro5.client

# first, find the name server: recall we're running it on heimdall (192.168.1.10)
ns_host = '192.168.1.10'
ns = Pyro5.core.locate_ns(host = ns_host)

# get the uri of the pyro daemon hosting the remote object by querying the name server
label_on_nameserver = 'test_object'
uri = ns.lookup(label_on_nameserver)

# make a proxy object
obj = Pyro5.client.Proxy(uri)
```
Now we can call exposed methods on the proxy object! Eg: `obj.hello()` returns `'Hello'`!

## Safety concerns
There are many ways you can allow bad routes into your machine with Pyro. You could easily expose a method that would parse arbitrary inputs from an external computer. There are some safety suggestions and things to do on the Pyro docs (eg SSL certs), but I think the general approach should be to tightly control access to the machine's networks rather than relying on Pyro to do the network safety. Underneath all the python stuff Pyro is just a low level python socket interface, so treat it accordingly.
