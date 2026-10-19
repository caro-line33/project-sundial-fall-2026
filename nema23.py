from time import sleep
from gpiozero import OutputDevice
from gpiozero.pins.lgpio import LGPIOFactory
import sys

# Read parameters from SSH command
enable_pin = int(sys.argv[1])
dir_pin = int(sys.argv[2])
step_pin = int(sys.argv[3])
direction = int(sys.argv[4])
steps = int(sys.argv[5])

# Validate parameters
if direction not in (0, 1):
    raise ValueError("Direction must be 0 or 1")

if steps < 0:
    raise ValueError("Steps cannot be negative")

# Initialize Raspberry Pi 5 GPIO
pi5 = LGPIOFactory()

# Initialize pin objects
ENABLE_CTRL = OutputDevice(
    enable_pin,
    pin_factory=pi5,
    active_high=False,
    initial_value=False
)

DIR_CTRL = OutputDevice(dir_pin, pin_factory=pi5)
STEP_CTRL = OutputDevice(step_pin, pin_factory=pi5)

try:
    # Set motor direction
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

    print(f"Successfully moved NEMA 23 by {steps} pulses")

finally:
    # Disable motor and release GPIO
    ENABLE_CTRL.off()

    DIR_CTRL.close()
    STEP_CTRL.close()
    ENABLE_CTRL.close()
