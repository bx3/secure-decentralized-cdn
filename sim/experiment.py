from graph import *
from network import Network
from messages import *
from config import *
from graph import State
from sybil import Sybil
import generate_network as gn
import attacks
import json
import sys
import time

class Snapshot:
    def __init__(self):
        self.round = 0
        self.nodes = {} # key:node id value: node state
        self.sybils = {}
        self.all_nodes = {}
        self.network = None # message queue in for each node

class Experiment:
    def __init__(self, setup_json, heartbeat):
        self.snapshots = []
        self.nodes = {}  # honest nodes
        self.sybils = {}
        self.all_nodes = {}

        self.network = Network(setup_json)
        self.heartbeat_period = heartbeat
    
        # load both nodes and sybils nodes
        self.load_nodes(setup_json) 
        self.setup_mesh()

        self.adversary = attacks.Adversary(self.sybils)

        # eclipse attack
        self.target = -1

    # # # # # # # # 
    #  main loop  #
    # # # # # # # # 
    def start(self, epoch, start_round=0, attack_strategy='None', attack_target=1):
        for r in range(start_round, start_round+epoch):
            # network store messages from honest nodes
            self.push_honest_msgs(r)
            # start attack
            if attack_strategy == 'eclipse':
                self.attack(r, attack_target)
            # network deliver msgs
            self.deliver_msgs(r)
            # honest node retrieve msgs 
            self.honest_nodes_handle_msgs(r)
            if attack_strategy == 'flash':
                # sybil node retrieve msgs
                self.sybil_nodes_handle_msgs(r)
            # take snapshot
            self.take_snapshot(r)
            #print("round", r, "finish using ", time.time()-start)
        return self.snapshots

    # honest nodes push msg to network
    def push_honest_msgs(self, curr_r):
        for u, node in self.nodes.items():
            # if network has too many messages, stop
            if not self.network.is_uplink_congested(u):
                msgs = node.send_msgs() 
                self.network.push_msgs(msgs, curr_r)

    def attack(self, r, attack_target=1):
        # chosen attack strategy to generate new messgae and arrange network 
        # if (not self.adversary.has_target()) and len(self.snapshots) > 0:
            # self.adversary.find_eclipse_publisher_target(r, self.snapshots)
        self.adversary.target = attack_target # some hack
        adv_msgs = self.adversary.eclipse_target(r, self.snapshots) # only possess snapshots
        self.network.push_msgs(adv_msgs, r)
                 
    def deliver_msgs(self, curr_r):
        num_delivered_msg =  0
        dst_msgs = self.network.update()
        for dst, msgs in dst_msgs.items():
            # honest 
            if dst in self.nodes:
                self.nodes[dst].insert_msg_buff(msgs)
            else:
                self.sybils[dst].insert_msg_buff(msgs)
            num_delivered_msg += len(msgs)

    def all_nodes_handle_msgs(self, curr_r):
        # node process messages
        for u, node in self.nodes.items():
            if node.role != NodeType.SYBIL:
                node.process_msgs(curr_r)
            else:
                node.adv_process_msgs(curr_r)
    
    def honest_nodes_handle_msgs(self, curr_r):
        for u, node in self.nodes.items():
            if node.role != NodeType.SYBIL:
                node.process_msgs(curr_r)

    def sybil_nodes_handle_msgs(self, curr_r):
        self.adversary.handle_msgs(curr_r)


    def take_snapshot(self, r):
        snapshot = Snapshot()
        snapshot.round = r
        # get all node states
        for u, node in self.nodes.items():
            snapshot.nodes[u] = node.get_states()

        for u, sybil in self.sybils.items():
            snapshot.sybils[u] = sybil.get_states()

        snapshot.all_nodes = {**(snapshot.nodes), **(snapshot.sybils)}
        # get network 
        snapshot.network = self.network.take_snapshot()
        
        self.snapshots.append(snapshot)

    def load_nodes(self, setup_file):
        nodes = gn.parse_nodes(setup_file)
        for u in nodes:
            u_id = u["id"]
            if u_id not in self.nodes:
                if u["role"] != 2: # 2 is sybil
                    self.nodes[u_id] = Node(
                        NodeType(u["role"]), 
                        u_id,
                        u["interval"],
                        u["known"],
                        self.heartbeat_period
                    )
                else:
                    self.sybils[u_id] = Sybil(
                        NodeType(u["role"]), 
                        u_id,
                        u["interval"],
                        u["known"],
                        self.heartbeat_period
                    )
            else: 
                print('Error. config file duplicate id')
                sys.exit(0)

    def setup_mesh(self):
        self.all_nodes = {**(self.nodes), **(self.sybils)}
        mesh = {} # key is node, value is mesh nodes
        for u, node in self.all_nodes.items():
            num_out = int(OVERLAY_D / 2)
            known_peers = node.peers.copy()
            known_peers = list(known_peers)
            random.shuffle(known_peers)
            chosen = known_peers[:num_out]
            for v in chosen:
                node.setup_peer(v, Direction.Outgoing, 0)
                self.all_nodes[v].setup_peer(u, Direction.Incoming, 0) 


# for u, node in self.nodes.items():
        #     if node.role == NodeType.SYBIL and r+1==40:
        #         peer = 0
        #         msg = node.gen_msg(MessageType.GRAFT, peer, CTRL_MSG_LEN, None)
        #         node.mesh[peer] = Direction.Outgoing
        #         if peer not in node.scores:
        #             node.scores[peer] = PeerScoreCounter()
        #         node.scores[peer].init_r(r)
        #         adv_msgs.append(msg)
        #         for peer in node.mesh:
        #             trans_id = TransId(node.id, node.gen_trans_num)
        #             node.gen_trans_num += 1
        #             msg = node.gen_msg(MessageType.TRANS, peer, TRANS_MSG_LEN, trans_id)
