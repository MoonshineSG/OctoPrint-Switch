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

		self.updateIcons = function () {
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
		
		self.onDataUpdaterPluginMessage = function (plugin, data) {
			if (plugin != "switch") {
				return;
			}
			self.lights = data.lights;
			self.power = data.power;
			self.mute = data.mute;
			//console.log(data);
			self.updateIcons();
		} 
		
		self._sendData = function(data, callback) {
			OctoPrint.postJson("api/plugin/switch", data)
				.done(function() {
					if (callback) callback();
				});
		};
		
		self.toggleMute = function() {
			self.mute = ! self.mute;
			self._sendData({"command":"mute", "status":self.mute}, function(){self.updateIcons();});
		}

		self.togglePower = function() {
			if (self.power) {
				if (self.printer.isPrinting() || self.printer.isPaused()) {
				showConfirmationDialog({
							 message: "You are about to stop the printer. This will stop your current job.",
							 onproceed: function() {
									 self._sendData({"command":"power", "status":false});
							 }});
				 } else {
				 	self._sendData({"command":"power", "status":false});
				 }
			} else self._sendData({"command":"power", "status":true});
			
		}
		
		self.toggleLights = function() {
			self._sendData({"command":"lights", "status":!self.lights}, function(){self.updateIcons();});
		}

		self.get_status = function() {
			self._sendData({"command":"status"});
		}

	}

	OCTOPRINT_VIEWMODELS.push([
		switchPluginViewModel, 
		["loginStateViewModel", "printerStateViewModel"],
		["#switch_menu_bar"]
	]);
});

