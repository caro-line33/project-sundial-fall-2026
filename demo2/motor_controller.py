
import sys
import time
import threading

# Shared between the main thread and motor thread
moving = threading.Event()
shutdown = threading.Event()


def motor_worker():
    while not shutdown.is_set():

        # Wait until START is received
        moving.wait()

        if shutdown.is_set():
            break

        # Simulate one motor step
        if moving.is_set():
            print("STEP", flush=True)
            time.sleep(0.2)


def main():
    motor_thread = threading.Thread(target=motor_worker)
    motor_thread.start()

    print("READY", flush=True)

    try:
        # Main thread listens for SSH commands
        for line in sys.stdin:
            command = line.strip()

            if command == "START":
                moving.set()
                print("STARTED", flush=True)

            elif command == "STOP":
                moving.clear()
                print("STOPPED", flush=True)

            elif command == "QUIT":
                break

    finally:
        moving.clear()
        shutdown.set()
        moving.set()  # Wake thread so it can exit
        motor_thread.join()


if __name__ == "__main__":
    main()
