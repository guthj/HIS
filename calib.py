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

os.chdir(os.path.dirname(__file__))
import gvar
import HIS

if not os.path.exists("/home/pi/.HIS"):
    os.makedirs("/home/pi/.HIS")
    

def getMoisture(addr, bus):
    mois = bus.read_word_data(addr, 0)
    return (mois >> 8) + ((mois & 0xFF) << 8)

x = input("Starting moisture measurements, during measurements dip the moisture sensors in water and let dry. To skip type n. CTRL+C to stop after finishing")
if not x == "n":
    try: 
        while True:
            for i in range(len(addr)):
                moist = getMoisture(addr[i],i2cbus)
                #print("Sensor",i,"is",moist)
                if moist < minval[i]:
                    minval[i] = moist
                if moist > maxval[i]:
                    maxval[i] = moist
            
    except KeyboardInterrupt:  
        print ("exiting program and saving max and min values" )
        print (minval[0],minval[1],minval[2],minval[3])
        print (maxval[0],maxval[1],maxval[2],maxval[3])

        with open('settingsMSensor.csv', 'w') as csvfile:
            spamwriter = csv.writer(csvfile, delimiter=',',quotechar='"', quoting=csv.QUOTE_MINIMAL)
            spamwriter.writerow(minval)
            spamwriter.writerow(maxval)
        print("values saved")
        with open(gvar.pathSensor, 'w') as csvfile:
            spamwriter = csv.writer(csvfile, delimiter=',',quotechar='"', quoting=csv.QUOTE_MINIMAL)
            spamwriter.writerow(minval)
            spamwriter.writerow(maxval)
        print("values saved2")
    finally:  
        print ("done")

x = input("Set watersensor on water tank w/o water, then press enter. write >n< to skip measurements")
if not x == "n":
    avDistanceE = 0.0
    for i in range (10):
        distance = HIS.measureUS()
        avDistanceE += distance/10

    y = input("Fill WaterTank, then press Enter")
    
    avDistanceF = 0.0
    for i in range (10):
        distance = gvar.measureUS()
        avDistanceF += distance/10
        
    with open(gvar.pathUS, 'w') as csvfile:
            spamwriter = csv.writer(csvfile, delimiter=',',quotechar='"', quoting=csv.QUOTE_MINIMAL)
            spamwriter.writerow(["Empty:"]+[avDistanceE])
            spamwriter.writerow(["Full :"]+[avDistanceF])
    print("values saved")
    
    
    
    
    