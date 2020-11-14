#!/usr/bin/env python
from config import *
import random
from collections import namedtuple
from messages import *

State = namedtuple('State', ['conn', 'role', 'lazy_conn', 'peers', 'out_msgs', 'scores'])

def get_rand_honest():
    return random.randint(0, N_PUB + N_LURK-1)

def get_rand_sybil():
    return random.randint(N_PUB + N_LURK, N_PUB + N_LURK + N_SYBIL - 1)



# generic data structure usable by all protocols
class Node:
    def __init__(self, role, u):
        # states
        self.loc = (0,0)
        self.conn = set()
        self.role = role
        self.lazy_conn = set()
        self.peers = set()
        self.out_msgs = [] 
        self.scores = {} # key is peer, value is score
        self.id = u

    # # # # # # # # # 
    # write node    # 
    # # # # # # # # #  
    def flush_msgs(self):
        msgs = self.out_msgs.copy()
        self.out_msgs = []
        return msgs 

    def push_local_mesh(self):
        # reset out_msgs
        out_msg = self.flush_out_msgs()
        return out_msg

    def process_msgs(self, msgs):
        # update local state
        for msg in msgs:
            # process to change state
            mtype, mid, src, dst, adv = msg
            assert self.id == dst
            if (mtype == GossipMessageType.GRAFT):
                self.conn.add(src)
                self.peers.add(src)
            elif (mtype == GossipMessageType.PRUNE):
                if src in self.conn:
                    self.conn.remove(src)
        self.node_action()

    def node_action(self):
        if len(self.conn) > OVERLAY_DHI:
            #  while (len(node.conn) > OVERLAY_DHI):
            rand_conn = self.conn.pop()
            msg = Message(GossipMessageType.PRUNE, 0, self.id, rand_conn, False, 0, '')
            self.out_msgs.append(msg)
        elif len(self.conn) < OVERLAY_DLO:
            #  while (len(node.conn) < OVERLAY_DLO):
            rand_peer = random.sample(self.peers, 1)[0]
            if rand_peer not in self.conn:
                self.conn.add(rand_peer)
                msg = Message(GossipMessageType.GRAFT, 0, self.id, rand_peer, False, 0, '')
                self.out_msgs.append(msg)
        else: 
            rand = random.random()
            if rand < 0.33:
                # remove a random connection
                rand_conn = self.conn.pop()
                msg = Message(GossipMessageType.PRUNE, 0, self.id, rand_conn, False)
                self.out_msgs.append(msg)
            elif rand < 0.66:
                # add a random honest connection
                rand_honest = random.randint(0, N_PUB + N_LURK-1)
                while rand_honest in self.conn:
                    rand_honest = random.randint(0, N_PUB + N_LURK-1)
                self.conn.add(rand_honest)
                self.peers.add(rand_honest)
                msg = Message(GossipMessageType.GRAFT, 0, self.id, rand_honest, False)
                self.out_msgs.append(msg)

    # # # # # # # # # 
    # read node     # 
    # # # # # # # # #  
    def get_conn(self):
        return self.conn

    # return State, remember to return a copy
    def get_states(self):
        pass


class Graph:
    def __init__(self, p,l,s):
        self.nodes = {}
        for i in range(p):
            self.nodes[i] = Node(NodeType.PUB, i) 
        for i in range(p,p+l):
            self.nodes[i]= Node(NodeType.LURK, i)
        for i in range(p+l, p+l+s):
            self.nodes[i] = Node(NodeType.SYBIL, i)
        print("total num node", len(self.nodes))

    # set honests peers to each node, populate node.conn
    def preset_rand_honest_peers(self):
        for u in self.nodes:
            peers = self.get_rand_honests(u)
            self.nodes[u].peers = peers

    # TODO
    def add_conn_msgs(self):
        # create msg
        # put msg to node.out_msgs
        # Initial msgs
        for u in self.nodes: 
            node = self.nodes[u]
            rand_peer = random.choice(node.peers)
            node.conn.add(rand_peer)
            msg = Message(GossipMessageType.GRAFT, 0, u, rand_peer, False)
            node.out_msgs.append(msg)
        pass

    # u is node
    def get_rand_honests(self, u):
        peers = set()
        attr = self.nodes[u]
        if attr.role == NodeType.PUB or attr.role == NodeType.LURK:
            # randomly select D honest node to connect
            assert(N_PUB + N_LURK > OVERLAY_D)
            while 1:
                v = get_rand_honest()
                if v not in attr.conn and v != u:
                    peers.add(v)
                else:
                    continue
                if len(peers) == OVERLAY_D:
                    break
        return peers 
