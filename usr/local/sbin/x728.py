#!/usr/bin/env python3
import struct
import smbus
import sys
import time
from time import sleep
import os
import io
import RPi.GPIO as GPIO

# General Options
SLEEP_INTERVAL = 5  # (seconds) How often we check all the things
BATTERY_LOW_THRESHOLD = 15 # Shutdown when battery percentage is this low
AC_DETECT_PIN = 6 # AC Power Loss Detection GPIO Pin
AC_ON = 0 # Status of AC Power: 0 = CONNECTED, 1 = DISCONNECTED
SHUTDOWN_PIN = 5 # Shutdown signal from x728 button press
REBOOT_PULSE_MIN = 600 # How many milliseconds of shutdown signal for REBOOT
REBOOT_PULSE_MAX = 900 # How many milliseconds of shutdown signal for SHUTDOWN
BOOT_PIN = 12 # ? Reboot pin ? unknown use
POWEROFF_PIN = 13 # Output pin to tell x728 we are shutting down
POWEROFF_PIN_DELAY = 4 # How long to hold POWEROFF_PIN

# Cooling Fan Options
FAN_ENABLED = 1 # Set to 0 if you don't have a fan
FAN_ON_THRESHOLD = 45  # (degrees Celsius) Fan kicks on at this temperature
FAN_OFF_THRESHOLD = 40  # (degress Celsius) Fan shuts off at this temperature
FAN_PIN = 17  # Which GPIO pin you're using to control the fan
FAN_ON = 0 # Status of the fan

# Setup the GPIOs
GPIO.setmode(GPIO.BCM) # Use BCM GPIO pin mapping
GPIO.setwarnings(False) # Turn off GPIO warnings
if (FAN_ENABLED):
    GPIO.setup(FAN_PIN, GPIO.OUT)
GPIO.setup(AC_DETECT_PIN, GPIO.IN)
GPIO.setup(SHUTDOWN_PIN, GPIO.IN)
GPIO.setup(POWEROFF_PIN, GPIO.OUT)

# https://stackoverflow.com/a/181654
# reopen stdout file descriptor with write mode
# and 0 as the buffer size (unbuffered)
try:
    # Python 3, open as binary, then wrap in a TextIOWrapper with write-through.
    sys.stdout = io.TextIOWrapper(open(sys.stdout.fileno(), 'wb', 0), write_through=True)
    # If flushing on newlines is sufficient, as of 3.7 you can instead just call:
    # sys.stdout.reconfigure(line_buffering=True)
except TypeError:
    # Python 2
    sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)

def millis_time():
    return round(time.time() * 1000)

def ac_loss_callback(channel):
    global AC_ON
    if GPIO.input(AC_DETECT_PIN):
        # if AC_DETECT_PIN == 1
        AC_ON = 1
        print("AC Power Loss, Battery Voltage: {:.2f}V, Capacity: {:.0f}%".format(readVoltage(i2cbus), readCapacity(i2cbus)))
    else:
        # if AC_DETECT_PIN == 0
        AC_ON = 0
        print("AC Power OK, Battery Voltage: {:.2f}V, Capacity: {:.0f}%".format(readVoltage(i2cbus), readCapacity(i2cbus)))

def shutdown_callback(channel):
	print("Shutdown button press")
	pulseStart = millis_time()
	while ( GPIO.input(SHUTDOWN_PIN) ):
		sleep(0.2)
		timeDiff = millis_time() - pulseStart
		print("Waiting for release:{}".format(timeDiff))
		if (millis_time() - pulseStart > REBOOT_PULSE_MAX):
			print("X728 Shutting down, halting Rpi ...")
			os.system("/sbin/poweroff")
			return
	if (millis_time() - pulseStart > REBOOT_PULSE_MIN):
		print("X728 Rebooting, restarting Rpi ...")
		os.system("/sbin/reboot")
		return
	return

def get_temp():
    f = open("/sys/class/thermal/thermal_zone0/temp", "r")
    CPUtemp = f.read(2)
    f.close()
    try:
        #print(CPUtemp + "C")
        return int(CPUtemp)
    except (IndexError, ValueError):
        raise RuntimeError('Could not parse temperature output.')

def readVoltage(bus):
     address = 0x36
     read = bus.read_word_data(address, 2)
     swapped = struct.unpack("<H", struct.pack(">H", read))[0]
     voltage = swapped * 1.25 /1000/16
     return voltage

def readCapacity(bus):
    address = 0x36
    read = bus.read_word_data(address, 4)
    swapped = struct.unpack("<H", struct.pack(">H", read))[0]
    capacity = swapped/256
    # sometimes capacity is reported over 100%, just make
    # it 100 or the actual value if below
    if ( capacity > 100 ):
        return 100
    else:
        return capacity

if __name__ == '__main__':
    # Validate the on and off thresholds
    if (FAN_OFF_THRESHOLD >= FAN_ON_THRESHOLD) and (FAN_ENABLED):
        raise RuntimeError('OFF_THRESHOLD must be less than ON_THRESHOLD')

    i2cbus = smbus.SMBus(1) # 0 = /dev/i2c-0 (port I2C0), 1 = /dev/i2c-1 (port I2C1)
    GPIO.add_event_detect(AC_DETECT_PIN, GPIO.BOTH, callback=ac_loss_callback)
    GPIO.add_event_detect(SHUTDOWN_PIN, GPIO.RISING, callback=shutdown_callback)
    lastCheck = 0; # Keep track of when we last checked all the things

    AC_ON = GPIO.input(AC_DETECT_PIN) # Get AC adapter status
    print("x728 service started, Battery Voltage: {:.2f}V, Capacity: {:.0f}%".format(readVoltage(i2cbus), readCapacity(i2cbus)))

    if (FAN_ENABLED):
        GPIO.output(FAN_PIN,False) # Start with fan off
    GPIO.output(POWEROFF_PIN,False) # Poweroff pin low
    while True:
        if (time.time() >= lastCheck):
            lastCheck = time.time() + SLEEP_INTERVAL
            # Fan Control
            if ((get_temp() >= FAN_ON_THRESHOLD) and (FAN_ON == 0) and (FAN_ENABLED)):
                GPIO.output(FAN_PIN,True)
                FAN_ON = 1
                print("CPU Temp " + format(get_temp()) + "C, Fan ON")
            elif ((get_temp() <= FAN_OFF_THRESHOLD) and (FAN_ON == 1) and (FAN_ENABLED)):
                GPIO.output(FAN_PIN,False)
                FAN_ON = 0
                print("CPU Temp " + format(get_temp()) + "C, Fan OFF")
            # Power loss, monitor battery capacity and shutdown when low
            if ( AC_ON > 0 ):
                if (readCapacity(i2cbus) <= BATTERY_LOW_THRESHOLD):
                    print("Battery capacity below threshold, shutting down...")
                    GPIO.output(POWEROFF_PIN,True)
                    sleep(POWEROFF_PIN_DELAY)
                    GPIO.output(POWEROFF_PIN,False)
