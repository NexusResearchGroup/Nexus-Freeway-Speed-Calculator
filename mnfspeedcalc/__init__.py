from speedlist import SpeedList
from trafficreader import TrafficReader
from datetime import date, timedelta
import impute
import xml.etree.cElementTree as ET

metro_config = 'test/metro_config.xml'
year = 2010

# load tree from metro_config.xml
tree = ET.parse(metro_config)
root = tree.getroot()

corridors = {}

for corridor_node in root.findall('corridor'):
	corridor_key = (corridor_node.get('route'), corridor_node.get('dir'))
	print "Found corridor: " + str(corridor_key)
	stations = {}
	for station_node in corridor_node.findall("r_node[@n_type='Station'][@station_id]"):
		station_key = station_node.get('station_id')
		print "    Found station: " + station_key
		for detector_node in station_node.findall("detector"): #filter on detector type=''?
			detector_key = detector_node.get('name')
			print "        Found detector: " + detector_key

