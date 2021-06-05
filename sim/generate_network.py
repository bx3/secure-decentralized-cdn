import json
import sys
import random
from config import NodeType
from config import MAX_BANDWIDTH 
from collections import namedtuple
from collections import defaultdict
import numpy as np
from numpy import linalg as LA
from enum import Enum

NetBandwidth = namedtuple('NetBandwidth', ['up_bd', 'down_bd'])
Point = namedtuple('Point', ['x', 'y'])

TopicSpec = namedtuple('TopicSpec', ['topic', 'cluster_spec', 'n_non_cluster']) 

TopicClusterSpec = namedtuple('TopicClusterSpec', 
        ['topic', 'n_pub', 'n_lurk', 'n_sybil', 'method'])

class TopicCluster:
    def __init__(self, topic, pubs, lurks, sybils):
        self.topic = topic
        self.pubs = pubs
        self.lurks = lurks
        self.sybils = sybils
    def get_nodes(self):
        return self.pubs + self.lurks + self.sybils

# list of nodes pubed/subscribed to topics
class TopicNodes:
    def __init__(self, topic, cluster, non_cluster):
        self.topic = topic
        self.cluster = cluster
        self.non_cluster = non_cluster 
    def get_all_nodes(self):
        return self.cluster.get_nodes() + self.non_cluster
    def get_cluster_nodes(self):
        return self.cluster.get_nodes()
    def get_non_cluster_nodes(self):
        return self.non_cluster
    def get_role(self, node_id):
        if node_id in self.cluster.pubs:
            return NodeType.PUB
        elif node_id in self.cluster.sybils:
            return NodeType.SYBIL
        elif node_id in self.cluster.lurks:
            return NodeType.LURK
        elif node_id in self.non_cluster:
            # non-cluster is assumed to be a lurk
            return NodeType.LURK
        else:
            return NodeType.IND


class Topic(str, Enum):
    EDU = 'EDU'
    COM = 'COM'
    GOV = 'GOV'
    BOOK = 'BOOK'
    NEWS = 'NEWS'
    MUSIC = 'MUSIC'
    SPORT = 'SPORT'

def get_topic_type(i):
    if i == 0 or i == 'EDU':
        return Topic.EDU
    elif i == 1 or i == 'COM':
        return Topic.COM
    elif i == 2 or i == 'GOV':
        return Topic.GOV
    elif i == 3 or i == 'BOOK':
        return Topic.BOOK
    elif i == 4 or i == 'NEWS':
        return Topic.NEWS
    elif i == 5 or i == 'MUSIC':
        return Topic.MUSIC
    elif i == 6 or i == 'SPORT':
        return Topic.SPORT
    else:
        print("Error. Unknown Topic")
        sys.exit(1)

def load_bandwidth(self, setup_json):
    nodes = parse_nodes(setup_json)
    netband = {}
    for u in nodes:
        if u.id not in self.netband:
            netband[u.id] = NetBandwidth(u.upB, u.downB)
        else:
            print('Error. Duplicate id in setup json')
            sys.exit(0)

def parse_summery(json_file):
    with open(json_file) as config:
        data = json.load(config)
        return data['summery']

def parse_nodes(json_file):
    with open(json_file) as config:
        data = json.load(config)
        return data['nodes']

def parse_real_data(json_file):
    with open(json_file) as config:
        data = json.load(config)
        summary = data['summery']
        return data['nodes'], summary['total_nodes'], summary['total_topics']


def get_rand_node(n):
    return random.randint(0, n-1)
def get_rand_choice(peers):
    return random.choice(peers)

