import sys
from time import sleep
import pigpio

# GET PIN NUMBERS AND MICROSTEPPING MODE INFO FROM COMMAND LINE ARGUMENTS
enable_pin = sys.argv[1]
steps_pin = sys.argv[2]
dir_pin = sys.argv[3]
m0 = sys.argv[4]
m1 = sys.argv[5]
m2 = sys.argv[6]
microsteps = sys.argv[7]

# CONNECT TO PIGPIO DAEMON
pi = pigpio.pi()

# DETERMINE WHAT TO WRITE TO M0, M1, M2 BASED ON SELECTED MICROSTEPPING MODE
microstep_pin_levels = {
            1: [0, 0, 0],
            2: [0, 0, 1],
            4: [0, 1, 0],
            8: [0, 1, 1],
            16: [1, 0, 0],
            32: [1, 1, 0]
        }

m0_level, m1_level, m2_level = microstep_pin_levels[microsteps]

# SET ALL PINS AS OUTPUTS
pi.set_mode(enable, pigpio.OUTPUT)
pi.set_mode(steps, pigpio.OUTPUT)
pi.set_mode(dir, pigpio.OUTPUT)
pi.set_mode(m0, pigpio.OUTPUT)
pi.set_mode(m1, pigpio.OUTPUT)
pi.set_mode(m2, pigpio.OUTPUT)

# WRITE APPROPRIATE LEVELS TO MICROSTEPPING MODE PINS
pi.write(m0, m0_level)
pi.write(m1, m1_level)
pi.write(m2, m2_level)

# 