from graph import *
from network import Network
from messages import *
from config import *
from graph import State
import generate_network as gn
import attacks
import json
import sys

class Snapshot:
    def __init__(self):
        self.round = 0
        self.nodes = {} # key:node id value: node state
        self.network = {} # message queue in for each node

class Experiment:
    def __init__(self, setup_json, heartbeat):
        self.snapshots = []
        self.nodes = {}
        self.network = Network(setup_json)
        self.heartbeat_period = heartbeat

        self.load_nodes(setup_json)
        self.adversary = attacks.Adversary()

    # # # # # # # # 
    #  main loop  #
    # # # # # # # # 
    def start(self, epoch):
        for r in range(epoch):
            # periodically gen hearbeat MOVED TO NODE
            # self.schedule_heartbeat(r)    
            # network store messages from honest nodes
            self.push_honest_msgs(r)
            # start attack
            self.act_adversarirs(r)
            # network deliver msgs
            self.deliver_msgs(r)
            # all node retrieve msgs 
            self.all_nodes_handle_msgs(r)    
            # take snapshot
            self.take_snapshot(r)
        return self.snapshots

    # heartbeat
    # def schedule_heartbeat(self, r):
        # if r%self.heartbeat_period==0:
            # self.network.deliver_heartbeats(r)
    
    # honest nodes push msg to network
    def push_honest_msgs(self, curr_r):
        # TODO honest nodes
        for u, node in self.nodes.items():
            # if network has too many messages, stop
            if not self.network.is_uplink_congested(u):
                msgs = node.send_msgs() 
                self.network.push_msgs(msgs, curr_r)

    def act_adversarirs(self, r):
        # examine network in curr round r
        # self.adversary
        # chosen attack strategy to generate new messgae and arrange network 
        adv_msgs = []
        self.network.push_msgs(adv_msgs, r)
        # maybe rearrange message order
        pass

    def deliver_msgs(self, curr_r):
        dst_msgs = self.network.update()
        for dst, msgs in dst_msgs.items():
            self.nodes[dst].insert_msg_buff(msgs)
        # for u, node in self.nodes.items():
            # msgs = self.network.get_msgs(u, curr_r)
            # node.insert_msg_buff(msgs)


    def all_nodes_handle_msgs(self, curr_r):
        # node process messages
        for u, node in self.nodes.items():
            node.process_msgs(curr_r)

    def take_snapshot(self, r):
        snapshot = Snapshot()
        snapshot.round = r
        # get all node states
        for u, node in self.nodes.items():
            snapshot.nodes[u] = node.get_states()
        # get network 
        snapshot.network = self.network.take_snapshot()
        
        self.snapshots.append(snapshot)

    def load_nodes(self, setup_file):
        nodes = gn.parse_nodes(setup_file)
        for u in nodes:
            u_id = u["id"]
            if u_id not in self.nodes:
                self.nodes[u_id] = Node(
                    NodeType(u["role"]), 
                    u_id,
                    u["prob"],
                    u["known"],
                    self.heartbeat_period
                )
            else: 
                print('Error. config file duplicate id')
                sys.exit(0)

