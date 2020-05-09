import RPi.GPIO as GPIO
import time
from time import sleep
#import sys
import os
from apscheduler.schedulers.background import BackgroundScheduler
#import apscheduler.events
import csv

os.chdir(os.path.dirname(__file__))

distanceEmpty = 0
distanceFull = 0

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

debuglevel = 5 
# 0 none
# 1 error
# 2 notice (default)
# 3 info
# 4 debug


#def ap_my_listener(event):
#        if event.exception:
#              print (event.exception)
#              print (event.traceback)


def log(text, level):
    if level <= debuglevel:
        print(text)
    


# GPIO setup
# GPIO.cleanup()
GPIO.setmode(GPIO.BCM) # GPIO Numbers instead of board numbers
GPIOPins = [4,17,27,22,10,9,11,8]

powerOutletPins = [GPIOPins[6], GPIOPins[7]]
pumpPin = GPIOPins[7]
valvePins = [GPIOPins[0], GPIOPins[1],GPIOPins[2],GPIOPins[3]]

USTriggerPin = 14
USEchoPin = 15

for i in GPIOPins:
    
        GPIO.setup(i, GPIO.OUT) # GPIO Assign mode
        GPIO.output(i, GPIO.HIGH) #


GPIO.setup(USTriggerPin,GPIO.OUT)
GPIO.setup(USEchoPin,GPIO.IN)
GPIO.output(USTriggerPin, False)


log("Waiting For Everything To Settle",2)

sleep(2)

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

        if average < targetMoisture[i]:
            wateringNeeded = True
            openValve(valvePins[i])
            log("Opening Valve " + str(i),2)
        #sleep for nicer sound
        sleep(1)
    
    if wateringNeeded:
        log("Waiting for Valves to open fully", 2)
        sleep (10)
        runPump(runPumpSec)
        sleep(5)
        closeAllValves()
    
    #ALARMS
    if alarmTankEmpty:
        log("ALARM !! TANK EMPTY", 1)
    
def playRelay():

    
    sleep(1)
    for i in GPIOPins:
    
        GPIO.output(i, GPIO.HIGH) # out
        sleep(1)
        GPIO.output(i, GPIO.LOW) # on
        sleep(1)

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
    log("Distance: "+ distance + "cm",4)
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
    
if __name__ == "__main__":
    scheduler = BackgroundScheduler()
    scheduler.start()
    scheduler.add_job(checkAndWater, 'interval', minutes=2)
    
    try:
        with open('settingsMoisture.csv') as csvDataFile:
            log("Setting Moisture Target Values",2)
            csvReader = csv.reader(csvDataFile)
            for row in csvReader:
                for cell in range(1,len(row)):
                    log("Sens "+str(hex(addr[i-1]))+ ": "+ cell)
                    targetMoisture[i-1] = int(row[cell])
    except:
        print("Unable to get Moisture Setting File",1)
    try:
        with open('settingsUS.csv') as csvDataFile:
            log("Setting Distance Values for US")
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
            log("Setting Calib Vals for Moisture Sensors")
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
        log("Unable to read Calib File for Moisture Sensors",1)


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
