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
import os
import pickle

class Snapshot:
    def __init__(self):
        self.round = 0
        self.nodes = {} # key:node id value: node state
        self.sybils = {}
        # self.all_nodes = {}
        self.network = None # message queue in for each node


class Experiment:
    def __init__(self, setup_json, heartbeat, update_method, dirname):
        self.snapshots = []
        self.nodes = {}  # honest nodes
        self.sybils = {}
        self.all_nodes = {}

        self.network = Network(setup_json)
        self.heartbeat_period = heartbeat

        if not os.path.exists(dirname):
            os.makedirs(dirname)


        self.snapshot_dir = os.path.join(dirname, 'snapshots')
        self.snapshot_index = 0
        if not os.path.exists(self.snapshot_dir):
            os.makedirs(self.snapshot_dir)

        # log file
        self.log_file = self.snapshot_path = os.path.join(dirname, 'log.txt')
        self.update_method = update_method
    
        # load both nodes and sybils nodes
        self.load_nodes(setup_json) 
        self.setup_mesh()

        self.adversary = attacks.Adversary(self.sybils)

        # eclipse attack
        self.target = -1

        self.copy_time = 0
        self.register_time = 0

        with open(self.log_file, 'w') as w:
            w.write("num_node" + str(len(self.nodes)) + '\n')

    def save_snapshots(self, snapshots):
        filename = os.path.join(self.snapshot_dir, 'snapshot'+str(self.snapshot_index))
        self.snapshot_index += 1
        with open(filename, 'wb') as f:
            pickle.dump(snapshots, f)

    # # # # # # # # 
    #  main loop  #
    # # # # # # # # 
    def start(self, epoch, start_round=0, attack_strategy='None', targets=[]):
        curr_shots = [] 
        start_time = time.time()
        heartbeat_time = start_time

        push_tot = 0
        deliver_tot = 0
        handle_tot = 0
        snap_tot = 0
        for r in range(start_round, start_round+epoch):
            # debug
            if r!=0 and r % HEARTBEAT == 0:
                print("****\t\theartbeat generated", r, 'at', time.time()-heartbeat_time)
                print("****\t\tpush tot", push_tot)
                print("****\t\t\tcopy_time", self.copy_time)
                print("****\t\t\tregister_time", self.register_time)


                print("****\t\tdeliver tot", deliver_tot)
                print("****\t\thandle tot", handle_tot)
                print("****\t\tsnap_tot", snap_tot)
                push_tot = 0
                deliver_tot = 0
                handle_tot = 0
                snap_tot = 0
                self.copy_time = 0
                self.register_time = 0

                heartbeat_time = time.time()
                self.save_snapshots(curr_shots)
                curr_shots.clear()

            # start attack
            # self.attack_management(r, self.network, targets)

            # network store messages from honest nodes
            # self.push_sybil_msgs(r)
            t1 = time.time()
            self.push_honest_msgs(r)
            t2 = time.time()
            push_tot += t2 - t1
            # if r > 0:
                # self.attack_freeze_network(r)
            
            # network deliver msgs
            self.deliver_msgs(r)
            t3 = time.time()
            deliver_tot += t3 - t2

            # honest node retrieve msgs 
            self.honest_nodes_handle_msgs(r)
            t4 = time.time()
            handle_tot += t4 - t3

            # self.sybil_nodes_handle_msgs(r)

            # assume sybils have powerful internal network, node processing speed
            # self.sybil_use_fast_internet(r) 

            # take snapshot
            shot = self.take_snapshot(r)
            t5 = time.time()
            snap_tot += t5 - t4

            curr_shots.append(shot)
            #print("round", r, "finish using ", time.time()-start)
        self.save_snapshots(curr_shots)
        print("****\t\tExp finishes at", time.time()-start_time)

        return self.snapshot_index 

    def push_sybil_msgs(self, r):
        for u, node in self.sybils.items():
            # if network has too many messages, stop
            msgs = node.send_msgs() 
            self.network.push_msgs(msgs, r)

    # honest nodes push msg to network
    def push_honest_msgs(self, curr_r):
        for u, node in self.nodes.items():
            # if network has too many messages, stop
            # if not self.network.is_uplink_congested(u):
            t1 = time.time()
            msgs = node.send_msgs() 
            t2 = time.time()
            self.copy_time += t2 - t1
            self.network.push_msgs(msgs, curr_r)
            t3 = time.time()
            self.register_time += t3 - t2

    def attack_management(self, r, network, targets):
        self.adversary.add_targets(targets) # some hack
        adv_msgs = []
        if r > 0: 
            adv_msgs = self.adversary.eclipse_target(r, self.snapshots, self.network) 
        self.network.push_msgs(adv_msgs, r)

    def attack_freeze_network(self, r):
        if r > 0:
            self.adversary.handle_freeze_requests(r, self.snapshots[-1], self.network)
                 
    def deliver_msgs(self, curr_r):
        num_delivered_msg =  0
        dst_msgs = self.network.update(True)
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
                node.process_msgs(curr_r)
    
    def honest_nodes_handle_msgs(self, curr_r):
        for u, node in self.nodes.items():
            # TODO assume all are honest
            #if node.role != NodeType.SYBIL:
            node.process_msgs(curr_r)

    def sybil_nodes_handle_msgs(self, curr_r):
        self.adversary.handle_msgs(curr_r)

    def sybil_use_fast_internet(self, curr_r):
        self.adversary.sybil_nodes_redistribute_msgs(curr_r)


    def take_snapshot(self, r):
        snapshot = Snapshot()
        snapshot.round = r
        # get all node states
        for u, node in self.nodes.items():
            snapshot.nodes[u] = node.get_states()

        # for u, sybil in self.sybils.items():
            # snapshot.sybils[u] = sybil.get_states()
        snapshot.sybils = {}
        # get network 
        # snapshot.network = self.network.take_snapshot()
        
        self.snapshots.append(snapshot)
        return snapshot

    def load_nodes(self, setup_file):
        nodes = gn.parse_nodes(setup_file)
        for u in nodes:
            u_id = int(u["id"])
            topics = []
            roles = {}
            known = {}
            for t in u["topics"]:
                topics.append(get_topic_type(t))
            for t, role in u["roles"].items():
                roles[get_topic_type(t)] = role
            for t, ks in u["known"].items():
                known[get_topic_type(t)] = ks
            interval = float(u["interval"])
            x = float(u["x"])
            y = float(u["y"])
            if u_id not in self.nodes:
                self.nodes[u_id] = Node(
                    roles,
                    u_id,
                    interval,
                    known,
                    self.heartbeat_period,
                    topics,
                    x,
                    y,
                    self.log_file,
                    self.update_method
                )
            else: 
                print('Error. config file duplicate id')
                sys.exit(0)

    # modified sybils node does not get in mesh, is system is warm
    def setup_mesh(self):
        # self.all_nodes = {**(self.nodes), **(self.sybils)}
        mesh = {} # key is node, value is mesh nodes
        # num_conn_1 = 0
        for u, node in self.nodes.items():
            for topic, actor in node.actors.items():
                num_out = int(OVERLAY_D / 2)
                known_peers = actor.peers.copy()
                known_peers = list(known_peers)
                random.shuffle(known_peers)
                chosen = known_peers[:num_out]
                for v in chosen:
                    # if v == 1:
                        # num_conn_1 += 1
                    node.setup_peer(v, Direction.Outgoing, 0, topic)
                    self.nodes[v].setup_peer(u, Direction.Incoming, 0, topic) 

        # print('num_conn_1', num_conn_1)


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