def gen_random_peers(is_cold_boot, init_peer_num, my_id, num_honest, num_sybil, honest_node_topic):
    peers = set()
    sybils = [i for i in range(num_honest, num_honest+num_sybil)]
    while 1:
        if not is_cold_boot:
            v = get_rand_choice(honest_node_topic)
            # v = get_rand_node(num_honest)
        else:
            v = get_rand_choice(honest_node_topic+sybils)
            # v = get_rand_node(num_honest+ num_sybil)
        if v not in peers and v != my_id:
            peers.add(v)
            if len(peers) == init_peer_num:
                break
    return list(peers)

def get_surrounding_peers(i, topic, num_node, num_peer, twoD_points, node_topics):
    peers = []
    num_r = 10
    num_c = 10
    x = i %num_c
    y =  int(i/num_r)
    p = np.array([x,y])

    dis = [] 
    for j, point in twoD_points.items():
        if topic in node_topics[j]:
            dis.append((j, LA.norm(p - point)))

    sorted_dis = sorted(dis, key=lambda x: x[1])
    for k in range(1, num_peer+1):
        peers.append(sorted_dis[k][0])
    return peers

def gen_two_topic_network(
        is_cold_boot, 
        init_peer_num, 
        n_pub, n_lurk, n_sybil, 
        down_mean, down_std, 
        up_mean, up_std,
        interval, 
        num_topic, 
        length, 
        use_grid):

    nodes = []
    total_node = n_pub + n_lurk + n_sybil
    topic_honest_nodes = defaultdict(list)
    node_topics = defaultdict(list)
    points = {}
    twoD_points = {}
    for i in range(n_pub + n_lurk):
        if i < int(0.75*total_node):
            topic_honest_nodes[0].append(i)
            node_topics[i].append(0)
        if i >= int(0.25*total_node):
            topic_honest_nodes[1].append(i)
            node_topics[i].append(1)
    num_r = 10
    num_c = 10
    for i in range(total_node):
        x = i % num_c
        y = int(i / num_r)
        if use_grid:
            points[i] = (x*length/num_c,y*length/num_r)
            twoD_points[i] = np.array([x,y]) 
        else:
            points[i] = (random.randint(0, length), random.randint(0, length))

    i = 0

    # use_grid = False

    pub_per_topic = int(n_pub/num_topic) 
    # first topic
    for _ in range(pub_per_topic):
        downB = random.gauss(down_mean, down_std)
        upB = random.gauss(up_mean, up_std)
        topics = [0]
        x, y = points[i]
        topic_peers = {}
        for topic in topics:
            if not use_grid:
                peers = gen_random_peers(is_cold_boot, init_peer_num, i, n_pub+n_lurk, n_sybil, 
                        topic_honest_nodes[topic])
            else:
                peers = get_surrounding_peers(i, topic, n_pub+n_lurk, init_peer_num, twoD_points, node_topics)

            topic_peers[topic] = peers
        node = {
            "id": i,
            "role": 0, #NodeType.PUB,
            "known": topic_peers,
            "downB": downB,
            "upB": upB,
            "interval": interval,
            "topics": topics,
            "x": x,
            "y": y
        }
        nodes.append(node)
        i += 1
    # sec topic
    for j in range(pub_per_topic):
        downB = random.gauss(down_mean, down_std)
        upB = random.gauss(up_mean, up_std)
        topics = [1]
        x, y = points[i]
        topic_peers = {}
        node_id = total_node-1 - j
        for topic in topics:
            if not use_grid:
                peers = gen_random_peers(is_cold_boot, init_peer_num, i, n_pub+n_lurk, n_sybil, 
                    topic_honest_nodes[topic])
            else:
                peers = get_surrounding_peers(node_id, topic, n_pub+n_lurk, init_peer_num, twoD_points, node_topics)

            topic_peers[topic] = peers
        node = {
            "id": node_id,
            "role": 0, #NodeType.PUB,
            "known": topic_peers,
            "downB": downB,
            "upB": upB,
            "interval": interval,
            "topics": topics,
            "x": x,
            "y": y
        }
        nodes.append(node)

    for _ in range(n_lurk):
        downB = random.gauss(down_mean, down_std)
        upB = random.gauss(up_mean, up_std)
        topics = node_topics[i]
        x, y = points[i]
        topic_peers = {}
        for topic in topics:
            if not use_grid:
                peers = gen_random_peers(is_cold_boot, init_peer_num, i, n_pub+n_lurk, n_sybil,
                    topic_honest_nodes[topic])
            else:
                peers = get_surrounding_peers(i, topic, n_pub+n_lurk, init_peer_num, twoD_points, node_topics)

            topic_peers[topic]= peers
        node = {
            "id": i,
            "role": 1, #NodeType.LURK,
            "known": topic_peers,
            "downB": downB,
            "upB": upB,
            "interval": 0,
            "topics": topics,
            "x": x,
            "y": y

        }
        nodes.append(node)
        i += 1

    summery = {
            "PUB": n_pub, 
            "LURK": n_lurk, 
            "SYBIL": n_sybil,
            "COLD_BOOT": is_cold_boot, 
            "INIT_PEER_NUM": init_peer_num,
            "DOWN_MEAN": down_mean,
            "DOWN_STD": down_std,
            "UP_MEAN": up_mean,
            "UP_STD": up_std,
            "INTERVAL": interval,
            "NUM_TOPIC": num_topic,
            "POINT_RANGE": length
        }
    setup = {"summery": summery, "nodes": nodes}
    print(json.dumps(setup, indent=4))



