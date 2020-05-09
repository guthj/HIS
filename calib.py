#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat May  2 18:38:39 2020

@author: guth
"""
from smbus2 import SMBus
#from time import sleep
import csv

import os 

i2cbus = SMBus(1)

addr = [0x20,0x21,0x30,0x31]

minval = [999,999,999,999]
maxval = [0,0,0,0]

if not os.path.exists("/home/pi/.HIS"):
    os.makedirs("/home/pi/.HIS")
    

def getMoisture(addr, bus):
    mois = bus.read_word_data(addr, 0)
    return (mois >> 8) + ((mois & 0xFF) << 8)

try: 
    while True:
        for i in range(len(addr)):
            moist = getMoisture(addr[i],i2cbus)
            print("Sensor",i,"is",moist)
            if moist < minval[i]:
                minval[i] = moist
            if moist > maxval[i]:
                maxval[i] = moist
            
except KeyboardInterrupt:  
    print ("exiting program and saving max and min values" )
    print (minval[0],minval[1],minval[2],minval[3])
    print (maxval[0],maxval[1],maxval[2],maxval[3])

    with open('settingsMSensor.csv', 'wb') as csvfile:
        spamwriter = csv.writer(csvfile, delimiter=',',quotechar='"', quoting=csv.QUOTE_MINIMAL)
        spamwriter.writerow(minval)
        spamwriter.writerow(maxval)
    print("values saved")
    with open('/home/pi/.HIS/settingsMSensor.csv', 'wb') as csvfile:
        spamwriter = csv.writer(csvfile, delimiter=',',quotechar='"', quoting=csv.QUOTE_MINIMAL)
        spamwriter.writerow(minval)
        spamwriter.writerow(maxval)
    print("values saved2")

finally:  
    print ("done")
