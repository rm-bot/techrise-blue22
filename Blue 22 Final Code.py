# import required modules and libraries
import trsim_blue
import board
import time
import storage
import busio
import digitalio
import adafruit_sdcard
import adafruit_vl6180x
from adafruit_ms8607 import MS8607
from analogio import AnalogIn

# Set up simulator library
TRsim = trsim_blue.Simulator()

# Variables for tracking events
curr_events = ''
prev_events = ''

# Variable for tracking time
time_on = time.time()

# Variable for tracking number of full telemetry packets received
num_packets = 0

# Variable to track progress
has_run = False
finished_running = False
init_data = False

# Variables for electronic components
motors_on = False
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
dc1A = digitalio.DigitalInOut(board.D4)
dc2A = digitalio.DigitalInOut(board.D5)

# Set up motor
dc1B = digitalio.DigitalInOut(board.D6)
dc2B = digitalio.DigitalInOut(board.D7)

dc1A.direction = digitalio.Direction.OUTPUT
dc2A.direction = digitalio.Direction.OUTPUT
dc1B.direction = digitalio.Direction.OUTPUT
dc2B.direction = digitalio.Direction.OUTPUT

# Set up LED pin
led = digitalio.DigitalInOut(board.D11)
led.direction = digitalio.Direction.OUTPUT

led2 = digitalio.DigitalInOut(board.D12)
led2.direction = digitalio.Direction.OUTPUT

# Set up camera pin
cam_trig = digitalio.DigitalInOut(board.D9)
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
SD_CS = board.D2

# Connect to the card and mount the filesystem.
spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
cs = digitalio.DigitalInOut(SD_CS)
sdcard = adafruit_sdcard.SDCard(spi, cs)
vfs = storage.VfsFat(sdcard)
storage.mount(vfs, "/sd")

# Get voltage from analog pin
def get_pressure_psi(pin):
    volts = (pin.value * 5.0) / 65536.0
    pressure_pascal = (3.47*(volts-0.46))*100000.0
    return pressure_pascal / 6894.76

# Save intitial data
def save_initial_data(dist, temp, press_out, press_in):
    with open("/sd/data.txt", "a") as f:
        f.write("\n\n\nFinal Final Data :))\n\n\n")
        f.write("Time (s)" + "," + "Distance (mm)" + "," + "Temperature (C)" + "," +
                "Pressure Outside (hPa)" + "," + "Pressure Inside (psi)\n")
        clck = time.time() - time_on
        f.write("{}, {}, {}, {}, {}\n".format
                (clck, dist, temp, press_out, press_in))

# START THE MAIN LOOP
while True:

    # Update to catch serial input.
    TRsim.update()

    curr_events = TRsim.events
    num_packets += 1

    if finished_running:
        break

    if (not has_run) and (not finished_running):

        # Collect initial data
        if time.time() - time_on > 195 and not init_data:

            # Turn everything on
            distance_on = True
            temp_on = True
            pressure_on = True
            cam_on = True
            LEDs_on = True
            led.value = True
            led2.value = True

            # Get initial round of data
            if not init_data:
                save_initial_data(distance_sensor.range,
                                  temp_sensor.temperature,
                                  temp_sensor.pressure,
                                  get_pressure_psi(pressure_analog_in))
                init_data = True

            # Turn camera on
            cam_trig.value = False
            time.sleep(0.6)
            cam_trig.value = True

        # Microgravity reached - turn everything on
        time_now = time.time()
        if (curr_events == trsim_blue.EVENT_COAST_START) or (time_now - time_on >= 200):
            motors_on = True
            has_run = True

    # Microgravity end - turn everything off
    time_now = time.time()
    if has_run and (not finished_running):
        if (curr_events == trsim_blue.EVENT_COAST_END) or (time_now - time_on >= 385):
            LEDs_on = False
            cam_on = False
            distance_on = False
            temp_on = False
            pressure_on = False
            has_run = False
            finished_running = True

    # Turn motor and solenoid on
    if motors_on:
        # open solenoid
        dc1A.value = True

        # start motor
        dc1B.value = True

        time.sleep(16)

        # close solenoid
        dc1A.value = False

        # stop motor
        dc1B.value = False

        motors_on = False

    # turn LEDs on/off
    if not LEDs_on:
        led.value = False
        led2.value = False

    # turn camera off
    if not cam_on:
        cam_trig.value = False
        time.sleep(0.6)
        cam_trig.value = True
        time.sleep(3)
        cam_trig.value = False

    # Collect distance data
    if distance_on:
        range_mm = distance_sensor.range
        distance_data = "Distance: {0}mm".format(range_mm)

    # Collect temperature & pressure outside data
    if temp_on:
        temp = temp_sensor.temperature
        pressure_out = temp_sensor.pressure
        fahrenheit = temp * 1.8 + 32
        temp_data = "Temperature: %.2f C, %.2f F" % (temp, fahrenheit)
        pressure_out_data = "Pressure outside: %.2f hPa" % (pressure_out)

    # collect pressure sensor data
    if pressure_on:
        pressure_data = "Pressure = " + str(get_pressure_psi(pressure_analog_in))
        pressure_data += "psi\n"

    # Write data to SD card
    if has_run:
        if num_packets % 100 == 1:
            with open("/sd/data.txt", "a") as f:
                clck = time.time() - time_on
                f.write("{}, {}, {}, {}, {}\n".format
                        (clck, distance_data, temp_data,
                         pressure_out_data, pressure_data))
