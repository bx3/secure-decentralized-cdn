#!/bin/bash
seed_start=0
seed_end=5

for (( i=${seed_start}; i<=${seed_end} ; i++ )); do
	#./testbed.py plot topo/two_pub_7_sybil_p05s.json test $i 0 1
	# ./testbed.py plot topo/ten_pub_7_sybil_p05.json test $i 0 1 2 3 4 5 6 7 8 9
	#./testbed.py plot topo/five_pub_7_sybil_p05.json test $i 0 1 2 3 4
	./testbed.py plot topo/three_pub_7_sybil_p05.json test $i 0 1 2
done
