import sys
import time
import threading

from gpiozero import DigitalInputDevice, DigitalOutputDevice
from gpiozero.pins.lgpio import LGPIOFactory

factory = LGPIOFactory()

# ==========================================
# GPIO CONFIGURATION
# ==========================================

# Optical sensors
sensor7 = DigitalInputDevice(
    7, pull_up=True, bounce_time=0.01,
    pin_factory=factory
)

sensor8 = DigitalInputDevice(
    8, pull_up=True, bounce_time=0.01,
    pin_factory=factory
)

# Mechanical limit switches
switch20 = DigitalInputDevice(
    20, pull_up=True, bounce_time=0.01,
    pin_factory=factory
)

switch21 = DigitalInputDevice(
    21, pull_up=True, bounce_time=0.01,
    pin_factory=factory
)

# NEMA 23 motor
direction = DigitalOutputDevice(
    6, pin_factory=factory
)

step = DigitalOutputDevice(
    26, pin_factory=factory
)

enable = DigitalOutputDevice(
    5,
    active_high=False,
    initial_value=False,
    pin_factory=factory
)

# ==========================================
# SHARED STATE
# ==========================================

moving = threading.Event()
shutdown = threading.Event()

state_lock = threading.RLock()

# +1 = forward, -1 = backward
motor_direction = 1

# This is the logical sensor state.
# Adjust if optical sensor polarity differs.
def sensor7_engaged():
    return not sensor7.is_active

def sensor8_engaged():
    return not sensor8.is_active

# Mechanical NC-to-GND switches:
# pressed -> GPIO HIGH -> is_active False
def forward_limit():
    return not switch20.is_active

def backward_limit():
    return not switch21.is_active


# ==========================================
# POSITION INFORMATION
# ==========================================

def at_home():
    return sensor7_engaged() and sensor8_engaged()


def at_dut_location():
    return sensor7_engaged()


def print_status():
    print(
        f"STATUS "
        f"HOME={at_home()} "
        f"DUT_ALIGNED={at_dut_location()} "
        f"FORWARD_LIMIT={forward_limit()} "
        f"BACKWARD_LIMIT={backward_limit()} "
        f"MOVING={moving.is_set()}",
        flush=True
    )


# ==========================================
# MOTOR SAFETY
# ==========================================

def can_move_nema23(requested_direction):
    if nema17_moving.is_set():
        return False

    if requested_direction == 1 and forward_limit():
        return False

    if requested_direction == -1 and backward_limit():
        return False

    return True


def can_move_nema17():
    return backward_limit() and not forward_limit()


def stop_motor(reason="STOPPED"):
    with state_lock:
        moving.clear()

    print(reason, flush=True)


# ==========================================
# SENSOR CALLBACKS
# ==========================================

def optical_sensor_changed():
    if at_home():
        print("DUT_HOME_POSITION", flush=True)

    elif at_dut_location():
        print("DUT_ALIGNED", flush=True)

    else:
        print("DUT_NOT_ALIGNED", flush=True)

    print_status()


def forward_limit_engaged():
    print("FORWARD_LIMIT_ENGAGED", flush=True)

    with state_lock:
        if moving.is_set() and motor_direction == 1:
            moving.clear()
            print("NEMA23_FORWARD_BLOCKED", flush=True)

    print("NEMA17_ROTATION_BLOCKED", flush=True)
    print_status()


def backward_limit_engaged():
    print("BACKWARD_LIMIT_ENGAGED", flush=True)

    with state_lock:
        if moving.is_set() and motor_direction == -1:
            moving.clear()
            print("NEMA23_BACKWARD_BLOCKED", flush=True)

    print_status()


def forward_limit_released():
    print("FORWARD_LIMIT_RELEASED", flush=True)
    print_status()


def backward_limit_released():
    print("BACKWARD_LIMIT_RELEASED", flush=True)
    print_status()


# Optical sensors: assumed engaged when HIGH
sensor7.when_deactivated = optical_sensor_changed
sensor7.when_activated = optical_sensor_changed

sensor8.when_deactivated = optical_sensor_changed
sensor8.when_activated = optical_sensor_changed

# NC mechanical switches: engaged when HIGH
switch20.when_deactivated = forward_limit_engaged
switch20.when_activated = forward_limit_released

switch21.when_deactivated = backward_limit_engaged
switch21.when_activated = backward_limit_released


# ==========================================
# MOTOR WORKER
# ==========================================

def motor_worker():
    while not shutdown.is_set():

        moving.wait(timeout=0.1)

        if shutdown.is_set():
            break

        while moving.is_set() and not shutdown.is_set():

            with state_lock:
                if not can_move_nema23(motor_direction):
                    moving.clear()
                    print("MOTION_BLOCKED_BY_LIMIT", flush=True)
                    break

                # Keep the lock while issuing the pulse
                # so commands/callbacks cannot change
                # motor state in the middle of it.
                step.on()
                time.sleep(0.001)
                step.off()

            time.sleep(0.005)

    step.off()
    enable.off()


# ==========================================
# COMMAND HANDLING
# ==========================================

def start_motor(requested_direction):
    global motor_direction

    with state_lock:
        if not can_move_nema23(requested_direction):
            print("ERROR: LIMIT SWITCH BLOCKS MOVEMENT", flush=True)
            return

        # Stop previous movement before reversing.
        moving.clear()

        motor_direction = requested_direction

        if requested_direction == 1:
            direction.on()
            print("NEMA23_FORWARD", flush=True)
        else:
            direction.off()
            print("NEMA23_BACKWARD", flush=True)

        enable.on()
        moving.set()


def main():
    motor_thread = threading.Thread(
        target=motor_worker,
        name="NEMA23Worker"
    )

    motor_thread.start()

    print("READY", flush=True)
    print_status()

    try:
        for line in sys.stdin:
            command = line.strip().upper()

            if command in ("FORWARD", "START FORWARD"):
                start_motor(1)

            elif command in ("BACKWARD", "START BACKWARD"):
                start_motor(-1)

            elif command == "START":
                start_motor(1)

            elif command == "STOP":
                stop_motor()

            elif command == "STATUS":
                print_status()

            elif command == "QUIT":
                break

            else:
                print(f"UNKNOWN_COMMAND: {command}", flush=True)

    finally:
        moving.clear()
        shutdown.set()

        motor_thread.join()

        step.off()
        enable.off()

        sensor7.close()
        sensor8.close()
        switch20.close()
        switch21.close()

        direction.close()
        step.close()
        enable.close()

        factory.close()

        print("SHUTDOWN_COMPLETE", flush=True)


if __name__ == "__main__":
    main()