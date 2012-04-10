from __future__ import division
from datetime import date, timedelta
from trafficreader import TrafficReader
from os import path
from collections import deque
import cProfile
import pstats
import impute
import xml.etree.cElementTree as ET

class TMS_Config:

	def __init__(self, metro_config_file=None, verbose=False):
		self._verbose = verbose
		if self._verbose:
			print "Creating tms_config node " + str(self)

		if metro_config_file != None:
			self.init_from_metro_config_file(metro_config_file)
		else:
			if self._verbose:
				print str(self) + " set blank values"
			self._timestamp = None
			self.corridor_list = None
			self._node = None

	def init_from_metro_config_file(self, metro_config_file):
		if self._verbose:
			print str(self) + " loading from file: " + metro_config_file
		tree = ET.parse(metro_config_file)
		self._node = tree.getroot()

		# get the date from the config file
		# disabled due to platform variations
		#time_string = self._node.get("time_stamp")
		#self._timestamp = datetime.strptime(time_string, "%a %b %d %H:%M:%S %Z %Y")
		#if self._verbose:
		#	print str(self) + " set timestamp = " + str(self._timestamp)

		# find all the defined corridors in the config file
		self.corridor_list = []
		if self._verbose:
			print str(self) + " loading corridors"
		for corridor_node in self._node.findall('corridor'):
			self.add_corridor(Corridor(corridor_node, verbose=self._verbose))

	def add_corridor(self, corridor):
		self.corridor_list.append(corridor)

	def corridors(self):
		return self.corridor_list

	def load_speeds(self, traffic_file):
		traffic_reader = TrafficReader(traffic_file)
		for corridor in self.corridor_list:
			corridor.load_speeds(traffic_reader)

	def load_speeds_for_year(self, year, directory):
		for corridor in self.corridor_list:
			corridor.load_speeds_for_year(year, directory)

	def print_speeds(self):
		for corridor in self.corridor_list:
			corridor.print_speeds()

	def spatial_impute(self):
		for corridor in self.corridor_list:
			corridor.spatial_impute()


class Corridor:

	def __init__(self, corridor_node=None, verbose=False):
		self._verbose = verbose
		if self._verbose:
			print "Creating corridor node " + str(self)

		if corridor_node != None:
			self.init_from_corridor_node(corridor_node)
		else:
			if self._verbose:
				print str(self) + " set blank values"
			self._route = ""
			self._dir = ""
			self.station_list = []
			self._node = None

	def init_from_corridor_node(self, corridor_node):
		if self._verbose:
			print str(self) + " loading from node: " + str(corridor_node)
		self._node = corridor_node

		# get the corridor identifiers
		self._route = self._node.get("route")
		self._dir = self._node.get("dir")
		if self._verbose:
			print str(self) + " set route, dir = " + self._route + ", " + self._dir

		# get all the stations in this corridor
		self.station_list = []
		if self._verbose:
			print str(self) + " loading stations"
		for station_node in self._node.findall("r_node[@n_type='Station'][@station_id]"):
			self.add_station(Station(station_node, self._verbose))

	def add_station(self, station):
		self.station_list.append(station)

	def stations(self):
		return self.station_list

	def load_speeds(self, traffic_reader):
		for station in self.station_list:
			station.load_speeds(traffic_reader)

	def load_speeds_for_year(self, year, directory):
		self._year = year
		for station in self.station_list:
			station.load_speeds_for_year(year, directory)

	def print_speeds(self):
		for station in self.station_list:
			station.print_speeds()

	def spatial_impute(self):
		if len(self.station_list) == 0:
			return

		current_day = date(self._year, 1, 1)
		last_day = date(self._year, 12, 31)
		one_day = timedelta(days=1)
		time_slots = range(len(self.station_list[0].speeds[current_day]))

		while current_day <= last_day:
			for time_slot in time_slots:
				station_speed_list = deque()

				# build the spatial list of speeds for this time slot for this day
				for station_sequence in range(len(self.station_list)):
					station = self.station_list[station_sequence]
					station_speed_list.append(station.speeds[current_day][time_slot])

				# impute missing values
				station_speed_list = impute.impute_range(list(station_speed_list), impute_length=4, input_length=1)

				# give the imputed values for this time slot on this day bask to the stations
				for station_sequence in range(len(self.station_list)):
					self.station_list[station_sequence].speeds[current_day][time_slot] = station_speed_list[station_sequence]

			current_day = current_day + one_day

		#for time_slot in time_slots:
		#	station_speed_list = []
		#
		#	# build the spatial list of speeds for this time slot
		#	for station_sequence in range(len(self.station_list)):
		#		station = self.station_list[station_sequence]
		#		station_speed_list.append(station.speed_list[time_slot])
		#
		#	# impute missing values
		#	station_speed_list = impute.impute_range(station_speed_list, impute_length=4, input_length=1)
		#
		#	# give the imputed values back to the stations for this time slot
		#	for station_sequence in range(len(self.station_list)):
		#		self.station_list[station_sequence].speed_list[time_slot] = station_speed_list[station_sequence]

