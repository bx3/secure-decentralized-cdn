#!/usr/bin/env python
from messages import *
from config import *
import random

# protocol 1 gossipsub
class GossipSub:
    def __init__(self):
        # all statistics for measurement
        self.curr_r = 0
        self.num_msg = 0
        self.censored = []
        self.eclipsed = []
        self.log_filename = 'gossipsub'

    # write to external file
    def write_log():
        pass


    # # # # # # # # # # #
    #   NODE ACTION     #
    # # # # # # # # # # #

    # define rules for each node to process messages
    def process_msgs(self, graph, u, msgs):
        # update local state
        node = graph.nodes[u]
        for msg in msgs:
            # process to change state
            mtype, mid, src, dst, adv = msg
            assert u == dst
            if (mtype == GossipMessageType.GRAFT):
                node.conn.add(src)
                node.peers.add(src)
            elif (mtype == GossipMessageType.PRUNE):
                if src in node.conn:
                    node.conn.remove(src)

    # define rules for each node to take action: change connection and send msgs
    def node_action(self, graph):
        for u in graph.nodes:
            node = graph.nodes[u]
            if len(node.conn) > OVERLAY_DHI:
                #  while (len(node.conn) > OVERLAY_DHI):
                rand_conn = node.conn.pop()
                msg = Message(GossipMessageType.PRUNE, 0, u, rand_conn, False)
                node.out_msgs.append(msg)
            elif len(node.conn) < OVERLAY_DLO:
                #  while (len(node.conn) < OVERLAY_DLO):
                rand_peer = random.sample(node.peers, 1)[0]
                if rand_peer not in node.conn:
                    node.conn.add(rand_peer)
                    msg = Message(GossipMessageType.GRAFT, 0, u, rand_peer, False)
                    node.out_msgs.append(msg)
            else: 
                rand = random.random()
                if rand < 0.33:
                    # remove a random connection
                    rand_conn = node.conn.pop()
                    msg = Message(GossipMessageType.PRUNE, 0, u, rand_conn, False)
                    node.out_msgs.append(msg)
                elif rand < 0.66:
                    # add a random honest connection
                    rand_honest = random.randint(0, N_PUB + N_LURK-1)
                    while rand_honest in node.conn:
                        rand_honest = random.randint(0, N_PUB + N_LURK-1)
                    node.conn.add(rand_honest)
                    node.peers.add(rand_honest)
                    msg = Message(GossipMessageType.GRAFT, 0, u, rand_honest, False)
                    node.out_msgs.append(msg)
            pass

    # define rules fore each node to write messages to network
    def push_local_mesh(self, graph, u):
        # reset out_msgs
        out_msg = graph.nodes[u].flush_out_msgs()
        return out_msg

    def lazy_push():
        pass


    def score_func():
        pass

    

    


class Flood:
    def __init__():
        self.curr_r = 0
        self.num_msg = 0
        self.censored = []
        self.eclipsed = []
        self.log_filename = 'flood'
    
    def write_log():
        pass


class Eth1_0:
    def __init__():
        self.curr_r = 0
        self.num_msg = 0
        self.censored = []
        self.eclipsed = []
        self.log_filename = 'flood'
    
    def write_log():
        pass
