import asyncio
import csv
import json
import math
import threading
import time

import beepy
import bleak
import requests

import Scripts.obd_computer_configs
from Accelerometer.Accelerometer import AccelerometerException, AccelerometerADXL313
from GPS.gps import LATITUDE, LONGITUDE, SPEED_KMH_GPS, HEADING, ALTITUDE, TIME_GPS
from GPS.gps import read_serial_gps
from OBD2.OBDFrames import nanoseconds_to_seconds, OBDFrame, decode, init_scanner_connection
from Scripts.obd_computer_configs import ACCELEROMETER_PORT, GPS_PORT, PRINT_TO_SCREEN, INTERVAL, CHARACTERISTIC_HANDLE, \
    DEVICE_ADDRESS, OPEN_WEATHER_API_KEY, CORRECTION_COEFFICIENT
from Scripts.constants import THEORETICAL_AIR_INTAKE, AFR, ATMOSPHERIC, FUEL_DENSITY

# engine live data, available to all threads
# kPa
MAP = 100
# C
IAT = 20
RPM = 0
# kmh
SPEED = 0
# %
LOAD = 0

# C
AAT = 286.95 - 273
# kPa
AAP = 101.8

# OpenWeather API info.
OPEN_WEATHER_API_URL = 'https://api.openweathermap.org/data/2.5/weather?lat=LATITUDE&lon=LONGITUDE&appid=KEY'

# accelerometer
accelerometer = None
accelerometerX = None
accelerometerY = None
accelerometerZ = None

# latest time in ns
LATEST = 0

# fuel used
FUEL_USED = 0
# distance went
DISTANCE = 0.000001
# L/100km
INSTANT_FUEL_CONSUMPTION = 0


# function to be called on accelerometer interrupt
def handle_accelerometer_interrupt():
    global accelerometerX, accelerometerY, accelerometerZ
    accelerometerX = accelerometer.get_x()
    accelerometerY = accelerometer.get_y()
    accelerometerZ = accelerometer.get_z()


def estimated_lambda():
    global MAP, RPM
    if MAP < 32:
        return math.inf
    if MAP > 90 and RPM >= 4500:
        return 0.88
    return 0.95


# Theoretical air intake as a function of RPM
def TAI(omega):
    if omega < 900:
        return 0
    v1 = (omega - 900) / 100
    pos1 = int(v1)
    pos2 = pos1 + 1
    p = v1 - pos1
    return THEORETICAL_AIR_INTAKE[pos1] * (1 - p) + THEORETICAL_AIR_INTAKE[pos2] * p


# Airflow g/s as a function of rpm
def AIRFLOW(omega):
    return TAI(omega) * 3 * omega / 120


# Current mass air flow
def MAF():
    global IAT, RPM, LOAD
    return (LOAD / 100) * AIRFLOW(RPM) * (101.4 / ATMOSPHERIC) * math.sqrt(298 / (17 + 273))


# converts grams of fuel to L
def grams_to_L(fuel_quantity):
    return fuel_quantity / FUEL_DENSITY


# converts fuel flow to L/100km, depending on current vehicle speed
def grams_per_second_to_L_per_100_km(fuel_flow):
    global SPEED
    val = fuel_flow * 3600 / ((SPEED + 0.0000001) * FUEL_DENSITY) * 100
    if val > 1000:
        val = math.inf
    return val


# processes one frame read from the OBD2 diagnostics tool
def process_frame(frame):
    global MAP, IAT, RPM, SPEED, LOAD
    obj = OBDFrame(frame[0], frame[1], frame[2], frame[3])
    value = obj.parse()[1]
    if obj.pid == 0x0B:
        MAP = value
    elif obj.pid == 0x0C:
        RPM = value
    elif obj.pid == 0x0D:
        SPEED = value
    elif obj.pid == 0x0F:
        IAT = value
    elif obj.pid == 0x04:
        LOAD = value


# calculates fuel flow and updates FUEL_USED and DISTANCE. If the time gets stuck, then a sound is made to alert the
# operator
def compute_engine_data():
    global SPEED, IAT, MAP, RPM, LOAD, LATEST, FUEL_USED, DISTANCE, INSTANT_FUEL_CONSUMPTION
    maf = MAF()
    fuel_flow = CORRECTION_COEFFICIENT * maf / (estimated_lambda() * AFR)
    current_time = time.time_ns()

    delta_t = current_time - LATEST
    delta_t_s = nanoseconds_to_seconds(delta_t)
    LATEST = current_time

    fuel_used_cycle = delta_t_s * fuel_flow
    FUEL_USED += fuel_used_cycle

    distance_cycle = SPEED * 10 / 36 * delta_t_s
    DISTANCE += distance_cycle
    INSTANT_FUEL_CONSUMPTION = grams_per_second_to_L_per_100_km(fuel_flow)
    if delta_t == 0:
        beepy.beep(sound="error")


# runs the engine cycle to continuously read data and update the variables
def run_cycle():
    while True:
        compute_engine_data()


