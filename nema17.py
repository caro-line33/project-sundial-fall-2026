
from time import sleep
from gpiozero import OutputDevice
from gpiozero.pins.lgpio import LGPIOFactory
import sys

# Read parameters sent through SSH
enable_pin = int(sys.argv[1])
dir_pin = int(sys.argv[2])
step_pin = int(sys.argv[3])
m0 = int(sys.argv[4])
m1 = int(sys.argv[5])
m2 = int(sys.argv[6])
microstepping_mode = int(sys.argv[7])
direction = int(sys.argv[8])
steps = int(sys.argv[9])

# Validate parameters
if microstepping_mode not in (1, 2, 4, 8, 16, 32):
    raise ValueError("Invalid microstepping mode")

if direction not in (0, 1):
    raise ValueError("Direction must be 0 or 1")

if steps < 0:
    raise ValueError("Steps cannot be negative")

pi5 = LGPIOFactory()

# Initialize GPIO objects
ENABLE_CTRL = OutputDevice(
    enable_pin,
    pin_factory=pi5,
    active_high=False,
    initial_value=False
)

DIR_CTRL = OutputDevice(dir_pin, pin_factory=pi5)
STEP_CTRL = OutputDevice(step_pin, pin_factory=pi5)

M0 = OutputDevice(m0, pin_factory=pi5)
M1 = OutputDevice(m1, pin_factory=pi5)
M2 = OutputDevice(m2, pin_factory=pi5)

# DRV8825 microstepping lookup table
microstep_pin_levels = {
    1:  [0, 0, 0],
    2:  [1, 0, 0],
    4:  [0, 1, 0],
    8:  [1, 1, 0],
    16: [0, 0, 1],
    32: [1, 0, 1]
}

try:
    # Set microstepping mode
    M0.value, M1.value, M2.value = microstep_pin_levels[microstepping_mode]

    # Set direction
    DIR_CTRL.value = direction

    # Enable motor driver
    ENABLE_CTRL.on()
    sleep(0.01)

    # Move motor
    for _ in range(steps):
        STEP_CTRL.on()
        sleep(0.01)
        STEP_CTRL.off()
        sleep(0.01)

    print(f"Successfully moved {steps} steps")

finally:
    # Disable driver and release GPIO
    ENABLE_CTRL.off()

    DIR_CTRL.close()
    STEP_CTRL.close()
    ENABLE_CTRL.close()
    M0.close()
    M1.close()
    M2.close()
