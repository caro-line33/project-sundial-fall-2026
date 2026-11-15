
import sys
import time
import threading

from gpiozero import DigitalOutputDevice
from gpiozero.pins.lgpio import LGPIOFactory

factory = LGPIOFactory()

direction = DigitalOutputDevice(20, pin_factory=factory)
step = DigitalOutputDevice(21, pin_factory=factory)
enable = DigitalOutputDevice(
    12,
    active_high=False,
    initial_value=False,
    pin_factory=factory
)

moving = threading.Event()
shutdown = threading.Event()

# One motor worker thread
def motor_worker():
    while not shutdown.is_set():

        # Wait until START is received
        moving.wait(timeout=0.1)

        if shutdown.is_set():
            break

        while moving.is_set() and not shutdown.is_set():
            step.on()
            time.sleep(0.001)
            step.off()
            time.sleep(0.005)

    step.off()
    enable.off()


def main():
    motor_thread = threading.Thread(target=motor_worker)
    motor_thread.start()

    print("READY", flush=True)

    try:
        # Main thread listens for commands
        for line in sys.stdin:
            args = line.strip().split()

            if not args:
                continue

            if args[0] == "START":
                direction.on()  # Forward
                enable.on()
                moving.set()
                print("STARTED", flush=True)

            elif args[0] == "STOP":
                moving.clear()
                print("STOPPED", flush=True)

            elif args[0] == "QUIT":
                break

    finally:
        moving.clear()
        shutdown.set()
        motor_thread.join()

        step.off()
        enable.off()

        direction.close()
        step.close()
        enable.close()
        factory.close()


if __name__ == "__main__":
    main()
