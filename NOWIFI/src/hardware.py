########################################################
#
#   Embedded Software for IoT, University of Trento
#   A.Y. 2023/2024
#   Final project
#
#   Authors: Carlotta Cazzolli 226912
#            Alessandro Iepure 228023
#            Martina Panini 226621
#
#   Smart Pet Door
#
#   MIT license, see LICENSE file
#
########################################################

import analogio
import board
import digitalio
import busio
import neopixel
import pwmio

import mfrc522

import adafruit_sht4x
from adafruit_motor import servo
from adafruit_debouncer import Debouncer
from src.logger import logger

# Addressable LED strip
pixels = neopixel.NeoPixel(
    pin=board.GP7, 
    n=26, 
    brightness=0.2, 
    auto_write=False, 
    pixel_order=neopixel.GRB
)
pixels.fill((0, 0, 255))
pixels.show()
logger.info('LED strip initialized')

# UART for serial communication between Pico and Pico W
uart = busio.UART(tx=board.GP0, rx=board.GP1, baudrate=115200)
logger.info('UART initialized at 115200 bauds')

# Servo motor IN
pwm_in = pwmio.PWMOut(board.GP12, duty_cycle=2**15, frequency=50)
motor_in = servo.Servo(pwm_in)
motor_in.angle = 0
logger.info('Servo motor in initialized')

# Servo motor OUT
pwm_out = pwmio.PWMOut(board.GP13, duty_cycle=2**15, frequency=50)
motor_out = servo.Servo(pwm_out)
motor_out.angle = 0
logger.info('Servo motor out initialized')

# RFID reader
spi = busio.SPI(clock=board.GP18, MOSI=board.GP19, MISO=board.GP16)
cs = digitalio.DigitalInOut(board.GP17)
rst = digitalio.DigitalInOut(board.GP22)
rfid = mfrc522.MFRC522(spi, cs, rst)
rfid.set_antenna_gain(0x07 << 4)
logger.info('RFID reader initialized')

# Temperature sensor
i2c = busio.I2C(scl=board.GP5, sda=board.GP4)
sht = adafruit_sht4x.SHT4x(i2c)
sht.mode = adafruit_sht4x.Mode.NOHEAT_HIGHPRECISION
logger.info('Temperature sensor initialized')

# Flex sensor
flex = analogio.AnalogIn(board.GP28)
logger.info('Flex sensor initialized')

# Debug button
btn_pin = digitalio.DigitalInOut(board.GP15)
btn_pin.direction = digitalio.Direction.INPUT
btn_pin.pull = digitalio.Pull.UP
debug_switch = Debouncer(btn_pin)
logger.info('Debug button initialized')