def generate_network(
        is_cold_boot, 
        init_peer_num, 
        n_pub, n_lurk, n_sybil, 
        down_mean, down_std, 
        up_mean, up_std,
        interval, 
        num_topic, 
        length):

    topic_honest_nodes = defaultdict(list)
    for i in range(n_pub + n_lurk):
        topic_honest_nodes[i%num_topic].append(i)

    i = 0
    for _ in range(n_pub):
        downB = random.gauss(down_mean, down_std)
        upB = random.gauss(up_mean, up_std)
        topics = [i % num_topic]
        x, y = random.randint(0, length), random.randint(0, length)
        topic_peers = {}
        for topic in topics:
            peers = gen_random_peers(is_cold_boot, init_peer_num, i, n_pub+n_lurk, n_sybil, 
                    topic_honest_nodes[topic])
            topic_peers[topic] = peers
        node = {
            "id": i,
            "role": 0, #NodeType.PUB,
            "known": topic_peers,
            "downB": downB,
            "upB": upB,
            "interval": interval,
            "topics": topics,
            "x": x,
            "y": y
        }
        nodes.append(node)
        i += 1
    
    # lurk
    for _ in range(n_lurk):
        downB = random.gauss(down_mean, down_std)
        upB = random.gauss(up_mean, up_std)
        topics = [i % num_topic]
        x, y = random.randint(0, length), random.randint(0, length)
        topic_peers = {}
        for topic in topics:
            topic_peers[topic]= gen_random_peers(is_cold_boot, init_peer_num, i, n_pub+n_lurk, n_sybil,
                topic_honest_nodes[topic])
        node = {
            "id": i,
            "role": 1, #NodeType.LURK,
            "known": topic_peers,
            "downB": downB,
            "upB": upB,
            "interval": 0,
            "topics": topics,
            "x": x,
            "y": y

        }
        nodes.append(node)
        i += 1

    # sybil 
    all_peers = [i for i in range(n_pub+n_lurk+n_sybil)]
    for _ in range(n_sybil):
        known = all_peers.copy()
        known.remove(i)
        x, y = random.randint(0, length), random.randint(0, length)
        node = {
            "id": i,
            "role": 2, #NodeType.SYBIL,
            "known": known,
            "downB": MAX_BANDWIDTH,
            "upB": MAX_BANDWIDTH,
            "interval": 0, # manually attack
            "topic": -1,  # any topic
            "x": x,
            "y": y
        }
        nodes.append(node)
        i += 1

    summery = {
            "PUB": n_pub, 
            "LURK": n_lurk, 
            "SYBIL": n_sybil,
            "COLD_BOOT": is_cold_boot, 
            "INIT_PEER_NUM": init_peer_num,
            "DOWN_MEAN": down_mean,
            "DOWN_STD": down_std,
            "UP_MEAN": up_mean,
            "UP_STD": up_std,
            "INTERVAL": interval,
            "NUM_TOPIC": num_topic,
            "POINT_RANGE": length
        }
    setup = {"summery": summery, "nodes": nodes}
    print(json.dumps(setup, indent=4))



