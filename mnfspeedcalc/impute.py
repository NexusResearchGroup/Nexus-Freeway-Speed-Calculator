from __future__ import division
from collections import deque
from numpy import *

def count_nonnan(inputarray):
	'''
	Given a numpy.array, returns an integer count of the elements which have
	some value other than NAN
	'''

	return count_nonzero(~isnan(inputarray))

def remove_values(inputlist, targetvalue):
	'''
	Returns a copy of inputlist with all elements with value targetvalue removed
	'''
	return [x for x in inputlist if x != targetvalue]

def gap_list(inputarray):
	'''
	Returns a list of indices into inputarray that indicate the first in a
	sequence of elements with value nan
	'''

	in_gap = False
	gap_start = 0
	gap_end = 0

	for i in range(len(inputarray)):
		if isnan(inputarray[i]):
			if not in_gap:
				in_gap = True
				gap_start = i
			else:
				continue
		else:
			if in_gap:
				gap_end = i
				yield gap_start, gap_end
				in_gap = False
				continue
			else:
				continue

	if in_gap:
		yield gap_start, gap_end

def impute1(inputlist, gap_value=None):
	'''
	Fills in single missing values by averaging adjacent values
	'''
	outputlist = inputlist

	for i in range(1, len(inputlist) - 1):
		if inputlist[i] == gap_value:
			prev = inputlist[i-1]
			next = inputlist[i+1]
			if prev != gap_value and next != gap_value:
				outputlist[i] = (prev + next) / 2

	return outputlist

def impute_range(inputarray, impute_length, input_length):
	'''
	Fills in gaps up to the specified length using linear regression.
	impute_length specifies the maximum number of values that can be imputed.
	input_length specifies how far to the left and right of a gap we should
	look for input values.
	'''
	outputarray = inputarray.copy()

	for gap_start, gap_end in gap_list(inputarray):
		gap_length = gap_end - gap_start

		if gap_length <= impute_length:
			# case [... o o o x x x o o o ...]
			# establish left and right bounds for regression, making sure not
			# to run off the beginning or end of the input list
			left = gap_start - input_length
			if left < 0:
				left = 0
			right = gap_end + input_length
			if right > len(inputarray):
				right = len(inputarray)

			try:
				regression_function = linear_regression(inputarray[left:right], min_valid=2)
			except ValueError:
				# if there aren't enough valid values nearby for regression,
				# skip this gap
				continue

			# fill in the gap values using the regression function. note that
			# for the purposes of regression, left = 0
			for i in range(gap_start, gap_end):
				outputarray[i] = regression_function(i - left)

		else:
			# case [... o o o x x x x o o o ...] and
			# case [... o o o x x x ... x x x o o o ...]

			# first, do the left end
			left = gap_start - input_length
			if left < 0:
				left = 0
			right = gap_start + input_length

			left_list = []

			try:
				regression_function = linear_regression(inputarray[left:right], min_valid=2)
				for i in range(gap_start, right):
					left_list.append(regression_function(i - left))
			except ValueError:
				# if there aren't enough valid values nearby for regression,
				# leave invalid values for this side of the gap
				left_list = [None] * impute_length

			# now the right end
			left = gap_end - input_length
			right = gap_end + input_length
			if right > len(inputarray):
				right = len(inputarray)

			right_list = []

			try:
				regression_function = linear_regression(inputarray[left:right], min_valid=2)
				for i in range(left, gap_end):
					right_list.append(regression_function(i - left))
			except ValueError:
				# if there aren't enough valid values nearby for regression,
				# leave invalid values for this side of the gap
				right_list = [None] * impute_length

			# put the imputed values into the output
			outputarray[gap_start:gap_start + impute_length] = left_list
			outputarray[gap_end - impute_length:gap_end] = right_list

			# do imputed ranges overlap?
			if gap_start + impute_length >= gap_end - impute_length:
				# find the indices where they overlap
				overlaps = list(set(range(gap_start, gap_start + impute_length)) & set(range(gap_end - impute_length, gap_end)))
				# average the overlaping parts of the lists and put them into
				# the output
				for i in overlaps:
					left_value = left_list[i - gap_start]
					right_value = right_list[impute_length - (gap_end - i)]
					if left_value == None:
						outputarray[i] = right_value
					elif right_value == None:
						outputarray[i] = left_value
					else:
						outputarray[i] = (left_value + right_value) / 2

	return outputarray

def linear_regression(y, min_valid=1):
	'''
	Returns a function that can generate new values based on parameters
	estimated using linear regression on the input values
	'''
	x = arange(len(y))

	# first, remove any invalid (None) data in y as well as the corresponding x
	# values
	mask = ~isnan(y)
	x = x[mask]
	y = y[mask]

	n = len(y)
	if n < min_valid:
		raise ValueError("Not enough valid values for regression")

	numerator = (n * sum(xi * yi for xi, yi in zip(x, y))) - (sum(x) * sum(y))
	denominator = (n * sum(xi**2 for xi in x)) - (sum(x)**2)

	slope = numerator / denominator
	intercept = (sum(y) / len(y)) - (slope * (sum(x) / len(x)))

	def f(input):
		return (slope * input) + intercept

	return f

def average_list(inputlist, block_size, max_invalid=1):
	'''
	Averages the input list into blocks of block_size. If more than max_invalid of the input elements in each block are invalid (None), the resulting average block is invalid.
	'''

	outputlist = deque()

	for i in range(0, len(inputlist), block_size):
		block = inputlist[i:i+block_size]

		if block.count(None) > max_invalid:
			outputlist.append(None)
		else:
			block = remove_values(block,None)
			outputlist.append(sum(block) / len(block))

	return list(outputlist)

def average_multilist(inputarrays, max_invalid=1):
	'''
	Averages the corresponding elements of the input arrays. If more than
	max_invalid of the input elements in each slot are invalid (NAN), the
	resulting average is invalid.
	'''

	inputstack = vstack(inputarrays)
	outputarray = empty([len(inputarrays[0])])

	for i in range(len(inputarrays[0])):
		group = inputstack[:, i]
		num_valid = count_nonnan(group)
		num_invalid = len(group) - num_valid
		if num_invalid > max_invalid:
			outputarray[i] = nan
		else:
			outputarray[i] = nansum(group) / num_valid

	return outputarray

if __name__ == "__main__":
	set_printoptions(precision=2)

	a = array([50,50,50,nan,55,50,50,50,50,50])
	b = array([60,nan,60,60,60,60,nan,60,60,60])
	c = array([70,70,nan,nan,70,70,nan,65,70,70])

	speeds = average_multilist([a,b,c])
	print speeds
	print impute_range(speeds, 3, 3)
