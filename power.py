#!/usr/bin/env python
import sys, os, pwd
from time import sleep
import argparse
import daemon, signal
import RPi.GPIO as GPIO
import httplib

if "root" != pwd.getpwuid( os.getuid() )[ 0 ] : 
	print("Please run as root (sudo)...")
	exit(2)
	
PIN_LED = 23	# IR LED power switch
PIN_POWER = 24	# Printer power switch
PIN_RPICAM = 32	# red LED on RPi camera

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

GPIO.setup(PIN_POWER, GPIO.OUT)		#default OFF (normally open)
GPIO.setup(PIN_LED, GPIO.OUT)		#default ON  (normally closed)
GPIO.setup(PIN_RPICAM, GPIO.OUT)	#default OFF (normally open)

APP_KEY = ""

def send_octopi(data):
	success = 0
	while success < 4: #try 3 times
		try:
			headers = {"Content-Type": "application/json",  "X-Api-Key": APP_KEY}
			conn = httplib.HTTPConnection("127.0.0.1", 5000)
			conn.request("POST", "/api/printer/command", data, headers)
			response = conn.getresponse()
			status = response.status
			conn.close()
			success = 5 #exit the while loop
		except:
			success += 1
			sleep(3)

def update_octopi_status(data):
	success = 0
	while success < 4: #try 3 times
		try:
			headers = {"Content-Type": "application/json",  "X-Api-Key": APP_KEY}
			conn = httplib.HTTPConnection("127.0.0.1", 5000)
			conn.request("POST", "/api/plugin/switch", data, headers)
			response = conn.getresponse()
			status = response.status
			#print(status)
			conn.close()
			success = 5 #exit the while loop
		except:
			success += 1
			sleep(3)
	
def show_status(show):
	if show:	
		print("Printer     : {0}".format( 'ON'  if GPIO.input(PIN_POWER)  else 'OFF' ))
		print("Camera LED  : {0}".format( 'ON'  if GPIO.input(PIN_RPICAM) else 'OFF' ))
		print("IR LEDs     : {0} (GPIO {1})".format('OFF' if GPIO.input(PIN_LED) else ('ON'  if GPIO.input(PIN_POWER)  else 'OFF'), 'OFF' if GPIO.input(PIN_LED) else "ON"))
		light = "false" if GPIO.input(PIN_LED) else ("true" if GPIO.input(PIN_POWER) else "false")
		status = '{"command": "update", "power": %s, "lights": %s }'%(str(bool(GPIO.input(PIN_POWER))).lower(), light)
		print status
		with daemon.DaemonContext(initgroups=False, stdout = sys.stdout):
			update_octopi_status( status )
		
def main():
	if args.camera == "on":
		GPIO.output(PIN_POWER, GPIO.HIGH)
		GPIO.output(PIN_RPICAM, GPIO.HIGH)
		GPIO.output(PIN_LED, GPIO.LOW)
	
	elif args.camera == "off":
		GPIO.output(PIN_RPICAM, GPIO.LOW)
		GPIO.output(PIN_LED, GPIO.HIGH)
	
	if args.printer == "on":
		GPIO.output(PIN_POWER, GPIO.HIGH)
	elif args.printer == "off":
		GPIO.output(PIN_POWER, GPIO.LOW)
		with daemon.DaemonContext(initgroups=False, stdout = sys.stdout):
			send_octopi('{"commands": ["M104 S0", "M140 S0", "M106 S0", "M18"]}')
	
	show_status(args.status)
	
if __name__ == '__main__':
	parser = argparse.ArgumentParser(description='Turn printer and/or camera on/off.', add_help=False)
	parser.add_argument('-p', '--printer', choices=['on', 'off'])
	parser.add_argument('-c', '--camera', choices=['on', 'off'])
	parser.add_argument('status', nargs='?')
	
	try:
		args = parser.parse_args()
		main()
	except:
		exit(1)
	else:
		exit(0)
