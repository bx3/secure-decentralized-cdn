from config import * 
from messages import MessageType
from collections import namedtuple
from enum import Enum

class AttackType(Enum):
    MSG_BOMB = 0
    UNDERCOVER = 1

BombRequest = namedtuple('BombRequest', ['node', 'time'])  # node, for how long
FreezeRequest = namedtuple('FreezeRequest', ['link', 'time']) # link, for how long

# each sybils uses notes to conduct attack
class Notes:
    def __init__(self, u):
        self.id = u
        self.targets = {} # key is desired targeted node, value is action type
        # self.innocent_helper = {} # key is other pub node, value is if in the mesh 
        self.bomb_request = [] # is a list of BombRequest
        self.freeze_request = [] # is a list of FreezeRequest

    def add_target(self, u, att_type):
        self.targets[u] = att_type

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

class Adversary:
    def __init__(self, sybils):
        self.state = None

        self.grafted = {} # key is honest node, values is a list of grafted sybil id 
        self.sybils = sybils # key is node id, value is 

        self.targets = set() # for eclipse
        self.attacks = {} # key is node id, value is notes

        self.undercovers = []
        self.msg_bombs = []

        # weapons
        self.num_undercover = OVERLAY_DHI + 1
        self.num_bomb = len(sybils) - self.num_undercover
        self.net_freezer = 0 # total number freezed round in all links

        self.assign_roles_to_sybils()


    # attack codes, u is node, return messages
    def censorship_attack(self, graph, u):
        pass

    def add_targets(self, targets):
        for t in targets:
            if t not in self.targets:
                self.targets.add(t)

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
            else:
                self.msg_bombs.append(v)

            
    def assign_undercover_to_targets(self, targets, r, pubs):
        msgs = []
        graft_targets = set()
        
        # distribute undercover to targets
        for t in targets:
            for u in self.undercovers:
                sybil = self.sybils[u]
                if t not in sybil.notes.targets:
                    sybil.insert_attack_note(t, AttackType.UNDERCOVER, pubs, r)
                    msgs.append(sybil.graft_peer(t, r))
                    graft_targets.add(t)

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

        return msgs

    def get_all_publishers(self, snapshot):
        pubs = []
        for u, node in snapshot.nodes.items():
            if node.role == NodeType.PUB:
                pubs.append(u)
        return pubs

    def pull_attack_requests(self):
        msgs = []


        return msgs

    def eclipse_target(self, r, snapshots, network):
        if not self.has_target():
            print('Warning. No target')

        pubs = self.get_all_publishers(snapshots[-1])
        msgs = self.assign_undercover_to_targets(self.targets, r, pubs)


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
