class Controller:
    def __init__(self, ssh):
        self.ssh = ssh

    def move_17(self, steps, direction, en, step, dir, m0, m1, m2, microsteps=1):

        microstep_pin_levels = {
            1: [0, 0, 0],
            2: [1, 0, 0],
            4: [0, 1, 0],
            8: [1, 1, 0],
            16: [0, 0, 1],
            32: [0, 1, 1]
        }

        m2, m1, m0 = microstep_pin_levels[microsteps]
        command = (
            f"python3 /home/pi/nema17.py "
            f"nema17 {int(en)} {int(steps)} {int(direction)}"
            f"{int(m0)} {int(m1)} {int(m2)} {int(microsteps)}"
        )

        stdin, stdout, stderr = self.ssh.exec_command(command)

        output = stdout.read().decode()
        error = stderr.read().decode()
        exit_code = stdout.channel.recv_exit_status()

        if exit_code != 0:
            raise RuntimeError(error or "Motor command failed")

        return output

    def move_23(self, steps, direction, en, step, dir):

        command = (
            f"python3 /home/pi/nema23.py "
            f"nema23 {int(en)} {int(steps)} {int(direction)}"
        )

        stdin, stdout, stderr = self.ssh.exec_command(command)

        output = stdout.read().decode()
        error = stderr.read().decode()
        exit_code = stdout.channel.recv_exit_status()

        if exit_code != 0:
            raise RuntimeError(error or "Motor command failed")

        return output