# gets ambient air temperature and ambient air pressure
def get_aat_aap():
    global AAT, AAP, OPEN_WEATHER_API_URL
    final_uri = OPEN_WEATHER_API_URL
    final_uri = final_uri.replace('LATITUDE', str(LATITUDE))
    final_uri = final_uri.replace('LONGITUDE', str(LONGITUDE))
    final_uri = final_uri.replace('KEY', str(OPEN_WEATHER_API_KEY))
    response = requests.get(final_uri)
    response.raise_for_status()
    obj = json.loads(response.text)
    AAT = float(obj['main']['temp']) - 273
    AAP = float(obj['main']['pressure']) / 10
    print(AAP, AAT)


# runs continuously and prints the data to csv
def print_cycle():
    global FUEL_USED, DISTANCE, RPM, SPEED, LOAD, LATEST, MAP, IAT
    global accelerometerX, accelerometerY, accelerometerZ
    writer = None
    file = None
    if Scripts.obd_computer_configs.OUTPUT is not None:
        file = open(Scripts.obd_computer_configs.OUTPUT, 'a')
        writer = csv.writer(file)
        csv_header = ["LATEST", "SPEED", "LOAD", "MAP", "IAT", "RPM", "DISTANCE", "FUEL_USED",
                      "FUEL_CONSUMPTION", "INSTANT_FUEL_CONSUMPTION", "LATITUDE", "LONGITUDE", "ALTITUDE", "HEADING",
                      "SPEED_GPS", "TIME_GPS", "X", "Y", "Z", "AAT", "AAP"]
        writer.writerow(csv_header)

    while True:
        fuel_consumption = grams_to_L(FUEL_USED) / DISTANCE * 100000
        if PRINT_TO_SCREEN:
            print("FUEL USED:", FUEL_USED)
            print("DISTANCE:", DISTANCE)
            print("SPEED:", SPEED)
            print("LOAD:", LOAD)
            print("RPM:", RPM)
            print("FUEL CONSUMPTION:", fuel_consumption)
            print("INSTANT FUEL CONSUMPTION:", INSTANT_FUEL_CONSUMPTION)

        if writer is not None:
            row = [LATEST, SPEED, LOAD, MAP, IAT, RPM,
                   DISTANCE, FUEL_USED, fuel_consumption, INSTANT_FUEL_CONSUMPTION, LATITUDE, LONGITUDE,
                   ALTITUDE,
                   HEADING, SPEED_KMH_GPS, TIME_GPS, accelerometerX, accelerometerY, accelerometerZ, AAT, AAP]
            writer.writerow(row)

        time.sleep(INTERVAL)


# reads engine data continuously
async def engine_data_read_cycle():
    global MAP, IAT, RPM, SPEED, LOAD, LATEST
    # connect to the given OBD-II scanner
    client = await init_scanner_connection(DEVICE_ADDRESS,
                                           CHARACTERISTIC_HANDLE)

    # update cycle for PIDs. the computer is currently able to run approx. 6 queries / second

    for i in Scripts.obd_computer_configs.INITIAL_READINGS:
        await client.write_gatt_char(CHARACTERISTIC_HANDLE, i, response=False)
        decoded = False
        while not decoded:
            response = await client.read_gatt_char(CHARACTERISTIC_HANDLE)
            decoded = decode(response)

        process_frame(decoded)

    LATEST = time.time_ns()
    while True:
        for i in Scripts.obd_computer_configs.UPDATE_CYCLE:
            try:
                await client.write_gatt_char(CHARACTERISTIC_HANDLE, i, response=False)
                decoded = False
                while not decoded:
                    response = await client.read_gatt_char(CHARACTERISTIC_HANDLE)
                    decoded = decode(response)

                process_frame(decoded)
                compute_engine_data()
            except bleak.BleakError as e:
                beepy.beep(sound="error")


def read_accelerometer():
    global accelerometer, accelerometerX, accelerometerY, accelerometerZ
    while True:
        try:
            accelerometerX, accelerometerY, accelerometerZ = accelerometer.get_frame()
            time.sleep(0.18)
        except AccelerometerException:
            continue


def update_aat_aap():
    while True:
        try:
            get_aat_aap()
        except requests.RequestException:
            pass
        time.sleep(12000)


if __name__ == '__main__':
    print_thread = threading.Thread(target=print_cycle)
    read_gps_thread = threading.Thread(target=read_serial_gps, kwargs={'serial_port': GPS_PORT})
    read_accelerometer_thread = threading.Thread(target=read_accelerometer)
    update_aat_aap_thread = threading.Thread(target=update_aat_aap)

    accelerometer = AccelerometerADXL313(ACCELEROMETER_PORT, 115200)
    accelerometer.connect_to_slave()
    time.sleep(3)

    read_gps_thread.start()
    read_accelerometer_thread.start()
    print_thread.start()
    update_aat_aap_thread.start()

    asyncio.run(engine_data_read_cycle())
