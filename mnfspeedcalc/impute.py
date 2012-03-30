from __future__ import division

def gap_list(inputlist, gap_value=-1):
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
				gap_end  = i
			else:
				gap_end = i
				continue
		else:
			if in_gap:
				yield gap_start, gap_end
				in_gap = False
				continue
			else:
				continue
	
	if in_gap:
		yield gap_start, gap_end

def impute1(inputlist, gap_value=-1):
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

def linear_regression(y):
	'''
	Returns a function that can generate new values based on parameters estimated using linear regression on the input values
	'''
	x = range(len(y))
	
	# first, remove any invalid (-1) data in y as well as the corresponding x values
	while True:
		try:
			i = y.index(-1)
			del y[i]
			del x[i]
		except ValueError:
			break
	
	n = len(y)
	
	numerator = (n * sum(xi * yi for xi, yi in zip(x, y))) - (sum(x) * sum(y))
	denominator = (n * sum(xi**2 for xi in x)) - (sum(x)**2)
	
	slope = numerator / denominator
	intercept = (sum(y) / len(y)) - (slope * (sum(x) / len(x)))
	
	def f(input):
		return (slope * input) + intercept
		
	return f

if __name__ == "__main__":

	testlist = [0,-1, 1,-1,-1,-1, 2,-1, 3, 4,-1,-1,-1, 5,-1]
	
	print "Test gap_list"
	for index in gap_list(testlist):
		print index
		
 	print "Test impute1"
	print impute1(testlist)
	
	print "Test linear_regression"
	f = linear_regression((0,3,4,4,8,10))
	print f(-1)