import bleak
import asyncio
import time

import OBD2.OBDFrames
from OBD2.OBDFrames import OBDLiveDataPIDs, init_scanner_connection

# configuration
LOG_PATH = 'fuel_monitoring_both_o2_map.log'
OBD_COMMANDS = [OBDLiveDataPIDs.MAP,
                OBDLiveDataPIDs.RPM,
                OBDLiveDataPIDs.OXYGEN_SENSOR_1,
                OBDLiveDataPIDs.OXYGEN_SENSOR_2,
                OBDLiveDataPIDs.FUEL_STATUS
                ]

SERVICE_UUID = "0000ffe0-0000-1000-8000-00805f9b34fb"
CHARACTERISTIC_UUID = "0000ffe1-0000-1000-8000-00805f9b34fb"
DEVICE_ADDRESS = '7190750E-043A-11A3-9560-D5FAAC66EEEA'
CHARACTERISTIC_HANDLE = 24

# open the file that needs to be written to in append mode and start with two blank lines, in case the file is not empty
file = open(LOG_PATH, 'a')
file.write("\n\n")


# gets a line from the OBD-II scanner and retains the PID, A byte and B byte of the transmitted data.
# It also concatenates the current time in nanoseconds and then returns the string.
def decode(data):
    decoded = OBD2.OBDFrames.decode('ascii')
    decoded = decoded.split(' ')

    pid = "FF"
    a = "FF"
    b = "FF"
    # identify the 'Mode' byte
    if decoded[0] == "41":
        # the following bytes are PID and byte A
        pid = decoded[1]
        a = decoded[2]
        # if the PID utilises byte B it is also saved. Only PIDs from the class above are supported in the condition
        if pid == "0C" or pid == "14" or pid == "15":
            b = decoded[3]
    else:
        return False
    return pid + a + b + str(time.time_ns())


async def read_data_and_put_in_file():
    global CHARACTERISTIC_UUID, CHARACTERISTIC_HANDLE, DEVICE_ADDRESS
    # connect to the given OBD-II scanner
    client = await init_scanner_connection(DEVICE_ADDRESS, CHARACTERISTIC_HANDLE)
    while True:
        for i in range(0, len(OBD_COMMANDS)):
            # write the command
            await client.write_gatt_char(CHARACTERISTIC_HANDLE, OBD_COMMANDS[i], response=False)
            decoded = False
            # decode will return false unless the 'Mode' byte has been identified (value 41)
            while not decoded:
                response = await client.read_gatt_char(CHARACTERISTIC_HANDLE)
                decoded = decode(response)
            # write the data to the file
            file.write(str(decoded) + '\n')


if __name__ == '__main__':
    asyncio.run(read_data_and_put_in_file())
