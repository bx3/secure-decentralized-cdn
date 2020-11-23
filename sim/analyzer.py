#!/usr/bin/env python
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from config import *

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
        component, honest_component = count_components(snapshot.nodes)
        components.append(component)
        honest_components.append(honest_component)

    return components, honest_components

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
            f.write('{}({}),'.format(s, node.scores[s].get_score()))
        f.write('\n')
    f.close()

def analyze_snapshot(snapshots):
    degrees_mean, degrees_max, degrees_min = get_degrees(snapshots)
    components, honest_components = get_components(snapshots)

    fig, axs = plt.subplots(3)
    
    axs[0].plot(degrees_mean, 'b', degrees_max, 'r', degrees_min, 'g')
    axs[0].set(ylabel='node degree')
    max_patch = mpatches.Patch(color='red', label='max')
    min_patch = mpatches.Patch(color='green', label='min')
    mean_patch = mpatches.Patch(color='blue', label='mean')
    axs[0].legend(handles=[max_patch,min_patch,mean_patch])
    
    # number of connectted component
    x_points = [ i for i in range(len(degrees_mean))]
    #axs[1].set_yscale('log')
    axs[1].plot(x_points, components)
    axs[1].set(ylabel='# components', xlabel='round')
    
    axs[2].plot(x_points, honest_components)
    axs[2].set(ylabel='# honest components', xlabel='round')

    plt.show()

    #dump_graph(snapshots[50])



