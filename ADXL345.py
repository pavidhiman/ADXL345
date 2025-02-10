"""
Test script for ADXL345 Accelerometer

Lot's of information was taken from the sensor datasheet, including: 
- The alternate address of 0x53 for the I2C address
- Acceptable limits for the self-test
- Assumed full resolution for the sensor (16g range)
- Based on the PDF image, the I2C pins are:
    - SDA -- MCU_D101
    - SCL -- MCU_DI02

"""

import time
import struct
import traceback 
#importing implemented zip test module
from zip_test_fwk import ZipTestBoard

# setting preamble configurations for sensors
ADXL345_ADDRESS = 0x53 #alternate default from datasheet

#addresses from datasheet
REG_BW_RATE = 0x2C #data rate output
REG_POWER_CTL = 0x2D #power saving
REG_DATA_FORMAT = 0x31  # data format (full-resolution, self-test)
REG_DATAX0 = 0x32 

#configuration
BW_RATE_800HZ = 0x0D  # 800 hz max data output with 40 kHz I2C
DATA_FORMAT_NORMAL = 0x0B  # self-test disabled
DATA_FORMAT_SELF_TEST = 0x8B  # same as normal but including self-test 
POWER_CTL_MEASURE     = 0x08

# ±16g mode, average sensitivity = 3.9 mg/LSB (range is 3.5 to 4.3)
ACCEL_SCALE = 0.0039  # g per LSB

# Self test table 8 -- difference is -1.05g for x and y and -0.85g for z
# rounding to -1.2 and -0.9 for X and Y and -1.0 to -0.7 for z. The rounding accounts for any variation due to 3V3 battery
SELF_TEST_THRESHOLDS = {
    'x': (-1.2, -0.9),
    'y': (-1.2, -0.9),
    'z': (-1.0, -0.7)
}

# Accelerometer Tester Class 

class AccelerometerTester:
    def __init__(self):
        self.board = None          # Zip Test Board instance
        self.start_time = None
        self.test_passed = False
        self.failure_reason = None # empty string hold error if failed

    def run_test(self):
        self.start_time = time.time()
        try:
            self.board = ZipTestBoard()
            self.board.turn_on_ps("3V3") #power for 3.3V source 
            
            #I2C pin connections --  SDA = "MCU_DIO1" and SCL = "MCU_DIO2" (based on diagram)
            self.board.i2c_setup("MCU_DIO1", "MCU_DIO2", 400000)
            self._configure_accelerometer()
            self._perform_self_test()

            # actuator 
            self._actuator_test("slow_climb", self._check_slow_climb)
            self._actuator_test("sharp_turn", self._check_sharp_turn)
            self._actuator_test("quick_drop", self._check_quick_drop)

            self.test_passed = True
        except Exception:
            self.failure_reason = traceback.format_exc()
        finally:
            self._log_result()
            if self.board:
                try:
                    self.board.turn_off_ps("3V3")
                except Exception:
                    pass 

    def _configure_accelerometer(self):
        self.board.i2c_cmd(ADXL345_ADDRESS, [REG_BW_RATE, BW_RATE_800HZ])
        self.board.i2c_cmd(ADXL345_ADDRESS, [REG_DATA_FORMAT, DATA_FORMAT_NORMAL])
        self.board.i2c_cmd(ADXL345_ADDRESS, [REG_POWER_CTL, POWER_CTL_MEASURE])
        time.sleep(0.1)  # 100ms for configuration 


    # sensor self test -- baseline without self-test -> enabling self test -> comparing delta against thresholds 
    # 100ms sensor delay 
    def _perform_self_test(self):
        # self-test off 
        self.board.i2c_cmd(ADXL345_ADDRESS, [REG_DATA_FORMAT, DATA_FORMAT_NORMAL])
        time.sleep(0.1)
        baseline = self._read_acceleration()

        # self-test on
        self.board.i2c_cmd(ADXL345_ADDRESS, [REG_DATA_FORMAT, DATA_FORMAT_SELF_TEST])
        time.sleep(0.1)
        st_reading = self._read_acceleration()

        self.board.i2c_cmd(ADXL345_ADDRESS, [REG_DATA_FORMAT, DATA_FORMAT_NORMAL])

        # comparing delta against thresholds 
        delta = {axis: st_reading[axis] - baseline[axis] for axis in ['x', 'y', 'z']}
        for axis, (min_thresh, max_thresh) in SELF_TEST_THRESHOLDS.items():
            if not (min_thresh <= delta[axis] <= max_thresh):
                raise ValueError(
                    f"The self-test was failed on {axis} axis: difference of {delta[axis]:.2f}g is not in [{min_thresh}, {max_thresh}]g"
                )

    # reading acceleration data 
    def _read_acceleration(self):
        data = self.board.i2c_cmd(ADXL345_ADDRESS, [REG_DATAX0], resp_len=6)
        x, y, z = struct.unpack('<hhh', bytes(data))
        return {'x': x * ACCEL_SCALE, 'y': y * ACCEL_SCALE, 'z': z * ACCEL_SCALE}

    # commanding actuator to move DUT -> read accelerometer -> check reading 
    # run actuator based on command and move config based on that 
    def _actuator_test(self, config, check_func):
        self.board.actuator_move(config)
        accel = self._read_acceleration()
        check_func(accel) #using class for accelerometer 

    # slow climb -- y-axis: -1 <= a <= 1; z-axis: 6 <= a <= 8 
    def _check_slow_climb(self, accel):
        if not (-1.0 <= accel['y'] <= 1.0):
            raise ValueError(f"Slow climb: y-axis {accel['y']:.2f}g not in [-1, 1]g")
        if not (6.0 <= accel['z'] <= 8.0):
            raise ValueError(f"Slow climb: z-axis {accel['z']:.2f}g not in [6, 8]g")

    # x > 5 and y > 5
    def _check_sharp_turn(self, accel):
        if not (accel['x'] > 5.0 and accel['y'] > 5.0):
            raise ValueError(f"Sharp turn: X {accel['x']:.2f}g or Y {accel['y']:.2f}g not > 5g")

    # z-axis: a < -8 
    def _check_quick_drop(self, accel):
        if not (accel['z'] < -8.0):
            raise ValueError(f"Quick drop: Z axis {accel['z']:.2f}g not < -8g")

    # printing time elapsed and errors if failed 
    def _log_result(self):
        elapsed = time.time() - self.start_time
        if self.test_passed:
            print(f"TEST PASSED in {elapsed:.2f} sec")
        else:
            print(f"TEST FAILED in {elapsed:.2f} sec due to {self.failure_reason}")

# main function for testing 
def main():
    testing = AccelerometerTester()
    testing.run_test()