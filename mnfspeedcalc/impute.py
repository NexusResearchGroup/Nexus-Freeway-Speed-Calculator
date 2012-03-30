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