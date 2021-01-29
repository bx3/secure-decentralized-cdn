#!/usr/bin/env python
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import networkx as nx
# import xlsxwriter 
from collections import defaultdict
from config import *
from messages import Direction
from messages import MessageType
import numpy as np
import sys

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

def count_components(nodes, topic):
    sets = {}
    honest_sets = {}
    actors = {}
    for u, node in nodes.items():
        if topic in node:
            actors[u] = node[topic]

    for u in actors:
        actor = actors[u]
        sets[u] = DisjointSet()
        if actor.role != NodeType.SYBIL:
            honest_sets[u] = DisjointSet()
    # Get the number of component
    for u in actors:
        actor = actors[u]
        for vtx in actor.mesh:
            sets[u].union(sets[vtx])
            if actor.role != NodeType.SYBIL and actors[vtx].role != NodeType.SYBIL: 
                honest_sets[u].union(honest_sets[vtx])
    component = len(set(x.find() for x in sets.values()))
    honest_component = len(set(x.find() for x in honest_sets.values()))
    return component, honest_component

def get_components(snapshots, topic):
    # get the number of components and honest components of all snapshots
    components = []
    honest_components = []
    for snapshot in snapshots:
        all_nodes = snapshot.nodes.copy()
        all_nodes.update(snapshot.sybils)
        component, honest_component = count_components(all_nodes, topic)
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


def get_num_honest(snapshot, topic):
    num_honest = 0
    honests = set()
    for u, node in snapshot.nodes.items():
        if topic in node:
            actor = node[topic]
            if actor.role == NodeType.PUB or actor.role == NodeType.LURK:
                num_honest += 1
                honests.add(u)

    return num_honest, honests


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
        trans_nodes = defaultdict(set)
        acc_gen_msg = 0
        for u, state in nodes.items():
            for tid, tp in state.trans_record: 
                trans_nodes[tid].add(u)
            acc_gen_msg += state.gen_trans_num
        num_90_msg = 0

        for tid, n in trans_nodes.items():
            if len(n) > 0.9 * num_honest_node:
                num_90_msg += 1

        acc_recv_msg_hist.append(num_90_msg)
        acc_gen_msg_hist.append(acc_gen_msg)
    return acc_recv_msg_hist, acc_gen_msg_hist

def trans_latency_90(snapshots, topic):
    trans_latency = defaultdict(list) # key is transid, value is a list of latency
    snapshot = snapshots[-1]
    nodes = snapshot.nodes
    trans_gen_r = {}
    for u, node in nodes.items():
        if topic in node:
            actor = node[topic] 
            for tid, tp in actor.trans_record.items():
                lat = tp[0] - tp[1] # 
                trans_latency[tid].append((u, lat))
                trans_gen_r[tid] = tp[1]

    num_honest_node, honest_nodes = get_num_honest(snapshots[-1], topic)
    # for tid, latencies in trans_latency.items():
        # if len(latencies) != num_honest_node -1:
            # print('topic', topic, 'Some node does not recv', tid)
            # recved = [a for a,l in latencies] + [tid[0]] #  + sender
            # missing = honest_nodes.difference(set(recved)) 
            # print(missing)
            # sys.exit(1)

    # find 90 percentile
    trans_90_lat = {}
    for tid, latencies in trans_latency.items():
        lats = [l for a, l in latencies]
        sorted_lat = sorted(lats)
        lat90 = sorted_lat[int(len(sorted_lat)*9.0/10.0) - 1]
        trans_90_lat[tid] = lat90
    return trans_90_lat, trans_gen_r


def plot_topics_latency(snapshots, topics):
    topic_latencies = {}
    topic_trans_gen = {}
    for topic in topics:
        components, honest_components = get_components(snapshots, topic)
        # plot_components(axs[0], honest_components)
        topic_latencies[topic], topic_trans_gen[topic] = trans_latency_90(snapshots, topic)
    plot_topic_latency(topic_latencies, topic_trans_gen, topics)

def get_cmap(n, name='hsv'):
    '''Returns a function that maps each index in 0, 1, ..., n-1 to a distinct
    RGB color; the keyword argument name must be a standard mpl colormap name.'''
    return plt.cm.get_cmap(name, n)

