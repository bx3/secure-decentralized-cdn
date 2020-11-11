#!/usr/bin/env python
import sys
import os
import networkx as nx
import graph as Graph
from messages import *
from config import *

# create nodes 
graph = Graph.init_nodes(N_PUB, N_LURK, N_SYBIL)
# create edges
Graph.setup_warm_network(graph, 'rand')

epoch = 120 # round 

m = Message(MessageType.GRAFT,1,2)
print(m)


for i in range(epoch):
    break
    # chosen attack strategy according to attack 1  
    # get a list of state to be added to the graph
    # update graph st


