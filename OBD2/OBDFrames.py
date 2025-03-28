import asyncio
import time

import bleak


# OBD-II PIDs. The PIDs are hardcoded as byte arrays in a class.
# The first byte represents the service/mode: show current data(01).
# The second byte represents the sensor data requested.
class OBDLiveDataPIDs:
    RPM = bytes('010C\n\r', 'ascii')
    MAP = bytes('010B\n\r', 'ascii')
    SPEED = bytes('010D\n\r', 'ascii')
    IAT = bytes('010F\n\r', 'ascii')
    THROTTLE_POSITION = bytes('0111\n\r', 'ascii')
    CALCULATED_ENGINE_LOAD = bytes('0104\n\r', 'ascii')
    COOLANT_TEMPERATURE = bytes('0105\n\r', 'ascii')
    SUPPORTED_PIDS_A = bytes('0100\n\r', 'ascii')
    SUPPORTED_PIDS_B = bytes('0120\n\r', 'ascii')
    SUPPORTED_PIDS_C = bytes('0140\n\r', 'ascii')
    OXYGEN_SENSOR_1 = bytes('0114\n\r', 'ascii')
    OXYGEN_SENSOR_2 = bytes('0115\n\r', 'ascii')
    TIMING_ADVANCE = bytes('010E\n\r', 'ascii')
    FUEL_STATUS = bytes('0103\n\r', 'ascii')


def nanoseconds_to_seconds(input):
    return input / 1000000000


class OBDFrame:
    def __init__(self, pid, a=0, b=0, time=0):
        self.pid = pid
        self.__a = a
        self.__b = b
        self.__time = time
        # get default header messages for PIDs

    def get_message(self, unit=None):
        if self.pid == 3:
            return "Fuel system operation mode"
        if self.pid == 4:
            return "Calculated engine load (%)"
        if self.pid == 5:
            return "Engine coolant temperature (Celsius)"
        if self.pid == 6:
            return "Short term fuel trim Bank 1 (%)"
        if self.pid == 7:
            return "Long term fuel trim Bank 1 (%)"
        if self.pid == 8:
            return "Short term fuel trim Bank 2 (%)"
        if self.pid == 9:
            return "Long term fuel trim Bank 2 (%)"
        if self.pid == 11:
            return "MAP (kPa)"
        if self.pid == 12:
            return "Engine speed (RPM)"
        if self.pid == 13:
            return "Vehicle speed (kph)"
        if self.pid == 14:
            return "Timing advance (degrees before TDC)"
        if self.pid == 15:
            return "IAT (Celsius)"
        if self.pid == 17:
            return "Throttle position (%)"
        if 20 <= self.pid <= 27 and unit == "V":
            return "Oxygen sensor " + str(self.pid - 19) + " (V)"
        if 20 <= self.pid <= 27 and unit == "%":
            return "Oxygen sensor " + str(self.pid - 19) + " (%)"
        return None

    def parse_percentage(self, message):
        return [message, self.__a / 2.55, nanoseconds_to_seconds(self.__time)]

    def parse_temp(self, message):
        return [message, self.__a - 40, nanoseconds_to_seconds(self.__time)]

    def parse_fuel_trim(self, message):
        return [message, self.__a / 1.28 - 100, nanoseconds_to_seconds(self.__time)]

    def parse_direct_value_byte_a(self, message):
        return [message, self.__a, nanoseconds_to_seconds(self.__time)]

    def parse_rpm(self, message):
        return [message, (256 * self.__a + self.__b) / 4, nanoseconds_to_seconds(self.__time)]

    def parse_timing_advance(self, message):
        return [message, self.__a / 2 - 64, nanoseconds_to_seconds(self.__time)]

    def parse_oxygen_sensor_voltage(self, message):
        return [message, self.__a / 200, nanoseconds_to_seconds(self.__time)]

    def parse_oxygen_sensor_fuel_trim(self, message):
        return [message, self.__b / 1.28 - 100, nanoseconds_to_seconds(self.__time)]

    def parse_fuel_status_a(self, message):
        status = "NONE"
        if self.__a == 0:
            status = "OFF"
        elif self.__a == 1:
            status = "OPEN_LOOP_INS_TEMP"
        elif self.__a == 2:
            status = "CLOSED_LOOP"
        elif self.__a == 4:
            status = "OPEN_LOOP"
        elif self.__a == 8:
            status = "OPEN_LOOP_FAULT"
        elif self.__a == 16:
            status = "CLOSED_LOOP_FAULT"
        return [message, status, nanoseconds_to_seconds(self.__time)]

    # get an array containing the header, human readable value and current time in seconds for an OBD frame
    def parse(self, unit=None, message=None):
        if message is None:
            message = self.get_message(unit)
        if self.pid == 3:
            return self.parse_fuel_status_a(message)
        if self.pid == 4:
            return self.parse_percentage(message)
        if self.pid == 5:
            return self.parse_temp(message)
        if self.pid == 6:
            return self.parse_fuel_trim(message)
        if self.pid == 7:
            return self.parse_fuel_trim(message)
        if self.pid == 8:
            return self.parse_fuel_trim(message)
        if self.pid == 9:
            return self.parse_fuel_trim(message)
        if self.pid == 11:
            return self.parse_direct_value_byte_a(message)
        if self.pid == 12:
            return self.parse_rpm(message)
        if self.pid == 13:
            return self.parse_direct_value_byte_a(message)
        if self.pid == 14:
            return self.parse_timing_advance(message)
        if self.pid == 15:
            return self.parse_temp(message)
        if self.pid == 17:
            return self.parse_percentage(message)
        if 20 <= self.pid <= 27 and unit == "V":
            return self.parse_oxygen_sensor_voltage(message)
        if 20 <= self.pid <= 27 and unit == "%":
            return self.parse_oxygen_sensor_fuel_trim(message)
        return None