def plot_topic_latency(topic_latencies, topic_trans_gen, topics):
    fig, axs = plt.subplots(len(topics))
    topics_data = {}
    publisers = set()
    for topic in topics:
        trans_gen = topic_trans_gen[topic]
        latencies = topic_latencies[topic]
        nodes_data = defaultdict(list)
        for tid, lat in latencies.items():
            gen_time = trans_gen[tid]
            node_id, trans_id = tid
            nodes_data[node_id].append((gen_time, lat))
            publisers.add(node_id)
        topics_data[topic] = nodes_data

    node_color = {}
    for p in publisers:
        node_color[p] = np.random.rand(3,)
    print(node_color) 
    for i in range(len(topics)):
        topic = topics[i]
        nodes_data = topics_data[topic] 
        k = 0
        for u in nodes_data:
            gen_time, lat = zip(*nodes_data[u])
            print('topic', i, 'node', u, gen_time, lat)
            axs[i].bar(list(gen_time), list(lat), label='node '+str(u))
            axs[i].set_title('topic ' + str(i) , fontsize='small')
            axs[i].set_xlabel('round', fontsize='small')
            axs[i].set_ylabel('latency (round)', fontsize='small')
            axs[i].legend(loc='upper right')
            k += 1
        # num_link_patch = mpatches.Patch(color='green', label='num link')
        # num_trans_link_patch = mpatches.Patch(color='blue', label='num link with trans')
        # axs[i].legend(handles=[num_link_patch, num_trans_link_patch])   
    plt.show()



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

def dump_node(snapshots, node_id, data_dir=None):
    pass
    # workbook = xlsxwriter.Workbook(data_dir+'/node{}.xlsx'.format(node_id)) 
    # worksheet = workbook.add_worksheet()
    # bold = workbook.add_format({'bold': True})
    # red = workbook.add_format({'font_color': 'red'})

    # worksheet.write(0, 0, 'Round', bold)
    # peers = {}
    # for snapshot in snapshots:
        # node = snapshot.nodes[node_id]
        # out_conn = node.out_conn
        # out = ''
        # r = snapshot.round
        # worksheet.write(r+1, 0, str(r))
        # nodes = snapshot.nodes.copy()
        # nodes.update(snapshot.sybils)
        # for s in node.scores:
            # if s not in peers:
                # peers[s] = len(peers) + 1
                # peer = nodes[s] 
                # if peer in out_conn:
                    # out = ' out'
                # else:
                    # out =  ''
                # if peer.role == NodeType.PUB: 
                    # worksheet.write(0, peers[s], str(s)+' (PUB)' + out, bold)
                # if peer.role == NodeType.LURK: 
                    # worksheet.write(0, peers[s], str(s)+' (LURK)'+ out, bold)
                # if peer.role == NodeType.SYBIL: 
                    # worksheet.write(0, peers[s], str(s)+' (SYBIL)', bold)
            # if s in node.mesh:
                # worksheet.write(r+1, peers[s], node.scores[s], red)
            # else:
                # worksheet.write(r+1, peers[s], node.scores[s])
    # workbook.close()

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

def profile_node(snapshots, u):
    mesh_hist = []
    for snapshot in snapshots:
        node = snapshot.nodes[u]
        mesh_hist.append(len(node.mesh))
    return mesh_hist

def analyze_network(snapshots):
    num_links_hist = []
    num_links_with_trans_hist = []
    total_num_trans_hist = []
    finished_trans_hist = []
    num_trans_hist = []
    for r in range(len(snapshots)):
        nodes = snapshots[r].nodes
        sybils = snapshots[r].nodes
        network = snapshots[r].network
        trans_nodes = defaultdict(set)

        num_links_hist.append(len(network.links))
        num_links_with_trans = 0
        num_trans = 0
        finished_trans = 0

        for pair, linkshot in network.links.items():
            if linkshot.num_trans > 0:
                num_links_with_trans += 1

            num_trans += linkshot.num_trans
            finished_trans += linkshot.finished_trans
        num_links_with_trans_hist.append(num_links_with_trans)
        num_trans_hist.append(num_trans)
        finished_trans_hist.append(num_links_with_trans)

    return num_links_hist, num_links_with_trans_hist, num_trans_hist, finished_trans_hist

