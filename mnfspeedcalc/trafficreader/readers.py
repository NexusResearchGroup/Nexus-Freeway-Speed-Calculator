from __future__ import division
from numpy import *
import struct

def list_volumes(volumefile):
	'''
	Reads the binary volume counts from volumefile and returns them as a
	1-dimensional numpy.array.
	'''

	# interpret the file as a sequence of 2880 signed chars (single bytes)
	format = 'b' * 2880

	try:
		vol_array = array(struct.unpack(format, volumefile.read()), dtype=float)
	# catch files with invalid lengths
	except struct.error:
		vol_array = array([NAN] * 2880)
		return vol_array

	# Valid sample ranges for volumes are 0 - 40. If outside this range, set to
	# NAN to indicate bad data.
	bad_mask = (vol_array < 0) | (vol_array > 40)
	vol_array[bad_mask] = NAN
	return vol_array

def list_occupancies(occupancyfile):
	'''
	Reads the binary occupancy ratios from occupancyfile and returns them as a
	list.
	'''

	# interpret the file as a sequence of 2880 short integers (double bytes,
	# big endian)
	format = '>' + ('h' * 2880)

	try:
		occ_array = array(struct.unpack(format, occupancyfile.read()), dtype=float)
	except struct.error:
		occ_array = array([NAN] * 2880)
		return occ_array

	# Valid sample ranges for occupancies are 0 - 1800. If outside this range,
	# set to None to indicate bad data. Return valid data as a ratio of 1800.
	bad_mask = (occ_array < 0) | (occ_array > 1800)
	occ_array[bad_mask] = NAN
	return occ_array / 1800

if __name__ == '__main__':
	occ_file = open('test/1234.c30')
	vol_file = open('test/1234.v30')
	print list_volumes(vol_file)
	print list_occupancies(occ_file)
