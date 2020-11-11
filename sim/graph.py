#!/usr/bin/env python
import networkx as nx
from config import *
import random

# # # # # # # # # 
# write graph   # 
# # # # # # # # #  
def init_nodes(p, l, s):
    graph = nx.Graph()
    for i in range(p):
        graph.add_node(i, role=NodeType.PUB) 
    for i in range(p,p+l):
        graph.add_node(i, role=NodeType.LURK)
    for i in range(p+l, p+l+s):
        graph.add_node(i, role=NodeType.SYBIL)
    print('created a graph of len', graph.number_of_nodes())
    #print(graph.nodes.data())
    return graph

# a warm network connect honest nodes together
# but it is not required, as we can use message to connect them
def setup_warm_network(graph, topo):
    if topo == 'rand':
        for u in graph.nodes:
            # print(graph.nodes[u])
            attr = graph.nodes[u]
            if attr['role'] == NodeType.PUB or attr['role'] == NodeType.LURK:
                # randomly select D honest node to connect
                assert(N_PUB + N_LURK > OVERLAY_D)
                num_conn = 0
                while 1:
                    v = get_rand_honest()
                    if 'conn' in attr:
                        if v not in attr['conn']:
                            attr['conn'].append(v)
                        else:
                            continue
                    else:
                        attr['conn'] = [v]
                    num_conn += 1
                    if num_conn == OVERLAY_D:
                        break
            #print(attr)

def get_rand_honest():
    return random.randint(0, N_PUB + N_LURK-1)

def get_rand_sybil():
    return random.randint(N_PUB + N_LURK, N_PUB + N_LURK + N_SYBIL - 1)

# add_edge g: graph, e:(u,v) uv are node
def add_edge(g, e, attr):
    g.add_edge(e, attr)

# add_node attr is a dict
def add_node(g, u, attr):
    graph.add_node(u, attr)


# # # # # # # # # 
# read graph    # 
# # # # # # # # #  




