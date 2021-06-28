#!/usr/bin/env python
from config import *
import random
from collections import namedtuple
from collections import defaultdict
from messages import *
from scores import PeerScoreCounter
import sys
from generate_network import Topic
from generate_network import get_topic_type
from adaptor import Adaptor


State = namedtuple('State', [
    'role', 
    'conn', 
    'mesh', 
    'peers', 
    'out_msgs', 
    # 'scores', 
    # 'scores_decompose',
    # 'trans_record', 
    'transids', 
    'gen_trans_num', 
    'out_conn']
    )
TransId = namedtuple('TransId', ['src', 'no']) # src is the node who first creates the trans
ScoreRecord = namedtuple('ScoreRecord', ['p1', 'p2', 'p3a', 'p3b', 'p4', 'p5', 'p6'])

class Peer:
    def __init__(self, direciton):
        self.direction = direction
        self.counter = PeerScoreCounter()

class Node:
    def __init__(self, topic_roles, u, interval, topic_peers, heartbeat_period, topics, x, y, log_file, update_method):
        self.id = u # my id
        self.topics = topics
        self.topic_peers = topic_peers.copy()
        self.heartbeat_period = heartbeat_period
        self.actors = {} # key is topic, value is actor
        self.x = x
        self.y = y
        self.in_msgs = []
        self.log_file = log_file

        if update_method not in ['individual', 'coll-subset']:
            print('Unknown update method')
            sys.exit(1)

        self.update_method = update_method # 'individual' # individual#'individual' # '' 'coll-subset'
        for topic in topics:
            peers = topic_peers[topic] 
            role = topic_roles[topic]
            self.actors[topic] = TopicActor(role, u, interval, peers, heartbeat_period, topic, 
                    self.update_method)


        desired_num_conn = len(self.topics) * OVERLAY_D
        desired_num_keep = desired_num_conn - 2 # TODO 2 rand conn 

        self.adaptor = Adaptor(self.id, self.topics, heartbeat_period, desired_num_conn, desired_num_keep, self.log_file) 
        

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
        self.in_msgs += msgs # append
        # print(self.id, self.in_msgs)

    def write_curr_mesh(self, r, note):
        with open(self.log_file, 'a') as w:
            comment = note + "Epoch {r:<5}, node {node_id:<5}".format(r=r, node_id=self.id)
            for topic, actor in self.actors.items():
                mesh = sorted(list(actor.mesh.keys()))
                topic_comm = "topic {topic:<4}: {mesh}".format(topic=topic, mesh=mesh)
                comment += " " + topic_comm
            w.write(comment + '\n')

    def get_curr_mesh(self):
        out_meshes = set()
        in_meshes = set()
        for topic, actor in self.actors.items():
            for peer, direction in actor.mesh.items():
                if direction == Direction.Outgoing:
                    out_meshes.add(peer)
                elif direction == Direction.Incoming:
                    in_meshes.add(peer)
                else:
                    print('Error. Unknown conn direction', direction)
                    sys.exit(1)
        return list(out_meshes), list(in_meshes)


    def process_msgs(self, curr_r):
        if curr_r % self.heartbeat_period == 0:
            self.write_curr_mesh(curr_r, '')

        # TODO experimental, collectively update
        if self.update_method=='coll-subset' and curr_r > 0 and curr_r % self.heartbeat_period == 0:
            
            out_meshes, in_meshes = self.get_curr_mesh()
            subset, rand_peers = self.adaptor.update(curr_r, out_meshes, in_meshes, self.topic_peers)

            # distribute conns to topic actors
            if subset is not None:
                for topic, actor in self.actors.items():
                    peers = []
                    for n in list(subset)+rand_peers:
                        if n in self.topic_peers[topic]:
                            peers.append(n)

                    actor.update_new_conn(peers, curr_r)
            
            self.adaptor.reset()

        # if self.id == 6:
            # self.write_curr_mesh(curr_r, '')

        # print("node", self.id, "process_msgs", len(self.in_msgs))
        actor_msgs = defaultdict(list)
        while len(self.in_msgs) > 0:
            msg = self.in_msgs.pop(0)
            mtype, _, src, dst, _, _, payload, topic, send_r = msg

            if topic not in self.actors:
                print('Warning. Receive non-subscribing topic', topic, 'round', curr_r,
                        'node', self.id, 'my topics', self.topics, 'mtype', mtype, 'from', src)
                sys.exit(1)

            # update adaptor for every transaction
            if self.update_method=='coll-subset' and mtype == MessageType.TRANS and src in self.actors[topic].mesh:
                self.adaptor.add_time(msg, curr_r)

            actor_msgs[topic].append(msg)
        # print(self.id, actor_msgs)
        for topic in self.topics:
            actor = self.actors[topic]
            in_msgs = actor_msgs[topic]
            # print(self.id, topic, in_msgs)
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
    def __init__(self, role, u, interval, peers, heartbeat_period, topic, update_method):
        self.id = u # my id
        self.topic = topic
        self.role = role
        self.conn = set() # lazy push
        self.mesh = {} # mesh push

        self.peers = set(peers) # known peers
        self.out_msgs = [] # msg to push in the next round
        # self.in_msgs = []
        self.D_scores = 2 #
        self.scores = {} # all peer score, key is peer, value is PeerScoreCounter
        self.seqno = 0
        self.D = OVERLAY_D # curr in local mesh degree: incoming + outgoing
        self.D_out = 2 # num outgoing connections in the mesh; D_out < OVERLAY_DLO and D_out < D/2

        self.init_peers_scores()

        if interval == 0:
            self.gen_prob = 0
        else:
            intervals_per_trans = float(interval) / float(SEC_PER_ROUND) /2
            self.gen_prob = 1/intervals_per_trans  # per round 

        self.msg_ids = set()
        self.heartbeat_period = heartbeat_period
        self.gen_trans_num = 0

        self.round_trans_ids = {} # keep track of msgs used for analysis
        self.trans_record = {}  # key is trans_id, value is (recv r, send r) send_r is the first born time
        self.last_heartbeat = -1
        self.update_method = update_method

    def run_scores_background(self, curr_r):
        for u, counters in self.scores.items():
            counters.run_background(curr_r)

    def update_new_conn(self, new_conns, r):
        # print("node", self.id, "update new conns", new_conns, 'from', self.mesh)
        mesh = self.mesh.copy()
        for n in mesh:
            if n not in new_conns:
                if self.id == 6:
                    print('round', r, 'node', 6, 'prune', n)
                self.prune_peer(n, r)

        for n in new_conns:
            if n not in mesh:
                self.graft_peer(n, r)
        

    # worker func 
    def process_msgs(self, msgs, r):
        # schedule heartbeat 
        if self.update_method == 'individual':
            self.schedule_heartbeat(r)
        # background peer local view update
        self.run_scores_background(r)
        self.round_trans_ids.clear()
        in_msgs = msgs.copy()
        # handle msgs 
        while len(in_msgs) > 0:
            msg = in_msgs.pop(0)
            mtype, _, src, dst, _, _, payload, topic, send_r = msg
            assert self.id == dst
            if mtype == MessageType.GRAFT:
                self.proc_GRAFT(msg, r)
            elif mtype == MessageType.PRUNE:
                self.proc_PRUNE(msg, r)
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
                # if self.id == 0 or self.id == 1 or self.id == 68:
                    # print(self.id, 'recv trans', payload, 'from', src)
                # print(self.id, "proc_TRANS", msg)
                self.proc_TRANS(msg, r)
            else:
                self.scores[src].update_p4() # Invalid msgs
        
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
            trans_id = TransId(self.id, self.gen_trans_num)
            # DEBUG
            # print('***** at epoch {r:<5}: node {node_id:>5} create a {topic:>5} msg *******'.format( 
                # r=r, node_id=self.id, topic=self.topic))
            for peer in self.mesh:
                msg = self.gen_msg(MessageType.TRANS, peer, TRANS_MSG_LEN, trans_id, r)
                # print(self.id, 'generate trans', trans_id, 'to', peer)
                self.out_msgs.append(msg)

    def proc_TRANS(self, msg, r):
        _, mid, src, _, _, _, trans_id, topic, send_r = msg
        # print('node', self.id, src)
        # print(self.mesh)
        # in case the peer has not been accepted by the mesh, but relay msg
        if src not in self.mesh:
            # print('Warning. In graph/Actor proc_TRANS. src not from mesh.', 
                    # "At round", r,
                    # '. Node', self.id, 'src',src, 'my-mesh', list(self.mesh.keys()),
                    # '. Topic', topic, 'my-topic', self.topic, 'payload', trans_id)
            return 

        self.scores[src].add_msg_delivery()

        # if not seen msg before
        # if mid not in self.msg_ids:

        if trans_id not in self.trans_record:
            self.msg_ids.add(mid)
            self.scores[src].update_p2()
            self.round_trans_ids[trans_id] = (r, send_r)
            # push it to other peers in mesh if not encountered
            for peer in self.mesh:
                if peer != src:
                    msg = self.gen_msg(MessageType.TRANS, peer, TRANS_MSG_LEN, trans_id, send_r)
                    # DEBUG
                    # print('at epoch {r:<5}: node {node_id:>5} forward a {topic:>5} msg msg born at {send_r}'.format(r=r, node_id=self.id, topic=self.topic, send_r=send_r))
                    # print(self.id, 'forward', self.topic, trans_id, 'to', peer)
                    self.out_msgs.append(msg)
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
        # print("proc_Heartbeat")
        nodes = self.get_rand_gossip_nodes()
        mesh_peers = []
        # prune neg mesh
        all_mesh_peers = self.mesh.keys()
        for u in list(all_mesh_peers):
            counters = self.scores[u]
            score = counters.get_score()
            if score < 0:
                counters.update_p3b(-score)
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
    def proc_PRUNE(self, msg, r):
        _, _, src, _, _, _, _, _, _ = msg
        # print('round', r, 'node', self.id, 'rejected by', src)
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
            # print('node', self.id, 'reject graft from',src)
            msg = self.gen_msg(MessageType.PRUNE, src, CTRL_MSG_LEN, None, r)
            self.out_msgs.append(msg)
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
        # scores_value = {} # key is peer

        # scores_decompose = {}
        # for peer in self.scores:
            # scores_value[peer] = self.scores[peer].get_score()
            # counters = self.scores[peer]
            # s = ScoreRecord(
                # round(counters.get_score1(), 2),
                # round(counters.get_score2(), 2),
                # round(counters.get_score3a(), 2),
                # round(counters.get_score3b(), 2),
                # round(counters.get_score4(), 2),
                # round(counters.get_score5(), 2),
                # round(counters.get_score6(), 2),
            # )
            # scores_decompose[peer] = s

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
                # scores_value, 
                # scores_decompose,
                # self.trans_record.copy(), 
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
