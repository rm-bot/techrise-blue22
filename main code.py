# import required modules and libraries
import os
import trsim_blue
import board
import time
import storage
import busio
import digitalio
import adafruit_sdcard
import adafruit_vl6180x
from adafruit_ms8607 import MS8607
from adafruit_motor import stepper
from analogio import AnalogIn

# Set up simulator library
TRsim = trsim_blue.Simulator()

# Variables for tracking events
curr_events = ''
prev_events = ''

# Variable for tracking number of full telemetry packets received
num_packets = 0

# Variables for electronic components
stepper_on = False
LEDs_on = False
cam_on = False
distance_on = False
temp_on = False
pressure_on = False

# Values to print
distance_data = ""
temp_data = ""
pressure_out_data = ""
pressure_data = ""

# Set up solenoid
dc1 = digitalio.DigitalInOut(board.D5)
dc2 = digitalio.DigitalInOut(board.D4)
pwma = digitalio.DigitalInOut(board.D3)
pwma.direction = digitalio.Direction.OUTPUT
dc1.direction = digitalio.Direction.OUTPUT
dc2.direction = digitalio.Direction.OUTPUT

pwma.value = True
dc1.value = False

# Initialize motor
DELAY = 0.01
STEPS = 900

coils = (
    digitalio.DigitalInOut(board.D6),  # IN1
    digitalio.DigitalInOut(board.D7),  # IN2
    digitalio.DigitalInOut(board.D8),  # IN3
    digitalio.DigitalInOut(board.D9),  # IN4
)

for coil in coils:
    coil.direction = digitalio.Direction.OUTPUT

motor = stepper.StepperMotor(coils[0], coils[1], coils[2], coils[3], microsteps=None)

# Set up LED pin
led = digitalio.DigitalInOut(board.D11)
led.direction = digitalio.Direction.OUTPUT

led2 = digitalio.DigitalInOut(board.D12)
led2.direction = digitalio.Direction.OUTPUT

# Set up camera pin
cam_trig = digitalio.DigitalInOut(board.D10)
cam_trig.direction = digitalio.Direction.OUTPUT

cam_trig.value = True

# Create I2C bus
i2c = busio.I2C(board.SCL, board.SDA)

# Create sensor instances
distance_sensor = adafruit_vl6180x.VL6180X(i2c)
temp_sensor = MS8607(i2c)

# Set up pressure sensor pin
pressure_analog_in = AnalogIn(board.A1)

# Use any pin that is not taken by SPI
SD_CS = board.D13

# Connect to the card and mount the filesystem.
spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
cs = digitalio.DigitalInOut(SD_CS)
sdcard = adafruit_sdcard.SDCard(spi, cs)
vfs = storage.VfsFat(sdcard)
storage.mount(vfs, "/sd")

# Get voltage from analog pin
def get_voltage(pin):
    return (pin.value * 5.0) / 65536.0

"""def print_directory(path, tabs=0):
    for file in os.listdir(path):
        stats = os.stat(path + "/" + file)
        filesize = stats[6]
        isdir = stats[0] & 0x4000

        if filesize < 1000:
            sizestr = str(filesize) + " by"
        elif filesize < 1000000:
            sizestr = "%0.1f KB" % (filesize / 1000)
        else:
            sizestr = "%0.1f MB" % (filesize / 1000000)

        prettyprintname = ""
        for _ in range(tabs):
            prettyprintname += "   "
        prettyprintname += file
        if isdir:
            prettyprintname += "/"
        print('{0:<40} Size: {1:>10}'.format(prettyprintname, sizestr))

        # recursively print directory contents
        if isdir:
            print_directory(path + "/" + file, tabs + 1)"""

# START THE MAIN LOOP
while True:
    print("code running!")

    # Update to catch serial input. THIS MUST BE CALLED AT THE TOP OF THE LOOP
    TRsim.update()

    curr_events = TRsim.events
    if curr_events == trsim_blue.EVENT_COAST_START:
        solenoid_on = True
        stepper_on = True
        LEDs_on = True
        cam_on = True
        distance_on = True
        temp_on = True
        pressure_on = True

    if curr_events == trsim_blue.EVENT_COAST_END:
        LEDs_on = False
        cam_on = False
        distance_on = False
        temp_on = False
        pressure_on = False

    else:
        # the data stream has stopped for 1.5s, reset the current event to 0
        curr_events = ''

    if stepper_on:
        # open solenoid
        dc2.value = True

        # move motor
        for step in range(STEPS):
            motor.onestep(style=stepper.DOUBLE)
            time.sleep(DELAY)
        motor.release()
        stepper_on = False

        # close solenoid
        dc2.value = False

    if distance_on:
        range_mm = distance_sensor.range
        distance_data = "Distance: {0}mm".format(range_mm)

    if temp_on:
        temp = temp_sensor.temperature
        pressure_out = temp_sensor.pressure
        fahrenheit = temp * 1.8 + 32
        temp_data = "Temperature: %.2f C, %.2f F" % (temp, fahrenheit)
        pressure_out_data = "Pressure outside: %.2f hPa" % (pressure_out)
        # time.sleep(1)

    if LEDs_on:
        led.value = True
        led2.value = True
        # print("LEDs on")
    else:
        led.value = False
        led2.value = False

    if cam_on:
        cam_trig.value = False
        # executing a signal less than 250ms to trigger a photo (0.2sec = 200ms)
        # change to greater than 250ms to trigger a video
        time.sleep(0.3)
        cam_trig.value = True
    else:
        cam_trig.value = False

    if pressure_on:
        volts = get_voltage(pressure_analog_in)
        # print(analog_in.value)
        # print(volts)

        pressure_pascal = (3.47*(volts-0.46))*100000.0
        pressure_psi = pressure_pascal / 6894.76

        pressure_data = "Pressure = " + str(pressure_psi) + " psi\n"

    if distance_on:
        with open("/sd/data.txt", "w") as f:
            f.write("Sensor data:")
            f.write("\r\nDistance: " + distance_data)
            f.write("\r\nTemperature: " + temp_data)
            f.write("\r\nPressure outside: " + pressure_out_data)
            f.write("\r\nPressure in syringe: " + pressure_data)

        """with open("/sd/data.txt", "r") as f:
            print("Printing lines in file:")
            line = f.readline()
            while line != '':
                print(line)
                line = f.readline()"""

    # if i sleep will i miss the event trigger? what if the loop is too long?
    # should i just do separate while loops?
    # time.sleep(1)

