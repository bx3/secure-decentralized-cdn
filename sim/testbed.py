#!/usr/bin/env python
import sys
import os
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from graph import *
from network import Network
from messages import *
from config import *
from protocols import GossipSub

def count_components(graph):
    sets = {}
    for u in graph.nodes:
      sets[u] = DisjointSet()
    for u in graph.nodes:
        for vtx in graph.nodes[u].conn:
            sets[u].union(sets[vtx])
    return len(set(x.find() for x in sets.values()))

class DisjointSet(object):
    def __init__(self):
        self.parent = None

    def find(self):
        if self.parent is None: return self
        return self.parent.find()

    def union(self, other):
        them = other.find()
        us = self.find()
        if them != us:
            us.parent = them

# storing node states 
graph = Graph(N_PUB, N_LURK, N_SYBIL)
# storing rx-msg queue states
network = Network(N_PUB+N_LURK+N_SYBIL)
# create random topology, need to change later 
graph.preset_rand_honest_peers()
#graph.add_conn_msgs()

epoch = 120 # round 

#m = Message(MessageType.GRAFT,1,2)

# protocol
gossipsub = GossipSub()
# flood =

degrees = []
components = []
for curr_r in range(epoch):
    # Get the degree of each node
    degree = []
    for u in graph.nodes:
        degree.append(len(graph.nodes[u].conn))
    degrees.append(degree)
    # Get the number of component
    components.append(count_components(graph))

    curr_msgs = []
    # TODO honest nodes
    for u in graph.nodes:
        msgs = gossipsub.push_local_mesh(graph, u)    
        curr_msgs += msgs

    # chosen attack strategy according to attack  
    adv_msgs = []
    # maybe rearrange message order
    curr_msgs = adv_msgs + curr_msgs
    # deliver msgs
    network.deliver_msgs(curr_msgs, curr_r)

    # node process messages
    for u in graph.nodes:
        msgs = network.get_msgs(u, curr_r)
        gossipsub.process_msgs(graph, u, msgs)    

    # node take new action
    gossipsub.node_action(graph)

    
# analyze stat ... generate figure
# print the final states
# for u in graph.nodes:
#     print(graph.nodes[u].conn)

# degree changes
degrees_mean = []
degrees_max = []
degrees_min = []
for i in range(epoch):
    degree = degrees[i]
    degrees_mean.append(sum(degree) / len(degree))
    degrees_max.append(max(degree))
    degrees_min.append(min(degree))

# plot
fig, axs = plt.subplots(2)

axs[0].plot(degrees_mean, 'b', degrees_max, 'r', degrees_min, 'g')
axs[0].set(ylabel='node degree')
max_patch = mpatches.Patch(color='red', label='max')
min_patch = mpatches.Patch(color='green', label='min')
mean_patch = mpatches.Patch(color='blue', label='mean')
axs[0].legend(handles=[max_patch,min_patch,mean_patch])

# number of connectted component
axs[1].plot(components)
axs[1].set(ylabel='# components', xlabel='round')

plt.show()
