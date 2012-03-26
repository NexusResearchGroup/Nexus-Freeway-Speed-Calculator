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

corridors = root.findall('corridor')

corridor_list = []

for corridor in corridors:
	
	corridor_dict = {}
	corridor_dict['name'] = corridor.get('route') + ' ' + corridor.get('dir')

	station_list = []

	r_nodes = corridor.findall('r_node')
	for r_node in r_nodes:

		if r_node.get('n_type') == 'Station':
			station_dict = {}
			station_dict['station_id'] = r_node.get(station_id)
			station_dict['speed_limit'] = eval(r_node.get('s_limit'))

			
			detectors = r_node.findall('detector')
			for detector in detectors:


			station_list.append(station_dict)

	corridor_dict['station_list'] = station_list
	corridor_list.append(corridor_dict)