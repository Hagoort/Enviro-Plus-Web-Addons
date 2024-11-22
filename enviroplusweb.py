# -*- coding: utf-8 -*-

"""
Project: Enviro Plus Web
Description: Web interface for Enviro and Enviro+ sensor board plugged into a Raspberry Pi.
Author: i.j
URL: https://gitlab.com/idotj/enviroplusweb
Forked from: https://github.com/nophead/EnviroPlusWeb
License: GNU
"""

"""
Add-on Free OpenWeather winddirection and -speed
Add-on Turn PMS5003 sensor on/off between readings to extend sensor lifetime
Add-on Dewpoint
Add-on Wind chill and Heat index
Author: Hagoort
URL: https://github.com/Hagoort/Enviro-Plus-Web
Add-ons for: https://gitlab.com/idotj/enviroplusweb
"""

"""
Instructions Add OpenWeatherMap winddirrection and -speed
Get your free API key: https://home.openweathermap.org/users/sign_up and read: https://openweathermap.org/appid
Fill in your info:
    API_KEY = "Your API-KEY"
    LAT = Your latitude
    LON = Your longitude
"""

"""
Instructions Turn PMS5003 sensor on/off between readings to extend sensor lifetime using Python's serial library
The serial port shouldn't be used by other processes. Disable Bluetooth and use the UART for PMS5003 Control. Edit the /boot/config.txt file:
    sudo nano /boot/config.txt
Add or ensure that the following lines are present and comment out #dtoverlay=pi3-miniuart-bt:
    enable_uart=1
    dtoverlay=pi3-disable-bt  # This disables Bluetooth and frees up the UART
Now the UART is available for communicating with the PMS5003 sensor. Reboot the Pi to apply changes:
    sudo reboot
"""

import RPi.GPIO as IO
import st7735
from fonts.ttf import RobotoMedium as UserFont
from PIL import Image, ImageDraw, ImageFont
from enviroplus.noise import Noise
from enviroplus import gas
from bme280 import BME280
from smbus2 import SMBus
try:
    from ltr559 import LTR559
    ltr559 = LTR559()
except ImportError:
    import ltr559
import logging
from flask import Flask, render_template, request
import os
import threading
import json
from math import ceil, floor
from time import sleep, time, asctime, localtime, strftime
import math

import requests
API_KEY = "Your API-KEY" # Your API-KEY
LAT = Your latitude  # Your latitude
LON = Your longitude  # Your longitude
URL = f"http://api.openweathermap.org/data/2.5/weather?lat={LAT}&lon={LON}&appid={API_KEY}&units=metric"
# List to store the wind data for plotting
wind_speed_data = []
wind_direction_data = []
windspd = None
winddir = None
# If you want OpenWeatherMap wind speed or direction data to be displayed
OWMwind_speed = True
OWMwind_direction = True

import serial
import logging
pms5003 = serial.Serial('/dev/ttyAMA0', baudrate=9600, timeout=1)  # Set the correct port if different
pm1 = None

# If you prefer to keep the Enviro LCD screen off, change the next value to False
lcd_screen = False
# If you don't have a fan plugged on GPIO, change the next value to False
fan_gpio = False
# Temperature scale in Celsius (switch to false to show in Fahrenheit)
temp_celsius = True
# Temperature and humidity compensation (edit values 'factor_temp' and 'factor_humi' to adjust them)
temp_humi_compensation = True
# Compensates the temperature in relation to the cpu temperature (useful if you have the Enviro board directly connected to the Rpi)
temp_cpu_compensation = False
# If you have an Enviro board without gas sensor, change the next value to False
gas_sensor = True
# If you don't have a particle sensor PMS5003 attached, change the next value to False
particulate_sensor = True
# dewpoint
dewpoint = True
# windchill
windchill = True
# Can't have particle sensor without gas sensor
assert gas_sensor or not particulate_sensor
# BME280 temperature, humidity and pressure sensor
bus = SMBus(1)
bme280 = BME280(i2c_dev=bus)
# Noise sensor
noise = Noise()
# Folder to save the readings
app_data = 'enviroplusweb-data'
# App init
app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True
log = logging.getLogger('werkzeug')
log.disabled = True
run_flag = True
cpu_temps = []

