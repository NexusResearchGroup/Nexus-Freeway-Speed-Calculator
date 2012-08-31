import mnfspeedcalc as mnfsc
import argparse
from datetime import time
from pprint import pprint
import re
import csv
import math


def s_num(station_id):
	# strip the alphabetic prefixes off the station IDs
	return int(re.findall(r'\d+', station_id)[0])

program_description = "Calculates average weekday speeds over specified time intervals from loop detector data stored in .traffic files"

parser = argparse.ArgumentParser(prog="NexusFSCalc.py", version="0.1.0", description=program_description)
parser.add_argument('-d', metavar='DIRECTORY', required=True, help='Directory holding .traffic files') # base directory of .traffic data
parser.add_argument('-y', metavar='YEAR', type=int, required=True, help='Year to analyze') # year
parser.add_argument('-m', metavar='METRO_CONFIG', required=True, help='Path to metro_config.xml') # metro_config file
parser.add_argument('-s', metavar='START_TIME', type=int, required=True, help='Start time (hour, e.g. 7 or 16)') # start time (hour)
parser.add_argument('-e', metavar='END_TIME', type=int, required=True, help='Start time (hour, e.g. 9 or 18') # end time (hour)
parser.add_argument('-o', metavar='OUTPUT_FILE', type=argparse.FileType('wb'), required=True, help='Output file')
args = parser.parse_args()

metro_config_file = args.m
year = args.y
data_dir = args.d
start_time = time(hour = args.s)
end_time = time(hour = args.e)
output_file = args.o

# Calculate average speeds
calculator = mnfsc.TMS_Config(metro_config_file)
calculator.load_speeds_for_year(year, data_dir)
calculator.spatial_impute()
calculator.weekly_impute()
calculator.long_temporal_impute()
results = (calculator.average_weekday_speeds(start_time, end_time))

# Write speeds to output file
w = csv.writer(output_file)
w.writerow(['sid', 'speed'])
for p in results.items():
	id = s_num(p[0])
	speed = p[1]
	if math.isnan(speed):
		continue
	w.writerow([id, speed])
output_file.close()