def plot_links_info(ax, num_links_hist, num_links_with_trans_hist):
    ax.plot(num_links_hist, 'g')
    ax.plot(num_links_with_trans_hist, 'b')
    num_link_patch = mpatches.Patch(color='green', label='num link')
    num_trans_link_patch = mpatches.Patch(color='blue', label='num link with trans')
    ax.legend(handles=[num_link_patch, num_trans_link_patch])

def plot_links_trans_info(ax, num_trans_hist, finished_trans_hist):
    ax.plot(num_trans_hist, 'g')
    ax.plot(finished_trans_hist, 'b')
    num_patch = mpatches.Patch(color='green', label='trans in the network')
    finished_patch = mpatches.Patch(color='blue', label='finished trans')
    ax.legend(handles=[num_patch, finished_patch])

def convert_round_to_sec_unit(x):
    return [trans_per_round*ROUND_PER_SEC*TRANS_MSG_LEN for trans_per_round in x]

def plot_avg_throughput(ax, avg_throughput, avg_gen):
    x_points = [ i for i in range(len(avg_throughput))]
    avg_throughput_sec = convert_round_to_sec_unit(avg_throughput)
    avg_gen_sec = convert_round_to_sec_unit(avg_gen)

    ax.plot(x_points, avg_throughput_sec, 'g')
    ax.plot(x_points, avg_gen_sec, 'b')
    ax.set(ylabel='# 90percentile bytes per sec', xlabel='round')
    avg_throughput_patch = mpatches.Patch(color='green', label='avg throughput')
    avg_gen_patch = mpatches.Patch(color='blue', label='avg trans gen rate')
    ax.legend(handles=[avg_throughput_patch, avg_gen_patch])

def plot_graph_deg(ax, degrees_mean, degrees_max, degrees_min):
    ax.plot(degrees_mean, 'b', degrees_max, 'r', degrees_min, 'g') 
    ax.yaxis.set_ticks(range(0, max(degrees_max)+1, 1))
    ax.set(ylabel='node degree')
    max_patch = mpatches.Patch(color='red', label='max')
    min_patch = mpatches.Patch(color='green', label='min')
    mean_patch = mpatches.Patch(color='blue', label='mean')
    ax.legend(handles=[max_patch,min_patch,mean_patch])

def plot_components(ax, honest_components):
     ax.plot(honest_components)
     ax.set(ylabel='# honest components', xlabel='round')

def plot_eclipse_attack(snapshots, targets, topic):
    degrees_mean, degrees_max, degrees_min = get_degrees(snapshots)
    components, honest_components = get_components(snapshots, topic)
    acc_recv_msg_hist, acc_gen_msg_hist = throughput_90(snapshots)
    avg_throughput_hist = avg_throughput(acc_recv_msg_hist, 20)
    avg_gen_hist = avg_throughput(acc_gen_msg_hist, 20)
    eclipse_hist_in, eclipse_hist_out = analyze_eclipse(snapshots, targets[0])
    num_links_hist, num_links_with_trans_hist, num_trans_hist, finished_trans_hist = analyze_network(snapshots)
    mesh_hist_0 = profile_node(snapshots, 0)

    fig, axs = plt.subplots(3)
    

    # print(num_trans_hist)
    plot_components(axs[0], honest_components)
    plot_links_trans_info(axs[1], num_trans_hist, finished_trans_hist)
    # plot_links_info(axs[1], num_links_hist, num_links_with_trans_hist)
    plot_avg_throughput(axs[2], avg_throughput_hist, avg_gen_hist)

    # axs[2].plot(x_points, acc_recv_msg_hist)
    # axs[2].plot(x_points, acc_gen_msg_hist)
    # axs[2].set(ylabel='# 90trans', xlabel='round')
    # axs[2].plot(honest_components)

    # axs[2].plot(finished_trans_hist)
    # axs[2].plot(num_trans_hist)
    # x_points = [ i for i in range(len(degrees_mean))]
    # in_conn = mpatches.Patch(color='green', label='honest incoming connection')
    # out_conn = mpatches.Patch(color='blue', label='honest outgoing connection')
    # axs[1].plot(x_points, eclipse_hist_in, color='green')
    # axs[1].plot(x_points, eclipse_hist_out, color='blue')
    # axs[1].set(ylabel='target node - num honest mesh node', xlabel='round')
    # axs[1].legend(handles=[in_conn, out_conn])



    
    # max_y = max(max(avg_gen_hist), max(avg_throughput_hist))
    # axs[2].yaxis.set_ticks(range(0, int(max_y)+1, 0.5))

    plt.show()


