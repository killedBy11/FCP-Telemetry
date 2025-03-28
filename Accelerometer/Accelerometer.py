import threading
import time

import serial


class AccelerometerException(Exception):
    def __init__(self, message):
        self.message = message


class AccelerometerADXL313:
    __serial = None

    _interrupt_mode = False
    _connected = False
    _interrupt_function = None
    _interrupt_watcher_thread = None
    _x = None
    _y = None
    _z = None

    # Define class variables for incoming communication messages
    SER_SUCCESS = "SER_SUCCESS"
    SER_FAIL = "SER_FAIL"
    ACC_FAIL = "ACC_FAIL"
    ACC_SUCCESS = "ACC_SUCCESS"
    ACC_FRAME = "ACC_FRAME"
    ENABLED_INTERRUPTS = "ENABLED_INTERRUPTS"
    DISABLED_INTERRUPTS = "DISABLED_INTERRUPTS"
    UNKNOWN_ERR = "UNKNOWN_ERR"
    ILLEGAL_ACTION = "ILL_ACT"

    # Define class variables for outgoing communication messages
    BEGIN = "BEGIN\n"
    END = "END\n"
    ENABLE_INTERRUPTS = "ENABLE_INTERRUPTS\n"
    DISABLE_INTERRUPTS = "DISABLE_INTERRUPTS\n"
    REQUEST_FRAME = "REQUEST_FRAME\n"
    SET_RANGE = "SET_RANGE\n"
    SET_ACTIVITY_THRESHOLD = "SET_ACT_THR\n"
    SET_INACTIVITY_TIMEOUT = "SET_INACT_TIME\n"
    SET_INTERRUPT_MODE_INTERVAL = "SET_INT_INTERVAL\n"

    # Define possible ranges
    ADXL313_RANGE_05_G = "0\n"
    ADXL313_RANGE_1_G = "1\n"
    ADXL313_RANGE_2_G = "2\n"
    ADXL313_RANGE_4_G = "3\n"

    # Initialises a serial connection with the given baudrate, timeout and port
    # input: port - string - the serial port the accelerometer is expected to be on
    #        baudrate - int - the baudrate on the serial connection the devices will be communicating on
    #        timeout - int - default 1s, the serial timeout for when the program is blocking execution and waiting for a message
    def __init__(self, port, baudrate, timeout=1):
        if timeout is None:
            self.__serial = serial.Serial(port, baudrate=baudrate)
        else:
            self.__serial = serial.Serial(port, baudrate=baudrate, timeout=timeout)
        time.sleep(3)

        self._interrupt_watcher_thread = threading.Thread(target=self._interrupt_mode_recv_xyz)

    # Initialises a connection to the board and raises an exception if not successful
    def connect_to_slave(self):
        if not self.__serial.is_open:
            self.__serial.open()

        self.__serial.write(self.BEGIN.encode())

        response = self.__serial.readline().decode().strip()
        if self.SER_SUCCESS != response:
            raise AccelerometerException("Arduino handshake incomplete. Received response: " + response)

        response = self.__serial.readline().decode().strip()
        if self.ACC_SUCCESS != response:
            raise AccelerometerException("Arduino handshake incomplete. Received response: " + response)

        self._connected = True

    # Closes the connection to the board and resets the board. Raises an exception if the accelerometer unit is not connected.
    def close_connection(self):
        if not self._connected:
            raise AccelerometerException("Accelerometer not connected")
        self.__serial.write(self.END.encode())
        self.__serial.flush()
        self.__serial.close()
        self._connected = False

    # Sets the accelerometer range to the given range.
    #   input: r - self.ADXL313_RANGE_05G through self.ADXL313_RANGE_4G
    #   raises: AccelerometerException - if the range could not be set
    def set_range(self, r):
        response = self._send_cmd_parameter_and_get_response(self.SET_RANGE, r)

        if self.UNKNOWN_ERR == response:
            raise AccelerometerException("Range set incomplete. Received response: " + response)

        set_value = int(response)
        supposed_value = int(r)

        if set_value != supposed_value:
            raise AccelerometerException("Range set incomplete. Received response: " + response)

    # Sets the activity threshold for accelerometer automatic sleep.
    # input: threshold - uint8_t - activity threshold
    # raises: AccelerometerException - if the range could not be set or the accelerometer is in interrupt mode
    def set_activity_threshold(self, threshold):
        response = self._send_cmd_parameter_and_get_response(self.SET_ACTIVITY_THRESHOLD, threshold)

        if self.UNKNOWN_ERR == response:
            raise AccelerometerException("Range set incomplete. Received response: " + response)

        if self.ILLEGAL_ACTION == response:
            raise AccelerometerException("Range set incomplete. Setting activity threshold is illegal while in "
                                         "interrupt mode. Received response: " + response)

        set_value = int(response)
        supposed_value = int(threshold)

        if set_value != supposed_value:
            raise AccelerometerException("Activity threshold set incomplete. Received response: " + response)

    # Sets the inactivity timeout for the accelerometer. The method should fail in interrupt mode.
    # input: timeout - uint16_t - the activity timeout that the accelerometer should be set to. unit in ms
    # raises: AccelerometerException - if the timeout is wrong or the accelerometer is in interrupt mode.
    def set_inactivity_timeout(self, timeout):
        response = self._send_cmd_parameter_and_get_response(self.SET_INACTIVITY_TIMEOUT, timeout)

        if self.UNKNOWN_ERR == response:
            raise AccelerometerException("Range set incomplete. Received response: " + response)

        if self.ILLEGAL_ACTION == response:
            raise AccelerometerException("Range set incomplete. Setting activity timeout is illegal while in "
                                         "interrupt mode. Received response: " + response)

        set_value = int(response)
        supposed_value = int(timeout)

        if set_value != supposed_value:
            raise AccelerometerException("Activity timeout set incomplete. Received response: " + response)

    # Sets the interupt mode transmission interval. Should only fail if the connection is not working properly.
    # input: interval - uint16_t - time in ms between transmissions
    # raises: AccelerometerException - if the connection is not proper and the setting could not be made
    def set_interrupt_mode_interval(self, interval):
        response = self._send_cmd_parameter_and_get_response(self.SET_INTERRUPT_MODE_INTERVAL, interval)

        if self.UNKNOWN_ERR == response:
            raise AccelerometerException("Range set incomplete. Received response: " + response)

        set_value = int(response)
        supposed_value = int(interval)

        if set_value != supposed_value:
            raise AccelerometerException("Interval set incomplete. Received response: " + response)

    # reads x, y, z coordinates from the accelerometer.
    # raises: AcceleromterException - if the connection is not working properly
    # returns: x, y, z - int, int, int - acceleration values from the accelerometer
    def get_frame(self):
        if not self._connected:
            raise AccelerometerException("Accelerometer not connected")

        self.__serial.write(self.REQUEST_FRAME.encode())
        x, y, z = self._read_frame()
        return x, y, z


    # Enables interrupt mode and creates a thread that runs a function designated to constantly receive coordinates.
    # input: function - function() - sets the function to be called when values are received from the accelerometer default to None
    def enable_interrupts(self, function=None):
        if not self._connected:
            raise AccelerometerException("Accelerometer not connected")

        self.__serial.write(self.ENABLE_INTERRUPTS.encode())
        response = self.__serial.readline().decode().strip()

        if self.ENABLED_INTERRUPTS != response:
            raise AccelerometerException("Enabled interrupts incomplete. Received response: " + response)

        self._interrupt_mode = True
        if function is not None:
            self._interrupt_function = function

        self._interrupt_watcher_thread.start()

    # Disables the interrupt mode and stops the thread
    def disable_interrupts(self):
        if not self._connected:
            raise AccelerometerException("Accelerometer not connected")

        prev_state = self._interrupt_mode

        self._interrupt_mode = False
        time.sleep(0.5)

        self.__serial.flush()
        self.__serial.write(self.DISABLE_INTERRUPTS.encode())
        response = self.__serial.readline().decode().strip()

        while self.ACC_FRAME == response:
            self.__serial.readline().decode().strip()
            response = self.__serial.readline().decode().strip()

        if self.DISABLED_INTERRUPTS != response:
            self._interrupt_mode = prev_state
            raise AccelerometerException("Disabled interrupts incomplete. Received response: " + response)

        self._interrupt_mode = False
        self._interrupt_watcher_thread.join()
        self._x = None
        self._y = None
        self._z = None

    # Callable only while in interrupt mode. Returns the read x coordinate from the accelerometer.
    # raises: Accelerometer exception if not in interrupt mode
    # returns: x - int - coordinate read from the accelerometer
    def get_x(self):
        if not self._interrupt_mode:
            raise AccelerometerException("Accelerometer must be in interrupt mode to use these methods.")
        return self._x

    # Callable only while in interrupt mode. Returns the read y coordinate from the accelerometer.
    # raises: Accelerometer exception if not in interrupt mode
    # returns: y - int - coordinate read from the accelerometer
    def get_y(self):
        if not self._interrupt_mode:
            raise AccelerometerException("Accelerometer must be in interrupt mode to use these methods.")
        return self._y

    # Callable only while in interrupt mode. Returns the read z coordinate from the accelerometer.
    # raises: Accelerometer exception if not in interrupt mode
    # returns: z - int - coordinate read from the accelerometer
    def get_z(self):
        if not self._interrupt_mode:
            raise AccelerometerException("Accelerometer must be in interrupt mode to use these methods.")
        return self._z

    # Designed to run in a separate thread. Loops continuously while in interrupt mode and reads the parameters from
    # the accelerometer. It sets the x, y, z properties in the object to the coordinates read.
    def _interrupt_mode_recv_xyz(self):
        while self._interrupt_mode:
            try:
                self._x, self._y, self._z = self._read_frame()
                self._interrupt_function()
            except AccelerometerException:
                continue

    # Reads a frame from serial and returns the integer values read from the accelerometer unit.
    # returns: x, y, z - int, int, int - coordinates read from the accelerometer
    def _read_frame(self):
        if not self._connected:
            raise AccelerometerException("Accelerometer not connected")

        response = self.__serial.readline().decode().strip()
        if self.ACC_FRAME != response:
            raise AccelerometerException("Serial input is not an accelerometer frame. Received response: " + response)

        response = self.__serial.readline().decode().strip()
        [x_str, y_str, z_str] = response.split(' ')

        x = int(x_str)
        y = int(y_str)
        z = int(z_str)

        return x, y, z

    # Sends the paramter for a command. To be called for commands that also send a parameter.
    # input - cmd - command from the class properties
    #         parameter - string - parameter that the command should send. Should be encoded as a string.
    # returns - response from the accelerometer
    def _send_cmd_parameter_and_get_response(self, cmd, parameter):
        if not self._connected:
            raise AccelerometerException("Accelerometer not connected")
        self.__serial.write(cmd.encode())
        self.__serial.write(parameter.encode())
        time.sleep(0.2)
        response = self.__serial.readline().decode().strip()
        return response
