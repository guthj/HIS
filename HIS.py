import RPi.GPIO as GPIO
import time
from time import sleep
#import sys
import os
from apscheduler.schedulers.background import BackgroundScheduler
#import apscheduler.events
import csv
import paho.mqtt.client as mqtt


os.chdir(os.path.dirname(__file__))

distanceEmpty = 5
distanceFull = 50

from smbus2 import SMBus
i2cbus = SMBus(1)

addr = [0x20,0x21,0x30,0x31]

sensorMin=[]
sensorMax=[]
targetMoisture=[]

for add in addr:
    sensorMin.append(200)
    sensorMax.append(500)
    targetMoisture.append(300)

runPumpSec = 20

enableAutomaticWatering = True

debuglevel = 5 
# 0 none
# 1 error
# 2 notice (default)
# 3 info
# 4 debug
debugStr = ["None  :  ","Error :  ","Notice:  ","Info  :  ","Debug :  "]


#def ap_my_listener(event):
#        if event.exception:
#              print (event.exception)
#              print (event.traceback)


def log(text, level):
    if level <= debuglevel:
        print(debugStr[level]+text)
        client.publish("HIS/Log", debugStr[level]+text)

    


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

    client.subscribe("HIS/Plant0/Pump/setOn")
    client.subscribe("HIS/enableAutomaticWatering/setOn")
    client.subscribe("HIS/displayONMode/setOn")
    client.subscribe("HIS/runLEDs/setOn")
    client.subscribe("HIS/WaterTarget/setIncrease")
    client.subscribe("HIS/WaterTarget/setDecrease")

def on_message(client, userdata, msg):
    print(msg.topic+" "+str(msg.payload))
    
    #CHECK FOR PLANT SPECIFIC MESSAGES
    for i in range(len(addr)):
        plant = "Plant" + str (i)
        if msg.topic == "HIS/"+plant+"/Pump/setOn":
            if msg.payload == "true":
                client.publish("HIS/"+plant+"/Pump/getOn", "true")
                log("Turned on water on "+plant+" via MQTT",2)
                forceWaterPlant(i,runPumpSec)
            if msg.payload == "false":
                client.publish("HIS/"+plant+"/Pump/getOn", "false")
                closeAllValves()


        if msg.topic == "HIS/"+plant+"/WaterTarget/setIncrease":
            targetMoisture[i] +=1
            client.publish("HIS/"+plant+"/WaterTarget/Target", targetMoisture[i])
        if msg.topic == "HIS/"+plant+"/WaterTarget/setDecrease":
            targetMoisture[i] -= 1
            client.publish("HIS/"+plant+"/WaterTarget/Target", targetMoisture[i])
            
            
    if msg.topic == "HIS/enableAutomaticWatering/setOn":
        if msg.payload == "true":
            client.publish("HIS/enableAutomaticWatering/getOn", "true")
            enableAutomaticWatering = True
            log("Tried turning on enableAutomaticWatering, new State: " + str (enableAutomaticWatering),2)
        if msg.payload == "false":
            client.publish("HIS/enableAutomaticWatering/getOn", "false")
            enableAutomaticWatering = False
            log("tried turning off enableAutomaticWatering, new State: " + str (enableAutomaticWatering),2)

            
        
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

def runPump(time):
    GPIO.output(pumpPin, GPIO.LOW)
    sleep(time)
    GPIO.output(pumpPin, GPIO.HIGH)

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
    if percTank <= 5:
        alarmTankEmpty = True
        log("Tank empty, sending alarm soon, trying to water anyway",1)

    
    
    #get mosisture 5x and average it out
    moistureArray = []
    wateringNeeded = False
    for i in range(len(addr)):     
        average = 0.0
        for i2 in range(5):
            moist = getMoisture(addr[i], i2cbus)
            log("Measurement "+str(i2) + "for Sensor " + str(i)+ ": " +str(moist),4)
            average = moist/5
            #sleep(2)
        moistureArray.append(average)
        log("Current moisture for "+str(hex(addr[i]))+"("+str(i)+"): " + str(average),3)
        
        percMoisture = convertMtoPerc(i,average)

        if percMoisture < targetMoisture[i] and enableAutomaticWatering:
            wateringNeeded = True
            openValve(valvePins[i])
            log("Opening Valve " + str(i),2)
        #sleep for nicer sound
        sleep(1)
    
    if wateringNeeded and enableAutomaticWatering:
        log("Waiting for Valves to open fully", 2)
        sleep (10)
        runPump(runPumpSec)
        sleep(5)
        closeAllValves()
    
    #ALARMS
    if alarmTankEmpty:
        log("ALARM !! TANK EMPTY", 1)

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
    log("Distance: "+ str(distance) + "cm",4)
    return distance

def getPercFullTank():
    distanceA = []
    for i in range(10):
        distance = measureUS()
        log("Measured Distance " + str(distance),4)
        distanceA.append(distance)
        sleep(1)
    if max(distanceA)-min(distanceA)>3:
        log("Discard " + str(max(distanceA)) + " and " + str(min(distanceA)),3)
        distanceA.remove(max(distanceA))
        distanceA.remove(min(distanceA))
    averageDist = 0
    for a in distanceA:
        averageDist += a/len(distanceA)
    log("Average distance is " + str(averageDist),2)
        
    return (distanceEmpty - averageDist)*100/(distanceEmpty-distanceFull)

def readSettingFiles():
    try:
        with open('settingsMoisture.csv') as csvDataFile:
            log("Setting Moisture Target Values",2)
            csvReader = csv.reader(csvDataFile)
            for row in csvReader:
                for i in range(1,len(row)):
                    log("Sens "+str(hex(addr[i-1]))+ ": "+ row[i],2)
                    targetMoisture[i-1] = int(row[i])
    except:
        print("Unable to get Moisture Setting File",1)
        

    try:
        with open('settingsUS.csv') as csvDataFile:
            log("Setting Distance Values for US",2)
            csvReader = csv.reader(csvDataFile)
            i=0
            for row in csvReader:
                if i == 0:
                    distanceEmpty = float(row[1])
                else:
                    distanceFull = float(row[1])
                i += 1
                    
    except:
        log("Unable to read US Settings File",1)
    try:
        with open('settingsMSensor.csv') as csvDataFile:
            log("Setting Calib Vals for Moisture Sensors",2)
            csvReader = csv.reader(csvDataFile)
            rownumber=0
            for row in csvReader:
                for i in range(len(row)):
                    
                    if rownumber == 0:
                        sensorMin[i] = int(row[i])
                    else:
                        sensorMax[i] = int(row[i])
                rownumber += 1
                    
    except:
        log("Unable to read Calib File for moisture Sensors",1)
    
if __name__ == "__main__":
    
        
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect("10.0.0.16", 1883, 60)
    
    sleep (2)
    readSettingFiles()

    # Blocking call that processes network traffic, dispatches callbacks and
    # handles reconnecting.
    # Other loop*() functions are available that give a threaded interface and a
    # manual interface.
    client.loop_start()
    log("MQTT Started",2)
    
    log("Waiting For Everything To Settle",2)
    sleep(2)

    scheduler = BackgroundScheduler()
    scheduler.start()
    scheduler.add_job(checkAndWater, 'interval', minutes=2)
    
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
