from __future__ import division
from datetime import date, timedelta, time
from trafficreader import TrafficReader
from os import path
from collections import deque
from numpy import *
from pprint import pprint
import cProfile
import pstats
import impute
import xml.etree.cElementTree as ET

def avg_list(inputlist):
    return sum(inputlist) / len(inputlist)

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

    def weekly_impute(self):
        for corridor in self.corridor_list:
            corridor.weekly_impute()

    def long_temporal_impute(self):
        for corridor in self.corridor_list:
            corridor.long_temporal_impute()

    def average_weekday_speeds(self, start_time=None, end_time=None):
        '''
        Returns a dictionary mapping station ids to the average weekday speed for that station during the specified time interval
        '''
        average_speeds = {}
        for corridor in self.corridor_list:
            average_speeds.update(corridor.average_weekday_speeds(start_time, end_time))

        return average_speeds

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

        # build dictionary for mapping station index > id
        self.station_indices = {}
        for i in range(len(self.station_list)):
            self.station_indices[i] = self.station_list[i].id

    def add_station(self, station):
        self.station_list.append(station)

    def stations(self):
        return self.station_list

    def load_speeds(self, traffic_reader):
        for station in self.station_list:
            station.load_speeds(traffic_reader)

    def load_speeds_for_year(self, year, directory):
        self.year = year
        current_day = date(year, 1,1)
        last_day = date(year, 12, 31)
        n_days = (last_day - current_day).days

        # create 3D array to hold speeds
        # dimensions: station (in spatial order), date, timeslot (288 5-min slots)
        self.speeds = empty((len(self.station_list), n_days, 288), dtype=object)

        for i in range(len(self.station_list)):
            self.speeds[i,:,:] = self.station_list[i].load_speeds_for_year(year, directory)

    def print_speeds(self):
        print "Speeds for corridor ", self._route, self._dir
        for station_index in range(self.speeds.shape[0]):
            station_id = self.station_indices[station_index]
            print "  Speeds for station ", station_id
            for day_index in range(self.speeds.shape[1]):
                print "    Speeds for day ", day_index
                print self.speeds[station_index, day_index, :]

    def spatial_impute(self):
        # if there are no stations in this corridor, don't do anything
        if len(self.station_list) == 0:
            return

        # dimension 1 of speeds array is day
        speeds = self.speeds
        for day in range(speeds.shape[1]):
            # dimension 2 of speeds array is timeslot
            for timeslot in range(speeds.shape[2]):
                # impute values along the spatial axis (dimension 0)
                speeds[:, day, timeslot] = impute.impute_range(list(speeds[:, day, timeslot]),
                                                                    impute_length=4,
                                                                    input_length=1)

    def weekly_impute(self):
        # if there are no station in this corridor, don't do anytihng
        if len(self.station_list) == 0:
            return

        # dimension 1 is day
        # using the first 7 days as starting points, impute over station and time slot for every seventh day
        speeds = self.speeds
        for start_day in range(7):
            # dimension 0 is station
            for station in range(speeds.shape[0]):
                # dimension 2 is timeslot
                for timeslot in range(speeds.shape[2]):
                    speeds[station, start_day::7, timeslot] = impute.impute_range(list(speeds[station, start_day::7, timeslot]),
                                                                                       impute_length=3,
                                                                                       input_length=2)

    def long_temporal_impute(self):
        # if there are no staions in this corridor don't do anything
        if len(self.station_list) == 0:
            return

        # speed array dimensions: station, day, time
        speeds = self.speeds
        for station in range(speeds.shape[0]):
            for day in range(speeds.shape[1]):
                speeds[station, day, :] = impute.impute_range(list(speeds[station, day, :]),
                                                                   impute_length=6,
                                                                   input_length=6)

    def average_weekday_speeds(self, start_time=None, end_time=None):
        '''
        Returns a dictionary mapping station ids to the average weekday speed for that station during the specified time interval
        '''
        # if no times were passed, average for the whole day
        if start_time == None:
            start_time = time(0, 0, 0)
        if end_time == None:
            end_time = time(23, 59, 59)

        # make sure times are valid
        if start_time > end_time:
            raise ValueError("Start time must be before end time")

        speed_dict = {}
        for station_index in range(self.speeds.shape[0]):
            id = self.station_indices[station_index]
            speed_dict[id] = self.average_weekday_speed_for_station(station_index, start_time, end_time)

        return speed_dict

    def average_weekday_speed_for_station(self, station_index, start_time=None, end_time=None):
        '''
        For the specified station in this corridor, returns a single speed that represents the average of all valid speeds on weekdays between start_time and end_time.
        '''
        # convert times to timeslot indices
        start_time_index = timeslot_from_time(start_time)
        end_time_index = timeslot_from_time(end_time)

        # get the index of the first monday in the current year
        first_monday = index_of_first_monday_in_year(self.year)

        # build a list of all weekday speeds during the specified time interval
        selected_speeds = deque()
        speeds = self.speeds
        for offset in range(5):
            day_index = first_monday + offset
            # slice out the speeds for all stations, current day of week, specified time period
            s = speeds[station_index, day_index::7, start_time_index:end_time_index].flatten()
            selected_speeds.extend(list(s))

        selected_speeds = impute.remove_values(selected_speeds, None)
        return avg_list(list(selected_speeds))

