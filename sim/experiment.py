from graph import *
from network import Network
from messages import *
from config import *
from graph import State
import attacks

class Snapshot:
    def __init__(self):
        self.round = 0
        self.nodes = {} # key:node id value: node state
        self.network = {} # message queue in for each node

class Experiment:
    def __init__(self, heartbeat, prob):
        self.snapshots = []
        self.network = Network(N_PUB+N_LURK+N_SYBIL)
        self.graph = Graph(N_PUB, N_LURK, N_SYBIL, prob)
        # init nodes and bandwidth
        #  self.graph.preset_known_peers()
        self.network.setup_link_bandwidth(self.graph)
        self.heartbeat_period = heartbeat
        self.adversary = attacks.Adversary()

    # # # # # # # # 
    #  main loop  #
    # # # # # # # # 
    def start(self, epoch):
        for r in range(epoch):
            # periodically gen hearbeat
            self.schedule_heartbeat(r)    
            # network store messages from honest nodes
            self.push_honest_msgs(r)
            # start attack
            self.act_adversarirs(r)
            # all node retrieve msgs 
            self.all_nodes_handle_msgs(r)    
            # take snapshot
            self.take_snapshot(r)
        return self.snapshots

    # three heartbeat
    def schedule_heartbeat(self, r):
        if r%self.heartbeat_period==0:
            self.network.deliver_heartbeats(r)
        # elif r!=1 and r%self.heartbeat_period==1:
            # self.network.gen_heartbeat()
        # elif r!=2 and r%self.heartbeat_period==2:
            # self.network.gen_heartbeat()

    # honest nodes push msg to network
    def push_honest_msgs(self, curr_r):
        # TODO honest nodes
        for _, node in self.graph.nodes.items():
            msgs = node.send_msgs() 
            self.network.deliver_msgs(msgs, curr_r)

    def act_adversarirs(self, r):
        # examine network in curr round r
        # self.adversary
        # chosen attack strategy to generate new messgae and arrange network 
        adv_msgs = []
        self.network.deliver_msgs(adv_msgs, r)
        # maybe rearrange message order
        pass

    def all_nodes_handle_msgs(self, curr_r):
        # node process messages
        for u, node in self.graph.nodes.items():
            msgs = self.network.get_msgs(u, curr_r)
            node.process_msgs(msgs, curr_r)

    def take_snapshot(self, r):
        snapshot = Snapshot()
        snapshot.round = r
        # get all node states
        for u, node in self.graph.nodes.items():
            snapshot.nodes[u] = node.get_states()
        # get network 
        snapshot.network = self.network.queues.copy()
        
        self.snapshots.append(snapshot)

