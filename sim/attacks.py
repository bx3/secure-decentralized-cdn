from config import * 
from messages import MessageType

# class Eclipse_Adv:
    # def __init__(self, sybils):
        # self.target = -1
        # self.favor_list = set()
    # def has_target(self):
        # return self.target > -1


class Adversary:
    def __init__(self, sybils):
        self.state = None

        self.grafted = {} # key is honest node, values is a list of grafted sybil id 
        self.sybils = sybils # key is node id, value is 

        self.target = -1 # for eclipse
        self.favor_list = set() # for eclipse

    # attack codes, u is node, return messages
    def censorship_attack(self, graph, u):
        pass

    def has_target(self):
        return self.target > -1

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
        self.target = sorted_list[0]

    def find_in_conns(self, r, snapshots, target):
        last_shot = snapshots[-1]
        nodes = last_shot.nodes
        node = nodes[target]
        outs = node.out_conn
        mesh = node.mesh
        ins = set(mesh).difference(set(outs))
        target = []
        for i in ins:
            if i not in self.sybils:
                target.append(i)
        return  target

    def find_out_conns(self, r, snapshots, target):
        last_shot = snapshots[-1]
        nodes = last_shot.nodes
        node = nodes[target]
        return node.out_conn

    # corrupt incoming peers, by sending many graft to them send slow
    def corrupt_ins(self, peers, r):
        msgs = []
        for peer in peers:
            if peer not in self.grafted:
                for i, sybil in self.sybils.items():
                    msg = sybil.gen_msg(MessageType.GRAFT, peer, CTRL_MSG_LEN, None)
                    sybil.graft_peer(peer, r)
                    msgs.append(msg)
        return msgs

    def corrupts_outs(self, peers, r):
        msgs = []
        for peer in peers:
            if peer not in self.grafted:
                for sybil in self.sybils:
                    msg = sybil.gen_msg(MessageType.GRAFT, peer, CTRL_MSG_LEN, None)
                    sybil.graft_peer(peer, r)
                    msgs.append(msg)
            self.favor_list.add(peer)
        return msgs

    # populate target incoming, by grafting to them, and send useful
    def populate_in_conns(self, target, r):
        msgs = []
        if target not in self.grafted:
            for u, sybil in self.sybils.items():
                msg = sybil.gen_msg(MessageType.GRAFT, target, CTRL_MSG_LEN, None)       
                msgs.append(msg)
                sybil.graft_peer(target, r)
        self.favor_list.add(target)
        return msgs



    def handle_msgs(self, r, attack):
        for i, sybil in self.sybils.items():
            sybil.adv_process_msgs(r, self.target, self.favor_list, attack)

    def eclipse_target(self, r, snapshots, network):
        if not self.has_target():
            print('Warning. No target')
        msgs = []
        if r > 0:
            ins = self.find_in_conns(r, snapshots, self.target) 
            msgs = self.corrupt_ins(ins, r)
            outs = self.find_out_conns(r, snapshots, self.target) 

        msgs += self.populate_in_conns(self.target, r)
        return msgs
