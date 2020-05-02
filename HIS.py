import RPi.GPIO as GPIO
import time
from time import sleep
import sys
import os
from apscheduler.schedulers.background import BackgroundScheduler
import apscheduler.events

os.chdir(os.path.dirname(__file__))

from smbus2 import SMBus
i2cbus = SMBus(1)

addr = [0x20,0x21,0x30,0x31]

targetMoisture = [300, 300, 300, 300]

runPumpSec = 20

def ap_my_listener(event):
        if event.exception:
              print (event.exception)
              print (event.traceback)


def log(text):
    print(text)
    


# GPIO setup
GPIO.cleanup()
GPIO.setmode(GPIO.BCM) # GPIO Numbers instead of board numbers
GPIOPins = [4,17,27,22,10,9,11,8]

powerOutletPins = [GPIOPins[0], GPIOPins[1]]
pumpPin = powerOutletPins[0]
valvePins = [GPIOPins[2], GPIOPins[3],GPIOPins[4],GPIOPins[5]]

USTriggerPin = 14
USEchoPin = 15

for i in GPIOPins:
    
        GPIO.setup(i, GPIO.OUT) # GPIO Assign mode
        GPIO.output(i, GPIO.LOW) #


GPIO.setup(USTriggerPin,GPIO.OUT)
GPIO.setup(USEchoPin,GPIO.IN)
GPIO.output(USTriggerPin, False)


log("Waiting For Everything To Settle")

sleep(2)

def openValve(pin):
    GPIO.output(pin, GPIO.HIGH)

def closeAllValves():
    GPIO.output(pumpPin, GPIO.LOW)
    for pin in valvePins:
        GPIO.output(pin, GPIO.LOW)

def runPump(time):
    GPIO.output(pumpPin, GPIO.HIGH)
    sleep(time)
    GPIO.output(pumpPin, GPIO.LOW)

def getMoisture(addr, bus):
    mois = bus.read_word_data(addr, 0)
    return (mois >> 8) + ((mois & 0xFF) << 8)

def getTemp(addr, bus):
    temp = bus.read_word_data(addr, 5)
    return (temp >> 8) + ((temp & 0xFF) << 8)

def resetSens(addr, bus):
    bus.write_byte(addr, 6)


def checkAndWater():
    #get mosisture 3x and average it out
    moistureArray = []
    wateringNeeded = False
    for i in range(addr.count):     
        average = 0.0
        for i in range(5):
            average = getMoisture(addr[i], i2cbus)/5
            sleep(2)
        moistureArray.append(average)
        log("Current moisture for "+str(hex(addr[i]))+"("+str(i)+"): " + str(average))

        if average < targetMoisture[i]:
            wateringNeeded = True
            openValve(valvePins[i])
            log("Opening Valve " + str(i))
            
    
    if wateringNeeded:
        log("Waiting for Valves to open fully")
        sleep (10)
        runPump(runPumpSec)
        sleep(5)
        closeAllValves()
    
        

        
    
        


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
    log("Distance: "+ distance + "cm")
    return distance
    
if __name__ == "__main__":
    scheduler = BackgroundScheduler()
    scheduler.add_listener(ap_my_listener, apscheduler.events.EVENT_JOB_ERROR)
    
    scheduler.add_job(checkAndWater, 'interval', minutes=1)

    #measure()




    try: 
        
        while True:
            time.sleep(10.0)
                

    except KeyboardInterrupt:  
        print ("exiting program" )

  
    finally:  
        closeAllValves()
        GPIO.cleanup()
        print ("done")
