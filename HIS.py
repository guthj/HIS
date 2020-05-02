import RPi.GPIO as GPIO
import time
GPIO.cleanup()
GPIO.setmode(GPIO.BCM) # GPIO Numbers instead of board numbers
GPIOPins = [4,17,27,22,10,9,11,8]

for i in GPIOPins:
    
        GPIO.setup(i, GPIO.OUT) # GPIO Assign mode
        GPIO.output(i, GPIO.LOW) #

TRIG = 14

ECHO = 15

GPIO.setup(TRIG,GPIO.OUT)

GPIO.setup(ECHO,GPIO.IN)
GPIO.output(TRIG, False)

print ("Waiting For Sensor To Settle")

time.sleep(2)


def playRelay():

    
    time.sleep(1)
    for i in GPIOPins:
    
        GPIO.output(i, GPIO.HIGH) # out
        time.sleep(1)
        GPIO.output(i, GPIO.LOW) # on
        time.sleep(1)

def measure():
    GPIO.output(TRIG, True)

    time.sleep(0.00001)

    GPIO.output(TRIG, False)
    while GPIO.input(ECHO)==0:

        pulse_start = time.time()

    while GPIO.input(ECHO)==1:

        pulse_end = time.time() 

    pulse_duration = pulse_end - pulse_start

    distance = pulse_duration * 17150

    distance = round(distance, 2)

    print ("Distance:",distance,"cm")

playRelay()
#measure()

GPIO.cleanup()
