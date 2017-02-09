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
from time import sleep
from thread import start_new_thread
import threading
import inspect

class SwitchPlugin(octoprint.plugin.AssetPlugin,
					octoprint.plugin.SimpleApiPlugin,
					octoprint.plugin.EventHandlerPlugin,
					octoprint.plugin.SettingsPlugin):
	
	PIN_RPICAM = 32	# red LED on RPi camera
	EXTRUDERS = None
	
	autoOnCommands = "G0,G1,G2,G3,G10,G11,G28,G29,G32,M104,M109,M140,M190,M303".split(",")
	idleIgnoreCommands = "M105,".split(",")
	idleTimeout = 15
	idleTimer = None
	
	
	def initialize(self):
		#self._logger.setLevel(logging.DEBUG)
		
		self._logger.info("Running RPi.GPIO version '{0}'...".format(GPIO.VERSION))
		if GPIO.VERSION < "0.6":
			raise Exception("RPi.GPIO must be greater than 0.6")
			
		GPIO.setmode(GPIO.BCM)
		GPIO.setwarnings(False)

		self.PIN_LED = self._settings.get_int(["led_pin"])
		self.PIN_POWER = self._settings.get_int(["power_pin"])
		self.PIN_RESET = self._settings.get_int(["reset_pin"])
		
		self.POWER_OFF_COMMAND = self._settings.get(["command_power_off"]).split(",")
		self.RETRACTION_LENGHT = self._settings.get_int(["retraction_length"])
		self.SHORT_RETRACTION_LENGHT = self._settings.get_int(["short_retraction_length"])
		self.RETRACTION_SPEED = self._settings.get_int(["retraction_speed"])
		
		
		if self.PIN_POWER != -1:
			GPIO.setup(self.PIN_POWER, GPIO.OUT)    #default OFF (normally open)
		else:
			self._logger.info("Power pin not setup.")
			
		if self.PIN_LED != -1:
			GPIO.setup(self.PIN_LED, GPIO.OUT)		#default OFF  (normally open)
		else:
			self._logger.info("LED pin not setup.")
				
		GPIO.setup(self.PIN_RPICAM, GPIO.OUT)	#default ON (internal)
				
		self.MUTE_FILE = os.path.join(self.get_plugin_data_folder(), "mute")
		self.POWEROFF_FILE = os.path.join(self.get_plugin_data_folder(), "poweroff")
		self.UNLOAD_FILE = os.path.join(self.get_plugin_data_folder(), "unload")
		
		#the power is turned on by lights (and it should be turned off if nobody else needs it)
		self.LIGHT = False 
		
		self._logger.info("SwitchPlugin initialized...")


	def get_settings_defaults(self):
		return dict(
			power_pin = -1,
			led_pin = -1,
			reset_pin = -1,
			command_power_off = "M81",
			retraction_speed = 3000,
			retraction_length = 600,
			short_retraction_length = 10
		)

	def get_assets(self):
		return dict(
			js=[
				"js/switch.js"
			],
			less=[],
			css= []
		)

	def is_api_adminonly(self):
		return True
		
	def get_api_commands(self):
		return dict(
			mute=["status"],
			power=["status"],
			lights=["status"],
			unload=["status"],
			poweroff=["status"],
			status=[],
			reset=[],
			reload=[]
		)

	def touch(self, file):
		if not os.path.isfile(file):
			os.mknod(file)

	def remove(self, file):
		if os.path.isfile(file):
			os.remove(file)
			
	def reconnect(self):
		self._logger.info("Will reconnect in 30sec...")
		sleep(30)		
		self._printer.connect()
		self._logger.info("== reconnected ==")
				
	def on_api_command(self, command, data):
		self._logger.debug("on_api_command called: '{command}' / '{data}'".format(**locals()))
		if command == "mute":
			if bool(data.get('status')):
				self.touch(self.MUTE_FILE)
			else:
				self.remove(self.MUTE_FILE)

		elif command == "reset":
			if self.PIN_RESET != -1:
				self._printer.disconnect()
				GPIO.setup(self.PIN_RESET, GPIO.OUT, initial=0)
				sleep(1)
				GPIO.cleanup(self.PIN_RESET)
				start_new_thread(self.reconnect, ())

		elif command == "reload":
			self._plugin_manager.send_plugin_message(self._identifier, dict( reload =  "now"))
			
		elif command == "poweroff":
			if bool(data.get('status')):
				self.touch(self.POWEROFF_FILE)
			else:
				self.remove(self.POWEROFF_FILE)

		elif command == "unload":
			if bool(data.get('status')):
				self.touch(self.UNLOAD_FILE)
			else:
				self.remove(self.UNLOAD_FILE)

		elif command == "power":
			if bool( data.get('status') ) :
				eventManager().fire(Events.POWER_ON)
			else:
				if not self._printer.is_printing():
					eventManager().fire(Events.POWER_OFF)

		elif command == "lights":
			if self.PIN_LED != -1 and self.PIN_POWER != -1:
				if bool( data.get('status') ):
					if not self.printer_status():
						GPIO.output(self.PIN_POWER, GPIO.HIGH)
						self.LIGHT = True
					GPIO.output(self.PIN_RPICAM, GPIO.HIGH)
					GPIO.output(self.PIN_LED, GPIO.HIGH)
				else:
					if not self._printer.is_printing():
						if self.LIGHT:
							GPIO.output(self.PIN_POWER, GPIO.LOW)
							self.LIGHT = False
						GPIO.output(self.PIN_RPICAM, GPIO.LOW)
						GPIO.output(self.PIN_LED, GPIO.LOW)

		elif command == "status":
			self.update_status()
		
	def update_status(self):
		mute_status  = str(os.path.isfile(self.MUTE_FILE)).lower()
		unload_status  = str(os.path.isfile(self.UNLOAD_FILE)).lower()
		poweroff_status  = str(os.path.isfile(self.POWEROFF_FILE)).lower()
		if self.PIN_LED != -1 and self.PIN_POWER != -1:
			light_status = ("true" if GPIO.input(self.PIN_POWER) else "false") if GPIO.input(self.PIN_LED) else "false" 
		else:
			light_status = "false"
		power_status = str(self.printer_status()).lower()
		
		payload =  dict( lights =  light_status, power = power_status,  mute = mute_status, unload = unload_status, poweroff = poweroff_status)
		
		self._plugin_manager.send_plugin_message(self._identifier, payload)

	def printer_status(self):
		if self.PIN_POWER != -1:
			return bool(GPIO.input(self.PIN_POWER))
		else:
			return False;

	def on_event(self, event, payload):
		if event == Events.POWER_ON:
			if self.PIN_POWER != -1:
				self.LIGHT = False
				if not self.printer_status():
					self.LIGHT = False
					if self._printer._comm:
						self._printer._comm._log("Power on printer...")
					GPIO.output(self.PIN_POWER, GPIO.HIGH)
					self.update_status()
					if not (self._printer.is_printing() or self._printer.is_paused()):
						self.start_idle_timer()
					
		elif event == Events.POWER_OFF:
			if self.PIN_POWER != -1:
				if self.printer_status():
					if not self._printer.is_printing() or self._printer.is_paused():
						if self._printer._comm:
							self._printer._comm._log("Power off printer...")
						GPIO.output(self.PIN_POWER, GPIO.LOW)
						self.update_status()
						self.stop_idle_timer()

		elif event == Events.PRINT_STARTED:
			GPIO.output(self.PIN_RPICAM, GPIO.HIGH)
			if self.PIN_LED != -1:
				GPIO.output(self.PIN_LED, GPIO.HIGH)
			self.update_status()
			self._logger.debug("Events.PRINT_STARTED calling stop")
			self.stop_idle_timer()
			
			
		elif event == Events.HOME:
			if not self.printer_status():
				eventManager().fire(Events.POWER_ON)
				self.update_status()
				
		elif event == Events.FILAMENT_RUNOUT:
				self._printer._comm._log("Filament runout!!")

		elif event == Events.PRINT_DONE:
			if os.path.isfile(self.UNLOAD_FILE):
				self._logger.info("Unload filament option is enabled. Running gcode sequence...")
				if self._printer.is_operational():
					self._printer._comm._log("Unload filament option is enabled. Running gcode sequence...")
					self._printer.commands( self.generate_unload_filament(self.RETRACTION_LENGHT, self.RETRACTION_SPEED) )
				else:
					self._logger.error("UNLOAD_FILE: printer is not operational?")
			if os.path.isfile(self.POWEROFF_FILE):
				self._logger.info("Power Off option is enabled. Running gcode sequence...")
				if self._printer.is_operational():
					self._printer._comm._log("Power Off option is enabled.")
					if os.path.isfile(self.UNLOAD_FILE):
						self._logger.info("Unload filament is enabled. Running simple gcode sequence...")
						self._printer.commands(self.POWER_OFF_COMMAND)
					else:
						self._logger.info("Unload filament is not enabled. Running long gcode sequence with small retraction...")
						self._printer.commands( self.generate_unload_filament(self.SHORT_RETRACTION_LENGHT, self.RETRACTION_SPEED, self.POWER_OFF_COMMAND) )
				else:
					self._logger.error("POWEROFF_FILE: printer is not operational ?")
			#self._printer.unselect_file()

	def generate_unload_filament(self, length, speed, additional = None):
		split = 10
		if self.EXTRUDERS:
			extruders = self.EXTRUDERS
		else:
			extruders = self._printer_profile_manager.get_current_or_default().get('extruder').get('count')
		
		ret = ["M83"] #make sure it's relative 

		if extruders > 1:
			for y in range(0, length/split): #every 10mm
				for x in range(0, extruders):
					ret.extend( ["T%s"%x, "G1 E-%s F%s"%(split, speed)] )

			if length % split:
				for x in range(0, extruders):
					ret.extend( ["T%s"%x, "G1 E-%s F%s"%(length % split, speed)] )

			for x in range(0, extruders):
				ret.extend( ["T%s"%x, "M92 E0"] ) #set them back to 0
			
			ret.append("T0")
		else:
			ret.extend( [ "G91" , "G1 E%s F%s"%(-length, speed), "G90"] )

		if additional:
			ret.extend(additional)
			
		return ret

	def custom_action_handler(self, comm, line, action, *args, **kwargs):
		if action.startswith("active_extruders"):
			try:
				act, self.EXTRUDERS = action.split(" ")
				self.EXTRUDERS = int(self.EXTRUDERS)
			except:
				self.EXTRUDERS = None
				
			self._logger.info("Curent job uses %s extruders ..."%self.EXTRUDERS)

		
	def hook_gcode_queuing(self, comm_instance, phase, cmd, cmd_type, gcode, *args, **kwargs):
		if gcode:
			if gcode in self.autoOnCommands and not self.printer_status():
					eventManager().fire(Events.POWER_ON)
			
			if not ( self._printer.is_printing() or self._printer.is_paused() ):
				if self.printer_status() and gcode not in self.idleIgnoreCommands:
					self.start_idle_timer() #restart the count
		

	def start_idle_timer(self):
		self.stop_idle_timer()
		
		if self.printer_status():
			self.idleTimer = threading.Timer(self.idleTimeout * 60, self.idle_poweroff)
			self.idleTimer.start()

	def stop_idle_timer(self):
		if self.idleTimer:
			self.idleTimer.cancel()
			self.idleTimer = None

	def idle_poweroff(self):
		if self._printer.is_printing() or self._printer.is_paused():
			return

		self._logger.info("Idle timeout reached after %s minute(s). Shutting down printer." % self.idleTimeout)
		eventManager().fire(Events.POWER_OFF)

	def get_version(self):
		if self._plugin_version:
			return self._plugin_version
		else:
			return "99" #manualy installed

	def get_update_information(self):
		return dict(
			octoprint_switch=dict(
				displayName="OctoPrint Switch",
				displayVersion=self.get_version(),

				# version check: github repository
				type="github_release",
				user="MoonshineSG",
				repo="OctoPrint-Switch",
				current=self.get_version(),

				# update method: pip
				pip="https://github.com/MoonshineSG/OctoPrint-Switch/archive/{target_version}.zip"
			)
		)

def __plugin_load__():
	global __plugin_implementation__
	__plugin_implementation__ = SwitchPlugin()
	
	global __plugin_hooks__
	__plugin_hooks__ = {
		"octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information,
		"octoprint.comm.protocol.action": __plugin_implementation__.custom_action_handler,
		"octoprint.comm.protocol.gcode.queuing": __plugin_implementation__.hook_gcode_queuing
	}
	
	
