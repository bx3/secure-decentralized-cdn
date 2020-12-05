#!/usr/bin/env python
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import xlsxwriter 
from collections import defaultdict
from config import *
from messages import Direction

def get_degrees(snapshots):
    # get the mean/max/min degrees of all nodes in all snapshots
    degrees = []
    for snapshot in snapshots:
        degree = []
        for u in snapshot.nodes:
            node_state = snapshot.nodes[u]
            degree.append(len(node_state.mesh))
        degrees.append(degree)

    # degree changes
    degrees_mean = []
    degrees_max = []
    degrees_min = []
    for i in range(len(degrees)):
        degree = degrees[i]
        degrees_mean.append(sum(degree) / len(degree))
        degrees_max.append(max(degree))
        degrees_min.append(min(degree))

    return degrees_mean, degrees_max, degrees_min

class DisjointSet(object):
    def __init__(self):
        self.parent = None

    def find(self):
        if self.parent is None: return self
        return self.parent.find()

    def union(self, other):
        them = other.find()
        us = self.find()
        if them != us:
            us.parent = them

def count_components(nodes):
    sets = {}
    honest_sets = {}
    for u in nodes:
        node = nodes[u]
        sets[u] = DisjointSet()
        if node.role != NodeType.SYBIL:
            honest_sets[u] = DisjointSet()
    # Get the number of component
    for u in nodes:
        node = nodes[u]
        for vtx in node.mesh:
            sets[u].union(sets[vtx])
            if node.role != NodeType.SYBIL and nodes[vtx].role != NodeType.SYBIL: 
                honest_sets[u].union(honest_sets[vtx])
    component = len(set(x.find() for x in sets.values()))
    honest_component = len(set(x.find() for x in honest_sets.values()))
    return component, honest_component

def get_components(snapshots):
    # get the number of components and honest components of all snapshots
    components = []
    honest_components = []
    for snapshot in snapshots:
        all_nodes = snapshot.nodes.copy()
        all_nodes.update(snapshot.sybils)
        component, honest_component = count_components(all_nodes)
        components.append(component)
        honest_components.append(honest_component)

    return components, honest_components


def handle_single_state(trans_recv, reached90_transid, state, node_id):
    trans_ids = state.transids
    for trans_id in trans_ids: 
        if trans_id not in reached90_transid:
            if trans_id in trans_recv:
                trans_recv[trans_id].add(node_id)
            else:
                trans_recv[trans_id] = set()
                trans_recv[trans_id].add(node_id)


def get_num_honest(snapshot):
    num_honest = 0
    for u, node in snapshot.nodes.items():
        if node.role == NodeType.PUB or node.role == NodeType.LURK:
            num_honest += 1

    return num_honest


def analyze_eclipse(snapshots, target):
    history_in = []
    history_out = []
    for snapshot in snapshots:
        nodes = snapshot.nodes
        sybils = snapshot.sybils
        mesh = nodes[target].mesh
        num_in = 0
        num_out = 0
        for peer, direction in mesh.items():
            if peer in nodes and direction == Direction.Incoming:
                num_in += 1
            elif peer in nodes and direction == Direction.Outgoing:
                num_out += 1

        history_in.append(num_in)
        history_out.append(num_out)
    return history_in, history_out

def throughput_90(snapshots):
    reached90_transid = set()
    trans_recv = {} # key is trans id, value is a group of receiving nodes
    acc_recv_msg_hist = [] # acc for accumulative
    acc_gen_msg_hist =[] 
    num_honest_node = get_num_honest(snapshots[-1])

    for r in range(len(snapshots)):
        # consider only honest node
        nodes = snapshots[r].nodes
        net = snapshots[r].network
        trans_nodes = defaultdict(set)
        acc_gen_msg = 0

        for u, state in nodes.items():
            for tid in state.trans_set: 
                trans_nodes[tid].add(u)
            acc_gen_msg += state.gen_trans_num

        num_90_msg = 0
        for tid, n in trans_nodes.items():
            if len(n) > 0.9 * num_honest_node:
                num_90_msg += 1

        acc_recv_msg_hist.append(num_90_msg)
        acc_gen_msg_hist.append(acc_gen_msg)




    return acc_recv_msg_hist, acc_gen_msg_hist

