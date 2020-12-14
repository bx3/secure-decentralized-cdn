#!/usr/bin/env python
from config import *
import random
from collections import namedtuple
from messages import *
from scores import PeerScoreCounter
import sys
from attacks import Notes
from attacks import AttackType

State = namedtuple('State', [
    'role', 
    'conn', 
    'mesh', 
    'secured_mesh',
    'channels',
    'attack_method',
    'peers', 
    'attempts',
    'out_msgs', 
    'scores', 
    'trans_set', 
    'transids', 
    'gen_trans_num', 
    'out_conn']
    )
TransId = namedtuple('TransId', ['src', 'no'])


# assume there is only one topic then
# generic data structure usable by all protocols
class Sybil:
    def __init__(self, role, u, prob, peers, heartbeat_period):
        self.id = u # my id
        self.role = role
        self.conn = set() # lazy push
        self.mesh = {} # mesh push
        
        self.secured_mesh = {} # key is peer, value is if secured
        self.trans_hist = {} # key is round, each element is a list of trans recv at that round

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

        self.round_trans_ids = set() # keep track of msgs used for analysis
        self.trans_set = set()

        self.last_heartbeat = -1
        self.notes = Notes(u)

        # useful later 
        self.topics = set()

    def insert_msg_buff(self, msgs):
        self.in_msgs += msgs # append

    def insert_attack_note(self, target, att_type, pubs, r):
        msgs = []
        self.notes.add_target(target, att_type)
        msgs.append(self.graft_peer(target, r))
        if att_type == AttackType.UNDERCOVER:
            for pub in pubs:
                if target != pub:
                    msgs.append(self.graft_peer(pub, r))
        return msgs

    def run_scores_background(self, curr_r):
        for u, counters in self.scores.items():
            counters.run_background(curr_r)
            #  if (self.id == 0 and u == 99):
                #  print('0 update score for', u, 'new score:', counters.get_score())

    def process_msgs(self, r):
        # self.schedule_heartbeat(r)
        self.run_scores_background(r)
        self.round_trans_ids.clear()

        while len(self.in_msgs) > 0:
            msg = self.in_msgs.pop(0)
            mtype, _, src, dst, _, _, _ = msg
            
            assert self.id == dst
            if mtype == MessageType.GRAFT:
                self.proc_GRAFT(msg, r)
            elif mtype == MessageType.PRUNE:
                # print(self.id, 'recv PRUNE from', src)
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
                self.proc_TRANS(msg, r)
            else:
                self.scores[src].update_p4()

        if r not in self.trans_hist:
            self.trans_hist[r] = []
        
        # maintainence and doing bomb things
        if self.notes.type == AttackType.MSG_BOMB:
            while len(self.notes.bomb_request) > 0:
                req = self.notes.bomb_request.pop(0)
                print(self.id, 'bombing', req.node)
                # for _ in range(BOMB_FACTOR):
                msg = self.gen_msg(MessageType.TRANS, req.node, TRANS_MSG_LEN, trans_id)
                self.out_msgs.append(msg)
        elif self.notes.type == AttackType.UNDERCOVER:
            # in case need to graft
            for t in self.notes.targets:
                if (t not in self.secured_mesh) or (not self.secured_mesh[t]):
                    self.send_graft_peer(t, r)
                    # print(self.id, 'send graft to', t)
                    self.secured_mesh[t] = False
        else:
            print('Error. unknown adv role')
            sys.exit(0)

        # for t in self.notes.targets:
            # # print('sybil', self.id, 'has target', t)
            # if t not in self.mesh:
                # if self.id == 90:
                    # print('sybil', self.id, 'try reconnect', t)
                # msg = self.graft_peer(t, r)
                # self.out_msgs.append(msg)

    def forward_msg(self, msg, peer, trans_id):
        _, mid, src, _, _, _, trans_id = msg
        if peer in self.notes.targets:
            attack = self.notes.targets[peer]
            msg = self.gen_msg(MessageType.TRANS, peer, TRANS_MSG_LEN, trans_id)
            # print(self.id, 'undercover forward msg to', peer)
            self.out_msgs.insert(0, msg)
        # unspecified attack for that peer
        else:
            msg = self.gen_msg(MessageType.TRANS, peer, TRANS_MSG_LEN, trans_id)
            # print(self.id, 'forward msg to', peer)
            self.out_msgs.append(msg)

        
    def proc_TRANS(self, msg, r):
        _, mid, src, _, adv_rate, _, trans_id = msg
        if adv_rate == AdvRate.SybilInternal:
            for peer in self.mesh:
                self.forward_msg(msg, peer, trans_id)
            return 

        self.scores[src].add_msg_delivery()
        if src in self.notes.targets:
            self.secured_mesh[src] = True
        # if not seen msg before
        if mid not in self.msg_ids:
            if r not in self.trans_hist:
                self.trans_hist[r] = [msg]
            else:
                self.trans_hist[r].append(msg)
            
            self.msg_ids.add(mid)
            self.scores[src].update_p2()
            self.round_trans_ids.add(trans_id)
            # push it to other peers in mesh if not encountered
            if trans_id not in self.trans_set:
                for peer in self.mesh:
                    if peer == src:
                        continue
                    self.forward_msg(msg, peer, trans_id)
                self.trans_set.add(trans_id)
            # else:
                # print(self.id, 'already had msg')

    def gen_msg(self, mtype, peer, msg_len, payload):
        adv_msg = AdvRate.SybilFlat
        for c in self.notes.channels:
            if peer == c.node:
                adv_msg = AdvRate.SybilPriority

        msg = Message(mtype, self.seqno, self.id, peer, adv_msg, msg_len, payload)
        self.seqno += 1
        return msg


    # TODO later out_msgs might not be empties instanteously due to upload bandwidth
    def send_msgs(self):
        # reset out_msgs
        out_msg = self.out_msgs.copy()
        self.out_msgs.clear()
        return out_msg

    def prune_peer(self, peer):
        # add backoff counter
        msg = self.gen_msg(MessageType.PRUNE, peer, CTRL_MSG_LEN, None)
        self.mesh.pop(peer, None)
        self.scores[peer].in_mesh = False
        self.out_msgs.append(msg)


    def graft_peer(self, peer, r):
        msg = self.gen_msg(MessageType.GRAFT, peer, CTRL_MSG_LEN, None)
        self.mesh[peer] = Direction.Outgoing
        if peer not in self.scores:
            self.scores[peer] = PeerScoreCounter()
        self.scores[peer].in_mesh = True
        self.scores[peer].init_r(r)
        
        return msg

    def send_graft_peer(self, peer, r):
        msg = self.graft_peer(peer, r)
        self.out_msgs.append(msg)

    def setup_peer(self, peer, direction, r):
        self.mesh[peer] = direction 
        if peer not in self.scores:
            self.scores[peer] = PeerScoreCounter()
        self.scores[peer].in_mesh = True
        self.scores[peer].init_r(r)

    def init_peers_scores(self):
        for p in self.peers:
            self.scores[p] = PeerScoreCounter()

    
    def get_num_outgoing(self, mesh_peers, m):
        num_out = 0
        for u in mesh_peers[:m]:
            assert( u in self.mesh)
            d = self.mesh[u]
            if d == Direction.Outgoing:
                num_out += 1
        return num_out

   
    # find other peers to add
    def proc_PRUNE(self, msg):
        _, _, src, _, _, _, _ = msg
        if src in self.mesh:
            self.mesh.pop(src, None)
            self.scores[src].in_mesh = False
         

    # the other peer has added me to its mesh, I will add it too 
    def proc_GRAFT(self, msg, r):
        _, _, src, _, _, _, _ = msg
        self.mesh[src] = Direction.Incoming
        if src not in self.scores:
            self.scores[src] = PeerScoreCounter()
        #  if (self.id == 0):
            #  print('Round {}: 0 graft {}, new score is {}'.format(r, src, self.scores[src].get_score()))
        self.scores[src].in_mesh = True
        self.peers.add(src)
        # if self.id > 50 or self.id == 1:
        #     print(self.id, 'graft', src)
        self.out_msgs.append(msg)

    def proc_LEAVE(self, msg):
        pass

    def proc_PX(self, msg):
        pass
   
    # send random subset peers gossip with GOSSIP_FACTOR, see section 6.4
    def get_rand_gossip_nodes(self):
        pass


    # return State, remember to return a copy
    def get_states(self):
        scores_value = {} # key is peer
        for peer in self.scores:
            scores_value[peer] = self.scores[peer].get_score()

        out_conn = []
        for peer, direction in self.mesh.items():
            if direction == Direction.Outgoing:
                out_conn.append(peer)

        secured_mesh = []
        for k, v in self.secured_mesh.items():
            if v:
                secured_mesh.append(k)
        attempts = []
        for t in self.notes.targets:
            if (t not in self.secured_mesh) or (not self.secured_mesh[t]):
                attempts.append(t)

        channels = []
        for c in self.notes.channels:
            channels.append(c.node)
        return State(
                self.role, 
                self.conn.copy(), 
                self.mesh.copy(), 
                secured_mesh,
                channels,
                self.notes.type.value,
                self.peers.copy(), 
                attempts,
                self.out_msgs.copy(), 
                scores_value, 
                self.trans_set.copy(), 
                self.round_trans_ids.copy(), 
                self.gen_trans_num,
                out_conn
                )
