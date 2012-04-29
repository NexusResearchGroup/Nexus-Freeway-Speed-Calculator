from __future__ import division
from datetime import date, timedelta, time
from trafficreader import TrafficReader
from os import path
from collections import deque, namedtuple
from pprint import pprint
from numpy import *
import cProfile
import pstats
import impute
import xml.etree.cElementTree as ET

Corridor = namedtuple(typename = 'Corridor',
					  field_names = ['name', 'station_ids'])

Station = namedtuple(typename = 'Station',
						  field_names = ['id','speed_limit', 'detector_names', 'index'])

def load_corridors(metro_config_file):
	'''
	Returns a list of corridors in the specified metro_config_file.

	Each corridor is represented by a Corridor named tuple. The corridors and
	stations are listed in the order in which they appear in the file.
	'''

	#print "Loading corridors from ", metro_config_file

	root = ET.parse(metro_config_file).getroot()

	corridor_list = []
	for corridor_node in root.findall('corridor'):
		corridor_name = corridor_node.get('route') + ' ' + corridor_node.get('dir')

		station_id_list = []
		for station_node in corridor_node.findall("r_node[@n_type='Station'][@station_id]"):
			station_id_list.append(station_node.get('station_id'))

		corridor_list.append(Corridor(name = corridor_name,
									  station_ids = station_id_list))

	return corridor_list

def load_stations(metro_config_file):
	'''
	Returns a dictionary mapping station ids to Station namedtuples.
	'''

	#print "Loading stations from ", metro_config_file

	root = ET.parse(metro_config_file).getroot()

	station_dict = {}
	station_index = 0
	for station_node in root.findall(".//r_node[@n_type='Station'][@station_id]"):

		detector_name_list = [det.get('name') for det in station_node.findall("detector")]

		station_dict[station_node.get('station_id')] = (Station(id = station_node.get('station_id'),
																speed_limit = station_node.get('s_limit'),
																detector_names = detector_name_list,
																index = station_index))
		station_index += 1

	return station_dict

def load_5m_station_speeds_year(stations, year, directory):
	'''
	Returns a numpy.array of 1-minute speeds for the stations.

	The dimensions of the array are (s, d, m), where:
		s = the index of the station
		d = the index of the day in the specified year
		m = the index of the 5-minute slot in the day
	Each value is either a float representing the station speed at that minute,
	or numpy.NaN if there is no valid speed.
	'''

	#print "Loading 5m data for year ", year

	speedarray = empty([len(stations), ndays_in_year(year), 288])

	date_index = 0
	for date in dates_in_year(year):
		load_5m_station_speeds_day(stations, date, directory, speedarray[:,date_index,:])
		date_index += 1

	return speedarray

def load_5m_station_speeds_day(stations, date, directory, targetarray):
	'''
	Fills targetarray with 1-minute speeds for the stations for a single day.

	The dimensions of the arrray are (s, m), where:
		s = the index of the station
		m = the index of the 5-minute slot in the day (288)
	Each value is either a float representing the station speed at that minute,
	or numpy.NaN if there is no valid speed.
	'''

	#print "Loading 5m data for date ", date
	#print "    from ", path.join(directory, traffic_filename_from_date(date))

	# make sure that targetarray has the right dimensions
	if targetarray.shape != (len(stations), 288):
		raise ValueError("Target array has wrong dimensions to hold station speeds")

	try:
		tr = TrafficReader(path.join(directory, traffic_filename_from_date(date)))
	except IOError:
		# if there is no file for the given day, return a list of invalid speeds
		targetarray[:,:] = nan
		return

	for sid in stations:

		#print "    Loading speeds for station ", sid

		# if there are no detectors associated with this station, it has no
		# speeds
		if len(stations[sid].detector_names) == 0:
			targetarray[stations[sid].index,:] = nan
		# otherwise, get the speeds for all detectors, combine them, and perform
		# imputation
		else:
			targetarray[stations[sid].index,:] = \
				impute.impute1(
					impute.impute_range(
						impute.average_list(
							impute.impute_range(
								impute.average_multilist(
									[tr.onemin_speeds_for_detector(d) for d in stations[sid].detector_names]
								),
								impute_length = 3,
								input_length = 3
							),
							block_size = 5,
							max_invalid = 1
						),
						impute_length = 3,
						input_length = 3
					)
				)

def avg_list(input):
	return sum(input) / len(input)

def count_nonnan(inputarray):
	'''
	Given a numpy.array, returns an integer count of the number of elements
	which are anything other than NAN.
	'''

	return count_nonzero(~isnan(inputarray))

