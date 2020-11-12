#!/usr/bin/env python
from messages import *

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
        pass

    # define rules fore each node to write messages to network
    def push_local_mesh(self, graph, u):
        # process internal logic + add msgs
        # msg = Message(GossipMessageType.GRAFT,1,2, False)
        # self.out_msgs = self.out_msgs + [msg]
       
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
