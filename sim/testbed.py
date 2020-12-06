#!/usr/bin/env python
import sys
import os
from experiment import Experiment
from config import *
import analyzer
import generate_network as gn
import random
random.seed(31)

if len(sys.argv) < 2:
    print("require subcommand: run, gen-network\n")
    print("run json epoch[int]")
    print("gen-network num_pub[int] num_lurk[int] num_sybil[int] is_cold_boot[y/n] init_peer_num[int] down_mean[float] down_std[float] up_mean[float] up_std[float] interval_sec[float]") 
    print('exmaple: ./testbed.py run topo/one_pub.json 100')
    print('exmaple: ./testbed.py gen-network 10 90 0 n 20 1000000 0 1000000 0 0.5 > ten_pub.json')
    sys.exit()

cmd = sys.argv[1]
if cmd == "gen-network":
    if len(sys.argv) < 10:
        print("require arguments")
        sys.exit(0)
    n_pub = int(sys.argv[2])
    n_lurk = int(sys.argv[3])
    n_sybil = int(sys.argv[4])
    is_cold_boot = sys.argv[5] == 'y'
    init_peer_num =  int(sys.argv[6])
    down_mean = float(sys.argv[7])
    down_std = float(sys.argv[8])
    up_mean = float(sys.argv[9])
    up_std = float(sys.argv[10])
    prob = float(sys.argv[11])
    gn.generate_network(
        is_cold_boot,
        init_peer_num,
        n_pub, n_lurk, n_sybil,
        down_mean, down_std,
        up_mean, up_std,
        prob
        )
elif cmd == "run":
    if len(sys.argv) < 3:
        print("require arguments")
        sys.exit(0)
    setup = sys.argv[2]
    epoch = int(sys.argv[3])
    heartbeat = HEARTBEAT
    gossipsub = Experiment(setup, heartbeat)
    snapshots = gossipsub.start(epoch)
    analyzer.plot_eclipse_attack(snapshots, [1])
    print("start analyze")
    # analyze_network(snapshots)
    # analyze_snapshot(snapshots)
    # dump_graph(snapshots[50])
    # kdump_node(snapshots, 1)
    # dump_node(snapshots, 99)
else:
    print('Require a valid subcommand', cmd)



