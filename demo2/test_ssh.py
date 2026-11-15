import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

ssh.connect('35.9.42.197', username='ece489', password='Sundial', port=22)
stdin, stdout, stderr = ssh.exec_command("echo hello")
print(stdout.read().decode())
stdin, stdout, stderr = ssh.exec_command('python3 -u /home/ece489/ece480fall2026/demo2/motor_controller.py')

while True:
    command = input("Enter command to send to motor controller (or 'exit' to quit): ")

    if command.lower() == 'exit':
        break

    stdin.write(command + '\n')
    stdin.flush()

    response = stdout.readline().strip()
    print(f"Motor controller response: {response}")

ssh.close()
