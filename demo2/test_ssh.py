import paramiko
import threading

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

ssh.connect('35.9.42.197', username='ece489', password='Sundial', port=22)

stdin, stdout, stderr = ssh.exec_command(
    "python3 -u /home/ece489/ece480fall2026/demo2/motor_controller.py"
)


def read_output():
    for line in stdout:
        print("PI:", line.strip())


# Background thread receives messages
reader = threading.Thread(target=read_output)
reader.start()

try:
    while True:
        command = input("Command: ")

        stdin.write(command + "\n")
        stdin.flush()

        if command == "QUIT":
            break

finally:
    # Ask the Pi to exit if still connected
    if not stdin.closed and not stdout.channel.closed:
        stdin.write("QUIT\n")
        stdin.flush()

    reader.join(timeout=2)
    ssh.close()