class Station:

    def __init__(self, station_node=None, verbose=False):
        self._verbose = verbose
        self._node = None
        self._speed_limit = None
        self.id = None
        self._latlon = None
        self.detector_list = None

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
        self.id = self._node.get("station_id")
        if self._verbose:
            print str(self) + " set id = " + self.id

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
            self.add_detector(Detector(detector_node,
                                       speed_limit=self._speed_limit,
                                       verbose=self._verbose))

    def add_detector(self, detector):
        self.detector_list.append(detector)

    def detectors(self):
        return self.detector_list

    def speeds(self):
        return self.speed_list

    def speed_limit(self):
        return self._speed_limit

    def load_speeds_for_year(self, year, directory, recalc_field_lengths=False):
        if self._verbose:
            print "Loading speeds for station ", self.id
        current_day = date(year, 1, 1)
        last_day = date(year, 12, 31)
        one_day = timedelta(days=1)
        n_days = (last_day - current_day).days

        # initialize empty 2D array to hold speeds
        # dimensions: date (n_days), timeslot (288 5-min slots)
        self.speeds = empty((n_days, 288), dtype=object)

        for day in range(n_days):
            if self._verbose:
                print "    Loading speeds for ", current_day

            # If there are no detectors, there are no valid speeds
            if self.detector_list == []:
                day_speeds = [None] * 288
            # Otherwise, load speeds from each detector
            else:
                try:
                    traffic_file = self.traffic_filename_from_date(current_day)
                    tr = TrafficReader(path.join(directory, traffic_file))

                    # average 1min speeds across detectors
                    day_speeds = impute.average_multilist(
                        [detector.load_speeds(tr, recalc_field_lengths)
                         for detector in self.detector_list])
                    # "short duration temporal linear regression" = impute gaps
                    # up to 3 slots long use adjacent values
                    day_speeds = impute.impute_range(day_speeds,
                                                     impute_length=3,
                                                     input_length=3)
                    # average 1min speeds to 5min speeds
                    day_speeds = impute.average_list(day_speeds, 5)
                    # "short duration temporal linear regression" again
                    day_speeds = impute.impute_range(day_speeds,
                                                     impute_length=3,
                                                     input_length=3)
                    # remove any single missing values by averaging adjacent
                    # values
                    day_speeds = impute.impute1(day_speeds)
                except IOError:
                    # If there is no file for the given day, add a list of
                    # invalid speeds
                    day_speeds = [None] * 288

            self.speeds[day,:] = day_speeds
            current_day = current_day + one_day

        return self.speeds

    def load_speeds(self, traffic_reader, recalc_field_lengths=False):
        # if there are no detectors for this station, give it a speed list of all invalid speeds
        if self.detector_list == []:
            self.speeds = [None] * 288
        # otherwise, load the speeds from the detectors
        else:
            for detector in self.detectors():
                detector.load_speeds(traffic_reader, recalc_field_lengths)

            speeds = impute.average_multilist([detector.load_speeds(traffic_reader) for detector in self.detector_list])
            speeds = impute.impute_range(speeds, impute_length=3, input_length=3)
            speeds = impute.average_list(speeds, 5)
            self.speed_list = impute.impute1(speeds)

    def print_speeds(self):
        print "Speeds for station " + self.id
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
            self.id = ""
            self.speed_list = []
            self._field_length = 0

    def init_from_detector_node(self, detector_node):
        if self._verbose:
            print str(self) + " loading from node: " + str(detector_node)
        self._node = detector_node

        # get the id for this detector
        self.id = self._node.get("name")
        if self._verbose:
            print str(self) + " set id = " + self.id

        # get the field length for this detector
        self._field_length = float(self._node.get("field"))
        if self._verbose:
            print str(self) + " set field length = " + str(self._field_length)

    def load_speeds(self, traffic_reader, recalc_field_length=False):
        if self._verbose:
            print str(self) + " loading speeds for detector " + str(self.id)

        if recalc_field_length:
            field_length = self._field_length
        else:
            field_length = None

        speeds = traffic_reader.onemin_speeds_for_detector(
                                                detectorID=self.id,
                                                speed_limit=self._speed_limit,
                                                field_length=field_length )

        if self._verbose:
            print "loaded speeds: ", str(speeds)
        return speeds


if __name__ == "__main__":
    testfile = "test/metro_config_short.xml"
    test_traffic_dir = "trafficreader/test"

    def testing():
        test_config = TMS_Config(testfile, verbose=False)
        test_config.load_speeds_for_year(2010, test_traffic_dir)
        test_config.spatial_impute()
        test_config.weekly_impute()
        test_config.long_temporal_impute()
        #pprint(test_config.average_weekday_speeds(start_time=time(hour=10), end_time=time(hour=12)), width=1)
        #test_config.print_speeds()

    #prof = cProfile.run('testing()', 'test_profile')
    #p = pstats.Stats('test_profile')
    #p.sort_stats('cumulative').print_stats(10)

    testing()