class Station:

	def __init__(self, station_node=None, verbose=False):
		self._verbose = verbose
		if self._verbose:
			print "Creating station node " + str(self)

		if station_node != None:
			self.init_from_station_node(station_node)
		else:
			raise Exception("Station initialization requires station node")

	def init_from_station_node(self, station_node):
		if self._verbose:
			print str(self) + " loading from node: " + str(station_node)
		self._node = station_node

		self.speeds = {}

		# get the id of this station
		self._id = self._node.get("station_id")
		if self._verbose:
			print str(self) + " set id = " + self._id

		# get the speed limit of this station
		self._speed_limit = float(self._node.get("s_limit"))
		if self._verbose:
			print str(self) + " set speed_limit = " + str(self._speed_limit)

		# get the location of this station
		lat = float(self._node.get("lat"))
		lon = float(self._node.get("lon"))
		self._latlon = (lat, lon)
		if self._verbose:
			print str(self) + " set latlon = " + str(self._latlon)

		# get all the detectors in this station
		self.detector_list = []
		if self._verbose:
			print str(self) + " loading detectors"
		for detector_node in self._node.findall("detector"):
			self.add_detector(Detector(detector_node, speed_limit=self._speed_limit, verbose=self._verbose))

	def add_detector(self, detector):
		self.detector_list.append(detector)

	def detectors(self):
		return self.detector_list

	def speeds(self):
		return self.speed_list

	def speed_limit(self):
		return self._speed_limit

	def load_speeds_for_year(self, year, directory):
		if self._verbose:
			print "Loading speeds for station ", self._id
		current_day = date(year, 1, 1)
		last_day = date(year, 12, 31)
		one_day = timedelta(days=1)

		while current_day <= last_day:
			if self._verbose:
				print "    Loading speeds for ", current_day
			# If there are no detectors, there are no valid speeds
			if self.detector_list == []:
				day_speeds = [None] * 288
			else:
				try:
					traffic_file = self.traffic_filename_from_date(current_day)
					tr = TrafficReader(path.join(directory, traffic_file))
					day_speeds = impute.average_multilist([detector.load_speeds(tr) for detector in self.detector_list])
					day_speeds = impute.impute_range(day_speeds, impute_length=3, input_length=3)
					day_speeds = impute.average_list(day_speeds, 5)
				except IOError:
					# If there is no file for the given day, add a list of invalid speeds
					day_speeds = [None] * 288

			self.speeds[current_day] = day_speeds
			current_day = current_day + one_day

	def load_speeds(self, traffic_reader):
		# if there are no detectors for this station, give it a speed list of all invalid speeds
		if self.detector_list == []:
			self.speeds = [None] * 288
		# otherwise, load the speeds from the detectors
		else:
			for detector in self.detectors():
				detector.load_speeds(traffic_reader)

			speeds = impute.average_multilist([detector.load_speeds(traffic_reader) for detector in self.detector_list])
			speeds = impute.impute_range(speeds, impute_length=3, input_length=3)
			speeds = impute.average_list(speeds, 5)
			self.speed_list = impute.impute1(speeds)

	def print_speeds(self):
		print "Speeds for station " + self._id
		dates = self.speeds.keys()
		dates.sort()
		for date in dates:
			print "Speeds for ", str(date)
			print self.speeds[date]

	def traffic_filename_from_date(self, date):
		return date.strftime("%Y%m%d") + ".traffic"

class Detector:

	def __init__(self, detector_node=None, speed_limit=0, verbose=False):
		self._verbose = verbose
		self._speed_limit = speed_limit
		if self._verbose:
			print "Creating detector node " + str(self)

		if detector_node != None:
			self.init_from_detector_node(detector_node)
		else:
			if self._verbose:
				print str(self) + " set blank values"
			self._id = ""
			self.speed_list = []
			self._field_length = 0

	def init_from_detector_node(self, detector_node):
		if self._verbose:
			print str(self) + " loading from node: " + str(detector_node)
		self._node = detector_node

		# get the id for this detector
		self._id = self._node.get("name")
		if self._verbose:
			print str(self) + " set id = " + self._id

		# get the field length for this detector
		self._field_length = float(self._node.get("field"))
		if self._verbose:
			print str(self) + " set field length = " + str(self._field_length)

	def load_speeds(self, traffic_reader):
		if self._verbose:
			print str(self) + " loading speeds for detector " + str(self._id)
		speeds = traffic_reader.onemin_speeds_for_detector(detectorID=self._id, speed_limit=self._speed_limit)
		if self._verbose:
			print "loaded speeds: ", str(speeds)
		return speeds

if __name__ == "__main__":
	testfile = "test/metro_config.xml"
	test_traffic_dir = "trafficreader/test"

	def testing():
		test_config = TMS_Config(testfile, verbose=False)
		test_config.load_speeds_for_year(2010, test_traffic_dir)
		test_config.spatial_impute()
		#test_config.print_speeds()

	#prof = cProfile.run('testing()', 'test_profile')
	#p = pstats.Stats('test_profile')
	#p.sort_stats('cumulative').print_stats(10)

	testing()