#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat May  2 18:38:39 2020

@author: janguth
"""
from smbus2 import SMBus
from time import sleep

i2cbus = SMBus(1)

addr = [0x20,0x21,0x30,0x31]


def getMoisture(addr, bus):
    mois = bus.read_word_data(addr, 0)
    return (mois >> 8) + ((mois & 0xFF) << 8)

while True:
    for a in addr:
        print("Sensor",a,"is",getMoisture(a,i2cbus))
    sleep(5)