#!/bin/bash

if [ $# -ne 4 ]; then
    echo "Require topo<str> epoch<int> exp-name<str> update_method<individual/coll-subset>"
    echo "Example. ./run.sh topo/pure_continent_500n_4topic.json 1000 test individual"
    echo "The result stored in output/test"
    exit 0
fi

topo=$1
epoch=$2
expname=$3
update_method=$4
dirPath="output/$expname"

echo $topo
echo $dirPath

rm -rf $dirPath
mkdir $dirPath
cp $topo $dirPath
echo "Start simulating"
./testbed.py run ${topo} ${epoch} $dirPath coll-subset
echo "Start plotting"
./testbed.py plot ${topo} ${epoch} ${dirPath}