def analyze_snapshot(snapshots):
    degrees_mean, degrees_max, degrees_min = get_degrees(snapshots)
    components, honest_components = get_components(snapshots)
    acc_recv_msg_hist, acc_gen_msg_hist = throughput_90(snapshots)
    latency_hist = latency(acc_recv_msg_hist, acc_gen_msg_hist)
    avg_throughput_hist = avg_throughput(acc_recv_msg_hist, 20)
    avg_gen_hist = avg_throughput(acc_gen_msg_hist, 20)

    fig, axs = plt.subplots(3)
    
    axs[0].plot(degrees_mean, 'b', degrees_max, 'r', degrees_min, 'g')
    axs[0].set(ylabel='node degree')
    max_patch = mpatches.Patch(color='red', label='max')
    min_patch = mpatches.Patch(color='green', label='min')
    mean_patch = mpatches.Patch(color='blue', label='mean')
    axs[0].legend(handles=[max_patch,min_patch,mean_patch])
    #axs[0].title.set_text("cumulative freeze")   
    
    target = 1
    eclipse_hist_in, eclipse_hist_out = analyze_eclipse(snapshots, target)
    
    # number of connectted component
    x_points = [ i for i in range(len(degrees_mean))]
    axs[1].plot(x_points, eclipse_hist_in, color='green')
    axs[1].plot(x_points, eclipse_hist_out, color='blue')
    axs[1].set(ylabel='target node - num honest mesh node', xlabel='round')
    in_conn = mpatches.Patch(color='green', label='honest incoming connection')
    out_conn = mpatches.Patch(color='blue', label='honest outgoing connection')
    axs[1].legend(handles=[in_conn, out_conn])


    
    axs[2].plot(x_points, honest_components)
    axs[2].set(ylabel='# honest components', xlabel='round')

    # x_points = [ i for i in range(len(acc_recv_msg_hist))]
    # axs[3].plot(x_points, acc_recv_msg_hist)
    # axs[3].plot(x_points, acc_gen_msg_hist)
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

def visualize_network(nodes, draw_nodes='all'):
    subset_color = {NodeType.PUB: 'limegreen', NodeType.LURK: 'yellow', NodeType.SYBIL: 'red'}
    pub_patch = mpatches.Patch(color='limegreen', label='PUB')
    lurk_patch = mpatches.Patch(color='yellow', label='LURK')
    sybil_patch = mpatches.Patch(color='red', label='SYBIL')

    color = []
    G = nx.Graph()
    for node in nodes:
        G.add_node(node)
        color.append(subset_color[nodes[node].role])
    for node in nodes:
        for m in nodes[node].mesh:
            if node in nodes[m].mesh:
                G.add_edge(node, m)

    plt.figure(num=0, figsize=(24, 12), dpi=80, facecolor='w', edgecolor='k')
    nx.draw(G, node_color=color, with_labels=True, edgecolors='black')
    plt.legend(handles=[pub_patch, lurk_patch, sybil_patch])

    if draw_nodes != 'all':
        table_data = [['Node', 'Out Msgs (id, src)']]
        color = []
        G = nx.Graph()
        edge_labels = {}
        fig = plt.figure(num=1, figsize=(24, 12), dpi=80, facecolor='w', edgecolor='k')
        for node in draw_nodes:
            row_data = [node]
            if not G.has_node(node):
                G.add_node(node)
                color.append(subset_color[nodes[node].role])
            for m in nodes[node].mesh:
                if not G.has_node(m):
                    G.add_node(m)
                    color.append(subset_color[nodes[m].role])
                edge_labels[(node, m)] = round(nodes[node].scores[m], 3)
                G.add_edge(node, m)
	    
            out_msgs = ''
            for msg in nodes[node].out_msgs:
                out_msgs += '({},{}) '.format(msg.id, msg.src)
            if out_msgs == '':
                out_msgs = 'None'
            row_data.append(out_msgs)
            table_data.append(row_data)

        pos = nx.spring_layout(G)
        nx.draw(G,pos,node_color=color, with_labels=True, edgecolors='black')
        nx.draw_networkx_edge_labels(G,pos,edge_labels=edge_labels,label_pos=0.7,font_size=7)
        plt.legend(handles=[pub_patch, lurk_patch, sybil_patch])

        table = plt.table(cellText=table_data, colWidths=[0.02, 0.06], loc='upper left')
        table.set_fontsize(8)
        #  table.scale(1,4)
        # table.axis('off')

    plt.show()

   
