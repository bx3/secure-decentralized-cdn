#!/usr/bin/env python
from config import *
import random
from collections import namedtuple
from messages import *
from scores import PeerScoreCounter
import sys

State = namedtuple('State', ['role', 'conn', 'mesh', 'peers', 'out_msgs', 'scores', 'mids'])
TransId = namedtuple('TransId', ['src', 'no'])

class Peer:
    def __init__(self, direciton):
        self.direction = direction
        self.counter = PeerScoreCounter()

# assume there is only one topic then
# generic data structure usable by all protocols
class Node:
    def __init__(self, role, u, prob, peers, heartbeat_period):
        self.id = u # my id
        self.role = role
        self.conn = set() # lazy push
        self.mesh = {} # mesh push

        self.peers = set(peers) # known peers
        self.out_msgs = [] # msg to push in the next round
        self.in_msgs = []
        self.D_scores = 6 #
        self.scores = {} # all peer score, key is peer, value is PeerScoreCounter
        self.seqno = 0
        self.D = 8 # curr in local mesh degree: incoming + outgoing
        self.D_out = 2 # num outgoing connections in the mesh; D_out < OVERLAY_DLO and D_out < D/2

        self.init_peers_scores()
        self.gen_prob = prob
        self.msg_ids = set()
        self.heartbeat_period = heartbeat_period
        self.gen_trans_num = 0

        # useful later 
        self.topics = set()

    def insert_msg_buff(self, msgs):
        self.in_msgs += msgs # append

    def run_scores_background(self, curr_r):
        for u, counters in self.scores.items():
            counters.run_background(curr_r)

    # worker func 
    def process_msgs(self, r):
        # schedule heartbeat 
        self.schedule_heartbeat(r)
        # background peer local view update
        self.run_scores_background(r)
        # handle msgs 
        while len(self.in_msgs) > 0:
            msg = self.in_msgs.pop(0)
            mtype, _, _, dst, _, _, _ = msg
            assert self.id == dst
            if mtype == MessageType.GRAFT:
                self.proc_GRAFT(msg, r)
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
                self.proc_Heartbeat(msg, r)
            elif mtype == MessageType.TRANS:
                self.proc_TRANS(msg)
        
        if self.role == NodeType.PUB:
            self.gen_trans()

    def schedule_heartbeat(self, r):
        if self.role == NodeType.PUB or self.role == NodeType.LURK:
            # someone is connected with me in mesh
            if (r%self.heartbeat_period) == HEARTBEAT_START:
                self.gen_heartbeat()

    def gen_heartbeat(self):
        for peer in self.peers:
            msg = self.gen_msg(MessageType.HEARTBEAT, peer, CTRL_MSG_LEN, None)
            self.out_msgs.append(msg)

    # only gen transaction when previous one is at least pushed 
    def gen_trans(self):
        for msg in self.out_msgs:
            mtype, _, _, _, _, _, _ = msg
            if mtype == MessageType.TRANS:
                return

        if random.random() < self.gen_prob:
            for peer in self.mesh:
                trans_id = TransId(self.id, self.gen_trans_num)
                self.gen_trans_num += 1
                msg = self.gen_msg(MessageType.TRANS, peer, TRANS_MSG_LEN, trans_id)
                self.out_msgs.append(msg)

    def proc_TRANS(self, msg):
        _, mid, src, _, _, _, payload = msg
        # if not seen msg before
        if mid not in self.msg_ids:
            self.msg_ids.add(mid)
            self.scores[src].update_p2()
            # push it to other peers in mesh
            for peer in self.mesh:
                if peer != src:
                    msg = self.gen_msg(MessageType.TRANS, peer, TRANS_MSG_LEN, payload)
                    self.out_msgs.append(msg)

    
    def init_peers_scores(self):
        for p in self.peers:
            self.scores[p] = PeerScoreCounter()

    def gen_msg(self, mtype, peer, msg_len, payload):
        msg = Message(mtype, self.seqno, self.id, peer, self.role, msg_len, payload)
        self.seqno += 1
        return msg


    # TODO later out_msgs might not be empties instanteously due to upload bandwidth
    def send_msgs(self):
        # reset out_msgs
        out_msg = self.out_msgs.copy()
        self.out_msgs = []
        return out_msg

    def prune_peer(self, peer):
        # add backoff counter
        msg = self.gen_msg(MessageType.PRUNE, peer, CTRL_MSG_LEN, None)
        self.mesh.pop(peer, None)
        self.out_msgs.append(msg)

    def graft_peer(self, peer, r):
        msg = self.gen_msg(MessageType.GRAFT, peer, CTRL_MSG_LEN, None)
        self.mesh[peer] = Direction.Outgoing
        if peer not in self.scores:
            self.scores[peer] = PeerScoreCounter()
        self.scores[peer].init_r(r)
        self.out_msgs.append(msg)

    # TODO generate IHave
    def proc_Heartbeat(self, msg, r):
        nodes = self.get_rand_gossip_nodes()
        mesh_peers = []
        # prune neg mesh
        all_mesh_peers = self.mesh.keys()
        for u in list(all_mesh_peers):
            counters = self.scores[u]
            if counters.get_score() < 0:
                self.scores[u].update_p3b(-counters.get_score())
                self.prune_peer(u)

        # add peers if needed
        if len(self.mesh) < OVERLAY_DLO:
            candidates = self.get_pos_score_peer()
            candidates.difference(self.mesh.keys())
            candidates.difference(self.conn)
            num_needed = min(len(candidates), self.D-len(self.mesh))
            new_peers = random.choices(list(candidates), k=num_needed)
            for u in new_peers:
                self.graft_peer(u, r)

        # prune peers if needed
        if len(self.mesh) > OVERLAY_DHI:
            # get pos score peers
            mesh_peers_scores = self.get_pos_score_mesh_peers()
            mesh_peers_scores.sort(key=lambda tup: tup[1], reverse=True)
            mesh_peers =  [i for i,j in mesh_peers_scores]
            
            # shuffle  TODO
            # mesh_peers

            num_out = self.get_num_outgoing(mesh_peers, self.D) 

            # insufficient out
            if num_out < self.D_out:
                out_needed = self.D_out - num_out
                # shift out to front for first D peers
                mesh_peer_copy = mesh_peers.copy()
                for idx, u in enumerate(mesh_peer_copy[:self.D]):
                    d = self.mesh[u]
                    if d == Direction.Outgoing:
                        mesh_peers.insert(0, mesh_peers.pop(idx))
                # shift out to front for remaining peers
                for u in mesh_peer_copy[self.D:]:
                    d = self.mesh[u]
                    if d == Direction.Outgoing:
                        mesh_peers.insert(0, mesh_peers.pop(idx))

            remove_peers = mesh_peers[self.D:]
            for peer in remove_peers:
                self.prune_peer(peer)

        # even there is enough mesh, check if there are enough outgoing mesh
        if len(self.mesh) > OVERLAY_DLO:
            mesh_peers_scores = self.get_pos_score_mesh_peers()
            mesh_peers_scores.sort(key=lambda tup: tup[1], reverse=True)
            mesh_peers = [i for i,j in mesh_peers_scores]
            num_out = self.get_num_outgoing(mesh_peers, len(self.mesh) ) 

            if num_out < self.D_out:
                out_needed = self.D_out - num_out
                candidates = self.get_pos_score_peer()
                candidates.difference(self.mesh.keys())
                candidates.difference(self.conn)
                
                new_peers = random.choices(list(candidates), k=out_needed)
                for u in new_peers:
                    self.graft_peer(u, r)

    def get_num_outgoing(self, mesh_peers, m):
        num_out = 0
        for u in mesh_peers[:m]:
            assert( u in self.mesh)
            d = self.mesh[u]
            if d == Direction.Outgoing:
                num_out += 1
        return num_out

    def get_pos_score_mesh_peers(self):
        mesh_peers = []
        for u in list(self.mesh.keys()):
            counters = self.scores[u];
            score = counters.get_score()
            if score >= 0:
                mesh_peers.append((u, score))
        return mesh_peers

    def get_pos_score_peer(self):
        pool = set()
        for u, counters in self.scores.items():
            score = counters.get_score()
            if score >= 0:
                pool.add(u)
        return pool

    # send IWANT to self.out_msgs
    def proc_IHAVE(self, msg):
        pass

    def proc_IWANT(self, msg):
        pass

    # find other peers to add
    def proc_PRUNE(self, msg):
        _, _, src, _, _, _, _ = msg
        if src in self.mesh:
            self.mesh.pop(src, None)
         

    # the other peer has added me to its mesh, I will add it too 
    def proc_GRAFT(self, msg, r):
        _, _, src, _, _, _, _ = msg
        self.mesh[src] = Direction.Incoming
        self.scores[src] = PeerScoreCounter()
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

    # def rand_walk_score(self):
        # for u, counters in scores.items():
            # counters.update_score()

    # def shuffle_rand_peer(self):
        # rand = random.random()
        # if rand < 0.33:
            # # remove a random connection
            # rand_conn = self.mesh.pop()
            # msg = Message(MessageType.PRUNE, 0, self.id, rand_conn, False, CTRL_MSG_LEN, None)
            # self.out_msgs.append(msg)
            # # recommend peer a list of peer
            # payload = PX(list(self.peers))
            # msg = Message(MessageType.PX, 0, self.id, rand_conn, False, CTRL_MSG_LEN, payload)
            # self.out_msgs.append(msg)
        # elif rand < 0.66:
            # # add a random honest connection
            # rand_honest = random.randint(0, N_PUB + N_LURK-1)
            # while rand_honest in self.conn:
                # rand_honest = random.randint(0, N_PUB + N_LURK-1)
            # self.mesh.add(rand_honest)
            # self.peers.add(rand_honest)
            # msg = Message(MessageType.GRAFT, 0, self.id, rand_honest, False, CTRL_MSG_LEN, None)
            # self.out_msgs.append(msg)


    # return State, remember to return a copy
    def get_states(self):
        return State(self.role, self.conn.copy(), self.mesh.copy(), self.peers.copy(), self.out_msgs.copy(), self.scores.copy(), self.msg_ids.copy())


# class Graph:
    # def __init__(self, p,l,s,prob):
        # random.seed(0)
        # self.nodes = {}
        # for i in range(p):
            # self.nodes[i] = Node(NodeType.PUB, i, prob) 
        # for i in range(p,p+l):
            # self.nodes[i]= Node(NodeType.LURK, i, prob)
        # for i in range(p+l, p+l+s):
            # self.nodes[i] = Node(NodeType.SYBIL, i, prob)
        # print("total num node", len(self.nodes))

    # # set honests peers to each node, populate node.conn
    # def preset_known_peers(self):
        # for u in self.nodes:
            # peers = self.get_rand_honests(u)
            # self.nodes[u].peers = peers

    # # u is node
    # def get_rand_honests(self, u):
        # peers = set()
        # attr = self.nodes[u]
        # if attr.role == NodeType.PUB or attr.role == NodeType.LURK:
            # # randomly select D honest node to connect
            # assert(N_PUB + N_LURK > OVERLAY_D)
            # while 1:
                # v = get_rand_honest()
                # if v not in attr.conn and v != u:
                    # peers.add(v)
                # else:
                    # continue
                # if len(peers) == OVERLAY_D:
                    # break
        # return peers 
