#!/bin/bash
trap kill_test INT
function kill_test() {
    stop_time=$(date +%s)
    echo "STOP EXP ${stop_time}" # >> experiment.txt
    for pid in $pidwaits; do
        echo "KILL $pid"
	$(sudo kill -9 $pid)
    done
}

num_epoch=10000
pids=""

map_dir="maps"
mkdir -p ${map_dir}


# # # # # # # # # # # # # # 
# # random topo 
# # # # # # # # # # # # # # 
#topo=random_500n_4topic
#./scripts/plot_topo.py topo/${topo}.json "${map_dir}/${topo}"

#./testbed.py run topo/${topo}.json ${num_epoch} output-${topo}-gossip-r${num_epoch} individual &
#pid="$!"
#pids="$pids $pid"

#./testbed.py run topo/${topo}.json ${num_epoch} output-${topo}-subset-r${num_epoch} coll-subset & 
#pid="$!"
#pids="$pids $pid"

## # # # # # # # # # # # # # 
## # pure continent
## # # # # # # # # # # # # # 

topo=pure_continent_100n_4topic
./scripts/plot_topo.py topo/${topo}.json "${map_dir}/${topo}"

./testbed.py run topo/${topo}.json ${num_epoch} sim-output-${topo}-gossip-r${num_epoch} individual & 
pid="$!"
pids="$pids $pid"

./testbed.py run topo/${topo}.json ${num_epoch} sim-output-${topo}-subset-r${num_epoch} coll-subset &
pid="$!"
pids="$pids $pid"

# # # # # # # # # # # # # # 
# # two continent
# # # # # # # # # # # # # # 

#topo=two_continent_100n_4topic
#./scripts/plot_topo.py topo/${topo}.json "${map_dir}/${topo}"

#./testbed.py run topo/${topo}.json ${num_epoch} output-${topo}-gossip-r${num_epoch} individual & 
#pid="$!"
#pids="$pids $pid"

#./testbed.py run topo/${topo}.json ${num_epoch} output-${topo}-subset-r${num_epoch} coll-subset & 
#pid="$!"
#pids="$pids $pid"

echo "wait $pids"
for pid in $pids; do
    wait $pid
done
echo "Done"
