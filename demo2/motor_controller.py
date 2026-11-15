from faulthandler import enable
from multiprocessing.dummy import shutdown
import sys
import time
import threading

from gpiozero import DigitalInputDevice, DigitalOutputDevice
from gpiozero.pins.lgpio import LGPIOFactory

# ==========================================
# GPIO CONFIGURATION
# ==========================================

factory = LGPIOFactory()

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
PUL23 = DigitalOutputDevice(23, pin_factory=factory)
DIR23 = DigitalOutputDevice(22, pin_factory=factory)
ENA23 = DigitalOutputDevice(24, active_high=False, initial_value=False, pin_factory=factory)

# NEMA 17 motor
PUL17 = DigitalOutputDevice(26, pin_factory=factory)
DIR17 = DigitalOutputDevice(6, pin_factory=factory)
ENA17 = DigitalOutputDevice(5, active_high=False, initial_value=False, pin_factory=factory)

# ==========================================
# SHARED STATES
# ==========================================

moving23 = threading.Event()
moving17 = threading.Event()
shutdown23 = threading.Event()
shutdown17 = threading.Event()
state_lock = threading.RLock()
direction23 = 1
direction17 = 1

# ==========================================
# MOTOR SAFETY & CONTROL
# ==========================================

def home_position():
    return sensor7.is_active and sensor8.is_active

def dut_aligned():
    return sensor7.is_active

def forward_limit():
    return switch20.is_active

def backward_limit():
    return switch21.is_active

def can_move_nema23(requested_direction):

    # cannot move if NEMA 17 is moving
    if moving17.is_set():
        return False

    # can only move forward if the DUT and PIB are aligned and forward limit is not engaged
    if requested_direction == 1 and forward_limit() and not dut_aligned():
        return False

    # can only move backward if backward limit not yet engaged
    if requested_direction == -1 and backward_limit():
        return False

    return True

def can_move_nema17():
    # can only move when the DUT is as far back as possible (backward limit engaged) and forward limit not engaged
    return backward_limit() and not forward_limit()

def print_status():
    print(
        f"STATUS "
        f"HOME={home_position()} "
        f"DUT_ALIGNED={dut_aligned()} "
        f"FORWARD_LIMIT={forward_limit()} "
        f"BACKWARD_LIMIT={backward_limit()} "
        f"MOVING 17={moving17.is_set()} "
        f"MOVING 23={moving23.is_set()}"
        flush=True
    )


def stop_17(reason="STOPPED"):
    with state_lock:
        moving17.clear()
    print(reason, flush=True)

def stop_23(reason="STOPPED"):
    with state_lock:
        moving23.clear()
    print(reason, flush=True)

# ==========================================
# SENSOR CALLBACKS
# ==========================================

def optical_sensor_changed():
    if home_position(): print("DUT_HOME_POSITION", flush=True)

    elif dut_aligned(): print("DUT_ALIGNED", flush=True)

    else: print("DUT_NOT_ALIGNED", flush=True)

    print_status()

def forward_limit_engaged():
    print("FORWARD_LIMIT_ENGAGED", flush=True)

    with state_lock:
        if moving23.is_set() and direction23 == 1:
            moving23.clear()
            print("NEMA23_FORWARD_BLOCKED", flush=True)

    print("NEMA17_ROTATION_BLOCKED", flush=True)
    print_status()

def backward_limit_engaged():
    print("BACKWARD_LIMIT_ENGAGED", flush=True)

    with state_lock:
        if moving23.is_set() and direction23 == -1:
            moving23.clear()
            print("NEMA23_BACKWARD_BLOCKED", flush=True)

    print_status()

def forward_limit_released():
    print("FORWARD_LIMIT_RELEASED", flush=True)
    print_status()

def backward_limit_released():
    print("BACKWARD_LIMIT_RELEASED", flush=True)
    print_status()

# Optical sensors
sensor7.when_deactivated = optical_sensor_changed
sensor7.when_activated = optical_sensor_changed
sensor8.when_deactivated = optical_sensor_changed
sensor8.when_activated = optical_sensor_changed

# Mechanical switches
switch20.when_activated = forward_limit_engaged
switch20.when_deactivated = forward_limit_released
switch21.when_activated = backward_limit_engaged
switch21.when_deactivated = backward_limit_released

# ==========================================
# NEMA17 WORKER
# ==========================================

def motor_worker17():
    while not shutdown17.is_set():
        moving17.wait(timeout=0.1)  
        if shutdown17.is_set(): break

        while moving17.is_set() and not shutdown17.is_set():
            with state_lock:
                if not can_move_nema17():
                    moving17.clear()
                    print("MOTION_BLOCKED_BY_LIMIT", flush=True)
                    break

                # Keep the lock while issuing the pulse
                # so commands/callbacks cannot change
                # motor state in the middle of it.
                PUL17.on()
                time.sleep(0.001)
                PUL17.off()

            time.sleep(0.005)

    PUL17.off()
    ENA17.off()

# ==========================================
# NEMA17 WORKER
# ==========================================

def motor_worker23():
    while not shutdown23.is_set():

        moving23.wait(timeout=0.1)

        if shutdown23.is_set():
            break

        while moving23.is_set() and not shutdown23.is_set():

            with state_lock:
                if not can_move_nema23(motor_direction):
                    moving23.clear()
                    print("MOTION_BLOCKED_BY_LIMIT", flush=True)
                    break

                # Keep the lock while issuing the pulse
                # so commands/callbacks cannot change
                # motor state in the middle of it.
                PUL23.on()
                time.sleep(0.001)
                PUL23.off()

            time.sleep(0.005)

    PUL23.off()
    ENA23.off()


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
