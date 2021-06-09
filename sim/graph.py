#!/usr/bin/env python
from sim.config import *
import random
from collections import namedtuple
from collections import defaultdict
from sim.messages import *
from sim.scores import PeerScoreCounter
import sys

State = namedtuple('State', [
    'role', 
    'conn', 
    'mesh', 
    'peers', 
    'out_msgs', 
    'scores', 
    'scores_decompose',
    'trans_record', 
    'transids', 
    'gen_trans_num', 
    'out_conn']
    )
TransId = namedtuple('TransId', ['src', 'no'])
ScoreRecord = namedtuple('ScoreRecord', ['p1', 'p2', 'p3a', 'p3b', 'p4', 'p5', 'p6'])


class Peer:
    def __init__(self, direction):
        self.direction = direction
        self.counter = PeerScoreCounter()


class Node:
    def __init__(self, role, u, interval, topic_peers, heartbeat_period, topics, x, y):
        self.id = u  # my id
        self.role = role
        self.topics = topics
        self.topic_peers = topic_peers  # topic peers: "known" dict in json; key=topic, value=peers
        self.actors = {}  # key is topic, value is actor
        self.x = x
        self.y = y
        self.in_msgs = []

        # each node has multiple topics => 1:1 for topic:actor
        for topic in topics:
            peers = topic_peers[str(topic)]  # json convert key into string
            self.actors[topic] = TopicActor(role, u, interval, peers, heartbeat_period, topic)

    def get_all_mesh(self):
        meshes = set()
        for topic, actor in self.actors.items():
            meshes = meshes.union(actor.mesh)
        return meshes

    def setup_peer(self, peer, direction, r, topic):
        self.actors[topic].setup_peer(peer, direction, r)

    # TODO randomize order maybe
    def send_msgs(self):
        out_msgs = []
        for topic, actor in self.actors.items():
            topic_msgs = actor.send_msgs()
            out_msgs += topic_msgs
        return out_msgs

    def insert_msg_buff(self, msgs):
        self.in_msgs += msgs  # append
        print("\nnode insert_msg_buff")
        print("self.in_msgs", self.in_msgs)
        print("msgs", msgs)

    def process_msgs(self, curr_r):
        # print("node", self.id, "process_msgs", len(self.in_msgs))
        actor_msgs = defaultdict(list)
        while len(self.in_msgs) > 0:
            msg = self.in_msgs.pop(0)
            mtype, _, src, dst, _, _, payload, topic, send_r = msg
            if topic not in self.actors:
                print('Warning. Receive other topic msg')
            actor_msgs[topic].append(msg)
    
        for topic in self.topics:
            actor = self.actors[topic]
            in_msgs = actor_msgs[topic]  # actor_msgs = {key: topic; value: list of in_msgs}
            print("node ", self.id, "process_msgs's in_msgs", in_msgs)
            actor.process_msgs(in_msgs, curr_r)

    def get_states(self):
        states = {}
        for topic, actor in self.actors.items():
            state = actor.get_states()
            states[topic] = state
        return states


