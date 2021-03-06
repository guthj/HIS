#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

@author: guth
"""


import RPi.GPIO as GPIO
import time
from time import sleep
#import sys
import os
from apscheduler.schedulers.background import BackgroundScheduler
#import apscheduler.events
import csv
import paho.mqtt.client as mqtt
import gvar

os.chdir(os.path.dirname(__file__))

from smbus2 import SMBus
i2cbus = SMBus(1)

addr = [0x20,0x21,0x30,0x31]

sensorMin=[]
sensorMax=[]
targetMoisture=[]

for add in addr:
    sensorMin.append(200)
    sensorMax.append(500)
    targetMoisture.append(60)


# GPIO setup
GPIO.cleanup()
GPIO.setmode(GPIO.BCM) # GPIO Numbers instead of board numbers
GPIOPins = [4,17,27,22,10,9,11,8]

powerOutletPins = [GPIOPins[6], GPIOPins[7]]
pumpPin = GPIOPins[7]
valvePins = [GPIOPins[0], GPIOPins[1],GPIOPins[2],GPIOPins[3]]

USTriggerPin = 24
USEchoPin = 23

for i in GPIOPins:
    
        GPIO.setup(i, GPIO.OUT) # GPIO Assign mode
        GPIO.output(i, GPIO.HIGH) #


GPIO.setup(USTriggerPin,GPIO.OUT)
GPIO.setup(USEchoPin,GPIO.IN)
GPIO.output(USTriggerPin, False)





#Setup MQTT:
def on_connect(client, userdata, flags, rc):
    print("Connected with result code "+str(rc))
    if rc == 0:
        print("-> This means we connected successfully")
        log("Connection to server successfull",2)
    else:
        print("Major connection error")
        raise SystemExit

    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    
    for i in range(len(addr)):
        client.subscribe("HIS/Plant"+str(i)+"/Pump/setOn")
        client.subscribe("HIS/Plant"+str(i)+"/WaterTarget/setIncrease")
        client.subscribe("HIS/Plant"+str(i)+"/WaterTarget/setDecrease")
    
    client.subscribe("HIS/enableAutomaticWatering/setOn")


def on_message(client, userdata, msg):
    print(msg.topic+" "+str(msg.payload))
    
    #CHECK FOR PLANT SPECIFIC MESSAGES
    for i in range(len(addr)):
        plant = "Plant" + str (i)
        if msg.topic == "HIS/"+plant+"/Pump/setOn":
            if msg.payload == "true":
                client.publish("HIS/"+plant+"/Pump/getOn", "true")
                log("Turned on water on "+plant+" via MQTT",2)
                forceWaterPlant(i,gvar.runPumpSec)
            if msg.payload == "false":
                client.publish("HIS/"+plant+"/Pump/getOn", "false")
                closeAllValves()


        if msg.topic == "HIS/"+plant+"/WaterTarget/setIncrease":
            targetMoisture[i] +=1
            client.publish("HIS/"+plant+"/WaterTarget/Target", targetMoisture[i])
            writeNewTargetMoistures()
        if msg.topic == "HIS/"+plant+"/WaterTarget/setDecrease":
            targetMoisture[i] -= 1
            client.publish("HIS/"+plant+"/WaterTarget/Target", targetMoisture[i])
            writeNewTargetMoistures()
            
    if msg.topic == "HIS/enableAutomaticWatering/setOn":
        if msg.payload == "true":
            client.publish("HIS/enableAutomaticWatering/getOn", "true")
            gvar.enableAutomaticWatering = True
            log("Tried turning on enableAutomaticWatering, new State: " + str (gvar.enableAutomaticWatering),2)
        if msg.payload == "false":
            client.publish("HIS/enableAutomaticWatering/getOn", "false")
            gvar.enableAutomaticWatering = False
            log("tried turning off enableAutomaticWatering, new State: " + str (gvar.enableAutomaticWatering),2)


def log(text, level):
    if level <= gvar.debuglevel:
        print(gvar.debugStr[level]+text)
        client.publish("HIS/Log", gvar.debugStr[level]+text)       
        
def convertMtoPerc(sensor, value):
    return int((value - sensorMin[sensor])*100/(sensorMax[sensor]-sensorMin[sensor]))

def forceWaterPlant(plant, time):
    openValve(valvePins[plant])
    sleep(3)
    runPump(time)
    closeAllValves()

def openValve(pin):
    GPIO.output(pin, GPIO.LOW)

def closeAllValves():
    GPIO.output(pumpPin, GPIO.HIGH)
    for pin in valvePins:
        GPIO.output(pin, GPIO.HIGH)
    log("Closed all Relays",2)


def runPump(time):
    log("Starting Pump",2)
    GPIO.output(pumpPin, GPIO.LOW)
    sleep(time)
    GPIO.output(pumpPin, GPIO.HIGH)
    log("Stopping Pump",2)


def getMoisture(addr, bus):
    mois = bus.read_word_data(addr, 0)
    return (mois >> 8) + ((mois & 0xFF) << 8)

def getTemp(addr, bus):
    temp = bus.read_word_data(addr, 5)
    return (temp >> 8) + ((temp & 0xFF) << 8)

def resetSens(addr, bus):
    bus.write_byte(addr, 6)


def checkAndWater():
    #fist check if water in tank:
    percTank = getPercFullTank()
    log("Tank " + str(percTank) + "% full",2)
    if percTank >100:
        percTank = 100
    if percTank <0:
        percTank = 0
    client.publish("HIS/Reservoir/Percentage", int(percTank))
    alarmTankEmpty = False
    if percTank <= 5:
        gvar.alarmTankEmpty = True
        log("Tank empty, sending alarm soon, trying to water anyway",1)
    

    
    
    #get mosisture 5x and average it out
    moistureArray = []
    wateringNeeded = False
    for i in range(len(addr)):     
        average = 0.0
        for i2 in range(5):
            moist = getMoisture(addr[i], i2cbus)
            log("Measurement "+str(i2) + " for Sensor " + str(i)+ ": " +str(moist)+" ("+str(convertMtoPerc(i,moist))+"%)",4)
            average += float(moist)/5
            #sleep(2)
        average = int(average)
        moistureArray.append(average)
        log("Current moisture for "+str(hex(addr[i]))+"("+str(i)+"): " + str(average)+" ("+str(convertMtoPerc(i,moist))+"%)",3)
        
        percMoisture = convertMtoPerc(i,average)
        client.publish("HIS/Plant"+str(i)+"/Moisture", int(percMoisture))
        client.publish("HIS/Plant"+str(i)+"/WaterTarget/Target", int(targetMoisture[i]))
        client.publish("HIS/Plant"+str(i)+"/WaterTarget/getDecrease", "false")
        client.publish("HIS/Plant"+str(i)+"/WaterTarget/getIncrease", "false")
        if percMoisture < targetMoisture[i]-5:
            gvar.alarmMoistureLow = True
            
        if percMoisture < targetMoisture[i] and gvar.enableAutomaticWatering:
            if (percMoisture > 10) or (gvar.savetyFromLooseMoistureSensor == False):
                wateringNeeded = True
                openValve(valvePins[i])
                log("Opening Valve " + str(i),2)
            else:
                log("Earth too dry, is Moisture Sensor correctly entered?",1)
                log("Will therefore not water!!!",1)
        #sleep for nicer sound
        sleep(1)
    
    if wateringNeeded and gvar.enableAutomaticWatering:
        log("Waiting for Valves to open fully", 2)
        sleep (10)
        runPump(gvar.runPumpSec)
        sleep(5)
        closeAllValves()
    
    #ALARMS
    if gvar.alarmTankEmpty and gvar.alarmTankEmptyDidAlarm == False:
        client.publish("HIS/MotionSensor/Alarm/Water", "true")
        time.sleep(3)
        client.publish("HIS/MotionSensor/Alarm/Water", "false")
        gvar.alarmTankEmptyDidAlarm = True
 
    if gvar.alarmMoistureLow and gvar.alarmMoistureLowDidAlarm == False:
        sleep(10)
        client.publish("HIS/MotionSensor/Alarm/Moisture", "true")
        time.sleep(3)
        client.publish("HIS/MotionSensor/Alarm/Moisture", "false")
        gvar.alarmTankEmptyDidAlarm = True
    
        
def measureUS():
    GPIO.output(USTriggerPin, True)

    sleep(0.00001)

    GPIO.output(USTriggerPin, False)
    while GPIO.input(USEchoPin)==0:

        pulse_start = time.time()

    while GPIO.input(USEchoPin)==1:

        pulse_end = time.time() 

    pulse_duration = pulse_end - pulse_start
    distance = pulse_duration * 17150
    distance = round(distance, 2)
    return distance

def getPercFullTank():
    distanceA = []
    log("Measuring Waterlevel (should be between " +str(gvar.distanceEmpty)+" and "+str(gvar.distanceFull)+"cm )",2)
    for i in range(10):
        distance = measureUS()
        log("Measured Distance " + str(distance)+ "cm",4)
        distanceA.append(distance)
        sleep(1)
    if max(distanceA)-min(distanceA)>3:
        log("Discard " + str(max(distanceA)) + " and " + str(min(distanceA)),3)
        distanceA.remove(max(distanceA))
        distanceA.remove(min(distanceA))
    averageDist = 0
    for a in distanceA:
        averageDist += a/len(distanceA)
    log("Average distance is " + str(averageDist)+ "cm",2)
        
    return int(gvar.distanceEmpty - averageDist)*100/(gvar.distanceEmpty-gvar.distanceFull)

def writeNewTargetMoistures():
    with open(gvar.pathMoisture, 'w') as csvfile:
        csvwriter = csv.writer(csvfile, delimiter=',',quotechar='"', quoting=csv.QUOTE_MINIMAL)
        csvwriter.writerow(["Moisture"]+targetMoisture)
    log("values saved",2)

def resetAlarmSuppression():
    gvar.alarmTankEmptyDidAlarm = False
    gvar.alarmMoistureLowDidAlarm = False
    

def readSettingFiles():
    try:
        with open(gvar.pathMoisture) as csvDataFile:
            log("Setting Moisture Target Values",2)
            csvReader = csv.reader(csvDataFile)
            for row in csvReader:
                for i in range(1,len(row)):
                    log("Sens "+str(hex(addr[i-1]))+ " Target: "+ str(int(row[i])),3)
                    targetMoisture[i-1] = int(row[i])
    except:
        log("Unable to get Moisture Setting File",1)
        if not os.path.isfile(gvar.pathMoisture):
            writeNewTargetMoistures()
            
        

    try:
        with open(gvar.pathUS) as csvDataFile:
            log("Setting Distance Values for US",2)
            csvReader = csv.reader(csvDataFile)
            i=0
            for row in csvReader:
                if i == 0:
                    gvar.distanceEmpty = float(row[1])
                    log("Empty: " + row[1],3)
                else:
                    gvar.distanceFull = float(row[1])
                    log("Full: " + row[1],3)

                i += 1                  
    except:
        log("Unable to read US Settings File. Did you run calib.py?",1)

    try:
        with open(gvar.pathSensor) as csvDataFile:
            log("Setting Calib Vals for Moisture Sensors",2)
            csvReader = csv.reader(csvDataFile)
            rownumber=0
            for row in csvReader:
                for i in range(len(row)):
                    
                    if rownumber == 0:
                        sensorMin[i] = int(row[i])
                        log("Sens "+str(hex(addr[i]))+ " Min: "+ row[i],3)
                        

                    else:
                        sensorMax[i] = int(row[i])
                        log("Sens "+str(hex(addr[i]))+ " Max: "+ row[i],3)

                rownumber += 1
                    
    except:
        log("Unable to read Calib File for moisture Sensors. Did you run calib.py?",1)

if __name__ == "__main__":
    
        
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect("10.0.0.16", 1883, 60)
    client.loop_start()
    sleep(2)
    log("MQTT Started",2)
    log("Waiting For Everything To Settle",2)
    sleep (5)
    
    readSettingFiles()
    writeNewTargetMoistures()
    # Blocking call that processes network traffic, dispatches callbacks and
    # handles reconnecting.
    # Other loop*() functions are available that give a threaded interface and a
    # manual interface.


    scheduler = BackgroundScheduler()
    scheduler.start()
    scheduler.add_job(checkAndWater, 'interval', minutes=15)
    
    scheduler.add_job(resetAlarmSuppression, 'cron', hour=18, minute=0, second=0)

    
    try: 
        checkAndWater()
        while True:
            time.sleep(10.0)
                

    except KeyboardInterrupt:  
        print ("exiting program" )

  
    finally:  
        closeAllValves()
        GPIO.cleanup()
        print ("done")
