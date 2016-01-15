var inactive = "#f5f5f5"; //white

var color_on = "#24AC00"; //green
var color_off = "#B1ADAD"; //grey

var action_on = "#3466FF"; //blue
var action_off = "#B1ADAD"; //red

$(function() {
	function switchPluginViewModel(viewModels) {
		var self = this;

		self.isPower = ko.observable();
		self.isLights = ko.observable();
		self.isMute = ko.observable();
		self.willUnload = ko.observable();
		self.willPowerOff = ko.observable();
		
		self.onBeforeBinding = function () {
			self.isAdmin = viewModels[0].isAdmin;
			self.printer = viewModels[1];
			self.power = false;
			self.lights = false;
			self.mute = false;
			self.unload = false;
			self.poweroff = false;
		}

		self.updateIcons = function (data) {
			self.lights = JSON.parse(data.lights);
			self.power = JSON.parse(data.power);
			self.mute = JSON.parse(data.mute);
			self.unload = JSON.parse(data.unload);
			self.poweroff = JSON.parse(data.poweroff);
			
			self.isPower( self.power ? color_on : color_off );
			self.isLights( self.lights ? color_on : color_off );
			self.isMute( self.mute ? color_off : color_on );
			self.willUnload( self.unload ? action_on : action_off );
			self.willPowerOff( self.poweroff ? action_on : action_off );
		}
		
		self.onStartup = function() {
			var element = $(".octoprint-container .accordion");

			if (element.length) {
				element.children().first().before(`<div id="switch_menu_bar" class="accordion-group "  data-bind="visible: isAdmin" style="display: none; font-size: 22px; height: 30px; padding-top: 10px; text-align: center;">

  <a href="#" title="Printer power"  style="padding-right: 14px" data-bind="click: togglePower">
    <span data-bind="style: { color: isPower }"><i class="icon-off"></i></span>
  </a>

  <a href="#" title="IR LED lights"  style="padding-right: 14px" data-bind="click: toggleLights">
    <span data-bind="style: { color: isLights }"><i class="icon-lightbulb"></i></span>
  </a>

  <a href="#"  title="Mute printer"  style="padding-right: 14px;" data-bind="click: toggleMute">
    <span data-bind="style: { color: isMute }"><i class="icon-bell"></i></span>
  </a>

  <a href="#"  title="Unload Fillament when printing is done"  style="padding-right: 14px; padding-left: 15px;" data-bind="click: toggleUnload">
    <span data-bind="style: { color: willUnload }"><i class="icon-external-link"></i></span>
  </a>

  <a href="#" title="Power off after printing finish"  style="padding-right: 14px;" data-bind="click: togglePowerOff">
    <span data-bind="style: { color: willPowerOff  }"><i class="icon-remove-sign"></i></span>
  </a>
				</div>`);
			}
		};
		
		
		self.onServerDisconnect = function(){
			self.isPower( inactive );
			self.isLights( inactive );
			self.isMute( inactive );
			self.willUnload( inactive );
			self.willPowerOff( inactive );
			return true;
		}
		
		self.onUserLoggedIn = function(user) {
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
			self.isMute( inactive );
			self.sendCommand({"command":"mute", "status":!self.mute});
		}

		self.togglePower = function() {
			if (self.power) {
				if (self.printer.isPrinting() || self.printer.isPaused()) {
				showConfirmationDialog({
							 message: "You are about to stop the printer. This will stop your current job.",
							 onproceed: function() {
									self.isPower( inactive );
									self.sendCommand({"command":"power", "status":false});
							 }});
				 } else {
		 			self.isPower( inactive );
				 	self.sendCommand({"command":"power", "status":false});
				 }
			} else {
				self.isPower( inactive );
				self.sendCommand({"command":"power", "status":true});
			}
			
		}
		
		self.toggleLights = function() {
			self.isLights( inactive );
			self.sendCommand({"command":"lights", "status":!self.lights});
		}

		self.toggleUnload = function() {
			self.willUnload( inactive );
			self.sendCommand({"command":"unload", "status":!self.unload});
		}

		self.togglePowerOff = function() {
			self.willPowerOff( inactive );
			self.sendCommand({"command":"poweroff", "status":!self.poweroff});
		}


		self.get_status = function() {
			OctoPrint.postJson("api/plugin/switch", {"command":"status"});
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