def latency(acc_recv_msg_hist, acc_gen_msg_hist):
    assert len(acc_recv_msg_hist) == len(acc_gen_msg_hist)
    latency_hist = []
    for r, acc_recv_msg in enumerate(acc_recv_msg_hist):
        if (acc_recv_msg == 0):
            latency_hist.append(0)
        else:
            if old_recv_msg == acc_recv_msg:
                latency_hist.append(latency_hist[-1])
            else:
                for i in range(r+1):
                    if acc_gen_msg_hist[i] >= acc_recv_msg:
                        latency = r - i
                        latency_hist.append(latency)
                        break
        old_recv_msg = acc_recv_msg
    assert len(latency_hist) == len(acc_recv_msg_hist), "length of latency_hist: {}".format(len(latency_hist))
    return latency_hist

def avg_throughput(acc_recv_msg_hist, avg_step=10):
    avg_throughput_hist = []
    for i in range(avg_step-1):
        avg_throughput_hist.append(0)
    for r_end in range(avg_step-1, len(acc_recv_msg_hist)):
        r_start = r_end - avg_step + 1
        avg_throughput = (acc_recv_msg_hist[r_end]-acc_recv_msg_hist[r_start]) / avg_step
        avg_throughput_hist.append(avg_throughput)
    return avg_throughput_hist

def dump_node(snapshots, node_id):
    workbook = xlsxwriter.Workbook('node{}.xlsx'.format(node_id)) 
    worksheet = workbook.add_worksheet()
    bold = workbook.add_format({'bold': True})
    red = workbook.add_format({'font_color': 'red'})

    worksheet.write(0, 0, 'Round', bold)
    peers = {}
    for snapshot in snapshots:
        node = snapshot.nodes[node_id]
        out_conn = node.out_conn
        out = ''
        r = snapshot.round
        worksheet.write(r+1, 0, str(r))
        nodes = snapshot.nodes.copy()
        nodes.update(snapshot.sybils)
        for s in node.scores:
            if s not in peers:
                peers[s] = len(peers) + 1
                peer = nodes[s] 
                if peer in out_conn:
                    out = ' out'
                else:
                    out =  ''
                if peer.role == NodeType.PUB: 
                    worksheet.write(0, peers[s], str(s)+' (PUB)' + out, bold)
                if peer.role == NodeType.LURK: 
                    worksheet.write(0, peers[s], str(s)+' (LURK)'+ out, bold)
                if peer.role == NodeType.SYBIL: 
                    worksheet.write(0, peers[s], str(s)+' (SYBIL)', bold)
            if s in node.mesh:
                worksheet.write(r+1, peers[s], node.scores[s], red)
            else:
                worksheet.write(r+1, peers[s], node.scores[s])
    workbook.close()

def dump_graph(snapshot):
    # dump the graph state of a snapshot to a file
    r = snapshot.round
    file_name = "graph_round{}.txt".format(r)
    f = open(file_name, "w")
    for u in snapshot.nodes:
        node = snapshot.nodes[u]
        f.write(str(u))
        if node.role == NodeType.PUB: 
            f.write(' PUB')
        if node.role == NodeType.LURK: 
            f.write(' LURK')
        if node.role == NodeType.SYBIL: 
            f.write(' SYBIL')
        f.write('\n')
        f.write('mesh: ')
        for m in node.mesh:
            f.write(str(m)+',')
        f.write('\n')
        f.write('peers: ')
        for p in node.peers:
            f.write(str(p)+',')
        f.write('\n')
        f.write('socres: ')
        for s in node.scores:
            f.write('{}({}),'.format(s, node.scores[s]))
        f.write('\n')
    f.close()