def print_node(t, node, sybils, nodes):
    is_eclipsed = True 
    for peer in node.mesh:
        if peer not in sybils:
            is_eclipsed = False 

    if not is_eclipsed:
        print("\t\tTargeted")
    else:
        print("\t\tEclipsed")

    print('id         ', t)
    print('num mesh   ', len(node.mesh))
    print('role       ', node.role)
    # print('num in msg ', len(node.num_in_msg))
    # print('num out msg', len(node.num_out_msg))

    for peer in node.mesh:
        score = round(node.scores[peer], 2)
        sd = node.scores_decompose[peer]
        data = "peer {peer}: {score} = {p1} {p2} {p3a} {p3b} {p4} {p5} {p6}".format(
            peer=peer,
            score=score,
            p1=sd.p1, p2=sd.p2, p3a=sd.p3a, p3b=sd.p3b, p4=sd.p4, p5=sd.p5, p6=sd.p6)

        is_targeted = False
        if peer in nodes:
            for v in nodes[peer].mesh:
                if v in sybils:
                    is_targeted = True
            if not is_targeted:
                print(data)
            else:
                print("\033[93m" + data + "\033[0m")
        else:
            print("\033[91m" + data + "\033[0m")

# last snapshot
def print_target_info(snapshot, targets):
    nodes = snapshot.nodes
    sybils = snapshot.sybils
    print("\t Round", snapshot.round)
    for t in targets:
        print_node(t, nodes[t], sybils, nodes)


def print_sybil(u, sybil):
    print("id {sybil_id}, role {role}, s-mesh {s_mesh}, attempts {attempts}, channels {channels}".format(
        sybil_id=u, 
        role=sybil.attack_method, 
        s_mesh=sybil.secured_mesh, 
        attempts=sybil.attempts, 
        channels=sybil.channels))

def print_sybils(snapshot, adversary):
    sybils = snapshot.sybils
    avail_channels = []
    for c in adversary.avail_channel:
        avail_channels.append(c.node)
    
    print("\t\tSybils  ", "Round", snapshot.round, "  avail channel", avail_channels)
    for u, sybil in sybils.items():
        print_sybil(u, sybil)

def get_eclipsed_target(snapshots, targets):
    hist = []
    for snapshot in snapshots:
        eclipsed = set()
        nodes = snapshot.nodes
        for t in targets:
            is_eclipsed = True
            for peer in nodes[t].mesh:
                if peer not in snapshot.sybils:
                    is_eclipsed = False
            if is_eclipsed:
                eclipsed.add(t)
        hist.append(eclipsed)
    return hist

def get_eclipsed_ratio(snapshots, targets):
    hist = []
    for snapshot in snapshots:
        num_eclipsed = 0
        num_mesh = 0
        nodes = snapshot.nodes
        for t in targets:
            for peer in nodes[t].mesh:
                num_mesh += 1
                if peer in snapshot.sybils:
                    num_eclipsed += 1

        
        hist.append(float(num_eclipsed)/num_mesh)
    return hist