pres_compensation = 3
hum_compensation = 12

# Configure the fan
if fan_gpio:
    IO.setmode(IO.BCM)
    IO.setup(4, IO.OUT)
    pwm = IO.PWM(4, 1000)
    pwm.start(100)

# Use temperature and humidity compensations to improve readings
if temp_humi_compensation:
    factor_temp = 0.43 # 3.10
    factor_humi = 1 # 1.50 1.315

    if temp_cpu_compensation:
        def get_cpu_temperature():
            with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                temp = f.read()
                temp = int(temp) / 1000.0
            return temp

        cpu_temps = [get_cpu_temperature()] * 5

# Create ST7735 LCD display class
if lcd_screen:
    disp = st7735.ST7735(
        port=0,
        cs=1,
        dc='GPIO9',
        backlight='GPIO12',
        rotation=270,
        spi_speed_hz=10000000
    )

    disp.begin()

    WIDTH = disp.width
    HEIGHT = disp.height

    color_above_threshold = (255, 0, 128)  # Magenta
    color_below_threshold = (64, 220, 220)  # Cyan
    color_within_threshold = (64, 220, 64)  # Green

    img = Image.new('RGB', (WIDTH, HEIGHT), color=(0, 0, 0))
    draw = ImageDraw.Draw(img)

    path = os.path.dirname(os.path.realpath(__file__)) + '/static/fonts'
    smallfont = ImageFont.truetype(path + '/asap/Asap-Bold.ttf', 10)
    x_offset = 2
    y_offset = 2
    unitTemp = '°C' if temp_celsius else '°F'

    units = [unitTemp,
             '%',
             'hPa',
             'Lux',
             'u',
             'u',
             'u',
             'u']

    if dewpoint:
        units += [
            '°C']

    if windchill:
        units += [
            '°C']

    if gas_sensor:
        units += [
            'kΩ',
            'kΩ',
            'kΩ']

    if particulate_sensor:
        units += [
            'μg/m3',
            'μg/m3',
            'μg/m3']

    if OWMwind_speed:
        units += [
            'km/h']

    if OWMwind_direction:
        units += [
            '°']

    def display_everything():
        draw.rectangle((0, 0, WIDTH, HEIGHT), (0, 0, 0))
        column_count = 2
        variables = list(record.keys())
        row_count = ceil(len(units) / column_count)
        last_values = days[-1][-1]
        for i in range(len(units)):
            variable = variables[i + 1]
            data_value = record[variable]
            last_value = last_values[variable]
            unit = units[i]
            x = x_offset + (WIDTH // column_count) * (i // row_count)
            y = y_offset + (HEIGHT // row_count) * (i % row_count)
            message = '{}: {:s} {}'.format(variable[:4], str(data_value), unit)
            tol = 1.01
            if data_value > last_value * tol:
                rgb = color_above_threshold
            elif data_value < last_value / tol:
                rgb = color_below_threshold
            else:
                rgb = color_within_threshold
            draw.text((x, y), message, font=smallfont, fill=rgb)
        disp.display(img)

# A function to fetch wind direction periodically
# This function is not triggered based on number of data readings or samples but every 600 seconds
def fetch_wind_data():
    global winddir
    global windspd
    while OWMwind_speed or OWMwind_direction:
        response = requests.get(URL)
        if response.status_code == 200:
            data = response.json()
            wind_speed = data['wind']['speed']  # Wind speed in m/s
            wind_direction = data['wind']['deg']  # Wind direction in degrees
            windspd = round(wind_speed * 3.6, 1)  # Wind speed in km/h
            winddir = wind_direction
            #print(f"Wind Speed: {windspd} km/h, Wind Direction: {winddir}°")
        else:
            print(f"Error fetching data: {response.status_code}")

        # Make an free API call no more than once in 10 minutes for your location otherwise you will be blocked
        # Also The update frequency of the OpenWeather model is not higher than once in 10 minutes
        # Sleep for 10 minutes/600 seconds before fetching data again
        sleep(600)

# Power on, off, reset and read functions for PMS5003
def power_on_pms5003():
    pms5003.write([0x42, 0x4D, 0xE4, 0x00, 0x01, 0x01, 0x74])  # Turn on sensor
    sleep(3)  # Sensor needs some time to turn on
    pms5003.reset_input_buffer()  # Clear the buffer to remove any residual data
    pms5003.write([0x42, 0x4D, 0xE2, 0x00, 0x00, 0x01, 0x71])  # Start read or start to continuously produce data by sensor

def power_off_pms5003():
    pms5003.write([0x42, 0x4D, 0xE4, 0x00, 0x00, 0x01, 0x73])  # Turn off sensor or switch to sleep mode

def reset_pms5003():
    pms5003.write([0x42, 0x4D, 0xE4, 0x00, 0x00, 0x01, 0x74])  # Reset sensor

def read_pms5003(): # Saves the last reading to a file (perhaps add rolling average of last 5 readings later)
    global pm1
    global pm25
    global pm10
    try:
        sleep(1) # Don't read the data too fast, wait to stabilize data (if needed)
        response = pms5003.read(32)  # Read 32 bytes (adjust as necessary based on your setup)

        # Check if the response is valid (length should be 32 bytes)
        if len(response) == 32:
            # Parse the particle readings (assuming the typical data format for PMS5003)
            pm1 = (response[4] << 8) + response[5]
            pm25 = (response[6] << 8) + response[7]
            pm10 = (response[8] << 8) + response[9]
            #print(f"PM1: {pm1}, PM2.5: {pm25}, PM10: {pm10}")
        else:
            print("Error: Invalid response length or corrupted data")

    except ReadTimeoutError:
        print("Read timeout error. Attempting to reinitialize PMS5003.")
        power_on_pms5003()  # Reinitialize sensor in case of timeout
    except RuntimeError as e:
        print('Particle read failed:', e.__class__.__name__)
        reset_pms5003()  # Reset sensor
        sleep(30)  # Wait before trying again
    except Exception as e:
        print(f"Unexpected error: {e}")
        # Continue to the next reading without halting the program

# A function to fetch pms data periodically and save the last reading (and not the average) to the file
# This function is not triggered based on number of data readings or samples but every 540 seconds
def fetch_pms_data():
    while particulate_sensor:
        # Turn on PMS5003 and take readings
        power_on_pms5003()

        # Take x number of readings in a loop
        for _ in range(30):  # Take x number of readings, adjust this based on your needs
            read_pms5003()  # Read the sensor

        # Turn off PMS5003 including its fan and wait for x-seconds
        power_off_pms5003()
        sleep(540)

# Get all sensors values
def read_data(time):
    global cpu_temps
    raw_temp = bme280.get_temperature()
    raw_humi = bme280.get_humidity()
    if temp_humi_compensation:
        if temp_cpu_compensation:
            cpu_temp = get_cpu_temperature()
            cpu_temps = cpu_temps[1:] + [cpu_temp]
            avg_cpu_temp = sum(cpu_temps) / float(len(cpu_temps))
            temperature_scaled = raw_temp - \
                ((avg_cpu_temp - raw_temp) / factor_temp)
            temperature = temperature_scaled if temp_celsius else temperature_scaled * 1.8 + 32
        else:
            temp_compensated = raw_temp * factor_temp
            temperature = temp_compensated if temp_celsius else temp_compensated * 1.8 + 32

        humidity = raw_humi * factor_humi + hum_compensation
    else:
        temperature = raw_temp if temp_celsius else raw_temp * 1.8 + 32
        humidity = bme280.get_humidity() + hum_compenstation

    pressure = bme280.get_pressure() + pres_compensation
    lux = ltr559.get_lux()
    low, mid, high, amp = noise.get_noise_profile()
    low *= 128
    mid *= 128
    high *= 128
    amp *= 64
    # Added dewpoint
    #dewpoint = (237.7 * (math.log(humidity/100)+17.271*temperature/(237.7+temperature))/(17.271 - math.log(humidity/100) - 17.271*temperature/(237.7 + temperature))) # Valid around sealevel

    dewpoint = (243.12 * math.log((humidity / 100) * (6.112 * math.exp((17.62 * temperature) / (243.12 + temperature)) * (pressure / 1013.25)) / 6.112)) / (17.62 - math.log((humidity / 100) * (6.112 * math.exp((17.62 * temperature) / (243.12 + temperature)) * (pressure / 1013.25)) / 6.112)) # Valid at sealevel and higher altitudes

    # Combine wind chill and heat index based on conditions
    # Wind Chill: U.S. National Weather Service, Wind Chill Guidelines
    # Heat Index: NOAA (National Oceanic and Atmospheric Administration) heat index formula
    if temperature <= 10 or windspd > 4.8:  # calculate wind chill
        windchill = 13.12 + 0.6215 * temperature - 11.37 * windspd**0.16 + 0.3965 * temperature * windspd**0.16  # Wind chill is the dominant factor
    elif temperature >= 26.7 and humidity >= 40:  # calculate heatindex
        windchill = 42.379 + 2.04901523 * temperature + 10.14333127 * humidity \
                     - 0.22475541 * temperature * humidity - 6.83783 * 10**-3 * temperature**2 \
                     - 5.481717 * 10**-2 * humidity**2 + 1.22874 * 10**-3 * temperature**2 * humidity \
                     + 8.5282 * 10**-4 * temperature * humidity**2 - 1.99 * 10**-6 * temperature**2 * humidity**2
    else:
        windchill = temperature  # Default to actual temperature if no other conditions are met

    record = {
        'time': asctime(localtime(time)),
        'temp': round(temperature, 1),
        'humi': round(humidity, 1),
        'pres': round(pressure, 1),
        'lux': round(lux),
        'high': round(high, 2),
        'mid': round(mid, 2),
        'low': round(low, 2),
        'amp': round(amp, 2),
    }

    if dewpoint:
        record.update({
            'dew': round(dewpoint, 1),
        })

    if windchill:
        record.update({
            'chill': round(windchill, 1),
        })

    if gas_sensor:
        gases = gas.read_all()
        oxi = round(gases.oxidising / 1000, 1)
        red = round(gases.reducing / 1000)
        nh3 = round(gases.nh3 / 1000)

        record.update({
            'oxi': oxi,
            'red': red,
            'nh3': nh3,
        })

    # particulate_sensor
    if pm1 is not None:
        record.update({
            'pm1': pm1,
            'pm25': pm25,
            'pm10': pm10,
        })
    # Update the record with the latest wind speed if available
    if windspd is not None:
        record.update({
            'windspd': windspd,
        })

    # Update the record with the latest wind direction if available
    if winddir is not None:
        record.update({
            'winddir': winddir,
        })

    return record

# Start the background thread to fetch wind data
wind_thread = threading.Thread(target=fetch_wind_data)
wind_thread.daemon = True  # Make it a daemon thread to exit when the main program exits
wind_thread.start()

# Start the background thread to fetch pms data
pms_thread = threading.Thread(target=fetch_pms_data)
pms_thread.daemon = True  # Make it a daemon thread to exit when the main program exits
pms_thread.start()

# Throw away the first readings as not accurate
record = read_data(time())
data = []
days = []


def filename(t):
    return strftime(app_data + '/%Y_%j', localtime(t))


def sum_data(data):
    totals = {'time': data[0]['time']}
    keys = list(data[0].keys())
    keys.remove('time')
    for key in keys:
        totals[key] = 0
    for d in data:
        for key in keys:
            totals[key] += d[key]
    count = float(len(data))
    for key in keys:
        totals[key] = round(totals[key] / count, 1)
    return totals
def record_time(r):
    t = r['time'].split()[3].split(':')
    return int(t[0]) * 60 + int(t[1])


# Number of 1 second samples average per file record
samples = 600 # At 600 data readings or samples the sensor data is written to a file
samples_per_day = 24 * 3600 // samples


def add_record(day, record):
    # If not the first record of the day
    if record_time(record) > 0:
        # Is there a gap
        while len(day) == 0 or record_time(day[-1]) < record_time(record) - samples // 60:
            if len(day):
                # Duplicate the last record to forward fill
                filler = dict(day[-1])
                t = record_time(filler) + samples // 60
            else:
                filler = dict(record)   # Need to back fill
                t = 0                   # Only happens if the day is empty so most be the first entry
            old_time = filler['time']   # Need to fix the time field
            colon_pos = old_time.find(':')
            filler['time'] = old_time[:colon_pos - 2] + \
                ('%02d:%02d' % (t / 60, t % 60)) + old_time[colon_pos + 3:]
            day.append(filler)
    day.append(record)


def background():
    global record, data
    sleep(2)
    last_file = None
    while run_flag:
        t = int(floor(time()))
        record = read_data(t)
        # Keep ten minutes
        data = data[-(samples - 1):] + [record]

        # The fetch wind and pms functions are not triggered based on number of data readings or samples
        # If you do want this follow these instructions:

        # Check if number of data readings has reached defined number of samples minus some time (60) to start and trigger fetching pms data
        # Change "While" to "If" in def fetch_pms_data()
        # Comment out #sleep() in def fetch_pms_data()
        # Leave background thread to fetch pms data not to have the code waiting for x-number of pms readings needed to warm-up and stabilize sensor
        # Turning the pms5003 on and off might not be usefull when samples is set below for instance 120
        #if len(data) == (samples - 60):
        #    fetch_pms_data()

        # Check if number of data readings has reached 600 data readings and trigger fetching wind data
        # 600 Data readings or samples is the minimum time interval to trigger OpenWeather API
        # Change "While" to "If" in def fetch_wind_data()
        # Comment out #sleep() in def fetch_wind_data()
        # Comment out the 3 lines background thread to fetch wind data
        #if len(data) == 600:
        #    fetch_wind_data()

        # At the end of a 10 minute or 600 samples period
        if t % samples == samples - 1 and len(data) == samples:
            totals = sum_data(data)
            fname = filename(t - (samples - 1))
            with open(fname, 'a+') as f:
                f.write(json.dumps(totals) + '\n')
            # Handle new day
            if not days or (last_file and last_file != fname):
                days.append([])
            last_file = fname
            # Add to today, filling any gap from last reading if been stopped
            add_record(days[-1], totals)
        if lcd_screen and days:
            display_everything()
        sleep(max(t + 1 - time(), 0.1))


background_thread = threading.Thread(target=background)


@app.route('/')
def index():
    return render_template('index.html', gas_sensor=gas_sensor, particulate_sensor=particulate_sensor, fan_gpio=fan_gpio, temp_celsius=temp_celsius)


@app.route('/readings')
def readings():
    if fan_gpio:
        arg = request.args['fan']
        pwm.ChangeDutyCycle(int(arg))
    return record
def compress_data(ndays, nsamples):
    cdata = []
    for day in days[-(ndays + 1):]:
        for i in range(0, len(day), nsamples):
            cdata.append(sum_data(day[i: i + nsamples]))
    length = ndays * samples_per_day // nsamples
    return json.dumps(cdata[-length:])


# 288 @ 5m = 24h
# 336 @ 30m = 1w
# 372 @ 2h = 31d
# 365 @ 1d = 1y
@app.route('/graph')
def graph():
    arg = request.args['time']
    if arg == 'day':
        last2 = []
        for day in days[-2:]:
            last2 += day
        return json.dumps(last2[-samples_per_day:])
    if arg == 'week':
        return compress_data(7, 30 * 60 // samples)
    if arg == 'month':
        return compress_data(31, 120 * 60 // samples)
    if arg == 'year':
        return compress_data(365, samples_per_day)
    return json.dumps(data)


def read_day(fname):
    day = []
    print('reading ' + fname)
    with open(fname, 'r') as f:
        for line in f.readlines():
            record = json.loads(line)
            add_record(day, record)
    return day


if __name__ == '__main__':
    if not os.path.isdir(app_data):
        os.makedirs(app_data)
    files = sorted(os.listdir(app_data))
    for f in files:
        days.append(read_day(app_data + '/' + f))
    background_thread.start()
    try:
        app.run(debug=False, host='0.0.0.0', port=8080, use_reloader=False)
    except Exception as e:
        print(e)
    run_flag = False
    IO.cleanup()
    if lcd_screen:
        disp.set_backlight(0)
    print('Waiting for background to quit')
    background_thread.join()

