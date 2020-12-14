from config import * 
from messages import MessageType
from messages import Message
from messages import AdvRate
from collections import namedtuple
from collections import defaultdict
from enum import Enum
import random

class AttackType(Enum):
    MSG_BOMB = 0
    UNDERCOVER = 1

class AttackAngle(Enum):
    FirstMsgDelivery = 0

BombRequest = namedtuple('BombRequest', ['node', 'time'])  # node, for how long, time must be 1
FreezeRequest = namedtuple('FreezeRequest', ['link', 'time']) # link, for how long, time must be 1
AttackChannel = namedtuple('AttackChannel', ['node', 'method']) # link, for how long, time must be 1

# each sybils uses notes to conduct attack
class Notes:
    def __init__(self, u):
        self.id = u
        self.type = None
        self.targets = {} # key is desired targeted node, value is action type
        self.bomb_request = [] # is a list of BombRequest
        self.freeze_request = [] # is a list of FreezeRequest
        self.channels = [] 
        self.trans_pool = defaultdict(list) # key is undercover, values is recv trans

    def add_target(self, u, att_type):
        self.targets[u] = att_type

    def assign_attack_type(self, att_type):
        self.type = att_type

    def flush_bomb_request(self):
        a = self.bomb_request.copy()
        self.bomb_request = []
        return a

    def flush_freeze_request(self):
        a = self.freeze_request.copy()
        self.freeze_request = []
        return a

    def add_bomb_request(self, t, r):
        self.bomb_request.append(BombRequest(t, r))
    def add_freeze_request(self, l, r):
        self.freeze_request.append(FreezeRequest(l, r))
    def release_channel(self, c):
        self.channels.remove(c)
    def add_channel(self, c):
        self.channels.append(c)