def write_eclipse_list(data, filename, dirname):
    filepath = dirname + '/' + filename
    with open(filepath, 'w') as w:
        for i, j in enumerate(data):
            w.write(str(i) + " " + str(len(j)) + "\n ")

def plot_summery(snapshots, data, data1, filename, dirname, num_targets):
    num_eclipsed_list = [len(i) for i in data]
    fig, axs = plt.subplots(4)
    
    filepath = dirname + '/' + filename
    axs[0].plot(num_eclipsed_list)
    # title_txt = 'number eclipsed out of ' + str(num_targets) + ' with ' + filename
    # axs[0].set_title(title_txt, size='small')  
    # axs[0].set_xlabel('round', fontsize='small')
    axs[0].set_ylabel('# eclipsed')
    axs[0].axes.xaxis.set_ticklabels([])
    axs[1].plot(data1)
    title_txt = 'ratio peer eclipsed out of ' + str(num_targets) + ' with ' + filename
    # axs[1].set_xlabel('round', fontsize='small')
    axs[1].set_ylabel('ratio eclipsed')
    # axs[1].set_title(title_txt, size='small')  
    axs[1].axes.xaxis.set_ticklabels([])

    freeze_hist = []
    prev_freeze_count = 0
    for snapshot in snapshots:
        network = snapshot.network
        curr_round_freeze_count = network.freeze_count - prev_freeze_count
        freeze_hist.append(curr_round_freeze_count)
        prev_freeze_count = network.freeze_count

    accumulate = [0]
    acc = 0
    for i in freeze_hist:
        acc += i
        accumulate.append(acc)

    axs[2].plot(accumulate)
    # axs[2].set_xlabel('round', fontsize='small')
    axs[2].set_ylabel('total # freeze')
    # axs[2].set_title("cumulative freeze", size='small')   
    axs[2].axes.xaxis.set_ticklabels([])

    axs[3].plot(freeze_hist)
    axs[3].set_ylabel('# freeze')
    axs[3].set_xlabel('round')
    # axs[3].set_title("number freeze per round", size='small')   

    plt.tight_layout()
    plt.show()
    fig.savefig(filepath)

def plot_eclipse_list(data, data1, filename, dirname, num_targets):
    num_eclipsed_list = [len(i) for i in data]
    fig, axs = plt.subplots(2)
    
    filepath = dirname + '/' + filename
    axs[0].plot(num_eclipsed_list)
    title_txt = 'number eclipsed out of ' + str(num_targets) + ' with ' + filename
    axs[0].title.set_text(title_txt)  
    axs[1].plot(data1)
    title_txt = 'ratio peer eclipsed out of ' + str(num_targets) + ' with ' + filename
    axs[1].title.set_text(title_txt)  
    plt.tight_layout()
    plt.show()
    fig.savefig(filepath)

def plot_eclipse_ratio_list(data, filename, dirname, num_targets):
    fig, ax = plt.subplots(1)
    filepath = dirname + '/' + filename
    ax.plot(data)
    title_txt = 'ratio peer eclipsed out of ' + str(num_targets) + ' with ' + filename
    ax.title.set_text(title_txt)  
    plt.show()
    plt.savefig(filepath)

def analyze_freezer(snapshots):
    freeze_hist = []
    prev_freeze_count = 0
    for snapshot in snapshots:
        network = snapshot.network
        curr_round_freeze_count = network.freeze_count - prev_freeze_count
        freeze_hist.append(curr_round_freeze_count)
        prev_freeze_count = network.freeze_count


    accumulate = [0]
    acc = 0
    for i in freeze_hist:
        acc += i
        accumulate.append(acc)
    
    print(accumulate[-1])

    # fig, axs = plt.subplots(2)
    
    # axs[0].plot(accumulate)
    # axs[0].set(ylabel='total # freeze', xlabel='round')
    # axs[0].title.set_text("cumulative freeze")   

    # axs[1].plot(freeze_hist)
    # axs[1].set(ylabel='# freeze in each round', xlabel='round')
    # axs[1].title.set_text("number freeze per round")   
    # plt.tight_layout()
    # plt.show()

