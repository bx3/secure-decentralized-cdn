#!/usr/bin/env python
import sys
import os
import networkx as nx
from graph import *
from network import Network
from messages import *
from config import *
from protocols import GossipSub

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

for curr_r in range(epoch):
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

# analyze stat ... generate figure

