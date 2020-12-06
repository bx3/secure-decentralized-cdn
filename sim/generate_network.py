import json
import sys
import random
from config import NodeType
from config import MAX_BANDWIDTH 
from collections import namedtuple

NetBandwidth = namedtuple('NetBandwidth', ['up_bd', 'down_bd'])

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
    print(json_file)
    with open(json_file) as config:
        data = json.load(config)
        return data['nodes']

def get_rand_node(n):
    return random.randint(0, n-1)

def gen_random_peers(is_cold_boot, init_peer_num, my_id, num_honest, num_sybil):
    peers = set()
    while 1:
        if not is_cold_boot:
            v = get_rand_node(num_honest)
        else:
            v = get_rand_node(num_honest+ num_sybil)
        if v not in peers and v != my_id:
            peers.add(v)
            if len(peers) == init_peer_num:
                break
    return list(peers)

def generate_network(
        is_cold_boot, 
        init_peer_num, 
        n_pub, n_lurk, n_sybil, 
        down_mean, down_std, 
        up_mean, up_std,
        interval):
    nodes = []
    i = 0
    for _ in range(n_pub):
        downB = random.gauss(down_mean, down_std)
        upB = random.gauss(up_mean, up_std)
        peers = gen_random_peers(is_cold_boot, init_peer_num, i, n_pub+n_lurk, n_sybil)
        node = {
            "id": i,
            "role": 0, #NodeType.PUB,
            "known": peers,
            "downB": downB,
            "upB": upB,
            "interval": interval
        }
        nodes.append(node)
        i += 1
    
    # lurk
    for _ in range(n_lurk):
        downB = random.gauss(down_mean, down_std)
        upB = random.gauss(up_mean, up_std)
        peers = gen_random_peers(is_cold_boot, init_peer_num, i, n_pub+n_lurk, n_sybil)
        node = {
            "id": i,
            "role": 1, #NodeType.LURK,
            "known": peers,
            "downB": downB,
            "upB": upB,
            "interval": 0 
        }
        nodes.append(node)
        i += 1

    # sybil 
    all_peers = [i for i in range(n_pub+n_lurk+n_sybil)]
    for _ in range(n_sybil):
        known = all_peers.copy()
        known.remove(i)
        node = {
            "id": i,
            "role": 2, #NodeType.SYBIL,
            "known": known,
            "downB": MAX_BANDWIDTH,
            "upB": MAX_BANDWIDTH,
            "interval": 0 # manually attack
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
            "INTERVAL": interval
        }
    setup = {"summery": summery, "nodes": nodes}
    print(json.dumps(setup, indent=4))


        

    

