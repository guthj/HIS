#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat May  9 18:20:56 2020

@author: guth
"""


distanceEmpty = 5.0
distanceFull = 50.0


savetyFromLooseMoistureSensor = True

debuglevel = 5 
# 0 none
# 1 error
# 2 notice (default)
# 3 info
# 4 debug
debugStr = ["None  :  ","Error :  ","Notice:  ","Info  :  ","Debug :  "]

runPumpSec = 20

enableAutomaticWatering = True

pathMoisture = '/home/pi/.HIS/settingsMoisture.csv'
pathUS = '/home/pi/.HIS/settingsUS.csv'
pathSensor = '/home/pi/.HIS/settingsMSensor.csv'