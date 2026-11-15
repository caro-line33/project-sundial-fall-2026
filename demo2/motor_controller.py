import sys
import time
import threading
from gpiozero import DigitalInputDevice, DigitalOutputDevice
from gpiozero.pins.lgpio import LGPIOFactory

# GPIO numbering is BCM. Verify wiring and polarity before applying motor power.
factory = LGPIOFactory()

sensor7 = DigitalInputDevice(7, pull_up=True, bounce_time=0.01, pin_factory=factory)
sensor8 = DigitalInputDevice(8, pull_up=True, bounce_time=0.01, pin_factory=factory)
switch20 = DigitalInputDevice(20, pull_up=True, bounce_time=0.01, pin_factory=factory)
switch21 = DigitalInputDevice(21, pull_up=True, bounce_time=0.01, pin_factory=factory)

PUL23 = DigitalOutputDevice(23, pin_factory=factory)
DIR23 = DigitalOutputDevice(22, pin_factory=factory)
ENA23 = DigitalOutputDevice(24, active_high=False, initial_value=False, pin_factory=factory)
PUL17 = DigitalOutputDevice(26, pin_factory=factory)
DIR17 = DigitalOutputDevice(6, pin_factory=factory)
ENA17 = DigitalOutputDevice(5, active_high=False, initial_value=False, pin_factory=factory)

# IMPORTANT: Set these after testing raw input states with motors disconnected.
# With pull_up=True, .is_active is True for a LOW GPIO level.
# NC-to-ground mechanical switches are usually pressed when .is_active is False.
OPTICAL_ENGAGED_WHEN_ACTIVE = True
LIMIT_ENGAGED_WHEN_ACTIVE = True

STEP_HIGH_S = 0.001
STEP_LOW_S = 0.005

moving17 = threading.Event()
moving23 = threading.Event()
shutdown = threading.Event()
state_lock = threading.RLock()

# All fields below are accessed/modified under state_lock.
direction17 = 1
direction23 = 1
remaining17 = None
remaining23 = None


def engaged(device, engaged_when_active):
    return device.is_active == engaged_when_active


def sensor7_engaged():
    return engaged(sensor7, OPTICAL_ENGAGED_WHEN_ACTIVE)


def sensor8_engaged():
    return engaged(sensor8, OPTICAL_ENGAGED_WHEN_ACTIVE)


def forward_limit():
    return engaged(switch20, LIMIT_ENGAGED_WHEN_ACTIVE)


def backward_limit():
    return engaged(switch21, LIMIT_ENGAGED_WHEN_ACTIVE)


def home_position():
    return sensor7_engaged() and sensor8_engaged()


def dut_aligned():
    return sensor7_engaged()


def can_move_17():
    return backward_limit() and not forward_limit() and not moving23.is_set()


def can_move_23(direction):
    if moving17.is_set():
        return False
    if forward_limit() and backward_limit():
        return False
    if direction == 1:
        return not forward_limit() and dut_aligned()
    return not backward_limit()


def print_status():
    with state_lock:
        print(
            'STATUS '
            f'SENSOR7={sensor7_engaged()} SENSOR8={sensor8_engaged()} '
            f'HOME={home_position()} DUT_ALIGNED={dut_aligned()} '
            f'FORWARD_LIMIT={forward_limit()} BACKWARD_LIMIT={backward_limit()} '
            f'MOVING17={moving17.is_set()} MOVING23={moving23.is_set()} '
            f'REMAINING17={remaining17 if remaining17 is not None else "CONTINUOUS"} '
            f'REMAINING23={remaining23 if remaining23 is not None else "CONTINUOUS"}',
            flush=True,
        )


def stop_locked(motor):
    global remaining17, remaining23
    if motor in ('17', 'ALL'):
        moving17.clear()
        remaining17 = None
        PUL17.off()
        ENA17.off()
    if motor in ('23', 'ALL'):
        moving23.clear()
        remaining23 = None
        PUL23.off()
        ENA23.off()


def stop_motor(motor, reason='STOPPED'):
    with state_lock:
        stop_locked(motor)
    print(f'{reason} MOTOR={motor}', flush=True)
    print_status()


def sensor_changed():
    with state_lock:
        # Losing alignment during forward insertion must halt motion.
        if moving23.is_set() and direction23 == 1 and not dut_aligned():
            stop_locked('23')
            print('NEMA23_STOPPED_ALIGNMENT_LOST', flush=True)
        if home_position():
            print('DUT_HOME_POSITION', flush=True)
        elif dut_aligned():
            print('DUT_ALIGNED', flush=True)
        else:
            print('DUT_NOT_ALIGNED', flush=True)
    print_status()


