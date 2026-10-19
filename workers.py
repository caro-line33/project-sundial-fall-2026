from PyQt6.QtCore import QThread, pyqtSignal
import paramiko

class ConnectWorker(QThread):
    success = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, ip, port, username, password):
        super().__init__()
        self.ip = ip
        self.port = port
        self.username = username
        self.password = password

    def run(self):
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        try:
            ssh.connect(
                hostname=self.ip,
                port=self.port,
                username=self.username,
                password=self.password,
                timeout=5
            )

            self.success.emit(ssh)

        except Exception as e:
            ssh.close()
            self.error.emit(str(e))

class Nema17Worker(QThread):
    success = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, ssh, en_pin, dir_pin, step_pin, m0_pin, m1_pin, m2_pin,
                 direction, steps, microstepping_mode):

        super().__init__()

        self.ssh_client = ssh
        self.en_pin = en_pin
        self.dir_pin = dir_pin
        self.step_pin = step_pin
        self.m0_pin = m0_pin
        self.m1_pin = m1_pin
        self.m2_pin = m2_pin
        self.direction = direction
        self.steps = steps
        self.microstepping_mode = microstepping_mode

    def run(self):
        if not self.ssh_client:
            self.error.emit("Raspberry Pi not connected. Please initialize SSH connection.")

        try:
            command = (
                f"python3 /home/ece489/ece480fall2026 nema17.py " 
                f"{self.en_pin} {self.dir_pin} {self.step_pin}" # args 1, 2, 3
                f"{self.m0_pin} {self.m1_pin} {self.m2_pin} {self.microstepping_mode}" # 4, 5, 6, 7
                f"{self.direction} {self.steps}" # 8, 9
            )

            stdin, stdout, stderr = self.ssh_client.exec_command(command)
            output = stdout.read().decode()
            error = stderr.read().decode()
            
            if output:
                self.signal.emit(f"Output: {output}")
            if error:
                self.error.emit(f"Error: {error}")

        except Exception as e:
            self.error.emit(f"Error executing : {e}")

class Nema23Worker(QThread):
    success = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, ssh, en_pin, dir_pin, step_pin,
                 direction, steps):

        super().__init__()

        self.ssh_client = ssh
        self.en_pin = en_pin
        self.dir_pin = dir_pin
        self.step_pin = step_pin
        self.direction = direction
        self.steps = steps

    def run(self):
        if not self.ssh_client:
            self.error.emit("Raspberry Pi not connected. Please initialize SSH connection.")

        try:
            command = (
                f"python3 /home/ece489/ece480fall2026 nema23.py " 
                f"{self.en_pin} {self.dir_pin} {self.step_pin}" # args 1, 2, 3
                f"{self.direction} {self.steps}"  # 4, 5
            )

            stdin, stdout, stderr = self.ssh_client.exec_command(command)
            output = stdout.read().decode()
            error = stderr.read().decode()
            
            if output:
                self.signal.emit(f"Output: {output}")
            if error:
                self.error.emit(f"Error: {error}")

        except Exception as e:
            self.error.emit(f"Error executing : {e}")
