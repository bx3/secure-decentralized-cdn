#!/usr/bin/env python
import networkx as nx
from config import *
import random

def get_rand_honest():
    return random.randint(0, N_PUB + N_LURK-1)

def get_rand_sybil():
    return random.randint(N_PUB + N_LURK, N_PUB + N_LURK + N_SYBIL - 1)

# generic data structure usable by all protocols
class Node:
    def __init__(self, role):
        # states
        self.conn = []
        self.role = role
        self.lazy = []
        self.peers = []
        self.out_msgs = []
        self.scores = {} # key is peer, value is score

    # # # # # # # # # 
    # write node    # 
    # # # # # # # # #  
    def flush_out_msgs(self):
        msgs = self.out_msgs.copy()
        self.out_msgs = []
        return msgs 

    # # # # # # # # # 
    # read node     # 
    # # # # # # # # #  
    def get_conn(self):
        return self.conn


class Graph:
    def __init__(self, p,l,s):
        self.nodes = {}
        for i in range(p):
            self.nodes[i] = Node(NodeType.PUB) 
        for i in range(p,p+l):
            self.nodes[i]= Node(NodeType.LURK)
        for i in range(p+l, p+l+s):
            self.nodes[i] = Node(NodeType.SYBIL)
        print("total num node", len(self.nodes))

    # set honests peers to each node, populate node.conn
    def preset_rand_honest_peers(self):
        for u in self.nodes:
            peers = self.get_rand_honests(u)
            self.nodes[u].peers = peers

    # u is node
    def get_rand_honests(self, u):
        peers = []
        attr = self.nodes[u]
        if attr.role == NodeType.PUB or attr.role == NodeType.LURK:
            # randomly select D honest node to connect
            assert(N_PUB + N_LURK > OVERLAY_D)
            while 1:
                v = get_rand_honest()
                if v not in attr.conn and v != u:
                    peers.append(v)
                else:
                    continue
                if len(peers) == OVERLAY_D:
                    break
        return peers 

    # a warm network connect honest nodes together
    # but it is not required, as we can use message to connect them
    # def setup_warm_network(graph, topo):
        # if topo == 'rand':
            # for u in graph.nodes:
                # # print(graph.nodes[u])
                # attr = graph.nodes[u]
                # if attr['role'] == NodeType.PUB or attr['role'] == NodeType.LURK:
                    # # randomly select D honest node to connect
                    # assert(N_PUB + N_LURK > OVERLAY_D)
                    # num_conn = 0
                    # while 1:
                        # v = get_rand_honest()
                        # if 'conn' in attr:
                            # if v not in attr['conn']:
                                # attr['conn'].append(v)
                            # else:
                                # continue
                        # else:
                            # attr['conn'] = [v]
                        # num_conn += 1
                        # if num_conn == OVERLAY_D:
                            # break
                #print(attr)

    









