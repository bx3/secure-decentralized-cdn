from sim.graph import *
from sim.network import Network
from sim.messages import *
from sim.config import *
from sim.graph import State
from sim.sybil import Sybil
import sim.generate_network as gn
import sim.attacks as attacks
import json
import sys
import time
import threading
import time


class Snapshot:
    def __init__(self):
        self.round = 0
        self.nodes = {}  # key: node id; value: node state from node.get_states()
        self.sybils = {}
        self.all_nodes = {}
        self.network = None  # message queue in for each node

    def __repr__(self):
        # print("round", self.round)
        # print("nodes: ")
        # for node_id, node_state in self.nodes.items():
        #     print("\t node_id:", node_id)
        #     for topic, state in node_state.items():
        #         print("\t topic:", topic)
        #         print("\t state:", state)
        #     print()
        #
        # # print("sybils", self.sybils)
        # # print("all_nodes", self.all_nodes)
        # # print("network", self.network)
        # print()
        return ""


class Experiment:
    def __init__(self, setup_json, heartbeat, update_method):
        self.snapshots = []
        self.nodes = {}  # honest nodes
        self.sybils = {}
        self.all_nodes = {}

        # sets up net with all nodes' bandwidth, coordinates and links
        self.network = Network(setup_json)
        # .2 sec
        self.heartbeat_period = heartbeat

        # log file
        self.log_file = 'data/log'
        self.update_method = update_method

        # load both nodes and sybil nodes
        self.load_nodes(setup_json)  # get each node's info and put it in self.nodes
        self.setup_mesh()

        self.adversary = attacks.Adversary(self.sybils)

        # eclipse attack
        self.target = -1

        with open(self.log_file, 'w') as w:
            w.write("num_node" + str(len(self.nodes)) + '\n')

        # self.temp_curr_r = 0

    # # # # # # # # 
    #  main loop  #
    # # # # # # # # 
    def start(self, epoch, start_round=0, attack_strategy='None', targets=[]):
        total_take_snapshot_time = 0
        total_honest_handle_time = 0
        total_push_honest_msgs = 0
        total_deliver_msgs = 0
        """
        # initialize how many nodes to process per thread
        from math import ceil
        number_of_chunks = 2
        chunk_size = ceil(len(self.nodes) / number_of_chunks)
        nodes = list(self.nodes.values())

        # initialize thread
        all_threads = [None] * len(self.nodes)
        for j in range(len(self.nodes)):
            threads = [None] * number_of_chunks
            for i in range(number_of_chunks):
                chunk = nodes[i * chunk_size:(i + 1) * chunk_size]
                t = threading.Thread(target=self.honest_nodes_handle_msgs_chunks_self_temp_r, args=[chunk])
                threads[i] = t

            all_threads[j] = threads
        """

        # curr_shots = [None] * len(range(start_round, start_round+epoch))
        curr_shots = []
        i = 0
        for r in range(start_round, start_round+epoch):
            # debug
            if r % HEARTBEAT == 0:
                print("****\t\theartbeat generated", r, HEARTBEAT)

            # start attack
            # self.attack_management(r, self.network, targets)

            # network store messages from honest nodes
            # self.push_sybil_msgs(r)
            t1 = time.time()
            self.push_honest_msgs(r)  # push msg into net
            t2 = time.time()
            total_push_honest_msgs += t2 - t1

            # print("self.push_honest_msgs time: ", t2 - t1)

            # if r > 0:
            #    self.attack_freeze_network(r)

            # network deliver msgs
            t1 = time.time()
            self.deliver_msgs(r)
            t2 = time.time()
            total_deliver_msgs += t2 - t1
            # print("self.deliver_msgs time: ", t2 - t1)

            # honest node retrieve msgs
            t1 = time.time()
            self.honest_nodes_handle_msgs(r)
            # self.honest_nodes_handle_msgs_multi_processing(r)
            """
            self.temp_curr_r = r
            self.honest_nodes_handle_msgs_initialized_multi_processing(all_threads[r])
            """
            t2 = time.time()
            print("self.honest_nodes_handle_msgs time: ", t2 - t1)
            total_honest_handle_time += t2 - t1
            # self.sybil_nodes_handle_msgs(r)

            # assume sybils have powerful internal network, node processing speed
            # self.sybil_use_fast_internet(r)

            # take snapshot
            start = time.time()
            curr_shots.append(self.take_snapshot(r))  # look at network state for each iter
            # curr_shots[i] = self.take_snapshot(r)
            # i += 1
            # print("round", r, "finish using ", time.time()-start)
            total_take_snapshot_time += time.time() - start
            print("take snapshot", time.time() - start)

        print("total_push_honest_msgs", total_push_honest_msgs)
        print("total_deliver_msgs", total_deliver_msgs)
        print("total_honest_handle_time", total_honest_handle_time)
        print("total_take_snapshot_time", total_take_snapshot_time)

        return curr_shots

    def push_sybil_msgs(self, r):
        for u, node in self.sybils.items():
            # if network has too many messages, stop
            msgs = node.send_msgs() 
            self.network.push_msgs(msgs, r)

    # honest nodes push msg to network
    def push_honest_msgs(self, curr_r):  # curr_r is an int between [0, epoch)
        for u, node in self.nodes.items():  # u = node id, node = node and its state
            # if network has too many messages, stop
            # if not self.network.is_uplink_congested(u):

            msgs = node.send_msgs()

            self.network.push_msgs(msgs, curr_r)

    def attack_management(self, r, network, targets):
        self.adversary.add_targets(targets)  # some hack
        adv_msgs = []
        if r > 0: 
            adv_msgs = self.adversary.eclipse_target(r, self.snapshots, self.network) 
        self.network.push_msgs(adv_msgs, r)

    def attack_freeze_network(self, r):
        if r > 0:
            self.adversary.handle_freeze_requests(r, self.snapshots[-1], self.network)
                 
    def deliver_msgs(self, curr_r):
        num_delivered_msg = 0
        # t1 = time.time()
        # updates where msgs are in terms of sending (ex: have elapsed time reached over prop_delay)
        dst_msgs = self.network.update(True)
        # t2 = time.time()
        # print(" self.network.update time: ", (t2 - t1) * 1e6)

        # print("dst_msgs", dst_msgs)
        for dst, msgs in dst_msgs.items():
            # honest 
            if dst in self.nodes:
                # print("\n\ncurr_r", curr_r)
                # once msgs have prop to dest, insert into dest node's in_msg list
                self.nodes[dst].insert_msg_buff(msgs)
            else:
                self.sybils[dst].insert_msg_buff(msgs)
            num_delivered_msg += len(msgs)

    def all_nodes_handle_msgs(self, curr_r):
        # print("all_nodes_handle_msgs")
        # node process messages
        for u, node in self.nodes.items():
            if node.role != NodeType.SYBIL:
                node.process_msgs(curr_r)
            else:
                node.process_msgs(curr_r)

    def honest_nodes_handle_msgs_multi_processing(self, curr_r):
        """
        from concurrent import futures
        from math import ceil
        number_of_chunks = 2
        chunk_size = ceil(len(self.nodes) / number_of_chunks)
        nodes = list(self.nodes.values())

        with futures.ThreadPoolExecutor() as executor:
            # for i in range(number_of_chunks):
            #     chunk = nodes[i * chunk_size:(i + 1) * chunk_size]
            #     executor.submit(self.honest_nodes_handle_msgs_chunks, chunk, curr_r)
            #     # !!!!! make sure executor.submit is running in parallel !!!!!!
            i = 0
            while i < number_of_chunks:
                chunk = nodes[i * chunk_size:(i + 1) * chunk_size]
                executor.submit(self.honest_nodes_handle_msgs_chunks, chunk, curr_r)
                i += 1
        """

        """
        threads = [None] * number_of_chunks
        for i in range(number_of_chunks):
            chunk = nodes[i * chunk_size:(i + 1) * chunk_size]
            t = threading.Thread(target=self.honest_nodes_handle_msgs_chunks, args=[chunk, curr_r])
            t.start()
            threads[i] = t

        for thread in threads:
            thread.join()
        """

        """
        from multiprocessing import Pool, cpu_count
        from itertools import repeat
        cpus = cpu_count()
        nodes = list(self.nodes.values())
        with Pool(processes=3) as pool:  # using default 1 process per cpu, reduce

            # if it makes machine run too slow
            pool.starmap(self.honest_node_handle_msgs, zip(nodes, repeat(curr_r)))
        """

        """
        from multiprocessing import Pool, cpu_count
        from math import ceil
        from itertools import repeat
        cpus = cpu_count()
        chunk_size = ceil(len(self.nodes) / cpus)
        nodes = list(self.nodes.values())

        chunks = [None] * cpus
        i = 0
        while i < cpus:
            chunk = nodes[i * chunk_size:(i + 1) * chunk_size]
            chunks[i] = chunk
            i += 1

        with Pool(processes=cpus) as pool:  # using default 1 process per cpu, reduce

            # if it makes machine run too slow
            pool.starmap(self.honest_nodes_handle_msgs_chunks, zip(chunks, repeat(curr_r)))
        """

        from multiprocessing.pool import ThreadPool
        from multiprocessing import cpu_count
        from itertools import repeat
        nodes = list(self.nodes.values())
        with ThreadPool(processes=2) as pool:  # using default 1 process per cpu, reduce

            # if it makes machine run too slow
            pool.starmap(self.honest_node_handle_msgs, zip(nodes, repeat(curr_r)))


    @staticmethod
    def honest_node_handle_msgs(node, curr_r):
        # print("thread: ", threading.current_thread())

        node.process_msgs(curr_r)

    @staticmethod
    def honest_nodes_handle_msgs_chunks(nodes, curr_r):
        print("thread: ", threading.current_thread())
        for node in nodes:
            # TODO assume all are honest
            # if node.role != NodeType.SYBIL:

            # generates out_msgs if random.random() < self.gen_prob and nodes' role is a publisher
            node.process_msgs(curr_r)

    def honest_nodes_handle_msgs_initialized_multi_processing(self, threads):
        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

    def honest_nodes_handle_msgs_chunks_self_temp_r(self, nodes):
        print("thread: ", threading.current_thread())
        for node in nodes:
            # TODO assume all are honest
            # if node.role != NodeType.SYBIL:

            # generates out_msgs if random.random() < self.gen_prob and nodes' role is a publisher
            node.process_msgs(self.temp_curr_r)

    def honest_nodes_handle_msgs(self, curr_r):
        for u, node in self.nodes.items():
            # TODO assume all are honest
            # if node.role != NodeType.SYBIL:

            # generates out_msgs if random.random() < self.gen_prob and nodes' role is a publisher
            node.process_msgs(curr_r)

    def sybil_nodes_handle_msgs(self, curr_r):
        self.adversary.handle_msgs(curr_r)

    def sybil_use_fast_internet(self, curr_r):
        self.adversary.sybil_nodes_redistribute_msgs(curr_r)

    def take_snapshot(self, r):

        snapshot = Snapshot()
        snapshot.round = r
        # get all node states
        t1 = time.time()

        for u, node in self.nodes.items():
            snapshot.nodes[u] = node.get_states()
        t2 = time.time()
        print("     self.network.take_snapshot for loops time: ", t2 - t1)

        for u, sybil in self.sybils.items():
            snapshot.sybils[u] = sybil.get_states()

        snapshot.all_nodes = {**snapshot.nodes, **snapshot.sybils}
        # get network
        snapshot.network = self.network.take_snapshot()
        
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

    # modified sybils node does not get in mesh, if system is warm
    def setup_mesh(self):
        # self.all_nodes = {**(self.nodes), **(self.sybils)}
        mesh = {}  # key is node, value is mesh nodes
        # num_conn_1 = 0
        for u, node in self.nodes.items():
            for topic, actor in node.actors.items():
                num_out = int(OVERLAY_D / 2)
                known_peers = actor.peers.copy()
                known_peers = list(known_peers)
                random.shuffle(known_peers)
                chosen = known_peers[:num_out]  # chooses first num_out peers
                for v in chosen:  # v = u = node id
                    # if v == 1:
                    #    num_conn_1 += 1
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
