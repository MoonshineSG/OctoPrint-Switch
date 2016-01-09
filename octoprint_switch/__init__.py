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

	MUTE_FILE = "/home/pi/.octoprint/data/sound/mute"
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
		GPIO.setup(self.PIN_RPICAM, GPIO.OUT)	#default OFF (normally open)
		GPIO.setup(self.PIN_POWER, GPIO.OUT) #default OFF (normally open)

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
			status=[]
		)

	def on_api_command(self, command, data):
		self._logger.info("on_api_command called: '{command}' / '{data}'".format(**locals()))
		if command == "mute":
			if bool(data.get('status')):
				if not os.path.isfile(self.MUTE_FILE):
					os.mknod(self.MUTE_FILE)
			else:
				if os.path.isfile(self.MUTE_FILE):
					os.remove(self.MUTE_FILE)
			
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
		light_status = "false" if GPIO.input(self.PIN_LED) else ("true" if GPIO.input(self.PIN_POWER) else "false")
		power_status = str(bool(GPIO.input(self.PIN_POWER))).lower()
	
		return dict( lights =  light_status, power = power_status,  mute = mute_status )
		
	def power_printer(self, status):
		if status:
			self._logger.info("Powering up...")
			GPIO.output(self.PIN_POWER, GPIO.HIGH)
		else:
			self._logger.info("Shuting down printer...")
			GPIO.output(self.PIN_POWER, GPIO.LOW)
			try:
				self._printer.commands(["M104 S0", "M140 S0", "M106 S0", "M18"])
			except Exception as e:
				self._logger.error(e)

	def on_event(self, event, payload):
		if event == Events.POWER_ON:
			self.power_printer(True)
			self._plugin_manager.send_plugin_message(self._identifier, self.get_status())
		elif event == Events.POWER_OFF:
			self.power_printer(False)
			self._plugin_manager.send_plugin_message(self._identifier, self.get_status())
 
__plugin_name__ = "Switch Plugin"

def __plugin_load__():
	global __plugin_implementation__
	__plugin_implementation__ = SwitchPlugin()

