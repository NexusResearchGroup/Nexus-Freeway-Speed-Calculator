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


def impute3(inputlist):
	outputlist = inputlist
	
	for gap_start, gap_end in gap_list(inputlist):
		gap_length = gap_end - gap_start + 1
		
		if gap_length <=3:
			pass
		
		else:
			pass
	
	return outputlist

def linear_regression

if __name__ == "__main__":

	testlist = [0,-1, 1,-1,-1,-1, 2,-1, 3, 4,-1,-1,-1, 5,-1]
	
	print "Test gap_list"
	for index in gap_list(testlist):
		print index
		
 	print "Test impute1"
	print impute1(testlist)