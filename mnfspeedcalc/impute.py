from __future__ import division
from collections import deque
from numpy import array
import itertools as IT

def remove_values(inputlist, targetvalue):
	'''
	Returns a copy of inputlist with all elements with value targetvalue removed
	'''
	return [x for x in inputlist if x != targetvalue]

def gap_list(inputlist, gap_value=None):
	'''
	Returns a list of indices into inputlist that indicate the first in a sequence of elements with value gap_value
	'''

	in_gap = False
	gap_start = 0
	gap_end = 0

	for i in range(len(inputlist)):
		if inputlist[i] == gap_value:
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


def impute_range(inputlist, impute_length, input_length):
	'''
	Fills in gaps up to the specified length using linear regression. impute_length specifies the maximum number of values that can be imputed. input_length specifies how far to the left and right of a gap we should look for input values.
	'''
	outputlist = inputlist

	for gap_start, gap_end in gap_list(inputlist):
		gap_length = gap_end - gap_start

		if gap_length <= impute_length:
			# case [... o o o x x x o o o ...]
			# establish left and right bounds for regression, making sure not to run off the beginning or end of the input list
			left = gap_start - input_length
			if left < 0:
				left = 0
			right = gap_end + input_length
			if right > len(inputlist):
				right = len(inputlist)

			try:
				regression_function = linear_regression(inputlist[left:right], min_valid=2)
			except ValueError:
				# if there aren't enough valid values nearby for regression, skip this gap
				continue

			# fill in the gap values using the regression function. note that for the purposes of regression, left = 0
			for i in range(gap_start, gap_end):
				outputlist[i] = regression_function(i - left)

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
				regression_function = linear_regression(inputlist[left:right], min_valid=2)
				for i in range(gap_start, right):
					left_list.append(regression_function(i - left))
			except ValueError:
				# if there aren't enough valid values nearby for regression, leave invalid values for this side of the gap
				left_list = [None] * impute_length

			# now the right end
			left = gap_end - input_length
			right = gap_end + input_length
			if right > len(inputlist):
				right = len(inputlist)

			right_list = []

			try:
				regression_function = linear_regression(inputlist[left:right], min_valid=2)
				for i in range(left, gap_end):
					right_list.append(regression_function(i - left))
			except ValueError:
				# if there aren't enough valid values nearby for regression, leave invalid values for this side of the gap
				right_list = [None] * impute_length

			# put the imputed values into the output
			outputlist[gap_start:gap_start + impute_length] = left_list
			outputlist[gap_end - impute_length:gap_end] = right_list

			# do imputed ranges overlap?
			if gap_start + impute_length >= gap_end - impute_length:
				# find the indices where they overlap
				overlaps = list(set(range(gap_start, gap_start + impute_length)) & set(range(gap_end - impute_length, gap_end)))
				# average the overlaping parts of the lists and put them into the output
				for i in overlaps:
					left_value = left_list[i - gap_start]
					right_value = right_list[impute_length - (gap_end - i)]
					if left_value == None:
						outputlist[i] = right_value
					elif right_value == None:
						outputlist[i] = left_value
					else:
						outputlist[i] = (left_value + right_value) / 2

	return outputlist

def linear_regression(y, min_valid=1):
	'''
	Returns a function that can generate new values based on parameters estimated using linear regression on the input values
	'''
	x = range(len(y))

	# first, remove any invalid (None) data in y as well as the corresponding x values
	while True:
		try:
			i = y.index(None)
			del y[i]
			del x[i]
		except ValueError:
			break

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

def average_multilist(inputlists, max_invalid=1):
	'''
	Averages the corresponding elements of the input lists. If more than max_invalid of the input elements in each slot are invalid (None), the resulting average is invalid.
	'''
	inputlist = zip(*inputlists)
	outputlist = deque()

	for i in range(len(inputlist)):
		group = inputlist[i]
		num_invalid = group.count(None)
		if len(group) <= 2 and num_invalid != 0:
			outputlist.append(None)
		elif num_invalid > max_invalid:
			outputlist.append(None)
		else:
			clean_group = remove_values(list(group), None)
			outputlist.append(sum(clean_group) / len(clean_group))

	return list(outputlist)


if __name__ == "__main__":

	testlist = [0,None, 1,None,None,None, 2,None, 3, 4,None,None,None, 5,None]

	print "Test gap_list"
	for index in gap_list(testlist):
		print index

 	print "Test impute1"
	print impute1(testlist)

	print "Test linear_regression"
	f = linear_regression((0,3,4,4,8,10))
	print f(None)

	print "Test impute_range"
	print impute_range(testlist,3,3)
