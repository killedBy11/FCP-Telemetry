#include <ADXL313_Registers.h>
#include <SparkFunADXL313.h>
#include <Wire.h>

// Define outgoing communication messages
#define SER_SUCCESS "SER_SUCCESS"
#define SER_FAIL "SER_FAIL"
#define ACC_FAIL "ACC_FAIL"
#define ACC_SUCCESS "ACC_SUCCESS"
#define ACC_FRAME "ACC_FRAME"
#define ENABLED_INTERRUPTS "ENABLED_INTERRUPTS"
#define DISABLED_INTERRUPTS "DISABLED_INTERRUPTS"
#define UNKNOWN_ERR "UNKNOWN_ERR"
#define ILLEGAL_ACTION "ILL_ACT"

// Define incoming communication messages
const String BEGIN("BEGIN");
const String END("END");
const String ENABLE_INTERRUPTS("ENABLE_INTERRUPTS");
const String DISABLE_INTERRUPTS("DISABLE_INTERRUPTS");
const String REQUEST_FRAME("REQUEST_FRAME");
const String SET_RANGE("SET_RANGE");
const String SET_ACTIVITY_THRESHOLD("SET_ACT_THR");
const String SET_INACTIVITY_TIMEOUT("SET_INACT_TIME");
const String SET_INTERRUPT_MODE_INTERVAL("SET_INT_INTERVAL");


// Define structures
ADXL313 accelerometer;

const uint8_t LED_PIN = 13;
const uint8_t BIG_LED_PIN = 3;

// vector representation using versors for each axis
struct vector {
  int16_t x, y, z;
};

// define constants
const vector default_resting_position_4g {
  0, -1, 123
};
const vector default_resting_position_2g {
  0, -2, 246
};
const vector default_resting_position_1g {
  1, -4, 492
};
const vector default_resting_positions[] = {{0, 0, 0}, default_resting_position_1g, default_resting_position_2g, default_resting_position_4g};

// current range set to accelerometer
uint8_t accelerometer_range = ADXL313_RANGE_4_G;

// if the controller is set to interrupt mode. Interrupt mode means that the accelerometer will interrupt when a change has happened. In that case the arduino will send the coordinates via serial without an existing request from the master.
boolean interrupt_mode = false;
boolean interrupt_flag = false;
boolean accelerometer_awake = false;

uint8_t activity_threshold = 7;
uint8_t inactivity_timeout = 5;
uint16_t interrupt_mode_interval = 50;

// Blinks LED indefinetely. The function starts an infinite loop to warn the user an error exists. The board needs resetting to exit the state.
// input: interval - uint16_t - the amount of ms between the LED state switches
//        pin      - uint8_t  - the pin that the LED is connected to
void blink_led(uint16_t interval, uint8_t pin) {
  for (uint8_t led_status = LOW; true;) {
    if (LOW == led_status) {
      led_status = HIGH;
    } else if (HIGH == led_status) {
      led_status = LOW;
    }
    digitalWrite(pin, led_status);
    delay(interval);
  }
}


// This function is used to reset the board. The memory is wiped and the program restarts.
void (*reset_board)(void) = 0;

// The function is called to block execution until a message is received via the serial connection on USB. The function blinks the on-board LED set on pin 13 by default.
// input: interval  - uint16_t - led blinking interval. The amount of time in ms in between the LED switching states.
//        max_delay - uint16_t - the maximum amount of time in ms that the program should wait for a message. By default
//                                  it is set to 0 and never exits the loop unless a message is received. It is recommended
//                                  to always limit the amount of time the program waits for a message
boolean await_serial_message(const uint16_t interval = 100, const uint16_t max_delay = 0) {
  // Await connection message begin
  uint16_t current_delay = 0;

  for (uint8_t led_status = LOW; 1 > Serial.available() && (!max_delay || current_delay < max_delay); current_delay += interval) {
    if (led_status == HIGH) {
      led_status = LOW;
    } else if (led_status == LOW) {
      led_status = HIGH;
    }

    digitalWrite(LED_PIN, led_status);
    delay(interval);
  }
  digitalWrite(LED_PIN, LOW);

  return Serial.available();
}

// Awaits the connection from the computer via USB. It waits indefinetely until a computer is connected and makes its presence known by a message. The LED blinks while it is awaiting connection.
//      The board will send back a message SER_SUCCESS if the connection is successful, or SER_FAIL if the BEGIN message is not received.
//      If the board receives another message other than BEGIN and it responds with SER_FAIL, then the board will reset and the prgoram will restart.
void await_master_and_acknowledge() {
  await_serial_message();

  // Acknowledge begin of master program
  String current_message = Serial.readStringUntil('\n');
  if (BEGIN == current_message) {
    Serial.println(SER_SUCCESS);
  } else {
    Serial.println(SER_FAIL);
    delay(500);
    reset_board();
  }
}