def sample_real_data(specs, data):
    topic_nodes = defaultdict(list) # key is topic, values are subscribing nodes
    node_topics = defaultdict(list) # key is id, values are subscribed topic 
    regions = {} # key is id, value is region
    points = {}  # key is id, value is x,y 

    for sample in data:
        node_id = int(sample['id'])
        topic_num = int(sample['topic']) # used default region to topic mapping
        topic = get_topic_type(topic_num)
        region = sample['region']
        la = float(sample['latitude'])
        lo = float(sample['longitude'])

        node_topics[node_id] = topic
        topic_nodes[topic].append(node_id) 
        points[node_id] = np.array([la, lo])
        regions[node_id] = region

    topics_cluster = {}
    
    for spec in specs:
        c_spec = spec.cluster_spec

        if c_spec.method == 'random':
            t = c_spec.topic
            nodes = topic_nodes[t].copy()
            np.random.shuffle(nodes)
            # gen pub
            pubs = nodes[:c_spec.n_pub]
            # gen lurk
            nodes = nodes[c_spec.n_pub:]
            lurks = nodes[:c_spec.n_lurk]
            # gen sybil
            nodes = nodes[c_spec.n_lurk:]
            sybils = nodes[:c_spec.n_sybil]
            topics_cluster[t] = TopicCluster(t, pubs, lurks, sybils)
        else:
            print('Unknown spec method', c_spec.method)
            sys.exit(1)

    return topics_cluster, node_topics, regions, points

# takes nodes in topics and created multi-topic and known peer relation
def mix_nodes(specs, topics_cluster):
    nodes = []
    for topic, cluster in topics_cluster.items():
        nodes += cluster.pubs + cluster.lurks + cluster.sybils
    assert(len(set(nodes)) == len(nodes))
    topics_nodes = {}
    nodes_topics = defaultdict(list)
    for spec in specs:
        tc = topics_cluster[spec.topic]
        cluster_nodes = tc.get_nodes()
        other_nodes = list(set(nodes).difference(set(cluster_nodes)))
        np.random.shuffle(other_nodes)
        non_cluster_nodes = other_nodes[:spec.n_non_cluster] 

        tn = TopicNodes(topic, tc, non_cluster_nodes) 
        topics_nodes[spec.topic] = tn 
        
        for n in cluster_nodes:
            nodes_topics[n].append(spec.topic)
        for n in non_cluster_nodes:
            nodes_topics[n].append(spec.topic)

    return topics_nodes, nodes_topics, nodes


def dump_specs(specs):
    out_specs = []
    for spec in specs:
        cp = spec.cluster_spec
        cluster_spec = {
                'topic': spec.topic, 
                'n_pub': cp.n_pub, 
                'n_lurk': cp.n_lurk, 
                'n_sybil': cp.n_sybil, 
                'method': cp.method
                }

        out_spec = {
                'topic': spec.topic,
                'cluster_spec': cluster_spec,
                'n_non_cluster': spec.n_non_cluster
                }
        out_specs.append(out_spec)
    print(json.dumps(out_specs, indent=4))


