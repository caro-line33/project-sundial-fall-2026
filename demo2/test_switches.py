from gpiozero import DigitalInputDevice
from gpiozero.pins.lgpio import LGPIOFactory
from signal import pause

factory = LGPIOFactory()

sensor7 = DigitalInputDevice(
    7,
    pull_up=True,
    bounce_time=0.01,
    pin_factory=factory
)

sensor8 = DigitalInputDevice(
    8,
    pull_up=True,
    bounce_time=0.01,
    pin_factory=factory
)

switch20 = DigitalInputDevice(
    20,
    pull_up=True,
    bounce_time=0.01,
    pin_factory=factory
)

switch21 = DigitalInputDevice(
    21,
    pull_up=True,
    bounce_time=0.01,
    pin_factory=factory
)

def sensor7_engaged():
    print("Sensor 7 engaged!", flush=True)

def sensor7_disengaged():
    print("Sensor 7 disengaged!", flush=True)

def sensor8_engaged():
    print("Sensor 8 engaged!", flush=True)

def sensor8_disengaged():
    print("Sensor 8 disengaged!", flush=True)

def switch20_engaged():
    print("Switch 20 engaged!", flush=True)

def switch20_disengaged():
    print("Switch 20 disengaged!", flush=True)

def switch21_engaged():
    print("Switch 21 engaged!", flush=True)

def switch21_disengaged():
    print("Switch 21 disengaged!", flush=True)

sensor7.when_activated = sensor7_engaged
sensor7.when_deactivated = sensor7_disengaged
sensor8.when_activated = sensor8_engaged
sensor8.when_deactivated = sensor8_disengaged
switch20.when_activated = switch20_engaged
switch20.when_deactivated = switch20_disengaged
switch21.when_activated = switch21_engaged
switch21.when_deactivated = switch21_disengaged

pause()