# assume there is only one topic then
# generic data structure usable by all protocols
class TopicActor:
    def __init__(self, role, u, interval, peers, heartbeat_period, topic):
        self.id = u  # my id
        self.topic = topic
        self.role = role
        self.conn = set()  # lazy push: nodes that are NOT PART of the mesh comm. w/ mesh-connected nodes through gossip
        self.mesh = {}  # mesh push

        self.peers = set(peers)  # known peers
        self.out_msgs = []  # msg to push in the next round
        # self.in_msgs = []
        self.D_scores = 2  #
        self.scores = {}  # all peer score, key is peer, value is PeerScoreCounter
        self.seqno = 0
        self.D = OVERLAY_D  # curr in local mesh degree: incoming + outgoing; target degree btwn D_low & D_high
        self.D_out = 2  # num outgoing connections in the mesh; D_out < OVERLAY_DLO and D_out < D/2
        # wat abt D_low and D_high? Also, D_out is adjusted during mesh maintenance so D_out < D_low & D_out <= D/2

        self.init_peers_scores()  # sets self.scores: key = peer and value = default PeerScoreCounter()

        if interval == 0:
            self.gen_prob = 0
        else:
            intervals_per_trans = float(interval) / float(SEC_PER_ROUND)
            self.gen_prob = 1/intervals_per_trans  # per round 

        self.msg_ids = set()
        self.heartbeat_period = heartbeat_period
        self.gen_trans_num = 0

        self.round_trans_ids = set()  # keep track of msgs used for analysis
        self.trans_record = {}  # key is trans_id, value is (recv r, send r) 
        self.last_heartbeat = -1

    def run_scores_background(self, curr_r):
        for u, counters in self.scores.items():
            counters.run_background(curr_r)

    # worker func 
    def process_msgs(self, msgs, r):
        # schedule heartbeat 
        self.schedule_heartbeat(r)
        # background peer local view update
        self.run_scores_background(r)
        self.round_trans_ids.clear()
        in_msgs = msgs.copy()
        # handle msgs
        # print()
        # print("len(in_msgs)", len(in_msgs))
        while len(in_msgs) > 0:
            msg = in_msgs.pop(0)
            mtype, _, src, dst, _, _, payload, topic, send_r = msg

            assert self.id == dst
            if mtype == MessageType.GRAFT:
                # if self.id == 0:
                    # print(self.id, 'recv GRAFT from', src)
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
                if r > self.last_heartbeat:
                    self.last_heartbeat = r
                    self.proc_Heartbeat(msg, r)
            elif mtype == MessageType.TRANS:
                # print("\tTRANS msgs:")
                # print("\tsend_r:", send_r)
                # print("\trecv_r:", r)
                # if self.id == 0 or self.id == 1 or self.id == 68:
                    # print(self.id, 'recv trans', payload, 'from', src)
                self.proc_TRANS(msg, r)
            else:
                self.scores[src].update_p4()  # Invalid msgs
        
        if self.role == NodeType.PUB:
            # if r<1:
            self.gen_trans(r)

    def schedule_heartbeat(self, r):
        if self.role == NodeType.PUB or self.role == NodeType.LURK:
            # someone is connected with me in mesh
            if (r%self.heartbeat_period) == HEARTBEAT_START:
                self.gen_heartbeat(r)

    def gen_heartbeat(self, r):
        # for peer in self.peers:
            # msg = self.gen_msg(MessageType.HEARTBEAT, peer, CTRL_MSG_LEN, None)
            # self.out_msgs.append(msg)
        self.proc_Heartbeat(None, r)
        self.last_heartbeat = r

    # only gen transaction when previous one is at least pushed 
    def gen_trans(self, r):
        for msg in self.out_msgs:
            mtype, _, _, _, _, _, tid, topic, send_r = msg
            # if my last msg is not pushed, give up
            if mtype == MessageType.TRANS and tid.src == self.id:
                return

        if random.random() < self.gen_prob:
            self.gen_trans_num += 1
            print('*****', self.id, 'gen a message *******')
            for peer in self.mesh:
                trans_id = TransId(self.id, self.gen_trans_num)
                msg = self.gen_msg(MessageType.TRANS, peer, TRANS_MSG_LEN, trans_id, r)
                # print(self.id, 'generate trans', trans_id, 'to', peer)
                self.out_msgs.append(msg)

    def proc_TRANS(self, msg, r):
        _, mid, src, _, _, _, trans_id, topic, send_r = msg
        # print('node', self.id, src)
        # print(self.mesh)
        # in case the peer has not been accepted by the mesh, but relay msg
        if src not in self.mesh:
            return 

        self.scores[src].add_msg_delivery()

        # if not seen msg before
        # if mid not in self.msg_ids:
        print("trans_id", trans_id)
        if trans_id not in self.trans_record:  # only adding 1st occurrences of TransIds' transfer records w/in a node
            self.msg_ids.add(mid)
            self.scores[src].update_p2()
            self.round_trans_ids.add(trans_id)
            # push it to other peers in mesh if not encountered
            for peer in self.mesh:
                if peer != src:
                    msg = self.gen_msg(MessageType.TRANS, peer, TRANS_MSG_LEN, trans_id, r)
                    # print(self.id, 'forward', trans_id, 'to', peer)
                    self.out_msgs.append(msg)
            print("\t\ttrans_id", trans_id)
            print("\t\tputting received and sent r into trans_record")
            print("\t\tsend_r:", send_r)
            print("\t\tr: ", r)
            self.trans_record[trans_id] = (r, send_r)

    def init_peers_scores(self):
        for p in self.peers:
            self.scores[p] = PeerScoreCounter()

    def gen_msg(self, mtype, peer, msg_len, payload, r):
        msg = Message(mtype, self.seqno, self.id, peer, AdvRate.NotSybil, msg_len, payload, self.topic, r)
        self.seqno += 1
        return msg

    # TODO later out_msgs might not be empties instanteously due to upload bandwidth
    def send_msgs(self):
        # reset out_msgs
        out_msg = self.out_msgs.copy()
        self.out_msgs.clear()
        return out_msg

    def prune_peer(self, peer, r):
        # add backoff counter
        # if self.id == 0:
        
        msg = self.gen_msg(MessageType.PRUNE, peer, CTRL_MSG_LEN, None, r)
        self.mesh.pop(peer, None)
        self.scores[peer].in_mesh = False
        self.out_msgs.append(msg)

    def graft_peer(self, peer, r):
        msg = self.gen_msg(MessageType.GRAFT, peer, CTRL_MSG_LEN, None, r)
        self.mesh[peer] = Direction.Outgoing
        if peer not in self.scores:
            self.scores[peer] = PeerScoreCounter()
        self.scores[peer].in_mesh = True
        #  if (self.id == 0):
            #  print('Round {}: 0 graft {}, new score is {}'.format(r, peer, self.scores[peer].get_score()))
        self.scores[peer].init_r(r)
        self.out_msgs.append(msg)

    def setup_peer(self, peer, direction, r):
        self.mesh[peer] = direction 
        if peer not in self.scores:
            self.scores[peer] = PeerScoreCounter()
        self.scores[peer].in_mesh = True
        self.scores[peer].init_r(r)

    # TODO generate IHave
    def proc_Heartbeat(self, msg, r):
        nodes = self.get_rand_gossip_nodes()
        mesh_peers = []
        # prune neg mesh
        all_mesh_peers = self.mesh.keys()
        for u in list(all_mesh_peers):
            counters = self.scores[u]
            if counters.get_score() < 0:
                counters.update_p3b(-counters.get_score())
                # print(self.id, "prune a peer", u, 'due to neg score')
                self.prune_peer(u, r)

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
            # print(self.id, 'mesh is high', len(self.mesh))
            # get pos score peers
            mesh_peers_scores = self.get_pos_score_mesh_peers()
            mesh_peers_scores.sort(key=lambda tup: tup[1], reverse=True)
            mesh_peers = [i for i, j in mesh_peers_scores]
            
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
                self.prune_peer(peer, r)
                # print(self.id, "prune a peer", peer, 'due to high mesh')

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
        _, _, src, _, _, _, _, _, _ = msg
        if src in self.mesh:
            self.mesh.pop(src, None)
            self.scores[src].in_mesh = False

    # return true if it won't pass
    def filter_graft(self, msg, r):
        _, _, src, _, _, _, _, _, _ = msg
        
        # check score
        if src in self.scores:
            counters = self.scores[src]
            if counters.get_score() < 0:
                # print(self.id, 'reject peer', src, 'due to neg score')
                msg = self.gen_msg(MessageType.PRUNE, src, CTRL_MSG_LEN, None, r)
                self.out_msgs.append(msg)
                return True

        is_outbound = False
        for peer, direction in self.mesh.items():
            if src == peer and direction == Direction.Outgoing:
                is_outbound = True
        # check existing number peer in the mesh
        if len(self.mesh) >= OVERLAY_DHI and (not is_outbound):
            msg = self.gen_msg(MessageType.PRUNE, src, CTRL_MSG_LEN, None, r)
            self.out_msgs.append(msg)
            # print(self.id, 'reject peer', src, 'due to mesh limit')
            return True

        return False

    # the other peer has added me to its mesh, I will add it too 
    def proc_GRAFT(self, msg, r):
        _, _, src, _, _, _, _, _, _ = msg
        if src in self.mesh:
            return

        if self.filter_graft(msg, r):
            # send prune msg
            return 

        # print(self.id, 'accept a GRAFT from', src)
        self.mesh[src] = Direction.Incoming
        if src not in self.scores:
            self.scores[src] = PeerScoreCounter()
        self.scores[src].in_mesh = True
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
        scores_value = {}  # key is peer

        scores_decompose = {}
        for peer in self.scores:
            scores_value[peer] = self.scores[peer].get_score()
            counters = self.scores[peer]
            s = ScoreRecord(
                round(counters.get_score1(), 2),
                round(counters.get_score2(), 2),
                round(counters.get_score3a(), 2),
                round(counters.get_score3b(), 2),
                round(counters.get_score4(), 2),
                round(counters.get_score5(), 2),
                round(counters.get_score6(), 2),
            )
            scores_decompose[peer] = s

        out_conn = []
        for peer, direction in self.mesh.items():
            if direction == Direction.Outgoing:
                out_conn.append(peer)

        return State(
                self.role, 
                self.conn.copy(), 
                self.mesh.copy(), 
                self.peers.copy(), 
                self.out_msgs.copy(), 
                scores_value, 
                scores_decompose,
                self.trans_record.copy(), 
                self.round_trans_ids.copy(), 
                self.gen_trans_num,
                out_conn
                )


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
