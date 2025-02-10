# ADXL345 Accelerometer
Test script to run the ADXL345 accelerometer with a Zip Test Board to provide power and an actuator which controls the internal DUT (device under test) configurations. 

All key threshold values were taken from the Analog Devices ADXL345 datasheet. This script was written for a 16g full-resolution sensor and specifically:

    > Configures the accelerometer to output valid x,y,z measurements at the maximum data rate (currently 800 Hz)
    > Runs self-tests to ensure the results are within acceptable ranges
    > Three possible actuator configurations based on actuator test and relevant axes:
        1. slow_climb -- y-axis and z-axis restrictions 
        2. sharp_turn -- x-axis and y-axis restrictions
        3. quick_drop -- z-axis restrictions 
        
This test returns the elapsed time in all tests were passed, otherwise returns the elapsed time with the associated error. 
