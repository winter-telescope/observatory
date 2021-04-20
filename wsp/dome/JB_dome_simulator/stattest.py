#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# import socket programming library
import socket
from datetime import datetime
import json

# import thread module
from _thread import *
import threading
  
print_lock = threading.Lock()
  
# thread function
def threaded(c):

    x = {"UTC":"2021-04-08 23:20:41.561","Telescope_Power":"OFF","Dome_Azimuth":0.0,"Dome_Status":"OFF","Home_Status":"NOT_READY","Shutter_Status":"OPEN","Control_Status":"CONSOLE","Close_Status":"READY","Weather_Status":"READY","Sunlight_Status":"NOT_READY","Wetness":"READY","Outside_Dewpoint_Threshold":2.0,"Average_Wind_Speed_Threshold":11.2,"Outside_Temp":17.8,"Outside_RH":31.0,"Outside_Dewpoint":0.4,"Pressure":829.7,"Wind_Direction":297,"Average_Wind_Speed":2.2,"Weather_Hold_time":0,"Faults":17}

   
    while True:
  
        # data received from client
        data_bytes = c.recv(1024)
        data = data_bytes.decode("utf-8").rstrip()
        if not data:
            print('No Data - Close Socket')
              
            # lock released on exit
            print_lock.release()
            break

        with open("status.txt") as fp:
            line = fp.readline()
            cnt = 1
            while line:
                val=line.split("=")
                val[1]=val[1].replace('\n','')
                if cnt == 1:
                    x['Telescope_Power'] = val[1]
                elif cnt == 2:
                    x["Dome_Azimuth"]=val[1]
                elif cnt == 3:
                    x["Dome_Status"]=val[1]
                elif cnt == 4:
                    x["Home_Status"]=val[1]
                elif cnt == 5:
                    x["Shutter_Status"]=val[1]
                elif cnt == 6:
                    x["Control_Status"]=val[1]
                elif cnt == 7:
                    x["Close_Status"]=val[1]
                elif cnt == 8:
                    x["Weather_Status"]=val[1]
                elif cnt == 9:
                    x["Sunlight_Status"]=val[1]
                elif cnt == 10:
                    x["Wetness"]=val[1]
                elif cnt == 11:
                    x["Outside_Dewpoint_Threshold"]=val[1]
                elif cnt == 12:
                    x["Average_Wind_Speed_Threshold"]=val[1]
                elif cnt == 13:
                    x["Outside_Temp"]=val[1]
                elif cnt == 14:
                    x["Outside_RH"]=val[1]
                elif cnt == 15:
                    x["Outside_Dewpoint"]=val[1]
                elif cnt == 16:
                    x["Pressure"]=val[1]
                elif cnt == 17:
                    x["Wind_Direction"]=val[1]
                elif cnt == 18:
                    x["Average_Wind_Speed"]=val[1]
                elif cnt == 19:
                    x["Weather_Hold_time"]=val[1]
                elif cnt == 20:
                    x["Faults"]=val[1]
                line = fp.readline()
                cnt += 1

        utc=datetime.utcnow()
        str_date=utc.strftime("%Y-%m-%d, %H:%M:%S.%f")
        str_date=str_date[:-3]

        x['UTC'] = str_date
        jstr=json.dumps(x)

        c.send(bytes(jstr,"utf-8"))
  
    # connection closed
    c.close()
  
  
def Main():
    host = ""
    port = 62000
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((host, port))
    print("socket binded to port", port)
  
    # put the socket into listening mode
    s.listen(5)
    print("socket is listening")
  
    # a forever loop until client wants to exit
    while True:
        try:
            # establish connection with client
            c, addr = s.accept()
      
            # lock acquired by client
            print_lock.acquire()
            print('Connected to :', addr[0], ':', addr[1])
      
            # Start a new thread and return its identifier
            start_new_thread(threaded, (c,))
        except KeyboardInterrupt:
            break
        
    s.close()
  
  
if __name__ == '__main__':
    Main()