def analyze_network(snapshots):
    # for i, snapshot in enumerate(snapshots):
        # nodes = snapshot.nodes
        # # print('snapshot', i)
        # for u, state in nodes.items():
            # print('round', i, 'node', u, 'num msg', len(state.trans_set))
    for r in range(len(snapshots)):
        nodes = snapshots[r].nodes
        net = snapshots[r].network
        trans_nodes = defaultdict(set)
        
        for u, node in nodes.items():
            for tid in node.trans_set: 
                trans_nodes[tid].add(u)
        num_90_msg = 0
        for tid, nodes in trans_nodes.items():
            if len(nodes) > 0.9 * len(nodes):
                num_90_msg += 1


def analyze_snapshot(snapshots):
    degrees_mean, degrees_max, degrees_min = get_degrees(snapshots)
    components, honest_components = get_components(snapshots)
    acc_recv_msg_hist, acc_gen_msg_hist = throughput_90(snapshots)
    latency_hist = latency(acc_recv_msg_hist, acc_gen_msg_hist)
    avg_throughput_hist = avg_throughput(acc_recv_msg_hist, 20)
    avg_gen_hist = avg_throughput(acc_gen_msg_hist, 20)

    fig, axs = plt.subplots(2)
    
    axs[0].plot(degrees_mean, 'b', degrees_max, 'r', degrees_min, 'g')
    axs[0].set(ylabel='node degree')
    max_patch = mpatches.Patch(color='red', label='max')
    min_patch = mpatches.Patch(color='green', label='min')
    mean_patch = mpatches.Patch(color='blue', label='mean')
    axs[0].legend(handles=[max_patch,min_patch,mean_patch])
    # axs[0].title.set_text("no score")   
    
    target = 1
    eclipse_hist_in, eclipse_hist_out = analyze_eclipse(snapshots, target)
    
    # number of connectted component
    x_points = [ i for i in range(len(degrees_mean))]
    #axs[1].set_yscale('log')
    axs[1].plot(x_points, eclipse_hist_in, color='green')
    axs[1].plot(x_points, eclipse_hist_out, color='blue')
    axs[1].set(ylabel='target node - num honest mesh node', xlabel='round')
    in_conn = mpatches.Patch(color='green', label='honest incoming connection')
    out_conn = mpatches.Patch(color='blue', label='honest outgoing connection')
    axs[1].legend(handles=[in_conn, out_conn])


    
    # axs[2].plot(x_points, honest_components)
    # axs[2].set(ylabel='# honest components', xlabel='round')

    # x_points = [ i for i in range(len(acc_recv_msg_hist))]
    # axs[3].plot(x_points, acc_recv_msg_hist)
    # # axs[3].plot(x_points, acc_gen_msg_hist)
    # axs[3].set(ylabel='# 90trans', xlabel='round')

    # axs[4].plot(x_points, avg_throughput_hist)
    # axs[4].plot(x_points, avg_gen_hist)
    # axs[4].set(ylabel='avg T', xlabel='round')

    # axs[5].plot(x_points, latency_hist)
    # axs[5].set(ylabel='latency', xlabel='round')

    plt.show()
    # print(snapshots[-1].nodes[target].mesh)
    # print(snapshots[-1].nodes[target].out_conn)
    # dump_graph(snapshots[50])





    # for r, snapshot in enumerate(snapshots):
        # nodes = snapshot.nodes
        # num_nodes = len(nodes)
        # acc_gen_msg = 0
        # for u, state in nodes.items():
            # handle_single_state(trans_recv, reached90_transid, state, u)
            # acc_gen_msg += state.gen_trans_num

        # # count 
        # remove_tid = [] 
        # for trans_id, recv_grp in trans_recv.items():
            # # print(trans_id, len(recv_grp))
            # if len(recv_grp) > num_nodes * 0.9:
                # reached90_transid.add(trans_id)
                # remove_tid.append(trans_id)
        # # make sure no double count
        # for tid in remove_tid:
            # trans_recv.pop(tid, None)
        # acc_recv_msg_hist.append(len(reached90_transid))
        # acc_gen_msg_hist.append(acc_gen_msg)
