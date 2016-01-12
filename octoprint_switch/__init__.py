# coding=utf-8
from __future__ import absolute_import

import octoprint.plugin
import octoprint.settings
import octoprint.util

from octoprint.events import eventManager, Events

import logging
import logging.handlers
import os
from flask import jsonify
import RPi.GPIO as GPIO 

class SwitchPlugin(octoprint.plugin.AssetPlugin,
					octoprint.plugin.TemplatePlugin,
					octoprint.plugin.SimpleApiPlugin,
					octoprint.plugin.EventHandlerPlugin):
	
	PIN_LED = 23	# IR LED power switch
	PIN_RPICAM = 32	# red LED on RPi camera
	PIN_POWER = 24	# Printer power switch

	def initialize(self):
		#self._logger.setLevel(logging.DEBUG)
		
		self._logger.info("Running RPi.GPIO version '{0}'...".format(GPIO.VERSION))
		if GPIO.VERSION < "0.6":
			raise Exception("RPi.GPIO must be greater than 0.6")
			
		GPIO.setmode(GPIO.BCM)
		GPIO.setwarnings(False)

		GPIO.setup(self.PIN_LED, GPIO.OUT)		#default ON  (normally closed)
		GPIO.setup(self.PIN_RPICAM, GPIO.OUT)	#default ON (internal)
		GPIO.setup(self.PIN_POWER, GPIO.OUT)    #default OFF (normally open)
					
		self.MUTE_FILE = os.path.join(self.get_plugin_data_folder(), "mute")
		self.POWEROFF_FILE = os.path.join(self.get_plugin_data_folder(), "poweroff")
		self.UNLOAD_FILE = os.path.join(self.get_plugin_data_folder(), "unload")
		
		self.touch(self.POWEROFF_FILE)
		self.touch(self.UNLOAD_FILE)
		
		self._logger.info("SwitchPlugin initialized...")

	def get_assets(self):
		return dict(
			js=[
				"js/switch.js"
			],
			less=[],
			css= []
		)

	def get_template_configs(self):
		return [
			dict(type="navbar", template="switch_menu_item.jinja2", custom_bindings=True)
		]

	def is_api_adminonly(self):
		return True
		
	def get_api_commands(self):
		return dict(
			mute=["status"],
			power=["status"],
			lights=["status"],
			unload=["status"],
			poweroff=["status"],
			status=[]
		)

	def touch(self, file):
		if not os.path.isfile(file):
			os.mknod(file)

	def remove(self, file):
		if os.path.isfile(file):
			os.remove(file)

			
	def on_api_command(self, command, data):
		self._logger.info("on_api_command called: '{command}' / '{data}'".format(**locals()))
		if command == "mute":
			if bool(data.get('status')):
				self.touch(self.MUTE_FILE)
			else:
				self.remove(self.MUTE_FILE)
		elif command == "poweroff":
			if bool(data.get('status')):
				self.touch(self.POWEROFF_FILE)
				self.touch(self.UNLOAD_FILE)
			else:
				self.remove(self.POWEROFF_FILE)
		elif command == "unload":
			if bool(data.get('status')):
				self.touch(self.UNLOAD_FILE)
			else:
				self.remove(self.UNLOAD_FILE)
			
		elif command == "power":
			self.power_printer(bool( data.get('status') ))

		elif command == "lights":
			if bool( data.get('status') ):
				self.power_printer(True)

				GPIO.output(self.PIN_RPICAM, GPIO.HIGH)
				GPIO.output(self.PIN_LED, GPIO.LOW)
			else:
				GPIO.output(self.PIN_RPICAM, GPIO.LOW)
				GPIO.output(self.PIN_LED, GPIO.HIGH)

		elif command == "status":
			self._plugin_manager.send_plugin_message(self._identifier, self.get_status())

	def get_status(self):
		mute_status  = str(os.path.isfile(self.MUTE_FILE)).lower()
		unload_status  = str(os.path.isfile(self.UNLOAD_FILE)).lower()
		poweroff_status  = str(os.path.isfile(self.POWEROFF_FILE)).lower()
		light_status = "false" if GPIO.input(self.PIN_LED) else ("true" if GPIO.input(self.PIN_POWER) else "false")
		power_status = str(self.printer_status()).lower()
	
		return dict( lights =  light_status, power = power_status,  mute = mute_status, unload = unload_status, poweroff = poweroff_status )
		
	def printer_status(self):
		return bool(GPIO.input(self.PIN_POWER))
		
	def power_printer(self, status):
		if status:
			if self._printer._comm:
				self._printer._comm._log("Power up printer...")
			GPIO.output(self.PIN_POWER, GPIO.HIGH)
		else:
			if self._printer._comm:
				self._printer._comm._log("Power down printer...")
			GPIO.output(self.PIN_POWER, GPIO.LOW)
			try:
				if self._printer.is_operational():
					self._printer.commands(["M104 S0", "M140 S0", "M106 S0", "M18"])
			except Exception as e:
				self._logger.error(e)

	def on_event(self, event, payload):
		if event == Events.POWER_ON:
			if not self.printer_status():
				self.power_printer(True)
				self._plugin_manager.send_plugin_message(self._identifier, self.get_status())
		elif event == Events.POWER_OFF:
			if self.printer_status():
				self.power_printer(False)
				self._plugin_manager.send_plugin_message(self._identifier, self.get_status())
		elif event == Events.PRINT_DONE:
			if os.path.isfile(self.UNLOAD_FILE):
				if self._printer.is_operational():
					self._printer.commands(["G92 E0", "G1 E-15 F6000", "G92 E0"])
			if os.path.isfile(self.POWEROFF_FILE):
				if self._printer.is_operational():
					self._printer.commands(["M104 S0", "M140 S0 C40"]) #see cooling plugin
 
__plugin_name__ = "Switch Plugin"

def __plugin_load__():
	global __plugin_implementation__
	__plugin_implementation__ = SwitchPlugin()