# decodes a frame read from Bluetooth or Serial and returns an array
# input: data - raw read data
# returns: [pid, a, b, time]
#           pid - int - pid from the OBD2 standard
#           a - int - byte a of the OBD2 frame
#           b - int - byte b of the OBD2 frame
#           time - int - time in ns
def decode(data):
    decoded = data.decode('ascii')
    decoded = decoded.split(' ')

    pid = 0xFF
    a = 0xFF
    b = 0xFF
    # identify the 'Mode' byte
    if decoded[0] == "41":
        # the following bytes are PID and byte A
        pid = int(decoded[1], base=16)
        a = int(decoded[2], base=16)
        # if the PID utilises byte B it is also saved. Only PIDs from the class above are supported in the condition
        if pid == "0C" or pid == "14" or pid == "15":
            b = int(decoded[3], base=16)
    else:
        return False
    return [pid, a, b, time.time_ns()]


async def init_scanner_connection(device_address, characteristic_handle):
    client = bleak.BleakClient(device_address)
    await client.connect()

    # wait for the scanner to initialise
    await asyncio.sleep(3)

    # await for the scanner to be ready to receive a command
    await client.read_gatt_char(characteristic_handle)

    # request data in order for the scanner to initialise a connection to the ECM
    await client.write_gatt_char(characteristic_handle, OBDLiveDataPIDs.THROTTLE_POSITION, response=False)
    await client.read_gatt_char(characteristic_handle)
    await client.read_gatt_char(characteristic_handle)
    await client.read_gatt_char(characteristic_handle)

    # repeat to make sure that a connection was made and the ECM is communicating
    await asyncio.sleep(5)
    await client.write_gatt_char(characteristic_handle, OBDLiveDataPIDs.THROTTLE_POSITION, response=False)
    await client.read_gatt_char(characteristic_handle)
    await client.read_gatt_char(characteristic_handle)
    await client.read_gatt_char(characteristic_handle)

    # get repeatedly each command by turns
    print("READING")
    return client
