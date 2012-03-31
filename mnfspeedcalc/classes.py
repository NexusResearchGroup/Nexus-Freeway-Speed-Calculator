from __future__ import division
from datetime import datetime

class TMS_Config:
	
	def __init__(self, metro_config_file=""):
		self._datetime = None
		self._corridor_list = []
		
	def init_from_metro_config_file(self, metro_config_file):
		pass

	def add_corridor(self, corridor):
		self._corridor_list.append(corridor)
	
	def corridors(self):
		return self._corridor_list

class Corridor:
	
	def __init__(self, route="", dir=""):
		self._route = route
		self._dir = dir
		self._station_list = []
		
	def add_station(self, station):
		self._station_list.append(station)
		
	def stations(self):
		return self._station_list
		
class Station:
	
	def __init__(self, id=""):
		self._id = id
		self._detector_list = []
		self._speed_list = []
		self._speed_limit = -1
	
	def add_detector(self, detector):
		self._detector_list.append(detector)
	
	def speeds(self):
		return self._speed_list
		
	def speed_limit(self):
		return self._speed_limit

class Detector:
	
	def __init__(self, id=""):
		self._id = id
		self._speed_list = []
		
	def speeds(self):
		return self._speed_list