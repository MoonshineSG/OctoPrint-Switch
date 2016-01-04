# coding=utf-8
from __future__ import absolute_import

import octoprint.plugin
import octoprint.settings
import octoprint.util

from octoprint.events import eventManager, Events
import logging
import logging.handlers
import os
from sarge import run
import flask

class SwitchPlugin(octoprint.plugin.AssetPlugin,
					octoprint.plugin.TemplatePlugin,
					octoprint.plugin.SimpleApiPlugin):

	MUTE_FILE = "/home/pi/.octoprint/data/sound/mute"

	def initialize(self):
		self._logger.setLevel(logging.DEBUG)
		self._logger.debug("SwitchPlugin initialized...")

	def get_assets(self):
		return dict(
			js=[
				"js/switch.js"
			]
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
			update=["lights", "power"],
			status=[]
		)

	def on_api_command(self, command, data):
		self._logger.info("on_api_command called: '{command}' / '{data}'".format(**locals()))
		if command == "mute":
			self.save_mute(bool(data.get('status')))
		elif command == "power":
			if bool( data.get('status') ):
				eventManager().fire(Events.POWER_ON)
			else:
				eventManager().fire(Events.POWER_OFF)
		elif command == "lights":
			if bool( data.get('status') ):
				run("sudo /home/pi/power.py status --camera on")
			else:
				run("sudo /home/pi/power.py status --camera off")

		elif command == "update":
				message = dict( lights =  data.get('lights'), power = data.get('power'),  mute = os.path.isfile(self.MUTE_FILE) )
				self._plugin_manager.send_plugin_message(self._identifier, message)
				
		elif command == "status":
				run("sudo /home/pi/power.py status")

	def save_mute(self, mute):
		if mute:
			run("touch %s"%self.MUTE_FILE)
		else:
			run("rm %s"%self.MUTE_FILE)
 
 
__plugin_name__ = "SwitchPlugin"

def __plugin_load__():
	global __plugin_implementation__
	__plugin_implementation__ = SwitchPlugin()

