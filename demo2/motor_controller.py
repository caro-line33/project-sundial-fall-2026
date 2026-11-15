import sys

for line in sys.stdin:
    command = line.strip()
    if command == "exit":
        break
    # Here you would add the logic to handle the command and control the motor
    print(f"Received command: {command}", flush=True)