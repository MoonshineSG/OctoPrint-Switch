$(function() {
	function switchPluginViewModel(viewModels) {
		var self = this;

		self.isPower = ko.observable();
		self.isLights = ko.observable();
		self.isMute = ko.observable();

		self.onBeforeBinding = function () {
			self.isAdmin = viewModels[0].isAdmin;
			self.printer = viewModels[1];
			self.power = false;
			self.lights = false;
			self.mute = false;
		}

		self.updateIcons = function (data) {
			self.lights = JSON.parse(data.lights);
			self.power = JSON.parse(data.power);
			self.mute = JSON.parse(data.mute);
			
			self.isPower( self.power ? '#24AC00' : '#BF210E' );
			self.isLights( self.lights ? '#24AC00' : '#BF210E' );
			self.isMute( self.mute ? '#BF210E' : '#24AC00' );
		}
		
		self.onServerDisconnect = function(){
			self.isPower( '#08c' );
			self.isLights( '#08c' );
			self.isMute( '#08c' );
		}
		
		self.onStartupComplete = function() {
			self.get_status();
		}
		
		self.onDataUpdaterReconnect = function() {
			self.get_status();
		}
		
		self.sendCommand = function(data) {
			OctoPrint.postJson("api/plugin/switch", data)
				.done(function() {
					self.get_status();
				});
		};
		
		self.toggleMute = function() {
			self.isMute( '#08c' );
			self.sendCommand({"command":"mute", "status":!self.mute});
		}

		self.togglePower = function() {
			if (self.power) {
				if (self.printer.isPrinting() || self.printer.isPaused()) {
				showConfirmationDialog({
							 message: "You are about to stop the printer. This will stop your current job.",
							 onproceed: function() {
									self.isPower( '#08c' );
									self.sendCommand({"command":"power", "status":false});
							 }});
				 } else {
		 			self.isPower( '#08c' );
				 	self.sendCommand({"command":"power", "status":false});
				 }
			} else {
				self.isPower( '#08c' );
				self.sendCommand({"command":"power", "status":true});
			}
			
		}
		
		self.toggleLights = function() {
			self.isLights( '#08c' );
			self.sendCommand({"command":"lights", "status":!self.lights});
		}

		self.get_status = function() {
			OctoPrint.postJson("api/plugin/switch", {"command":"status"})
				.done(function(data) {
					self.updateIcons(data);
				});
		}
		
		self.onDataUpdaterPluginMessage = function (plugin, data) {
					if (plugin != "switch") {
						return;
					}
					self.updateIcons(data);
				} 
	}

	OCTOPRINT_VIEWMODELS.push([
		switchPluginViewModel, 
		["loginStateViewModel", "printerStateViewModel"],
		["#switch_menu_bar"]
	]);
});

