import pynmea2
import serial

LATITUDE = None
LONGITUDE = None
SPEED_KMH_GPS = None
HEADING = None
ALTITUDE = None
ALTITUDE_UNITS = None
TIME_GPS = None
DATE_GPS = None


def read_serial_gps(serial_port):
    global LATITUDE, LONGITUDE, SPEED_KMH_GPS, HEADING, ALTITUDE, ALTITUDE_UNITS, DATE_GPS, TIME_GPS
    conn = serial.Serial(serial_port, 9600, timeout=1.05)
    while True:
        try:
            line = conn.readline().decode('ascii')
            msg = pynmea2.parse(line)
        except:
            continue

        if hasattr(msg, 'latitude') and hasattr(msg, 'longitude'):
            LATITUDE = msg.latitude
            LONGITUDE = msg.longitude

        if hasattr(msg, 'timestamp'):
            TIME_GPS = msg.timestamp

        if hasattr(msg, 'datestamp'):
            DATE_GPS = msg.datestamp

        if hasattr(msg, 'altitude') and hasattr(msg, 'altitude_units'):
            ALTITUDE = msg.altitude
            ALTITUDE_UNITS = msg.altitude_units

        if hasattr(msg, 'true_attack'):
            HEADING = msg.true_attack
        elif hasattr(msg, 'true_course'):
            HEADING = msg.true_course

        if hasattr(msg, 'spd_over_grnd_kmph'):
            SPEED_KMH_GPS = msg.spd_over_grnd_kmph
