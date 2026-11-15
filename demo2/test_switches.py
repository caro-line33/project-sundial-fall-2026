from gpiozero import DigitalInputDevice
from gpiozero.pins.lgpio import LGPIOFactory
from signal import pause

factory = LGPIOFactory()

switch20 = DigitalInputDevice(
    20,
    pull_up=True,
    bounce_time=0.01,
    active_state=True,
    pin_factory=factory
)

switch21 = DigitalInputDevice(
    21,
    pull_up=True,
    bounce_time=0.01,
    active_state=True,
    pin_factory=factory
)

def switch20_engaged():
    print("HI! Switch 20 engaged!", flush=True)

def switch21_engaged():
    print("HI! Switch 21 engaged!", flush=True)

switch20.when_activated = switch20_engaged
switch21.when_activated = switch21_engaged

print("Monitoring switches...")
pause()