class Adversary:
    def __init__(self, sybils):
        self.state = None

        self.grafted = {} # key is honest node, values is a list of grafted sybil id 
        self.sybils = sybils # key is node id, value is 

        self.targets = set() # for eclipse

        self.undercovers = []
        self.msg_bombs = []

        self.secured_conn = defaultdict(list) # key is sybil node, value is targeted nods

        # weapons
        self.num_undercover = OVERLAY_DHI + 1
        self.num_bomb = len(sybils) - self.num_undercover
        self.net_freezer = 0 # total number freezed round in all links

        self.assign_roles_to_sybils()
        self.avail_channel = []


    # attack codes, u is node, return messages
    def censorship_attack(self, graph, u):
        pass

    def add_targets(self, targets):
        for t in targets:
            if t not in self.targets:
                self.targets.add(t)
                channel = AttackChannel(t, AttackAngle.FirstMsgDelivery)
                self.avail_channel.append(channel)

    def sybil_nodes_redistribute_msgs(self, curr_r):
        trans_pool= {} # key is trans id, value is msg
        # collect all curr round trans
        for u, sybil in self.sybils.items():
            trans_list = sybil.trans_hist[curr_r]
            for msg in trans_list:
                _, mid, src, _, _, _, tid = msg
                if tid not in trans_pool:
                    trans_pool[tid] = msg

        trans_id_set = set(trans_pool.keys()) 
        for u, sybil in self.sybils.items():
            trans_list = sybil.trans_hist[curr_r]
            trans_id_list = self.get_trans_id_list(trans_list)
            missings = trans_id_set.difference(set(trans_id_list))
            for tid in missings:
                self.send_missing_trans_to_sybil(missings, trans_pool, sybil, curr_r)

    def get_trans_id_list(self, trans_list):
        trans_id_list = []
        for msg in trans_list:
            _, mid, src, _, _, _, trans_id = msg
            trans_id_list.append(trans_id)
        return trans_id_list
        
    def send_missing_trans_to_sybil(self, missings, trans_pool, sybil, r):
        for tid in missings:
            msg = trans_pool[tid]
            _, mid, _, _, _, _, trans_id = msg
            internal_msg = Message(
                    MessageType.TRANS, 
                    ADV_SPECIAL_SEQNO,
                    ADV_SPECIAL_SENDER,
                    sybil.id,
                    AdvRate.SybilInternal,
                    TRANS_MSG_LEN,
                    trans_id)
            sybil.proc_TRANS(internal_msg, r)

    def has_target(self):
        return len(self.targets) > 0

    def find_eclipse_publisher_target(self, r, snapshots):
        node_avg_score = {}
        last_shot = snapshots[-1]
        nodes_shot = last_shot.nodes
        for u in range(len(nodes_shot)):
            node = nodes_shot[u]
            node_view_total = 0
            if node.role == NodeType.PUB:   
                for peer in node.mesh:
                    node_view_total += node.scores[peer]
                avg = float(node_view_total)/len(node.mesh)
                node_avg_score[u] = avg
        sorted_score = {k: v for k, v in sorted(node_avg_score.items(), key=lambda item: item[1])}
        sorted_list = list(sorted_score)
        self.targets = sorted_list[0]

    def find_target_in_conns(self, r, snapshots, target):
        last_shot = snapshots[-1]
        nodes = last_shot.nodes
        new_targets = []
        node = nodes[target]
        outs = node.out_conn
        mesh = node.mesh
        ins = set(mesh).difference(set(outs))
        for i in ins:
            if i not in self.sybils:
                new_targets.append(i)
        return new_targets
    
    # for one nodes
    def find_target_out_conns(self, r, snapshots, target):
        last_shot = snapshots[-1]
        nodes = last_shot.nodes
        node = nodes[target]
        return node.out_conn

    def handle_msgs(self, r):
        for i, sybil in self.sybils.items():
            sybil.process_msgs(r)

    def assign_roles_to_sybils(self):
        # assign roles
        for v, sybil in self.sybils.items():
            if len(self.undercovers) < self.num_undercover:
                self.undercovers.append(v)
                sybil.notes.assign_attack_type(AttackType.UNDERCOVER)
            else:
                self.msg_bombs.append(v)
                sybil.notes.assign_attack_type(AttackType.MSG_BOMB)

    def is_undercover_stable(self):
        pass

    def is_undercover_medium_well(self, target, undercover):
        if undercover not in target.mesh:
            return False

        pair_list = []
        num_peer = len(target.mesh)
        for k, _ in target.mesh.items():
            v = target.scores[k]
            pair_list.append((k,v))
        sorted_pair_list = sorted(pair_list, key=lambda x: x[1], reverse=True)
        sorted_peer = [i for i,j in sorted_pair_list]
        rank = sorted_peer.index(undercover)
        if rank < num_peer/2 and rank < OVERLAY_D /2:
            return True
        else:
            return False


    # snapshots[-1]
    def redistribute_channel_to_undercover(self, snapshot):
        for u in self.undercovers:
            sybil = self.sybils[u]
            for channel in sybil.notes.channels:
                # if sybil is meshed by channel already 
                target = channel.node
                node = snapshot.nodes[target]
                # reclaim channel from sybil
                if self.is_undercover_medium_well(node, u):
                    sybil.notes.release_channel(channel)
                    self.avail_channel.append(channel)
                    self.secured_conn[u].append(target)

        # redistribute avail channels to other undercovers
        while len(self.avail_channel) > 0:
            channel = self.avail_channel.pop(0) 
            sybil_list = list(self.sybils.keys())
            # random.shuffle(sybil_list)
            for u in sybil_list:
                # the targeted node by the channel is not yet secure by adv
                if channel.node not in self.secured_conn[u]:
                    self.sybils[u].notes.add_channel(channel)
                    break

    # a simple implement, much room to improve
    def assign_undercover_to_targets(self, targets, r, pubs):
        msgs = []
        graft_targets = set()
        
        # distribute undercover to targets
        for t in targets:
            for u in self.undercovers:
                sybil = self.sybils[u]
                if t not in sybil.notes.targets:
                    sybil.insert_attack_note(t, AttackType.UNDERCOVER, pubs, r)
                    # msgs.append(sybil.graft_peer(t, r))
                    # graft_targets.add(t)

        # print(r, msgs)
        return msgs

    def get_all_publishers(self, snapshot):
        pubs = []
        for u, node in snapshot.nodes.items():
            if node.role == NodeType.PUB:
                pubs.append(u)
        return pubs


    # every bomber does it
    def bombers_accept_request(self, req):
        for bomb in self.msg_bombs:
            sybil = self.sybils[bomb]
            sybil.add_bomb_request(req.node, req.time)

    def handle_bomb_requests(self, snapshot):
        for u, sybil in self.sybils.items():
            # reqs = sybil.notes.flush_bomb_request()
            

            for req in reqs:
                self.bombers_accept_request(req)

    def handle_freeze_requests(self, r, nodes, network):
        for t in self.targets:
            node = nodes[t]
            for peer in node.mesh:
                if peer not in self.sybils:
                    # freeze it for 1 round
                    pair = (peer, t)
                    network.break_link(pair, 1)


    def eclipse_target(self, r, snapshots, network):
        if not self.has_target():
            print('Warning. No target')

        pubs = self.get_all_publishers(snapshots[-1])
        msgs = self.assign_undercover_to_targets(self.targets, r, pubs)

        if r % HEARTBEAT == 1:
            self.redistribute_channel_to_undercover(snapshots[-1])

        # handle all bomb requests, requests are later handled by
        # self.handle_bomb_requests(snapshots[-1])
        # self.handle_freeze_requests(r, snapshots[-1], network)

        # targets_ins_set = set()
        # targets_outs_set = set()
        # for target in self.targets:
            # targets_ins = self.find_target_in_conns(r, snapshots, target)
            # targets_outs = self.find_target_out_conns(r, snapshots, target) 

            # for t in targets_ins:
                # targets_ins_set.add(t)
            
            # for t in targets_outs:
                # targets_outs_set.add(t)

        # dist


        # for t, sybil in self.sybils.items():
            # for r in sybil.notes.targets:
                # print('sybil', t, 'has target',r)

        return msgs



    # corrupt incoming peers, by sending many graft to them send slow
    # def graft_ins(self, peers, r):
        # msgs = []
        # for peer in peers:
            # if peer not in self.grafted:
                # for i, sybil in self.sybils.items():
                    # msg = sybil.gen_msg(MessageType.GRAFT, peer, CTRL_MSG_LEN, None)
                    # sybil.graft_peer(peer, r)
                    # msgs.append(msg)
        # return msgs

    # def corrupts_outs(self, peers, r):
        # msgs = []
        # for peer in peers:
            # if peer not in self.grafted:
                # for sybil in self.sybils:
                    # msg = sybil.gen_msg(MessageType.GRAFT, peer, CTRL_MSG_LEN, None)
                    # sybil.graft_peer(peer, r)
                    # msgs.append(msg)
            # self.favor_list.add(peer)
        # return msgs

    # populate target incoming, by grafting to them, and send useful
    # def graft_targets(self, targets, r):
        # msgs = []
        # for target in targets:
            # if target not in self.grafted:
                # for u, sybil in self.sybils.items():
                    # msg = sybil.gen_msg(MessageType.GRAFT, target, CTRL_MSG_LEN, None)       
                    # msgs.append(msg)
                    # sybil.graft_peer(target, r)
            # self.favor_list.add(target)
        # return msgs

            # for u in self.msg_bombs:
                # sybil = self.sybils[u]
                # sybil.insert_attack_note(t, AttackType.MSG_BOMB, pubs, r)

        # for t in targets_ins_set:
            # for v, sybil in self.sybils.items():
                # sybil.notes.add_target(t, AttackType.MSG_BOMB)
                # if v not in graft_targets:
                    # graft_targets.add(t)
                    # msgs.append(sybil.graft_peer(t, r))

        # for  t in targets_outs_set:
            # for v, sybil in self.sybils.items():
                # sybil.notes.add_target(t, AttackType.UNDERCOVER)
                # if v not in graft_targets:
                    # graft_targets.add(t)
                    # msgs.append(sybil.graft_peer(t, r))