def nanavg(inputarray):
	'''
	Given a numpy.array, returns the average value of all elements, ignoring
	elements whose value is NAN.
	'''
	num_nonnan = count_nonnan(inputarray)
	if num_nonnan == 0:
		return nan
	else:
		return nansum(inputarray) / num_nonnan

def timeslot_from_time(input_time):
	'''
	Determines the 5-minute slot index of the given time of day, where 00:00:00
	is index 0, 00:05:00 is index 1, and 23:55:00 is index 287
	'''
	hour = input_time.hour
	minute = (input_time.minute // 5)
	return (hour * 12) + minute

def index_of_first_monday_in_year(year):
	'''
	Determines the index of the first Monday in the given year, where January 1
	is index 0.
	'''
	test_date = date(year, 1, 1)
	one_day = timedelta(days=1)
	for index in range(7):
		# monday is weekday 0
		if (test_date + (one_day * index)).weekday() == 0:
			return index

def ndays_in_year(year):
	return (date(year + 1, 1, 1) - date(year, 1, 1)).days

def weekday_indices_in_year(year):
	'''
	Returns a list of the indices of all the weekdays (M-F) in the given year,
	where index 0 is January 1
	'''
	first_monday = index_of_first_monday_in_year(year)
	ndays = ndays_in_year(210)
	weekdays = []
	for base_weekday in range(first_monday, first_monday + 5):
		weekdays.extend(range(base_weekday, ndays, 7))
	weekdays.sort()
	return weekdays

def traffic_filename_from_date(date):
	return date.strftime("%Y%m%d") + ".traffic"

def dates_in_year(year):
	'''
	Returns a generator which iterates over all dates in the specified year.
	'''
	current_date = date(year, 1, 1)
	one_day = timedelta(days=1)
	while current_date.year == year:
		yield current_date
		current_date = current_date + one_day

def weekdays_in_year(year):
	'''
	Returns a generator which iterates over all weekdays in the specified year.
	'''
	current_date = date(year, 1,1)
	one_day = timedelta(days=1)
	while current_date.year == year:
		if current_date.weekday() in range(5):
			yield current_date
		current_date = current_date + one_day

def weekly_impute(speedarray):
	'''
	Given the speed array, performs week-to-week imputation of speeds for
	individual stations. The speed array is updated in place; nothing is
	returned.
	'''
	for start_day in range(7):
		for station in range(speedarray.shape[0]):
			for timeslot in range(speedarray.shape[2]):
				speedarray[station, start_day::7, timeslot] = \
					impute.impute_range(speedarray[station, start_day::7, timeslot],
										impute_length=3,
										input_length=2)

def corridor_impute(corridors, stations, speedarray):
	'''
	Given a list of corridors, a list of stations, and the speed array, performs
	spatial imputation of speeds along the stations in a corridor.

	The speed array is updated in place; nothing is returned
	'''
	for corridor in corridors:
		station_indices = [stations[sid].index for sid in corridor.station_ids]
		for day in range(speedarray.shape[1]):
			for timeslot in range(speedarray.shape[2]):
				speedarray[station_indices, day, timeslot] = \
					impute.impute_range(speedarray[station_indices, day, timeslot],
										impute_length=4,
										input_length=1)

def long_temporal_impute(stations, speedarray):
	'''
	Given the speed array, performs "long" temporal impution of gaps up to
	6 timeslots long. The speed array is updated in place; nothing is returned.
	'''

	for station in range(speedarray.shape[0]):
		for day in range(speedarray.shape[1]):
			speedarray[station, day, :] = impute.impute_range(speedarray[station, day, :],
															  impute_length=6,
															  input_length=6)

def average_hourly_weekday_speeds(speedarray, stations, year):
	results = {}
	weekdays = weekday_indices_in_year(2010)
	hours = range(0, 288, 12) # 12 timeslots per hour
	for station_id in stations:
		sidx = stations[station_id].index
		hourly_speed_list = [nanavg(speedarray[sidx, weekdays, h:(h+12)])
							 for h in hours]
		results[station_id] = hourly_speed_list
	return results

if __name__ == "__main__":
	test_mcfile = "test/metro_config.xml"
	test_traffic_dir = "/Users/aowen/Desktop/2010/test"
	year = 2010

	def testing():
		stations = load_stations(test_mcfile)
		corridors = load_corridors(test_mcfile)
		speedarray = load_5m_station_speeds_year(stations, 2010, test_traffic_dir)
		print speedarray


	testing()