def load_specs(json_file):
    specs = []
    with open(json_file) as specs_json:
        data = json.load(specs_json)
        for spec_json in data:
            topic = get_topic_type(spec_json['topic'])
            cs = spec_json['cluster_spec']
            ns = spec_json['n_non_cluster']

            n_pub = cs['n_pub']
            n_lurk = cs['n_lurk']
            n_sybil = cs['n_sybil']
            method = cs['method']


            topic_cluster_spec = TopicClusterSpec(topic, n_pub, n_lurk, n_sybil, method)
            topic_spec = TopicSpec(topic, topic_cluster_spec, ns)
            specs.append(topic_spec)
    return specs  

def gen_specs(num_topic, n_pub_per_topic, n_lurk_per_topic, n_sybil_per_topic, n_non_cluster):
    specs = []
    for i in range(num_topic):
        topic = get_topic_type(i)
        topic_cluster_spec = TopicClusterSpec(
            topic, n_pub_per_topic, n_lurk_per_topic, n_sybil_per_topic, 'random')
        topic_spec = TopicSpec(topic, topic_cluster_spec, n_non_cluster)
        specs.append(topic_spec)
    dump_specs(specs)

def gen_real_data_network(
        is_cold_boot, 
        init_peer_num, 
        specs_json, 
        down_mean, down_std, 
        up_mean, up_std,
        interval, 
        geocluster_file):
    real_data, data_num_nodes, data_num_topic = parse_real_data(geocluster_file)

    specs = load_specs(specs_json)
    num_topic = len(specs)
    topics_cluster, real_node_topics, real_regions, real_points = sample_real_data(
            specs, real_data)
    topics_nodes, nodes_topics, selected_nodes = mix_nodes(specs, topics_cluster)
    num_node = len(nodes_topics)
    # print('topics_nodes', topics_nodes)
    # print('nodes_topics', nodes_topics)
    out_nodes = []

    i = 0
    nodeId_outId_map = {}
    for node_id in selected_nodes:
        nodeId_outId_map[node_id] = i
        i += 1

    for node_id in selected_nodes:
        topics = nodes_topics[node_id]
        topic_role = {}
        for topic in topics:
            tn = topics_nodes[topic]
            topic_role[topic] = tn.get_role(node_id)

        topic_peers = {}
        for topic in topics:
            nodes = topics_nodes[topic].get_all_nodes() 
            nodes.remove(node_id)
            np.random.shuffle(nodes)
            selected_init_peers = nodes[:init_peer_num]
            topic_peers[topic] = [nodeId_outId_map[j] for j in selected_init_peers]

        downB = random.gauss(down_mean, down_std)
        upB = random.gauss(up_mean, up_std)
        x, y = real_points[node_id]

        node = {
            "id": nodeId_outId_map[node_id],
            "roles": topic_role, #NodeType.PUB,
            "known": topic_peers,
            "downB": downB,
            "upB": upB,
            "interval": interval,
            "topics": topics,
            "x": x,
            "y": y
        }
        out_nodes.append(node)

    topics_nodes_summary = {}
    num_node_check = set() 
    topics =  []
    for topic, tn in topics_nodes.items():
        topics.append(topic)
        nodes = tn.get_all_nodes()
        num_node_check = num_node_check.union(set(nodes))
        topics_nodes_summary[topic] = [nodeId_outId_map[j] for j in nodes]
    assert(len(num_node_check) == len(nodeId_outId_map))


    summery = {
            "NUM_NODE": len(nodeId_outId_map),
            "COLD_BOOT": is_cold_boot, 
            "INIT_PEER_NUM": init_peer_num,
            "DOWN_MEAN": down_mean,
            "DOWN_STD": down_std,
            "UP_MEAN": up_mean,
            "UP_STD": up_std,
            "INTERVAL": interval,
            "NUM_TOPIC": num_topic,
            "TOPICS": topics,
            "topics_nodes": topics_nodes_summary,
            "spec": specs
        }
    setup = {"summery": summery, "nodes": out_nodes}
    print(json.dumps(setup, indent=4))

    

