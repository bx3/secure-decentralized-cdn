#!/usr/bin/env python
from config import *
import random
from collections import namedtuple
from messages import *

State = namedtuple('State', ['role', 'conn', 'mesh', 'peers', 'out_msgs', 'scores'])

def get_rand_honest():
    return random.randint(0, N_PUB + N_LURK-1)

def get_rand_sybil():
    return random.randint(N_PUB + N_LURK, N_PUB + N_LURK + N_SYBIL - 1)

# assume there is only one topic then
class PeerScoreCounter:
    def __init__(self):
        self.r = 0 # the lastest update round
        self.P1 = 0 # time in mesh
        self.P2 = 0 # num first message from 
        self.P3a = 0 # num message failure rate, need to a window
        self.P3b = 0 # num mesh message deliver failure
        self.P4 = 0 # num invalid message uncapped
        self.P5 = 0 # application specific
        self.P6 = 0 # node id collocation

    # TODO update all counters
    def update(self):
        pass

    # TODO add decay to all counters, see section 5.2
    def decay(self):
        pass
    
    # TODO implement window-ed counters 
    def get_counters(self):
        pass


# generic data structure usable by all protocols
class Node:
    def __init__(self, role, u):
        self.role = role
        self.conn = set() # lazy push
        self.mesh = set() # mesh push
        self.peers = set() # known peers
        self.out_msgs = [] # msg to push in the next round
        self.D_scores = {} # mesh peer score, key is peer, value is PeerScoreCounter
        self.id = u # my id
        self.D = 0 # curr in local mesh degree: incoming + outgoing
        self.D_out = 0 # num outgoing connections in the mesh
        # useful later 
        self.loc = (0,0) # for compute propagation delay
        self.down_bd = BANDWIDTH # for compute transmission delay
        self.up_bd = BANDWIDTH
        self.num_rx_trans = 0
        self.num_tx_trans = 0
        self.topics = set()

    # worker func 
    def process_msgs(self, msgs):
        # update local state
        for msg in msgs:
            mtype, _, _, dst, _, _, _ = msg
            assert self.id == dst
            if mtype == MessageType.GRAFT:
                self.proc_GRAFT(msg)
            elif mtype == MessageType.PRUNE:
                self.proc_PRUNE(msg)
            elif mtype == MessageType.LEAVE:
                self.proc_LEAVE(msg) 
            elif mtype == MessageType.IHAVE:
                self.proc_IHAVE(msg) 
            elif mtype == MessageType.IWANT:
                self.proc_IWANT(msg) 
            elif mtype == MessageType.PX:
                self.proc_PX(msg)
            elif mtype == MessageType.HEARTBEAT:
                self.proc_Heartbeat(msg)

        #self.update()

    # TODO compute scores
    def compute_score(self, peer):
        score = 0
        # TODO if not peer add one
        # counters = self.D_score[peer]
        # compute counters ...
        return score

    # TODO later out_msgs might not be empties instanteously due to upload bandwidth
    def send_msgs(self):
        # reset out_msgs
        out_msg = self.out_msgs.copy()
        self.out_msgs = []
        return out_msg

    # TODO add random  transactions 
    def gen_trans(self):
        trans = None # Message(..)
        self.out_msgs.append(trans)

    # TODO generate IHave
    def proc_Heartbeat(self, msg):
        nodes = self.get_rand_gossip_nodes()

        # prune negative score peer, add positive peer, maintain D_out
        peers_score = {}
        peer_keep = set()
        for peer in self.peers:
            peers_score[peer] = self.compute_score(peer)
            peer_keep.add(peer)

        # prune negative peers, peer_keep.remove(peer)

        # keep highest OVERLAY_DSCORE to keep

        # make sure outgoing D_out < OVERLAY_DLO and D_out < D/2

        # graft random peer from self.peers
        

    # send IWANT to self.out_msgs
    def proc_IHAVE(self, msg):
        pass

    def proc_IWANT(self, msg):
        pass

    # find other peers to add
    def proc_PRUNE(self, msg):
        _, _, src, _, _, _, _ = msg
        if src in self.mesh:
            self.mesh.remove(src)
        pass

    # the other peer has added me to its mesh, I will add it too 
    def proc_GRAFT(self, msg):
        _, _, src, _, _, _, _ = msg
        self.mesh.add(src)
        self.peers.add(src)

    def proc_LEAVE(self, msg):
        pass

    def proc_PX(self, msg):
        pass
   
    # send random subset peers gossip with GOSSIP_FACTOR, see section 6.4
    def get_rand_gossip_nodes(self):
        pass

    # TODO
    # def update(self):
        # if len(self.conn) > OVERLAY_DHI:
            # #  while (len(node.conn) > OVERLAY_DHI):
            # rand_conn = self.conn.pop()
            # msg = Message(MessageType.PRUNE, 0, self.id, rand_conn, False, 0, '')
            # self.out_msgs.append(msg)
        # elif len(self.conn) < OVERLAY_DLO:
            # #  while (len(node.conn) < OVERLAY_DLO):
            # rand_peer = random.sample(self.peers, 1)[0]
            # if rand_peer not in self.conn:
                # self.conn.add(rand_peer)
                # msg = Message(MessageType.GRAFT, 0, self.id, rand_peer, False, 0, '')
                # self.out_msgs.append(msg)
        # else: 
            # pass
            # self.random_change()

    # def random_change(self):
        # rand = random.random()
        # if rand < 0.33:
            # # remove a random connection
            # rand_conn = self.conn.pop()
            # msg = Message(MessageType.PRUNE, 0, self.id, rand_conn, False)
            # self.out_msgs.append(msg)
        # elif rand < 0.66:
            # # add a random honest connection
            # rand_honest = random.randint(0, N_PUB + N_LURK-1)
            # while rand_honest in self.conn:
                # rand_honest = random.randint(0, N_PUB + N_LURK-1)
            # self.conn.add(rand_honest)
            # self.peers.add(rand_honest)
            # msg = Message(MessageType.GRAFT, 0, self.id, rand_honest, False)
            # self.out_msgs.append(msg)

    # # # # # # # # # 
    # read node     # 
    # # # # # # # # #  
    def get_conn(self):
        return self.conn

    # return State, remember to return a copy
    def get_states(self):
        return State(self.role, self.conn.copy(), self.mesh.copy(), self.peers.copy(), self.out_msgs.copy(), self.D_scores.copy())


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
    def preset_known_peers(self):
        for u in self.nodes:
            peers = self.get_rand_honests(u)
            self.nodes[u].peers = peers

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
