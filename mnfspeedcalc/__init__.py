from speedlist import SpeedList
from trafficreader import TrafficReader
import impute
import xml.etree.cElementTree as ET

metro_config = 'test/metro_config.xml'

# load tree from metro_config.xml
tree = ET.parse(metro_config)
root = tree.getroot()

corridors = root.findall('corridor')

# for each corridor

#	for each station

#		for each detector