def limits_changed():
    with state_lock:
        if moving23.is_set() and not can_move_23(direction23):
            stop_locked('23')
            print('NEMA23_STOPPED_INTERLOCK', flush=True)
        if moving17.is_set() and not can_move_17():
            stop_locked('17')
            print('NEMA17_STOPPED_INTERLOCK', flush=True)
    print_status()


for device in (sensor7, sensor8):
    device.when_activated = sensor_changed
    device.when_deactivated = sensor_changed
for device in (switch20, switch21):
    device.when_activated = limits_changed
    device.when_deactivated = limits_changed


def motor_worker(motor):
    global remaining17, remaining23
    is17 = motor == '17'
    event = moving17 if is17 else moving23
    pulse = PUL17 if is17 else PUL23
    while not shutdown.is_set():
        if not event.wait(timeout=0.1):
            continue
        with state_lock:
            if shutdown.is_set() or not event.is_set():
                continue
            permitted = can_move_17() if is17 else can_move_23(direction23)
            if not permitted:
                stop_locked(motor)
                print(f'NEMA{motor}_STOPPED_INTERLOCK', flush=True)
                continue
            remaining = remaining17 if is17 else remaining23
            if remaining is not None and remaining <= 0:
                stop_locked(motor)
                print(f'NEMA{motor}_COMPLETE', flush=True)
                continue
            pulse.on()
            time.sleep(STEP_HIGH_S)
            pulse.off()
            if remaining is not None:
                remaining -= 1
                if is17:
                    remaining17 = remaining
                else:
                    remaining23 = remaining
                if remaining == 0:
                    stop_locked(motor)
                    print(f'NEMA{motor}_COMPLETE', flush=True)
        # Do not hold the lock while idle between pulses.
        shutdown.wait(STEP_LOW_S)
    with state_lock:
        stop_locked(motor)


def start_motor(motor, direction, steps=None):
    global direction17, direction23, remaining17, remaining23
    if direction not in (-1, 1) or (steps is not None and steps <= 0):
        print('ERROR_INVALID_MOVE', flush=True)
        return
    with state_lock:
        if shutdown.is_set():
            return
        event = moving17 if motor == '17' else moving23
        if event.is_set():
            print(f'ERROR_NEMA{motor}_BUSY_STOP_FIRST', flush=True)
            return
        permitted = can_move_17() if motor == '17' else can_move_23(direction)
        if not permitted:
            print(f'ERROR_NEMA{motor}_INTERLOCK', flush=True)
            return
        if motor == '17':
            direction17 = direction
            remaining17 = steps
            DIR17.on() if direction == 1 else DIR17.off()
            ENA17.on()
        else:
            direction23 = direction
            remaining23 = steps
            DIR23.on() if direction == 1 else DIR23.off()
            ENA23.on()
        event.set()
    mode = 'CONTINUOUS' if steps is None else f'STEPS={steps}'
    print(f'NEMA{motor}_STARTED DIRECTION={direction} {mode}', flush=True)
    print_status()


def process_command(line):
    parts = line.strip().upper().split()
    if not parts:
        return True
    command = parts[0]
    if command == 'QUIT':
        return False
    if command == 'STATUS' and len(parts) == 1:
        print_status()
    elif command == 'STOP' and len(parts) == 2 and parts[1] in ('17', '23', 'ALL'):
        stop_motor(parts[1])
    elif command == 'MOVE' and len(parts) in (3, 4):
        motor = parts[1]
        direction = {'FORWARD': 1, 'BACKWARD': -1, 'CW': 1, 'CCW': -1}.get(parts[2])
        if motor not in ('17', '23') or direction is None:
            print('ERROR_USAGE MOVE 17|23 FORWARD|BACKWARD [STEPS]', flush=True)
            return True
        try:
            steps = int(parts[3]) if len(parts) == 4 else None
        except ValueError:
            print('ERROR_INVALID_STEPS', flush=True)
            return True
        start_motor(motor, direction, steps)
    else:
        print('ERROR_UNKNOWN_COMMAND', flush=True)
    return True


def main():
    threads = [
        threading.Thread(target=motor_worker, args=('17',), name='NEMA17Worker'),
        threading.Thread(target=motor_worker, args=('23',), name='NEMA23Worker'),
    ]
    for thread in threads:
        thread.start()
    print('READY', flush=True)
    print_status()
    try:
        for line in sys.stdin:
            if not process_command(line):
                break
    except KeyboardInterrupt:
        pass
    finally:
        shutdown.set()
        with state_lock:
            stop_locked('ALL')
        for thread in threads:
            thread.join()
        for device in (sensor7, sensor8, switch20, switch21,
                       PUL17, DIR17, ENA17, PUL23, DIR23, ENA23):
            device.close()
        factory.close()
        print('SHUTDOWN_COMPLETE', flush=True)


if __name__ == '__main__':
    main()