// Sends the current X, Y, Z coordinates to the computer via USB. The format of the message is the header ACC_FRAME and then the coordinates x, y and z, separated by a space are sent.
//      The message is sent as an ASCII string.
void send_frame() {
  boolean data_ready = false;

  if (interrupt_mode) {
    accelerometer.updateIntSourceStatuses();
    data_ready = accelerometer.intSource.dataReady;
  } else if (!interrupt_mode) {
    data_ready = accelerometer.dataReady();
  }
  
  if (data_ready) {
    accelerometer.readAccel();
    Serial.println(ACC_FRAME);
    Serial.print(accelerometer.x);
    Serial.print(" ");
    Serial.print(accelerometer.y);
    Serial.print(" ");
    Serial.println(accelerometer.z);
  }
}

// For a command that requires a parameter this function should be called. It sends a response if necessary, if the parameter is not read UNKNOWN_ERR or ILLEGAL_ACTION
//  if the command is not applicable in the current state. i.e. an attempt is made to change the settings while in interrupt mode
//      input:  illegal - boolean - if true the program will read the parameter to empty the buffer and send back ILLEGAL_ACTION via USB
//      output: parameter - String& - the paramter read from serial
//      returns: true - the parameter was read and nothing was sent to USB. The operation was successful.
//               false - the parameter was not read succesfully or illegal was set to true. In this case the function also responds to USB.
boolean get_command_parameter(String& parameter, boolean illegal = false) {
  boolean read_parameter = await_serial_message(50, 5000);

  if (!read_parameter) {
    Serial.println(UNKNOWN_ERR);
    return false;
  }

  parameter = Serial.readStringUntil('\n');

  if (illegal) {
    Serial.println(ILLEGAL_ACTION);
    return false;
  }

  return true;
}


// This function is called when the header SET_ACTIVITY_THRESHOLD is received. The function sets the parameter for activity threshold in memory.
// The function sets the parameter for the interrupt mode and it is not callable while in interrupt mode. If the call was successful, the function sends back the sent value via USB.
// This function uses the get_command_parameter function to reads its parameter from USB.
void set_activity_threshold() {
  String parameter;
  boolean read_parameter = get_command_parameter(parameter, interrupt_mode);

  if (!read_parameter) {
    return;
  }
  
  uint8_t value = parameter.toInt();
  
  activity_threshold = value;
  Serial.println(activity_threshold);
}

// This function is called when the header SET_INACT_TIME is received. The function sets the parameter for inactivity timeout in memory.
// The function sets the parameter for the interrupt mode and it is not callable while in interrupt mode. If the call was successful, the function sends back the sent value via USB.
// This function uses the get_command_parameter function to reads its parameter from USB.
void set_inactivity_timeout() {
  String parameter;
  boolean read_parameter = get_command_parameter(parameter, interrupt_mode);

  if (!read_parameter) {
    return;
  }
  
  uint8_t value = parameter.toInt();
  
  inactivity_timeout = value;
  Serial.println(inactivity_timeout);
}

// This function is called when the header SET_INT_INTERVAL is received. The function sets the parameter for interval in memory.
// The function sets the parameter for the interrupt mode interval and it is callable while in interrupt mode. If the call was successful, the function sends back the sent value via USB.
// The interrupt mode interval sets the delay in ms between frames. On interrupt mode the board will send automatically, without request the values from the sensor when activity is detected.
// The values are continuously sent until inactivity is detected and the timeout expires. Between each sent frame, the board waits for this amount of time.
// This function uses the get_command_parameter function to reads its parameter from USB.
void set_interrupt_mode_interval() {
  String parameter;
  boolean read_parameter = get_command_parameter(parameter);

  if (!read_parameter) {
    return;
  }
  
  uint16_t value = parameter.toInt();
  
  interrupt_mode_interval = value;
  Serial.println(interrupt_mode_interval);
}

// This function reads the range that the accelerometer should be sent to. The command parameter is read from USB with get_command_parameter.
// The values of the read parameter are in the range defined by ADXL313 library.
void set_range() {
  String parameter;
  boolean read_parameter = get_command_parameter(parameter);

  if (!read_parameter) {
    return;
  }
  
  uint8_t range = parameter.toInt();
  
  accelerometer.standby();
  accelerometer.setRange(range);
  accelerometer.measureModeOn();
  
  Serial.println(range);
}

