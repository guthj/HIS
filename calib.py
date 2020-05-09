#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat May  2 18:38:39 2020

@author: guth
"""
from smbus2 import SMBus
#from time import sleep
import csv

i2cbus = SMBus(1)

addr = [0x20,0x21,0x30,0x31]

minval = [999,999,999,999]
maxval = [0,0,0,0]


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
    with open('settingsMSensor.csv', 'wb') as csvfile:
        spamwriter = csv.writer(csvfile, delimiter=',',quotechar='"', quoting=csv.QUOTE_MINIMAL)
        spamwriter.writerow(minval)
        spamwriter.writerow(maxval)
    print("values saved")


finally:  
    print ("done")