// This function enables the interrupt mode. The accelerometer will also be set to automatically sleep.
// This function will also set the pin assigned for the BIG_LED_PIN to HIGH.
// The function will send on USB the frame ENABLED_INTERRUPTS
// When interrupts will be received from the accelerometer, the interrupt flag will be set to true.
void enable_interrupt_mode() {
  accelerometer.standby();

  // setup activity sensing options
  accelerometer.setActivityX(true);
  accelerometer.setActivityY(true);
  accelerometer.setActivityZ(false);
  accelerometer.setActivityThreshold(activity_threshold); // 0-255 (62.5mg/LSB)

  // setup inactivity sensing options
  accelerometer.setInactivityX(true);
  accelerometer.setInactivityY(true);
  accelerometer.setInactivityZ(false);
  accelerometer.setInactivityThreshold(activity_threshold);
  accelerometer.setTimeInactivity(inactivity_timeout);

  accelerometer.setInterruptMapping(ADXL313_INT_ACTIVITY_BIT, ADXL313_INT1_PIN);
  accelerometer.setInterruptMapping(ADXL313_INT_INACTIVITY_BIT, ADXL313_INT1_PIN);

  // enable/disable interrupts
  accelerometer.InactivityINT(true);
  accelerometer.ActivityINT(true);
  accelerometer.DataReadyINT(false);

  accelerometer.measureModeOn();
  attachInterrupt(digitalPinToInterrupt(2), trigger_interrupt_flag, RISING); // note, the INT output on the ADXL313 is default active HIGH.

  interrupt_mode = true;
  interrupt_flag = false;
  Serial.println(ENABLED_INTERRUPTS);
  digitalWrite(BIG_LED_PIN, HIGH);
}

// This function disables the interrupt mode. The accelerometer will disengage automatic sleep.
// This function will also set the pin assigned for the BIG_LED_PIN to LOW.
// The function will send on USB the frame DISABLED_INTERRUPTS
void disable_interrupt_mode() {
  accelerometer.standby();

  // enable/disable interrupts
  accelerometer.InactivityINT(false);
  accelerometer.ActivityINT(false);
  accelerometer.DataReadyINT(false);

  accelerometer.measureModeOn();
  
  detachInterrupt(digitalPinToInterrupt(2));

  interrupt_mode = false;
  interrupt_flag = false;
  accelerometer_awake = false;
  Serial.println(DISABLED_INTERRUPTS);
  digitalWrite(BIG_LED_PIN, LOW);
}

// The function gets the request read from USB. This function will read its header and call the correct function for each header. If no command is recognized, the function will reply with UNKNOWN_ERR.
// input: request - const String& - request header
void handle_request(const String &request) {
  if (REQUEST_FRAME == request) {
    send_frame();
  } else if (SET_RANGE == request) {
    set_range();
  } else if (END == request) {
    reset_board();
  } else if (ENABLE_INTERRUPTS == request) {
    enable_interrupt_mode();
  } else if (DISABLE_INTERRUPTS == request) {
    disable_interrupt_mode();
  } else if (SET_ACTIVITY_THRESHOLD == request) {
    set_activity_threshold();
  } else if (SET_INACTIVITY_TIMEOUT == request) {
    set_inactivity_timeout();
  } else if (SET_INTERRUPT_MODE_INTERVAL == request) {
    set_interrupt_mode_interval();
  } else {
    Serial.println(UNKNOWN_ERR);
  }
}

// Function automatically called by the board. Sets up initial variables and waits for a connection.
void setup() {
  // Init communications
  Serial.begin(115200);
  Wire.begin();

  pinMode(2, INPUT);
  pinMode(LED_PIN, OUTPUT);
  pinMode(BIG_LED_PIN, OUTPUT);

  digitalWrite(BIG_LED_PIN, LOW);

  delay(500);

  await_master_and_acknowledge();

  delay(100);

  // Send confirmation to master that accelerometer is operational
  if (false == accelerometer.begin()) {
    Serial.println(ACC_FAIL);
    blink_led(1000, LED_PIN);
  } else {
    Serial.println(ACC_SUCCESS);
  }

  accelerometer.standby();
  accelerometer.setRange(accelerometer_range);
  accelerometer.autosleepOff();
  accelerometer.measureModeOn();
}

// Function automatically called by the board inside an infinite loop.
void loop() {
  if (Serial.available()) {
    const String request = Serial.readStringUntil('\n');
    handle_request(request);
  }

  // if the interrupt flag was set, because the accelerometer sent an interrupt. Cannot be true outside of interrupt mode
  if (interrupt_flag) {
    accelerometer.updateIntSourceStatuses();

    // if activity was detected it sets the status as awake
    if (accelerometer.intSource.activity) {
      accelerometer_awake = true;
    }

    // if inactivity was detected it sets the status as asleep
    if (accelerometer.intSource.inactivity) {
      accelerometer_awake = false;
    }
  }

  // if the accelerometer is awake it sents a frame and waits for the interrupt_mode_interval amount of ms.
  if (accelerometer_awake) {
    send_frame();
    delay(interrupt_mode_interval);
  }
}


// Sets the interrupt flag to true.
void trigger_interrupt_flag() {
  interrupt_flag = true;
}
